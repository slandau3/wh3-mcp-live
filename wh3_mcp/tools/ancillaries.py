"""Ancillary database tools and live ancillary data."""
import json
import os
from mcp.server.fastmcp import FastMCP
from config import WH3_DATA_DIR
from state import find_faction, find_character, all_characters, read_factions

_cache = None


def _load_ancillary_db() -> dict:
    global _cache
    if _cache is not None:
        return _cache["db"]

    db = {}
    cat_locs = {}
    dump_dir = os.path.join(WH3_DATA_DIR, "WH3-Dump")

    anc_path = os.path.join(dump_dir, "db", "ancillaries_tables", "data__.tsv")
    effects_path = os.path.join(dump_dir, "db", "ancillary_to_effects_tables", "data__.tsv")
    loc_path = os.path.join(dump_dir, "text", "db", "ancillaries__.loc.tsv")

    locs = {}
    if os.path.exists(loc_path):
        with open(loc_path, encoding="utf-8-sig") as f:
            lines = f.readlines()
        for line in lines[2:]:
            parts = line.strip().split("\t")
            if len(parts) < 2:
                continue
            key, text = parts[0], parts[1]
            if key.startswith("ancillaries_onscreen_name_"):
                anc_key = key[len("ancillaries_onscreen_name_"):]
                if anc_key not in locs:
                    locs[anc_key] = {"name": "", "description": ""}
                locs[anc_key]["name"] = text
            elif key.startswith("ancillaries_colour_text_"):
                anc_key = key[len("ancillaries_colour_text_"):]
                if anc_key not in locs:
                    locs[anc_key] = {"name": "", "description": ""}
                locs[anc_key]["description"] = text

    cat_loc_path = os.path.join(dump_dir, "text", "db", "ancillaries_categories__.loc.tsv")
    if os.path.exists(cat_loc_path):
        with open(cat_loc_path, encoding="utf-8-sig") as f:
            lines = f.readlines()
        for line in lines[2:]:
            parts = line.strip().split("\t")
            if len(parts) < 2:
                continue
            key, text = parts[0], parts[1]
            if key.startswith("ancillaries_categories_onscreen_name_"):
                cat_key = key[len("ancillaries_categories_onscreen_name_"):]
                cat_locs[cat_key] = text

    if os.path.exists(anc_path):
        with open(anc_path, encoding="utf-8-sig") as f:
            lines = f.readlines()
        headers = lines[0].strip().split("\t")
        for line in lines[2:]:
            parts = line.strip().split("\t")
            if len(parts) < 3:
                continue
            row = {}
            for i, h in enumerate(headers):
                row[h] = parts[i] if i < len(parts) else ""
            key = row.get("key", "")
            if not key:
                continue
            loc = locs.get(key, {"name": "", "description": ""})
            db[key] = {
                "key": key,
                "name": loc["name"],
                "description": loc["description"],
                "type": row.get("type", ""),
                "category": row.get("category", ""),
                "subcategory": row.get("subcategory", ""),
                "applies_to": row.get("applies_to", ""),
                "transferrable": row.get("transferrable", "") == "true",
                "unique_to_faction": row.get("unique_to_faction", "") == "true",
                "unique_to_world": row.get("unique_to_world", "") == "true",
                "legendary_item": row.get("legendary_item", "") == "true",
                "immortal": row.get("immortal", "") == "true",
                "faction_set": row.get("faction_set", ""),
                "effects": [],
            }

    if os.path.exists(effects_path):
        with open(effects_path, encoding="utf-8-sig") as f:
            lines = f.readlines()
        for line in lines[2:]:
            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue
            anc_key, effect_key, scope, value = parts[0], parts[1], parts[2], parts[3]
            if anc_key in db:
                db[anc_key]["effects"].append({
                    "effect": effect_key,
                    "scope": scope,
                    "value": value,
                })

    _cache = {"db": db, "categories": cat_locs}
    return db


