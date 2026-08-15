# Setup & Agent Workflow

## End-to-end (Windows PC + any SSH-capable agent machine)

1. **Install the Lua mod** (see README): build `wh3_mcp.pack`, copy to the
   game's `data/` folder, enable once in the launcher Mod Manager, set
   `OUTPUT_DIR` in `wh3_mod/wh3_mcp_dump.lua` to a writable folder and create
   `<OUTPUT_DIR>\exec`.
2. **Run the MCP server** (`wh3_mcp/server.py`) on any machine that can read
   the state folder — typically the same PC, or remotely via SSH/SCP.
3. **Agent loop** — either the bundled `tools/wh3-exec`, or drive the files
   directly from any agent:

```
WRITE  <OUTPUT_DIR>\exec\exec_script.lua     (the Lua to run)
WRITE  <OUTPUT_DIR>\exec\exec_trigger.txt    (increasing number)
READ   <OUTPUT_DIR>\exec\exec_result.json    (poll until {ok,...} appears)
READ   <OUTPUT_DIR>\*_state.json             (verify effects)
```

## MCP server config

| Env var          | Default          | Meaning                          |
|------------------|------------------|----------------------------------|
| `WH3_DATA_DIR`   | `C:\wh3-mcp-data`| folder with the state JSON files |

## Timing

- State dumps: every 30s, on turn end, on save, on many events
- Exec trigger poll: every 5s in campaign
- Exec runs synchronously: trigger seen → script executes → result written →
  state refreshed

## Caveats

- The mod runs in **campaign mode**; battle-scene execution is not supported
  by the dump mod (battle scripting has a separate context).
- If the game is closed, nothing executes — the agent should check
  `campaign_state.json` exists/updated first.
- Data-table changes (unit stats, item stats, DB tables) require a pack
  rebuild + game restart. Batch them; iterate everything else live.

## Agent loop example (raw, no tooling)

```bash
# push
scp exec_script.lua wh3-pc:C:/wh3-mcp-data/exec/
printf '%s' "$(date +%s)" | ssh wh3-pc "cat > C:/wh3-mcp-data/exec/exec_trigger.txt"
# poll
for i in $(seq 1 45); do
  scp wh3-pc:C:/wh3-mcp-data/exec/exec_result.json . 2>/dev/null && break
  sleep 1
done
cat exec_result.json
```
