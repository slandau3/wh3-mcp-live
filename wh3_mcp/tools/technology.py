"""Technology database and live state tools."""
import json
from mcp.server.fastmcp import FastMCP
from db import load_tsv
from config import WH3_DUMP_DIR
from state import read_technology, read_factions, read_campaign_state

_cache = None


def _load_tech_db() -> dict:
    global _cache
    if _cache is not None:
        return _cache

    db = WH3_DUMP_DIR / "db"
    text = WH3_DUMP_DIR / "text" / "db"

    technologies = load_tsv(db / "technologies_tables" / "data__.tsv")
    nodes = load_tsv(db / "technology_nodes_tables" / "data__.tsv")
    links = load_tsv(db / "technology_node_links_tables" / "data__.tsv")
    effects = load_tsv(db / "technology_effects_junction_tables" / "data__.tsv")
    node_sets = load_tsv(db / "technology_node_sets_tables" / "data__.tsv")
    required_techs = load_tsv(db / "technology_required_technology_junctions_tables" / "data__.tsv")
    required_buildings = load_tsv(db / "technology_required_building_levels_junctions_tables" / "data__.tsv")
    ui_tabs = load_tsv(db / "technology_ui_tabs_tables" / "data__.tsv")
    ui_groups = load_tsv(db / "technology_ui_groups_tables" / "data__.tsv")
    ui_tab_nodes = load_tsv(db / "technology_ui_tabs_to_technology_nodes_junctions_tables" / "data__.tsv")
    ui_group_nodes = load_tsv(db / "technology_ui_groups_to_technology_nodes_junctions_tables" / "data__.tsv")

    # Localization
    tech_loc = {}
    for row in load_tsv(text / "technologies__.loc.tsv"):
        key = row.get("key", "")
        val = row.get("text", "")
        if key.startswith("technologies_onscreen_name_"):
            tech_key = key[len("technologies_onscreen_name_"):]
            tech_loc[tech_key] = val
        elif key.startswith("technologies_short_description_"):
            tech_key = key[len("technologies_short_description_"):]
            if tech_key not in tech_loc:
                tech_loc[tech_key] = val

    node_loc = {}
    for row in load_tsv(text / "technology_ui_groups__.loc.tsv"):
        key = row.get("key", "")
        val = row.get("text", "")
        if val:
            node_loc[key] = val

    # Build node sets
    node_set_map = {}
    for ns in node_sets:
        ns_key = ns.get("key", "")
        node_set_map[ns_key] = {
            "key": ns_key,
            "culture": ns.get("culture", ""),
            "subculture": ns.get("subculture", ""),
        }

    # Build technology lookup
    tech_by_key = {}
    for t in technologies:
        tech_by_key[t["key"]] = {
            "key": t["key"],
            "icon": t.get("icon_name", ""),
            "is_civil": t.get("is_civil", "") == "true",
            "is_engineering": t.get("is_engineering", "") == "true",
            "is_military": t.get("is_military", "") == "true",
            "is_hidden": t.get("is_hidden", "") == "true",
            "display_name": tech_loc.get(t["key"], t["key"]),
        }

    # Build nodes with dependencies
    nodes_by_key = {}
    for n in nodes:
        node_key = n.get("key", "")
        tech_key = n.get("technology_key", "")
        nodes_by_key[node_key] = {
            "node_key": node_key,
            "technology_key": tech_key,
            "tier": n.get("tier", "0"),
            "research_points_required": n.get("research_points_required", "0"),
            "cost_per_round": n.get("cost_per_round", "0"),
            "food_cost": n.get("food_cost", "0"),
            "faction_key": n.get("faction_key", ""),
            "node_set": n.get("technology_node_set", ""),
            "ui_group": n.get("optional_ui_group", ""),
            "parents": [],
            "children": [],
            "effects": [],
            "required_technologies": [],
            "required_buildings": [],
            "display_name": tech_loc.get(tech_key, tech_key),
        }

    # Add parent-child links
    for lk in links:
        child = lk.get("child_key", "")
        parent = lk.get("parent_key", "")
        if child in nodes_by_key:
            nodes_by_key[child]["parents"].append(parent)
        if parent in nodes_by_key:
            nodes_by_key[parent]["children"].append(child)

    # Add effects
    for eff in effects:
        tech_key = eff.get("technology", "")
        for nk, nv in nodes_by_key.items():
            if nv["technology_key"] == tech_key:
                nv["effects"].append({
                    "effect": eff.get("effect", ""),
                    "scope": eff.get("effect_scope", ""),
                    "value": eff.get("value", ""),
                })

    # Add required technologies
    for rt in required_techs:
        tech_key = rt.get("technology", "")
        req_tech = rt.get("required_technology", "")
        for nk, nv in nodes_by_key.items():
            if nv["technology_key"] == tech_key:
                nv["required_technologies"].append(req_tech)

    # Add required buildings
    for rb in required_buildings:
        tech_key = rb.get("technology", "")
        building = rb.get("building_level", "")
        for nk, nv in nodes_by_key.items():
            if nv["technology_key"] == tech_key:
                nv["required_buildings"].append(building)

    # Group by node set
    by_node_set = {}
    for nk, nv in nodes_by_key.items():
        ns = nv["node_set"]
        if ns not in by_node_set:
            by_node_set[ns] = []
        by_node_set[ns].append(nv)

    _cache = {
        "technologies": tech_by_key,
        "nodes": nodes_by_key,
        "node_sets": node_set_map,
        "by_node_set": by_node_set,
    }
    return _cache


