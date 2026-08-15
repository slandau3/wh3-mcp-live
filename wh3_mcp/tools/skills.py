"""Character skill tree tools."""
import json
from mcp.server.fastmcp import FastMCP
from db import load_tsv
from config import WH3_DUMP_DIR

_cache = None


def _load_skill_db() -> dict:
    global _cache
    if _cache is not None:
        return _cache

    db_dir = WH3_DUMP_DIR / "db"

    skills = load_tsv(db_dir / "character_skills_tables" / "data__.tsv")
    nodes = load_tsv(db_dir / "character_skill_nodes_tables" / "data__.tsv")
    node_sets = load_tsv(db_dir / "character_skill_node_sets_tables" / "data__.tsv")
    set_items = load_tsv(db_dir / "character_skill_node_set_items_tables" / "data__.tsv")
    links = load_tsv(db_dir / "character_skill_node_links_tables" / "data__.tsv")
    effects = load_tsv(db_dir / "character_skill_level_to_effects_junctions_tables" / "data__.tsv")
    level_details = load_tsv(db_dir / "character_skill_level_details_tables" / "data__.tsv")

    # Build rank lookup from level_details (level=1 = minimum rank to unlock)
    rank_by_skill = {}
    for d in level_details:
        if d.get("level", "") == "1":
            sk = d.get("skill_key", "")
            rank = d.get("unlocked_at_rank", "0")
            if sk:
                rank_by_skill[sk] = rank

    skills_by_key = {}
    for s in skills:
        key = s.get("key", "")
        if key:
            skills_by_key[key] = {
                "key": key,
                "name": s.get("localised_name", ""),
                "description": s.get("localised_description", ""),
                "unlocked_at_rank": s.get("unlocked_at_rank", ""),
                "is_background": s.get("is_background_skill", "") == "true",
            }

    nodes_by_key = {}
    for n in nodes:
        key = n.get("key", "")
        if key:
            sk = n.get("character_skill_key", "")
            nodes_by_key[key] = {
                "skill_key": sk,
                "faction_key": n.get("faction_key", ""),
                "subculture": n.get("subculture", ""),
                "tier": n.get("tier", ""),
                "indent": n.get("indent", ""),
                "required_parents": n.get("required_num_parents", "0"),
                "visible": n.get("visible_in_ui", "") == "true",
                "unlocked_at_rank": rank_by_skill.get(sk, n.get("tier", "0")),
            }

    children_to_parents = {}
    for l in links:
        child = l.get("child_key", "")
        parent = l.get("parent_key", "")
        if child and parent:
            if child not in children_to_parents:
                children_to_parents[child] = []
            children_to_parents[child].append(parent)

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

    _cache = {
        "skills_by_key": skills_by_key,
        "nodes_by_key": nodes_by_key,
        "children_to_parents": children_to_parents,
        "effects_by_skill": effects_by_skill,
        "set_to_items": set_to_items,
        "set_to_subtype": set_to_subtype,
    }
    return _cache


def register(mcp: FastMCP):

    @mcp.tool()
    def get_skill_tree(character_key: str, category: str = "", indent: int = -1, summary: bool = False) -> str:
        """Look up character skill tree from WH3 game data.

        Args:
            character_key: Character subtype key (e.g. "wh3_main_kis_katarin")
                           or partial match
            category: Filter by category prefix (army, magic, combat, campaign, unique, generic, innate)
            indent: Filter by indent level (0=root, 1-5=tiers, 6=capstone, 99=background)
            summary: If true, return only name + tier + indent (skip effects/descriptions)
        """
        db = _load_skill_db()

        matching = [
            (sk, sub) for sk, sub in db["set_to_subtype"].items()
            if character_key.lower() in sub.lower() or character_key.lower() in sk.lower()
        ]

        if not matching:
            return json.dumps({"error": f"No skill tree found for '{character_key}'"})

        results = []
        for set_key, subtype in matching[:5]:
            node_keys = db["set_to_items"].get(set_key, set())

            skill_nodes = []
            for nk in node_keys:
                if category and category.lower() not in nk.lower():
                    continue
                node = db["nodes_by_key"].get(nk)
                if not node:
                    continue
                if indent >= 0 and node.get("indent", "") != str(indent):
                    continue
                skill = db["skills_by_key"].get(node["skill_key"], {})
                if summary:
                    skill_nodes.append({
                        "node_key": nk,
                        "name": skill.get("name", ""),
                        "tier": node["tier"],
                        "indent": node["indent"],
                    })
                else:
                    skill_nodes.append({
                        "node_key": nk,
                        "name": skill.get("name", ""),
                        "description": skill.get("description", ""),
                        "tier": node["tier"],
                        "indent": node["indent"],
                        "unlocked_at_rank": node.get("unlocked_at_rank", "0"),
                        "is_background": skill.get("is_background", False),
                        "effects": db["effects_by_skill"].get(node["skill_key"], []),
                    })

            results.append({
                "subtype": subtype,
                "set_key": set_key,
                "num_skills": len(skill_nodes),
                "skills": skill_nodes,
            })

        return json.dumps(results, indent=2)
