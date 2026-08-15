"""Unit database tools."""
import json
from mcp.server.fastmcp import FastMCP
from db import load_tsv
from config import WH3_DUMP_DIR

_cache = None


def _load_unit_db() -> dict:
    global _cache
    if _cache is not None:
        return _cache

    db = WH3_DUMP_DIR / "db"
    text = WH3_DUMP_DIR / "text" / "db"

    units = load_tsv(db / "land_units_tables" / "data__.tsv")

    unit_loc = {}
    for row in load_tsv(text / "unit_description_short_texts__.loc.tsv"):
        key = row.get("key", "")
        val = row.get("text", "")
        if "unit_description_short_texts_text_" in key:
            unit_loc[key.replace("unit_description_short_texts_text_", "")] = val

    units_by_key = {}
    for u in units:
        key = u.get("key", "")
        if not key:
            continue
        units_by_key[key] = {
            "key": key,
            "category": u.get("category", ""),
            "class": u.get("class", ""),
            "armour": u.get("armour", ""),
            "melee_attack": u.get("melee_attack", ""),
            "melee_defence": u.get("melee_defence", ""),
            "charge_bonus": u.get("charge_bonus", ""),
            "morale": u.get("morale", ""),
            "accuracy": u.get("accuracy", ""),
            "primary_ammo": u.get("primary_ammo", ""),
            "secondary_ammo": u.get("secondary_ammo", ""),
            "mount": u.get("mount", ""),
            "shield": u.get("shield", ""),
            "primary_melee_weapon": u.get("primary_melee_weapon", ""),
            "primary_missile_weapon": u.get("primary_missile_weapon", ""),
            "description": unit_loc.get(key, ""),
        }

    _cache = units_by_key
    return _cache


def register(mcp: FastMCP):

    @mcp.tool()
    def get_unit_stats(unit_key: str) -> str:
        """Look up unit stats from WH3 game data.

        Args:
            unit_key: Unit key (e.g. "wh3_main_pro_ksl_inf_kossars_0") or partial match
        """
        db = _load_unit_db()
        if unit_key in db:
            return json.dumps(db[unit_key], indent=2)
        matches = [v for k, v in db.items() if unit_key.lower() in k.lower()]
        if matches:
            return json.dumps(matches[:20], indent=2)
        return json.dumps({"error": f"Unit '{unit_key}' not found"})
