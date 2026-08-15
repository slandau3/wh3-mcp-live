"""Diplomacy tools."""
import json
from mcp.server.fastmcp import FastMCP
from state import read_diplomacy_factions, read_pending_deals


def register(mcp: FastMCP):

    @mcp.tool()
    def get_diplomacy(faction_key: str = "") -> str:
        """Get diplomatic relationships for a faction or all factions.

        Args:
            faction_key: Optional faction key to get diplomacy for. If empty, returns all.
        """
        factions = read_diplomacy_factions()
        if faction_key:
            if faction_key in factions:
                return json.dumps({faction_key: factions[faction_key]}, indent=2)
            return json.dumps({"error": f"No diplomacy data for '{faction_key}'"})
        return json.dumps(factions, indent=2)

    @mcp.tool()
    def get_war_list() -> str:
        """List all active wars between factions."""
        factions = read_diplomacy_factions()
        wars = []
        seen = set()
        for fkey, dip in factions.items():
            for enemy in dip.get("at_war", []):
                pair = tuple(sorted([fkey, enemy]))
                if pair not in seen:
                    seen.add(pair)
                    wars.append({"faction_a": pair[0], "faction_b": pair[1]})
        return json.dumps(wars, indent=2)

    @mcp.tool()
    def get_allies(faction_key: str) -> str:
        """Get all allies (military + defensive) of a faction.

        Args:
            faction_key: Faction key to check allies for
        """
        factions = read_diplomacy_factions()
        if faction_key not in factions:
            return json.dumps({"error": f"No diplomacy data for '{faction_key}'"})
        dip = factions[faction_key]
        return json.dumps({
            "faction": faction_key,
            "military_allies": dip.get("allied", []),
            "defensive_allies": dip.get("defensive_allied", []),
            "nap": dip.get("nap", []),
            "trade": dip.get("trade", []),
        }, indent=2)

    @mcp.tool()
    def get_faction_relations(faction_key: str) -> str:
        """Get all diplomatic relations for a faction categorized by type.

        Args:
            faction_key: Faction key to check relations for
        """
        factions = read_diplomacy_factions()
        if faction_key not in factions:
            return json.dumps({"error": f"No diplomacy data for '{faction_key}'"})
        dip = factions[faction_key]

        incoming = {"at_war": [], "allied": [], "nap": [], "trade": [], "met": []}
        for other_key, other_dip in factions.items():
            if other_key == faction_key:
                continue
            for rel_type in ["at_war", "allied", "nap", "trade", "met"]:
                if faction_key in other_dip.get(rel_type, []):
                    incoming[rel_type].append(other_key)

        return json.dumps({
            "faction": faction_key,
            "outgoing": dip,
            "incoming": incoming,
        }, indent=2)

    @mcp.tool()
    def get_pending_deals(faction_key: str = "") -> str:
        """Get all pending diplomatic offers and demands.

        Args:
            faction_key: Optional filter by faction involved in the deal
        """
        pending = read_pending_deals()

        if faction_key:
            pending = [
                d for d in pending
                if d.get("proposer") == faction_key or d.get("target") == faction_key
            ]

        # Summarize deal types
        for deal in pending:
            types = []
            if deal.get("is_trade"): types.append("trade")
            if deal.get("is_nap"): types.append("non_aggression_pact")
            if deal.get("is_defensive"): types.append("defensive_alliance")
            if deal.get("is_military"): types.append("military_alliance")
            if deal.get("is_peace"): types.append("peace_treaty")
            if deal.get("is_war"): types.append("war_declaration")
            if deal.get("is_confederation"): types.append("confederation")
            if deal.get("is_vassal"): types.append("vassalage")
            deal["deal_types"] = types if types else ["unknown"]

        return json.dumps({
            "count": len(pending),
            "pending_deals": pending,
        }, indent=2)
