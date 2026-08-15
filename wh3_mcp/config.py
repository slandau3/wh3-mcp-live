"""Configuration for WH3 MCP Server."""
import os
from pathlib import Path

WH3_DATA_DIR = Path(os.environ.get(
    "WH3_DATA_DIR",
    r"C:\wh3-mcp-data"
))

# Separate dump files (written by Lua mod)
CAMPAIGN_STATE_FILE = WH3_DATA_DIR / "campaign_state.json"
FACTIONS_STATE_FILE = WH3_DATA_DIR / "factions_state.json"
REGIONS_STATE_FILE = WH3_DATA_DIR / "regions_state.json"
CHARACTERS_STATE_FILE = WH3_DATA_DIR / "characters_state.json"
DIPLOMACY_STATE_FILE = WH3_DATA_DIR / "diplomacy_state.json"
CARAVANS_STATE_FILE = WH3_DATA_DIR / "caravans_state.json"
TECHNOLOGY_STATE_FILE = WH3_DATA_DIR / "technology_state.json"
COMPASS_STATE_FILE = WH3_DATA_DIR / "compass_state.json"
EVENTS_LOG_FILE = WH3_DATA_DIR / "events_state.json"

TRIGGER_FILE = WH3_DATA_DIR / "dump_trigger.txt"
WH3_DUMP_DIR = WH3_DATA_DIR / "WH3-Dump"
