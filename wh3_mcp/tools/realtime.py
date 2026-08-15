"""Real-time campaign state tools."""
import json
import time
from mcp.server.fastmcp import FastMCP
from state import (
    read_campaign_state, read_factions, read_regions, read_characters,
    find_faction, find_region, find_character,
    all_characters, all_armies,
)
from config import TRIGGER_FILE


def register(mcp: FastMCP):

    @mcp.tool()
    def get_campaign_state() -> str:
        """Get the full current campaign snapshot: turn, factions, regions, armies, characters."""
        meta = read_campaign_state()
        meta["factions"] = read_factions()
        meta["regions"] = read_regions()
        meta["characters"] = read_characters()
        return json.dumps(meta, indent=2)

    @mcp.tool()
    def get_my_faction() -> str:
        """Get detailed info about the player's faction: treasury, regions, armies, characters."""
        meta = read_campaign_state()
        faction = find_faction(meta.get("local_faction", ""))
        if faction:
            # Attach regions and characters for this faction
            fkey = faction["key"]
            faction["regions"] = [r for r in read_regions() if r.get("owner_key") == fkey]
            faction["characters"] = [c for c in read_characters() if c.get("faction_key") == fkey]
            return json.dumps(faction, indent=2)
        return json.dumps({"error": "Player faction not found"})

    @mcp.tool()
    def get_faction_info(faction_key: str) -> str:
        """Get detailed info about any faction by key.

        Args:
            faction_key: Faction key (e.g. "wh3_main_kis_kislev")
        """
        faction = find_faction(faction_key)
        if faction:
            faction["regions"] = [r for r in read_regions() if r.get("owner_key") == faction_key]
            faction["characters"] = [c for c in read_characters() if c.get("faction_key") == faction_key]
            return json.dumps(faction, indent=2)
        return json.dumps({"error": f"Faction '{faction_key}' not found"})

    @mcp.tool()
    def list_factions() -> str:
        """List all alive factions with basic info."""
        factions = []
        for f in read_factions():
            if not f.get("is_dead"):
                factions.append({
                    "key": f["key"],
                    "culture": f.get("culture"),
                    "treasury": f.get("treasury"),
                    "num_regions": f.get("num_regions"),
                    "is_human": f.get("is_human"),
                })
        return json.dumps(factions, indent=2)

    @mcp.tool()
    def list_armies(faction_key: str = "") -> str:
        """List all military forces, optionally filtered by faction.

        Args:
            faction_key: Optional faction key to filter by
        """
        return json.dumps(all_armies(faction_key or None), indent=2)

    @mcp.tool()
    def list_characters(faction_key: str = "", char_type: str = "") -> str:
        """List all characters, optionally filtered by faction or type.

        Args:
            faction_key: Optional faction key filter
            char_type: Optional type filter (general, agent, etc.)
        """
        return json.dumps(all_characters(faction_key or None, char_type or None), indent=2)

    @mcp.tool()
    def get_character(cqi: int) -> str:
        """Get a single character by their Command Queue Index.

        Args:
            cqi: Character CQI (Command Queue Index)
        """
        c = find_character(cqi)
        if c:
            return json.dumps(c, indent=2)
        return json.dumps({"error": f"Character with CQI {cqi} not found"})

    @mcp.tool()
    def get_region(region_key: str) -> str:
        """Get detailed info about a specific region.

        Args:
            region_key: Region key (e.g. "wh3_main_region_kislev")
        """
        r = find_region(region_key)
        if r:
            return json.dumps(r, indent=2)
        return json.dumps({"error": f"Region '{region_key}' not found"})

    @mcp.tool()
    def list_provinces() -> str:
        """List all regions grouped by province."""
        provinces: dict = {}
        for r in read_regions():
            prov = r.get("province", "unknown")
            if prov not in provinces:
                provinces[prov] = []
            provinces[prov].append(r)
        return json.dumps(provinces, indent=2)

    @mcp.tool()
    def get_turn_info() -> str:
        """Get current turn number and faction whose turn it is."""
        meta = read_campaign_state()
        return json.dumps({
            "turn": meta.get("turn_number"),
            "turn_faction": meta.get("turn_faction"),
            "local_faction": meta.get("local_faction"),
            "alive_factions": len([
                f for f in read_factions() if not f.get("is_dead")
            ]),
        }, indent=2)

    @mcp.tool()
    def trigger_dump() -> str:
        """Send a signal to the Lua mod to dump an immediate game state snapshot."""
        try:
            TRIGGER_FILE.write_text(str(time.time()), encoding="utf-8")
            return "Trigger sent. Live state will update within a few seconds."
        except Exception as e:
            return f"Failed to write trigger: {e}"
