"""Building database tools."""
import json
from mcp.server.fastmcp import FastMCP
from db import load_tsv
from config import WH3_DUMP_DIR

_cache = None


def _load_building_db() -> dict:
    global _cache
    if _cache is not None:
        return _cache

    db = WH3_DUMP_DIR / "db"
    text = WH3_DUMP_DIR / "text" / "db"

    chains = load_tsv(db / "building_chains_tables" / "data__.tsv")
    levels = load_tsv(db / "building_levels_tables" / "data__.tsv")
    effects = load_tsv(db / "building_effects_junction_tables" / "data__.tsv")
    units_allowed = load_tsv(db / "building_units_allowed_tables" / "data__.tsv")

    chain_loc = {}
    for row in load_tsv(text / "building_chains__.loc.tsv"):
        key = row.get("key", "")
        val = row.get("text", "")
        if "building_chains_chain_tooltip_" in key:
            chain_loc[key.replace("building_chains_chain_tooltip_", "")] = val

    # Load localized building level names
    level_loc = {}
    for row in load_tsv(text / "building_culture_variants__.loc.tsv"):
        key = row.get("key", "")
        val = row.get("text", "")
        if key.startswith("building_culture_variants_name_"):
            suffix = key[len("building_culture_variants_name_"):]
            level_loc[suffix] = val

    # Build level_name → culture key mapping from variants table
    level_culture_names = {}
    for row in load_tsv(db / "building_culture_variants_tables" / "data__.tsv"):
        building = row.get("building", "")
        culture = row.get("culture", "")
        if building and culture:
            loc_key = building + culture
            if loc_key in level_loc:
                # Prefer Cathay names for Cathay buildings, etc.
                if building not in level_culture_names:
                    level_culture_names[building] = level_loc[loc_key]
        elif building and not culture and not row.get("faction", ""):
            # Generic (no culture, no faction)
            if building in level_loc:
                if building not in level_culture_names:
                    level_culture_names[building] = level_loc[building]

    chains_by_key = {}
    for c in chains:
        chains_by_key[c["key"]] = {
            "key": c["key"],
            "category": c.get("chain_category", ""),
            "superchain": c.get("building_superchain", ""),
            "sort_order": c.get("optional_sort_order", ""),
            "can_be_dismantled": c.get("can_be_dismantled", "") == "true",
            "display_name": chain_loc.get(c["key"], c["key"]),
            "levels": [],
        }

    for lv in levels:
        lname = lv.get("level_name", "")
        chain_key = lv.get("chain", "")
        if chain_key not in chains_by_key:
            continue
        chains_by_key[chain_key]["levels"].append({
            "level_name": lname,
            "display_name": level_culture_names.get(lname, lname),
            "tier": lv.get("level", ""),
            "create_time": lv.get("create_time", ""),
            "create_cost": lv.get("create_cost", ""),
            "upkeep_cost": lv.get("upkeep_cost", ""),
            "only_in_capital": lv.get("only_in_capital", "") == "true",
            "faction_unique": lv.get("faction_unique", "") == "true",
            "can_convert": lv.get("can_convert", "") == "true",
            "development_point_cost": lv.get("development_point_cost", "0"),
            "visible_in_ui": lv.get("visible_in_ui", "") == "true",
            "effects": [],
        })

    for eff in effects:
        building = eff.get("building", "")
        for chain in chains_by_key.values():
            for lv in chain["levels"]:
                if lv["level_name"] == building:
                    lv["effects"].append({
                        "effect": eff.get("effect", ""),
                        "scope": eff.get("context_requirement", "") or eff.get("effect_scope", ""),
                        "value": eff.get("value", ""),
                        "value_damaged": eff.get("value_damaged", ""),
                        "value_ruined": eff.get("value_ruined", ""),
                    })

    for ua in units_allowed:
        building = ua.get("building", "")
        for chain in chains_by_key.values():
            for lv in chain["levels"]:
                if lv["level_name"] == building:
                    if "recruits" not in lv:
                        lv["recruits"] = []
                    lv["recruits"].append({
                        "unit": ua.get("unit", ""),
                        "xp": ua.get("XP", "0"),
                        "faction": ua.get("faction", ""),
                    })

    _cache = chains_by_key
    return _cache


def _chain_specificity(key: str) -> int:
    """Lower score = more specific. Capital/city chains rank above generic."""
    k = key.lower()
    if "_city_" in k or "_special_" in k:
        return 0
    if "_prologue_" in k:
        return 2
    return 1


def register(mcp: FastMCP):

    @mcp.tool()
    def get_building_detail(building_key: str) -> str:
        """Get full building detail: all levels, costs, effects from WH3 game data.

        Args:
            building_key: Building chain key (e.g. "wh3_prologue_building_ksl_barracks")
                          or partial match (e.g. "ksl_barracks")
        """
        db = _load_building_db()
        q = building_key.lower()
        matches = [(k, v) for k, v in db.items() if q in k.lower()]
        if not matches:
            if building_key in db:
                return json.dumps(db[building_key], indent=2)
            return json.dumps({"error": f"Building '{building_key}' not found", "available_chains": list(db.keys())[:30]})
        matches.sort(key=lambda kv: (_chain_specificity(kv[0]), len(kv[0])))
        best_key, best_val = matches[0]
        if len(matches) == 1:
            return json.dumps(best_val, indent=2)
        others = [k for k, _ in matches[1:]]
        result = dict(best_val)
        result["_also_matched"] = others[:10]
        return json.dumps(result, indent=2)

    @mcp.tool()
    def list_buildings(category: str = "", offset: int = 0, limit: int = 30) -> str:
        """List all building chains, optionally filtered by category (money/military).

        Args:
            category: Optional filter: "money" or "military"
            offset: Pagination offset (default 0)
            limit: Max results to return (default 30, max 100)
        """
        db = _load_building_db()
        result = []
        for key, val in db.items():
            if category and val.get("category") != category:
                continue
            entry = {
                "key": val["key"],
                "display_name": val["display_name"],
                "category": val["category"],
                "num_levels": len(val["levels"]),
            }
            if _chain_specificity(key) == 0:
                entry["settlement"] = "capital"
            result.append(entry)
        total = len(result)
        result = result[offset:offset + min(limit, 100)]
        return json.dumps({"total": total, "offset": offset, "count": len(result), "buildings": result}, indent=2)
