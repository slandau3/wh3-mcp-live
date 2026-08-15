"""Recruitable lord/hero trait tools (the background skill choices shown when hiring)."""
import json
from mcp.server.fastmcp import FastMCP
from db import load_tsv
from config import WH3_DUMP_DIR

_cache = None


def _load_lord_db() -> dict:
    global _cache
    if _cache is not None:
        return _cache

    db_dir = WH3_DUMP_DIR / "db"

    skills = load_tsv(db_dir / "character_skills_tables" / "data__.tsv")
    nodes = load_tsv(db_dir / "character_skill_nodes_tables" / "data__.tsv")
    node_sets = load_tsv(db_dir / "character_skill_node_sets_tables" / "data__.tsv")
    set_items = load_tsv(db_dir / "character_skill_node_set_items_tables" / "data__.tsv")
    effects = load_tsv(db_dir / "character_skill_level_to_effects_junctions_tables" / "data__.tsv")

    skills_by_key = {}
    for s in skills:
        key = s.get("key", "")
        if key:
            skills_by_key[key] = {
                "key": key,
                "name": s.get("localised_name", ""),
                "description": s.get("localised_description", ""),
                "is_background": s.get("is_background_skill", "") == "true",
                "background_weighting": s.get("background_weighting", ""),
            }

    nodes_by_key = {}
    for n in nodes:
        key = n.get("key", "")
        if key:
            nodes_by_key[key] = {
                "skill_key": n.get("character_skill_key", ""),
                "faction_key": n.get("faction_key", ""),
                "indent": n.get("indent", ""),
                "tier": n.get("tier", ""),
            }

    set_to_items = {}
    for si in set_items:
        set_key = si.get("set", "")
        item = si.get("item", "")
        if set_key and item:
            if set_key not in set_to_items:
                set_to_items[set_key] = set()
            set_to_items[set_key].add(item)

    set_to_subtype = {}
    for ns in node_sets:
        set_key = ns.get("key", "")
        subtype = ns.get("agent_subtype_key", "")
        if set_key and subtype:
            set_to_subtype[set_key] = subtype

    effects_by_skill = {}
    for e in effects:
        sk = e.get("character_skill_key", "")
        if sk:
            if sk not in effects_by_skill:
                effects_by_skill[sk] = []
            effects_by_skill[sk].append({
                "effect": e.get("effect_key", ""),
                "level": e.get("level", ""),
                "scope": e.get("effect_scope", ""),
                "value": e.get("value", ""),
            })

    _cache = {
        "skills_by_key": skills_by_key,
        "nodes_by_key": nodes_by_key,
        "set_to_items": set_to_items,
        "set_to_subtype": set_to_subtype,
        "effects_by_skill": effects_by_skill,
    }
    return _cache


def _background_traits_for_subtype(subtype: str) -> list:
    """Return all recruitable (background) traits available to a given agent subtype."""
    db = _load_lord_db()
    result = []
    for set_key, sub in db["set_to_subtype"].items():
        if sub != subtype:
            continue
        for nk in db["set_to_items"].get(set_key, set()):
            node = db["nodes_by_key"].get(nk)
            if not node:
                continue
            skill = db["skills_by_key"].get(node["skill_key"], {})
            if not skill.get("is_background"):
                continue
            result.append({
                "node_key": nk,
                "trait": skill.get("name", ""),
                "description": skill.get("description", ""),
                "background_weighting": skill.get("background_weighting", ""),
                "effects": db["effects_by_skill"].get(node["skill_key"], []),
            })
    return result


def register(mcp: FastMCP):

    @mcp.tool()
    def get_lord_traits(character_key: str) -> str:
        """List recruitable lord/hero trait options (the background skill choices shown when hiring).

        Args:
            character_key: Character subtype key (e.g. "wh3_main_ksl_boyar")
                           or partial match (e.g. "boyar", "ataman", "patriarch")
        """
        db = _load_lord_db()

        subtypes = set()
        for set_key, sub in db["set_to_subtype"].items():
            if character_key.lower() in sub.lower() or character_key.lower() in set_key.lower():
                subtypes.add(sub)

        if not subtypes:
            return json.dumps({"error": f"No lord/hero subtype found for '{character_key}'"})

        results = []
        for sub in sorted(subtypes):
            traits = _background_traits_for_subtype(sub)
            results.append({
                "subtype": sub,
                "num_traits": len(traits),
                "traits": traits,
            })

        return json.dumps(results, indent=2)

    @mcp.tool()
    def list_lord_subtypes() -> str:
        """List all recruitable lord/hero subtypes that have trait (background skill) choices."""
        db = _load_lord_db()

        subtypes = {}
        for set_key, sub in db["set_to_subtype"].items():
            traits = _background_traits_for_subtype(sub)
            if traits:
                subtypes[sub] = [t["trait"] for t in traits]

        return json.dumps(subtypes, indent=2)