def register(mcp: FastMCP):

    FACTION_NODE_SETS = {
        "wh3_main_cth_the_northern_provinces": ["cth_mil"],
        "wh3_main_cth_the_western_provinces": ["cth_mil"],
        "wh3_main_cth_celestial_loyalists": ["cth_mil"],
        "wh3_main_cth_dissenter_lords_of_jinshen": ["cth_mil"],
        "wh3_main_cth_rebel_lords_of_nan_yang": ["cth_mil"],
        "wh3_main_cth_burning_wind_nomads": ["cth_mil"],
        "wh3_main_cth_imperial_wardens": ["cth_mil"],
        "wh3_dlc24_cth_the_celestial_court": ["cth_mil"],
        "wh3_main_kis_kislev": ["ksl_mil"],
        "wh3_main_ksl_the_ice_court": ["ksl_mil"],
        "wh3_main_ksl_the_great_orthodoxy": ["ksl_mil"],
        "wh3_main_ksl_brotherhood_of_the_bear": ["ksl_mil"],
        "wh3_main_kho_exiles_of_khorne": ["kho_mil"],
        "wh3_main_nur_poxmakers_of_nurgle": ["nur_mil"],
        "wh3_main_tze_oracles_of_tzeentch": ["tze_mil"],
        "wh3_main_sla_seducers_of_slaanesh": ["sla_mil"],
        "wh_main_emp_empire": ["emp_civ_reworkd"],
        "wh_main_dwf_dwarfs": ["dwf_mil"],
        "wh_main_grn_greenskins": ["grn_new"],
        "wh_main_vmp_vampire_counts": ["vmp_mil"],
        "wh_main_brt_bretonnia": ["brt_mil"],
        "wh2_main_hef_high_elves": ["hef_mil"],
        "wh2_main_def_dark_elves": ["def_mil"],
        "wh2_main_lzd_lizardmen": ["lzd_mil"],
        "wh2_main_skv_clan_moulder": ["skv_mil"],
    }

    @mcp.tool()
    def get_technology_tree(faction_key: str = "", max_tier: int = 0) -> str:
        """Get the technology tree for a faction, optionally filtered by max tier.

        Args:
            faction_key: Faction key (e.g. "wh3_main_cth_the_northern_provinces").
                         If empty, returns all node sets.
            max_tier: If > 0, only return techs at or below this tier.
        """
        db = _load_tech_db()
        node_set_filter = FACTION_NODE_SETS.get(faction_key, []) if faction_key else []

        result = {}
        for ns_key, ns_info in db["node_sets"].items():
            if node_set_filter and ns_key not in node_set_filter:
                continue
            nodes = db["by_node_set"].get(ns_key, [])
            if max_tier > 0:
                nodes = [n for n in nodes if int(n.get("tier", 0)) <= max_tier]
            result[ns_key] = {
                "node_set": ns_info,
                "nodes": sorted(nodes, key=lambda n: int(n.get("tier", 0))),
            }

        return json.dumps(result, indent=2)

    @mcp.tool()
    def get_available_technologies(faction_key: str) -> str:
        """Get technologies available for research (not yet researched, prerequisites met).

        Args:
            faction_key: Faction key (e.g. "wh3_main_cth_the_northern_provinces")
        """
        db = _load_tech_db()

        # Get researched techs from live state
        tech_state = read_technology()
        researched = set()
        for t in tech_state.get("researched", []):
            if isinstance(t, str):
                researched.add(t)
            elif isinstance(t, dict):
                researched.add(t.get("key", ""))
        current_research = tech_state.get("current_research", "")

        # Get faction's node set
        node_set_filter = FACTION_NODE_SETS.get(faction_key, [])
        if not node_set_filter:
            return json.dumps({"error": f"No tech tree for faction '{faction_key}'"})

        # Get all nodes for this faction
        all_nodes = []
        for ns in node_set_filter:
            all_nodes.extend(db["by_node_set"].get(ns, []))

        # Build tech_key -> node mapping
        tech_to_node = {}
        for n in all_nodes:
            tech_to_node[n["technology_key"]] = n

        # Filter: not researched, parent prerequisites met
        available = []
        for n in all_nodes:
            tech_key = n["technology_key"]
            if tech_key in researched:
                continue
            if tech_key == current_research:
                continue

            # Check parent prerequisites
            parents_met = True
            for parent_node_key in n.get("parents", []):
                parent_node = db["nodes"].get(parent_node_key, {})
                parent_tech = parent_node.get("technology_key", "")
                if parent_tech and parent_tech not in researched:
                    parents_met = False
                    break

            # Check required technologies
            for req_tech in n.get("required_technologies", []):
                if req_tech not in researched:
                    parents_met = False
                    break

            if not parents_met:
                continue

            available.append({
                "technology_key": tech_key,
                "display_name": n.get("display_name", tech_key),
                "tier": n.get("tier", "0"),
                "research_points_required": n.get("research_points_required", "0"),
                "cost_per_round": n.get("cost_per_round", "0"),
                "food_cost": n.get("food_cost", "0"),
                "effects": n.get("effects", []),
                "children": n.get("children", []),
            })

        available.sort(key=lambda x: int(x.get("tier", 0)))

        return json.dumps({
            "faction": faction_key,
            "current_research": current_research,
            "num_researched": len(researched),
            "num_available": len(available),
            "available": available,
        }, indent=2)

    @mcp.tool()
    def get_technology_detail(technology_key: str) -> str:
        """Get full technology detail: effects, prerequisites, tier.

        Args:
            technology_key: Technology key (e.g. "wh3_main_tech_cth_1")
                           or partial match (e.g. "tech_cth")
        """
        db = _load_tech_db()

        matches = []
        for nk, nv in db["nodes"].items():
            if technology_key.lower() in nv.get("technology_key", "").lower():
                matches.append(nv)

        if matches:
            return json.dumps(matches, indent=2)

        if technology_key in db["nodes"]:
            return json.dumps(db["nodes"][technology_key], indent=2)

        return json.dumps({
            "error": f"Technology '{technology_key}' not found",
            "hint": "Use get_technology_tree to see available technologies",
        })

    @mcp.tool()
    def get_faction_technology(faction_key: str) -> str:
        """Get a faction's researched technologies and current research.

        Args:
            faction_key: Faction key (e.g. "wh3_main_cth_the_northern_provinces")
        """
        faction = None
        local_faction = read_campaign_state().get("local_faction")
        for f in read_factions():
            if f.get("key") == faction_key:
                faction = f
                break

        if not faction:
            return json.dumps({"error": f"Faction '{faction_key}' not found"})

        if local_faction and faction_key != local_faction:
            return json.dumps({"error": f"Technology state is only dumped for the local faction ('{local_faction}'); requested '{faction_key}'"})

        tech_state = read_technology()

        return json.dumps({
            "faction": faction_key,
            "current_research": tech_state.get("current_research", ""),
            "researched": tech_state.get("researched", []),
            "num_researched": len(tech_state.get("researched", [])),
        }, indent=2)