def register(mcp: FastMCP):

    @mcp.tool()
    def get_ancillary_detail(ancillary_key: str) -> str:
        """Look up ancillary detail from WH3 game data: type, effects, description.

        Args:
            ancillary_key: Ancillary key (e.g. "wh3_main_anc_arcane_item_abhorrent_lodestone")
                           or partial match
        """
        db = _load_ancillary_db()
        if ancillary_key in db:
            return json.dumps(db[ancillary_key], indent=2)
        matches = [v for k, v in db.items() if ancillary_key.lower() in k.lower()]
        if matches:
            return json.dumps(matches[:20], indent=2)
        return json.dumps({"error": f"Ancillary '{ancillary_key}' not found"})

    @mcp.tool()
    def list_ancillaries(category: str = "") -> str:
        """List all ancillary chains by category (arcane_item, armour, enchanted_item, talisman, weapon, mount, follower, banner).

        Args:
            category: Optional filter by category
        """
        db = _load_ancillary_db()
        results = []
        for key, val in db.items():
            if category and val["category"] != category:
                continue
            results.append({
                "key": key,
                "name": val["name"],
                "type": val["type"],
                "category": val["category"],
                "subcategory": val["subcategory"],
                "effects": val["effects"],
            })
        return json.dumps(results[:50], indent=2)

    @mcp.tool()
    def get_character_ancillaries(cqi: int) -> str:
        """Get equipped ancillaries for a character by CQI from live game state.

        Args:
            cqi: Character Command Queue Index
        """
        c = find_character(cqi)
        if not c:
            return json.dumps({"error": f"Character with CQI {cqi} not found"})
        ancillaries = c.get("ancillaries", [])
        db = _load_ancillary_db()
        enriched = []
        for anc in ancillaries:
            key = anc.get("key", "")
            info = db.get(key, {})
            enriched.append({
                "key": key,
                "category": anc.get("category", info.get("category", "")),
                "name": info.get("name", key),
                "type": info.get("type", ""),
                "effects": info.get("effects", []),
            })
        return json.dumps({
            "character_cqi": cqi,
            "forename": c.get("forename", ""),
            "family_name": c.get("family_name", ""),
            "faction_key": c.get("faction_key", ""),
            "ancillaries": enriched,
        }, indent=2)

    @mcp.tool()
    def get_faction_inventory(faction_key: str) -> str:
        """Get unequipped ancillaries (inventory) for a faction from live game state.

        Args:
            faction_key: Faction key (e.g. "wh3_main_cth_the_northern_provinces")
        """
        faction = find_faction(faction_key)
        if not faction:
            return json.dumps({"error": f"Faction '{faction_key}' not found"})
        inventory = faction.get("inventory_ancillaries", [])
        db = _load_ancillary_db()
        enriched = []
        for anc in inventory:
            key = anc.get("key", "")
            info = db.get(key, {})
            enriched.append({
                "key": key,
                "category": anc.get("category", info.get("category", "")),
                "name": info.get("name", key),
                "type": info.get("type", ""),
                "effects": info.get("effects", []),
            })
        return json.dumps({
            "faction_key": faction_key,
            "inventory_ancillaries": enriched,
        }, indent=2)

    @mcp.tool()
    def get_all_equipped_ancillaries(faction_key: str = "") -> str:
        """Get all equipped ancillaries across characters, optionally filtered by faction.

        Args:
            faction_key: Optional faction key filter
        """
        chars = all_characters(faction_key=faction_key)
        db = _load_ancillary_db()
        results = []
        for c in chars:
            ancillaries = c.get("ancillaries", [])
            if not ancillaries:
                continue
            enriched = []
            for anc in ancillaries:
                key = anc.get("key", "")
                info = db.get(key, {})
                enriched.append({
                    "key": key,
                    "category": anc.get("category", info.get("category", "")),
                    "name": info.get("name", key),
                })
            results.append({
                "character_cqi": c.get("cqi"),
                "forename": c.get("forename", ""),
                "family_name": c.get("family_name", ""),
                "faction_key": c.get("faction_key", ""),
                "ancillaries": enriched,
            })
        return json.dumps(results, indent=2)
