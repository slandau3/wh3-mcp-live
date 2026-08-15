"""Wu Xing Compass tools for Cathay campaign."""
import json
from mcp.server.fastmcp import FastMCP
from db import load_tsv
from config import WH3_DUMP_DIR
from state import read_compass

_cache = None


def _load_compass_db() -> dict:
    global _cache
    if _cache is not None:
        return _cache

    db = WH3_DUMP_DIR / "db"
    text = WH3_DUMP_DIR / "text" / "db"

    directions = load_tsv(db / "compass_directions_tables" / "data__.tsv")
    actions = load_tsv(db / "winds_of_magic_compass_actions_tables" / "data__.tsv")
    dir_to_actions = load_tsv(db / "winds_of_magic_compass_direction_to_actions_tables" / "data__.tsv")
    action_outcomes = load_tsv(db / "winds_of_magic_compass_action_to_outcomes_tables" / "data__.tsv")
    action_requirements = load_tsv(db / "winds_of_magic_compass_action_to_requirements_tables" / "data__.tsv")
    effects = load_tsv(db / "effect_bundles_to_effects_junctions_tables" / "data__.tsv")

    # Localization
    dir_loc = {}
    for row in load_tsv(text / "compass_directions__.loc.tsv"):
        key = row.get("key", "")
        val = row.get("text", "")
        if key.startswith("compass_directions_title_"):
            dir_key = key[len("compass_directions_title_"):]
            dir_loc[dir_key] = val

    # Build direction lookup
    directions_by_key = {}
    for d in directions:
        dir_key = d.get("direction_key", "")
        directions_by_key[dir_key] = {
            "direction_key": dir_key,
            "display_name": dir_loc.get(dir_key, dir_key),
            "min_power": d.get("min_power", "0"),
            "max_power": d.get("max_power", "0"),
            "faction_set": d.get("faction_set", ""),
            "display_order": d.get("display_order", "0"),
            "initially_locked": d.get("initially_locked", "") == "true",
            "unlock_condition": d.get("turns_until_unlocked_script_key", ""),
            "selection_effect": d.get("selection_effect_list", ""),
            "power_effect": d.get("power_effect_list_chain", ""),
            "actions": [],
            "outcomes": [],
        }

    # Map actions to directions
    for da in dir_to_actions:
        action_key = da.get("action", "")
        dir_key = da.get("direction", "")
        if dir_key in directions_by_key:
            directions_by_key[dir_key]["actions"].append(action_key)

    # Map outcomes to actions
    for ao in action_outcomes:
        action_key = ao.get("action", "")
        for dk, dv in directions_by_key.items():
            if action_key in dv["actions"]:
                dv["outcomes"].append({
                    "action": action_key,
                    "outcome": ao.get("outcome", ""),
                    "payload": ao.get("payload", ""),
                    "value": ao.get("value", "0"),
                })

    _cache = {
        "directions": directions_by_key,
        "actions": {a.get("key", ""): a for a in actions},
    }
    return _cache


def register(mcp: FastMCP):

    @mcp.tool()
    def get_compass_state() -> str:
        """Get the current Wu Xing Compass state for the player faction."""
        compass = read_compass()
        if not compass:
            return json.dumps({"error": "No compass data available. May not be a Cathay campaign."})
        return json.dumps(compass, indent=2)

    @mcp.tool()
    def get_compass_directions() -> str:
        """Get all compass directions with their effects and bonuses."""
        db = _load_compass_db()
        return json.dumps(db["directions"], indent=2)

    @mcp.tool()
    def get_compass_detail(direction_key: str = "") -> str:
        """Get detail for a specific compass direction or all directions.

        Args:
            direction_key: Direction key (e.g. "wh3_main_chaos_compass_bastion")
                           or partial match (e.g. "bastion"). If empty, returns all.
        """
        db = _load_compass_db()
        if not direction_key:
            return json.dumps(db["directions"], indent=2)

        if direction_key in db["directions"]:
            return json.dumps(db["directions"][direction_key], indent=2)

        matches = {k: v for k, v in db["directions"].items()
                   if direction_key.lower() in k.lower()}
        if matches:
            return json.dumps(matches, indent=2)

        return json.dumps({
            "error": f"Direction '{direction_key}' not found",
            "available": list(db["directions"].keys()),
        })
