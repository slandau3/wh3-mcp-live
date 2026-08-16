"""Edict/Commandment database tools."""
import json
from mcp.server.fastmcp import FastMCP
from db import load_tsv
from config import WH3_DUMP_DIR
from state import read_factions

_cache = None

# Faction key -> subculture mapping
FACTION_SUBCULTURE = {
    "wh3_main_ksl_the_ice_court": "wh3_main_sc_ksl_kislev",
    "wh3_main_ksl_the_great_orthodoxy": "wh3_main_sc_ksl_kislev",
    "wh3_main_ksl_brotherhood_of_the_bear": "wh3_main_sc_ksl_kislev",
    "wh3_main_cth_the_northern_provinces": "wh3_main_sc_cth_cathay",
    "wh3_main_cth_the_western_provinces": "wh3_main_sc_cth_cathay",
    "wh3_main_kho_exiles_of_khorne": "wh3_main_sc_kho_khorne",
    "wh3_main_nur_poxmakers_of_nurgle": "wh3_main_sc_nur_nurgle",
    "wh3_main_tze_oracles_of_tzeentch": "wh3_main_sc_tze_tzeentch",
    "wh3_main_sla_seducers_of_slaanesh": "wh3_main_sc_sla_slaanesh",
    "wh_main_emp_empire": "wh_main_sc_emp_empire",
    "wh_main_dwf_dwarfs": "wh_main_sc_dwf_dwarfs",
    "wh_main_grn_greenskins": "wh_main_sc_grn_greenskins",
    "wh_main_vmp_vampire_counts": "wh_main_sc_vmp_vampire_counts",
    "wh_main_brt_bretonnia": "wh_main_sc_brt_bretonnia",
}


def _load_edict_db() -> dict:
    global _cache
    if _cache is not None:
        return _cache

    db = WH3_DUMP_DIR / "db"
    text = WH3_DUMP_DIR / "text" / "db"

    records = load_tsv(db / "provincial_initiative_records_tables" / "data__.tsv")
    subculture_map = load_tsv(db / "provincial_initiatives_to_subculture_junctions_tables" / "data__.tsv")
    effects = load_tsv(db / "effect_bundles_to_effects_junctions_tables" / "data__.tsv")

    # Localization
    edict_loc = {}
    for row in load_tsv(text / "provincial_initiative_records__.loc.tsv"):
        key = row.get("key", "")
        val = row.get("text", "")
        if key and val:
            # Keys are like "provincial_initiative_records_localised_name_<edict_key>"
            if "provincial_initiative_records_localised_name_" in key:
                edict_key = key.replace("provincial_initiative_records_localised_name_", "")
                edict_loc[edict_key] = val

    # Build edict records
    edicts_by_key = {}
    for r in records:
        key = r.get("key", "")
        if not key:
            continue
        edicts_by_key[key] = {
            "key": key,
            "effect_bundle": r.get("effect_bundle", ""),
            "icon": r.get("icon_path", ""),
            "display_name": edict_loc.get(key, key),
            "effects": [],
        }

    # Add effects from effect bundles
    for e in effects:
        bundle = e.get("effect_bundle_key", "")
        for edict_key, edict in edicts_by_key.items():
            if edict["effect_bundle"] == bundle:
                edict["effects"].append({
                    "effect": e.get("effect_key", ""),
                    "scope": e.get("effect_scope", ""),
                    "value": e.get("value", ""),
                })

    # Build subculture -> edicts mapping
    subculture_edicts = {}
    faction_edicts = {}
    for row in subculture_map:
        edict_key = row.get("provincial_initiative_key", "")
        subculture = row.get("subculture", "")
        faction = row.get("faction", "")
        if edict_key and subculture:
            if subculture not in subculture_edicts:
                subculture_edicts[subculture] = []
            subculture_edicts[subculture].append(edict_key)
        if edict_key and faction:
            if faction not in faction_edicts:
                faction_edicts[faction] = []
            faction_edicts[faction].append(edict_key)

    _cache = {
        "edicts": edicts_by_key,
        "subculture_edicts": subculture_edicts,
        "faction_edicts": faction_edicts,
    }
    return _cache


def register(mcp: FastMCP):

    @mcp.tool()
    def get_available_edicts(faction_key: str) -> str:
        """Get available edicts/commandments for a faction.

        Args:
            faction_key: Faction key (e.g. "wh3_main_ksl_the_ice_court")
        """
        db = _load_edict_db()
        # Prefer the live-dumped subculture; fall back to the static map
        subculture = ""
        for f in read_factions():
            if f.get("key") == faction_key:
                subculture = f.get("subculture", "") or ""
                break
        if not subculture:
            subculture = FACTION_SUBCULTURE.get(faction_key, "")

        # Get edicts for this faction (by faction key or subculture)
        available_keys = set()
        if faction_key in db["faction_edicts"]:
            available_keys.update(db["faction_edicts"][faction_key])
        if subculture in db["subculture_edicts"]:
            available_keys.update(db["subculture_edicts"][subculture])

        # Build result with full edict data
        available = []
        for key in sorted(available_keys):
            edict = db["edicts"].get(key)
            if edict:
                available.append(edict)

        return json.dumps({
            "faction": faction_key,
            "subculture": subculture,
            "count": len(available),
            "edicts": available,
        }, indent=2)

    @mcp.tool()
    def get_edict_detail(edict_key: str) -> str:
        """Get full detail for a specific edict/commandment.

        Args:
            edict_key: Edict key (e.g. "wh3_main_edict_ksl_awaken_the_land")
        """
        db = _load_edict_db()
        edict = db["edicts"].get(edict_key)
        if edict:
            return json.dumps(edict, indent=2)

        # Partial match
        matches = []
        for k, v in db["edicts"].items():
            if edict_key.lower() in k.lower():
                matches.append(v)
        if matches:
            return json.dumps(matches, indent=2)

        return json.dumps({"error": f"Edict '{edict_key}' not found"})
