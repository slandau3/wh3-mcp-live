#!/bin/bash
# Agent review loop: hands the wh3-mcp-live repo to Kimi-K for a code review.
# Usage: kimi-review.sh [focus]
#   focus: security | correctness | compat | all (default: all)
# Run me when Kimi-K quota is available. OpenCode then acts on the findings.

set -e
cd "$(dirname "$0")/.."

FOCUS="${1:-all}"

REVIEW_PROMPT="You are reviewing the repository at $(pwd) — a Total War: Warhammer 3
live AI mod-development bridge (fork of 007lock/wh3-mcp with an exec bridge that
lets AI agents execute Lua inside the running game via trigger files).

Review focus: ${FOCUS}

Read the code and report CONCRETE issues only, grouped by severity:
1. CRITICAL — bugs that break the mod, crash the game's Lua interpreter, or corrupt saves
2. MAJOR — logic errors, race conditions (trigger polling), unsafe file handling, path bugs
3. MINOR — style, docs, edge cases

Pay special attention to:
- wh3_mod/wh3_mcp_dump.lua (campaign exec bridge: trigger monotonicity, pcall
  wrapping, out() capture/restore, json encode of exec_result, dofile safety)
- wh3_mod_battle/script/battle/default_battle/battle_start.lua (battle override:
  vanilla mirror correctness, bm:callback polling, module-free json encoder)
- tools/wh3-exec (scp file flow, trigger monotonicity, result polling)
- tools/make_pack.py (PFH5 pack format correctness)
- Personal-info leaks (emails, machine names, IPs, keys) anywhere in the repo

Format: markdown, one issue per line with file:line and a one-line fix
suggestion. If a category is clean, say so explicitly."

~/.kimi-code/bin/kimi -p "$REVIEW_PROMPT" --output-format text
