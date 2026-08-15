"""MCP prompts for campaign advice."""
from mcp.server.fastmcp import FastMCP
from state import read_campaign_state, read_factions, read_regions, read_characters, find_faction


def register(mcp: FastMCP):

    @mcp.prompt()
    def campaign_advisor() -> str:
        """Get strategic advice for the current campaign state."""
        meta = read_campaign_state()
        turn = meta.get("turn_number", "?")
        faction = meta.get("local_faction", "unknown")
        fobj = find_faction(faction)
        treasury = fobj.get("treasury", 0) if fobj else 0
        # Count regions from flat list
        num_regions = len([r for r in read_regions() if r.get("owner_key") == faction])
        num_armies = len(fobj.get("military_forces", [])) if fobj else 0

        return (
            f"You are advising the player in a Total War: Warhammer 3 campaign.\n\n"
            f"Current state:\n"
            f"- Turn: {turn}\n"
            f"- Faction: {faction}\n"
            f"- Treasury: {treasury} gold\n"
            f"- Regions: {num_regions}\n"
            f"- Armies: {num_armies}\n\n"
            f"Provide concise, actionable strategic advice. Consider economy, "
            f"military positioning, threats, and expansion opportunities."
        )

    @mcp.prompt()
    def army_review() -> str:
        """Review the player's armies and suggest improvements."""
        meta = read_campaign_state()
        faction = find_faction(meta.get("local_faction", ""))
        if not faction:
            return "No campaign data available. Start a campaign with the Lua mod enabled."

        armies = faction.get("military_forces", [])
        fkey = faction.get("key", "")
        chars = [c for c in read_characters() if c.get("faction_key") == fkey]
        lines = ["You are reviewing the player's military forces in WH3.\n"]
        for i, mf in enumerate(armies, 1):
            lines.append(f"Army {i}: CQI {mf.get('cqi')}, "
                         f"Stance: {mf.get('stance')}, "
                         f"Strength: {mf.get('strength')}, "
                         f"Units: {mf.get('num_units')}")

        lines.append(f"\nTotal characters: {len(chars)}")
        lines.append("\nSuggest army composition improvements, recruitment priorities, and positioning advice.")
        return "\n".join(lines)
