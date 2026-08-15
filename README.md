# WH3 MCP — Live AI Mod-Development Bridge for Total War: Warhammer 3

Query your **live** Total War: Warhammer 3 campaign and execute Lua **inside the
running game** — driven by AI agents, no restarts, no UI interaction.

This is a fork of [007lock/wh3-mcp](https://github.com/007lock/wh3-mcp) (the
campaign-state MCP) with a new **exec bridge** that lets an agent push Lua
snippets into the running campaign and read the results back as JSON.

## Why

Total War modding normally means: edit → rebuild pack → **restart the game** →
test. With this, script/logic iteration happens **live**:

```
Agent writes Lua  →  file lands on the PC  →  in-game mod dofiles it (≤5s poll)
       ↑                                                   ↓
Agent reads result ←──  exec_result.json + state dumps + script.log
       └───────────────── iterate ─────────────────────────┘
```

Data-table edits (DB tables inside packs) still require a rebuild + restart —
that's an engine limitation. All *logic* iteration is live.

## Architecture

```
WH3 Game (running)                      Python MCP server (any machine)
  wh3_mcp.pack (Lua mod)                server.py
  - dumps campaign state every 30s ───► - exposes 44 tools
  - dumps on turn end / events          - factions, armies, units, diplomacy,
  - EXEC BRIDGE: polls exec trigger ──►   tech, caravans, events, lords...
    every 5s, dofiles exec_script.lua
    live, writes exec_result.json
```

## Repository layout

```
wh3_mod/           Lua game mod (wh3_mcp_dump.lua + helpers) — includes exec bridge
wh3_mcp/           Python MCP server (FastMCP)
tools/             wh3-exec (agent loop CLI) + make_pack.py (pack builder)
docs/              setup + agent workflow
```

## Install

### 1. Build and install the Lua mod

```bash
mkdir -p build/mod/script/campaign/mod
cp -R wh3_mod/wh3_mcp build/mod/script/campaign/mod/
cp wh3_mod/wh3_mcp_dump.lua build/mod/script/campaign/mod/
python3 tools/make_pack.py build/mod build/wh3_mcp.pack
```

Copy `wh3_mcp.pack` into the game's `data/` folder
(`<Steam>\steamapps\common\Total War WARHAMMER III\data\`) and enable it in the
launcher's **Mod Manager**.

**Edit the config in `wh3_mod/wh3_mcp_dump.lua` first:** set `OUTPUT_DIR` to a
folder the game can write to (e.g. `C:\wh3-mcp-data`) and create it, including
an `exec` subfolder.

### 2. Run the MCP server

```bash
cd wh3_mcp
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
python server.py                                  # stdio MCP server
```

Set `WH3_DATA_DIR` to the same folder as the mod's `OUTPUT_DIR` if it differs.

### 3. Agent loop (the exec bridge)

```bash
# ~/.ssh/config entry for your Windows PC, then:
tools/wh3-exec 'cm:grant_money("wh3_main_ksl_the_ice_court", 10000)'
tools/wh3-exec -f /path/to/script.lua
```

Prints `exec_result.json`:
```json
{"ok": true, "error": "", "output": "gold granted",
 "result": {"ok": true}, "timestamp": 1786766759}
```

In the exec'd script you get:
- `wh3_exec_out("...")` — append lines to the result `output`
- `wh3_exec_result = <any Lua value>` — serialized to the result `result`

## What the exec script can do

Anything the campaign scripting API allows, called live:
`cm:grant_money`, spawn/teleport units, trigger dilemmas, equip ancillaries,
mutate faction state, run probes, then return structured data. The state dumps
refresh immediately after each execution so the agent can verify effects.

## Upstream & prior art

- Forked from [007lock/wh3-mcp](https://github.com/007lock/wh3-mcp) — campaign
  state dumper + MCP server. This repo adds the exec bridge, the agent loop
  tool, and the pack builder.
- In-game external-Lua execution was pioneered by the community dev-tool mods:
  - **Execute External Lua File (Modding Tool)** — WH2 `1916572654`, WH3
    `2791573994` (runs `exec.lua` from the game folder on an in-game hotkey)
  - **Modding Devtool Console** (mklabs) — desktop REPL with execute-on-save
  - **Modding Development Tools: Lua Console** (Groove Wizard) — in-game UI
    console
- Our delta over those: the execution is **trigger-file driven (no hotkey or
  human input)**, results come back as **machine-readable JSON** for agents,
  and it's wired into an **MCP server + remote agent loop**.

MIT licensed (see LICENSE); upstream contributions remain under their own terms.
