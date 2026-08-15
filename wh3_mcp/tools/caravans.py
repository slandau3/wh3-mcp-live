"""Caravan tools for Cathay campaign."""
import json
from mcp.server.fastmcp import FastMCP
from state import read_caravans, read_factions, read_characters, read_campaign_state
from config import WH3_DUMP_DIR
from db import load_tsv


# ---- Static caravan master trait data ----
_TRAIT_CACHE = None

def _load_caravan_traits() -> dict:
    """Load caravan master trait definitions from game data."""
    global _TRAIT_CACHE
    if _TRAIT_CACHE is not None:
        return _TRAIT_CACHE

    db = WH3_DUMP_DIR / "db"
    text = WH3_DUMP_DIR / "text" / "db"

    # Load skill definitions
    skills = load_tsv(db / "character_skills_tables" / "data__.tsv")
    skill_loc = {}
    for row in load_tsv(text / "character_skills__.loc.tsv"):
        key = row.get("key", "")
        val = row.get("text", "")
        if key.startswith("character_skills_localised_name_"):
            skill_loc[key[len("character_skills_localised_name_"):]] = val
        elif key.startswith("character_skills_localised_description_"):
            k = key[len("character_skills_localised_description_"):]
            if k not in skill_loc:
                skill_loc[k] = val

    # Load skill effects
    skill_effects = {}
    for row in load_tsv(db / "character_skill_level_to_effects_junctions_tables" / "data__.tsv"):
        skill_key = row.get("character_skill_key", "")
        if "innate_cth_caravan_master" not in skill_key:
            continue
        effect = row.get("effect_key", "")
        value = row.get("value", "0")
        if skill_key not in skill_effects:
            skill_effects[skill_key] = []
        skill_effects[skill_key].append({"effect": effect, "value": value})

    # Load starting units per trait
    caravan_core_path = WH3_DUMP_DIR / "script" / "campaign" / "wh3_campaign_caravans_core.lua"
    trait_units = {}
    if caravan_core_path.exists():
        content = caravan_core_path.read_text(encoding="utf-8", errors="replace")
        import re
        start = content.find("caravans.traits_to_units = {")
        if start != -1:
            depth = 0
            end = start
            for i, ch in enumerate(content[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            block = content[start:end+1]
            current_trait = None
            for line in block.split("\n"):
                trait_m = re.search(r'\["(wh3_main_skill_innate_cth_caravan_master_[^"]+)"\]', line)
                if trait_m:
                    current_trait = trait_m.group(1)
                    trait_units[current_trait] = []
                    continue
                if current_trait:
                    if line.strip().startswith("}") and "," in line:
                        current_trait = None
                        continue
                    unit_m = re.search(r'"(wh[^"]+)"', line)
                    if unit_m:
                        trait_units[current_trait].append(unit_m.group(1))

    # Build trait records
    traits = {}
    for s in skills:
        key = s.get("key", "")
        if "innate_cth_caravan_master" not in key:
            continue
        short = key.replace("wh3_main_skill_innate_cth_caravan_master_", "")
        # Get description from loc file
        desc = skill_loc.get(key, s.get("localised_description", ""))
        traits[key] = {
            "skill_key": key,
            "trait_name": s.get("localised_name", skill_loc.get(key, short)),
            "description": desc,
            "short_name": short,
            "effects": skill_effects.get(key, []),
            "starting_units": trait_units.get(key, []),
        }

    _TRAIT_CACHE = traits
    return traits


def register(mcp: FastMCP):

    @mcp.tool()
    def get_caravans() -> str:
        """Get all caravan data: active caravan masters, cargo, destinations, units."""
        caravans = read_caravans()
        if not caravans:
            return json.dumps({"error": "No caravan data available. May not be a Cathay campaign or caravans system not yet initialized."})
        return json.dumps(caravans, indent=2)

    @mcp.tool()
    def list_caravan_masters(faction_key: str = "") -> str:
        """List caravan masters and their active caravans.

        Args:
            faction_key: Faction key to filter by (defaults to player faction)
        """
        caravans = read_caravans()
        active = caravans.get("active_caravans", [])
        if not active:
            return json.dumps({"message": "No active caravans found", "caravans": []})

        result = []
        for cv in active:
            entry = {
                "force_cqi": cv.get("force_cqi", ""),
                "cargo": cv.get("cargo", 0),
                "master_cqi": cv.get("master_cqi", ""),
                "master_name": cv.get("master_name", ""),
                "master_rank": cv.get("master_rank", 0),
                "position": {"x": cv.get("force_x", 0), "y": cv.get("force_y", 0)},
                "num_units": len(cv.get("units", [])),
            }
            if faction_key and cv.get("force_faction", "") != faction_key:
                continue
            result.append(entry)

        return json.dumps({"active_caravans": result, "total": caravans.get("total_caravans", 0)}, indent=2)

    @mcp.tool()
    def list_caravan_recruits(faction_key: str = "") -> str:
        """List available caravan master recruits with their traits and bonuses.

        Shows which caravan master traits exist, which are already recruited,
        and which are available. Includes trait effects and starting units.

        Args:
            faction_key: Faction key (defaults to player faction)
        """
        if not faction_key:
            meta = read_campaign_state()
            faction_key = meta.get("local_faction", "")

        # Find caravan masters already in the faction
        recruited_traits = set()
        faction_chars = []
        for c in read_characters():
            if c.get("faction_key") != faction_key:
                continue
            for u in c.get("units", []):
                if "caravan_master" in u.get("key", ""):
                    faction_chars.append({
                        "cqi": c.get("cqi"),
                        "rank": c.get("rank", 0),
                        "unit_key": u.get("key", ""),
                        "region": c.get("region_key", ""),
                        "x": c.get("x", 0),
                        "y": c.get("y", 0),
                    })

        # Load all possible traits
        traits = _load_caravan_traits()
        result = []
        for trait_key, trait_data in traits.items():
            entry = {
                "trait": trait_data["trait_name"],
                "short_name": trait_data["short_name"],
                "description": trait_data["description"],
                "effects": trait_data["effects"],
                "starting_units": trait_data["starting_units"],
            }
            result.append(entry)

        return json.dumps({
            "faction": faction_key,
            "total_traits": len(result),
            "recruited_masters": faction_chars,
            "available_traits": result,
        }, indent=2)

    @mcp.tool()
    def list_caravan_destinations() -> str:
        """List all possible caravan destinations from game data."""
        db = WH3_DUMP_DIR / "db"

        nodes = load_tsv(db / "campaign_map_route_nodes_tables" / "data__.tsv")
        networks = load_tsv(db / "campaign_caravan_networks_tables" / "data__.tsv")

        # Build network lookup
        network_map = {}
        for n in networks:
            network_map[n.get("key", "")] = {
                "caravan_commander": n.get("caravan_commander", ""),
                "default_contract": n.get("default_contract", ""),
            }

        # Build destination list from nodes
        destinations = []
        for node in nodes:
            node_key = node.get("key", "")
            contracts = node.get("available_contracts", "")
            if not contracts:
                continue
            destinations.append({
                "node_key": node_key,
                "x": int(node.get("position_x", "0")),
                "y": int(node.get("position_y", "0")),
                "available_contracts": contracts,
                "active_contracts_count": int(node.get("active_contracts_count", "0")),
                "rounds_to_refresh": int(node.get("rounds_to_refresh", "0")),
            })

        return json.dumps({
            "total_destinations": len(destinations),
            "networks": network_map,
            "destinations": destinations,
        }, indent=2)

    @mcp.tool()
    def list_caravan_networks() -> str:
        """List caravan network destinations and routes."""
        db = WH3_DUMP_DIR / "db"

        networks = load_tsv(db / "campaign_caravan_networks_tables" / "data__.tsv")
        segments = load_tsv(db / "campaign_map_route_segments_tables" / "data__.tsv")

        # Group segments by network
        net_segments = {}
        for seg in segments:
            net = seg.get("network", "")
            if net not in net_segments:
                net_segments[net] = []
            net_segments[net].append({
                "from": seg.get("from", ""),
                "to": seg.get("to", ""),
            })

        result = []
        for n in networks:
            key = n.get("key", "")
            result.append({
                "network_key": key,
                "campaign": n.get("campaign", ""),
                "caravan_commander": n.get("caravan_commander", ""),
                "default_contract": n.get("default_contract", ""),
                "num_segments": len(net_segments.get(key, [])),
                "segments": net_segments.get(key, []),
            })

        return json.dumps(result, indent=2)
