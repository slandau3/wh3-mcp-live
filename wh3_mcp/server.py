"""
WH3 Real-Time MCP Server
Exposes live Total War: Warhammer 3 campaign data as MCP tools.
Reads JSON snapshots dumped by the companion Lua mod.
"""
import sys
from mcp.server.fastmcp import FastMCP
from config import WH3_DATA_DIR

mcp = FastMCP("wh3-realtime")

# Register all tool modules
from tools import realtime, diplomacy, buildings, units, skills, ancillaries, caravans, technology, compass, events, lords, edicts
realtime.register(mcp)
diplomacy.register(mcp)
buildings.register(mcp)
units.register(mcp)
skills.register(mcp)
ancillaries.register(mcp)
caravans.register(mcp)
technology.register(mcp)
compass.register(mcp)
events.register(mcp)
lords.register(mcp)
edicts.register(mcp)

# Register prompts
from prompts import register as register_prompts
register_prompts(mcp)

# Resource
import json
from state import read_live_state

@mcp.resource("wh3://live-state")
def live_state_resource() -> str:
    """Live campaign state as a readable resource."""
    return json.dumps(read_live_state(), indent=2)


if __name__ == "__main__":
    print("WH3 MCP Server starting...", file=sys.stderr)
    print(f"Data directory: {WH3_DATA_DIR}", file=sys.stderr)
    mcp.run()
