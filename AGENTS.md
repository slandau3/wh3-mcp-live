# AGENTS.md — agent collaboration notes

## Project

WH3 live AI mod-development bridge: query campaign state + execute Lua inside a
running Total War: Warhammer 3 game, driven by AI agents. See README.md.

## Agent loop (OpenCode ↔ Kimi-K)

- **OpenCode** implements and self-verifies: Lua syntax check (`lua -e
  "assert(loadfile(...))"`), the exec-bridge logic test harness
  (`test/exec_bridge_test.lua`), pack build + personal-info sweep before any
  commit.
- **Kimi-K3** reviews locally (the review tool lives outside this repo — not
  published): hand it the review checklist below or run the local helper. It
  requires Kimi quota; it 403s when exhausted — just retry later.
- After a review, OpenCode triages findings: CRITICAL → fix + retest; MAJOR →
  fix or document; MINOR → address in a batch. Findings that are intentional
  or impossible (e.g., game-engine constraints) get a one-line note in the
  issue reply rather than a code change.

## Golden rules

1. Never commit without the Lua syntax check + pack build passing.
2. Every new Lua that runs in-game must be pcall-wrapped and trigger-driven
   (no hotkeys, no human input).
3. Personal info stays out: no emails, machine names, IPs, or keys. Run the
   local sweep helper (kept OUT of the repo) before push.
4. The battle-context override is patch-sensitive by design — label any change
   to `wh3_mod_battle/` as experimental in the commit.
5. Game-engine constraints are not bugs: DB-table edits still require pack
   rebuild + restart; battle state does not persist.

## Verification commands

```bash
lua -e "assert(loadfile('wh3_mod/wh3_mcp_dump.lua'))"            # campaign mod
lua -e "assert(loadfile('wh3_mod_battle/script/battle/default_battle/battle_start.lua'))"
lua test/exec_bridge_test.lua                                     # exec bridge logic tests
rm -rf build && mkdir -p build/mod/script/campaign/mod
cp -R wh3_mod/wh3_mcp build/mod/script/campaign/mod/ && cp wh3_mod/wh3_mcp_dump.lua build/mod/script/campaign/mod/
python3 tools/make_pack.py build/mod build/wh3_mcp.pack            # campaign pack
python3 tools/make_pack.py wh3_mod_battle build/wh3_battle.pack
bash -n tools/wh3-exec
```
