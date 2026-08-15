--[[ see README "Battle context (experimental)" section ]]

-- Mirror vanilla default battle script setup. If this fails, the bridge
-- silently disables itself instead of breaking battles.
local ok, err = pcall(function()
    load_script_libraries()
    bm = battle_manager:new(empire_battle:new())
end)
if not ok then
    out("WH3 BATTLE EXEC: vanilla battle setup failed, bridge disabled: " .. tostring(err))
    return
end

-- ============================================================
-- CONFIG (edit to match your setup; must equal the campaign OUTPUT_DIR)
-- ============================================================
local EXEC_DIR = [[C:\wh3-mcp-data\exec]]
local EXEC_SCRIPT_PATH = EXEC_DIR .. [[\exec_battle_script.lua]]
local EXEC_TRIGGER_PATH = EXEC_DIR .. [[\exec_battle_trigger.txt]]
local EXEC_RESULT_PATH = EXEC_DIR .. [[\exec_battle_result.json]]
local POLL_INTERVAL = 3

-- ============================================================
-- BRIDGE
-- ============================================================
local last_trigger_time = 0
local battle_output_buffer = {}

function wh3_battle_exec_out(text)
    table.insert(battle_output_buffer, tostring(text))
end

local function write_file(path, data)
    local f = io.open(path, "w")
    if f then
        f:write(data)
        f:close()
        return true
    end
    return false
end

-- Minimal JSON encoder (avoids module-path coupling in battle context)
local function json_encode(v)
    if type(v) == "string" then
        return '"' .. v:gsub('["\\]', function(c) return "\\" .. c end) .. '"'
    elseif type(v) == "number" then
        return tostring(v)
    elseif type(v) == "boolean" then
        return tostring(v)
    elseif type(v) == "nil" then
        return "null"
    elseif type(v) == "table" then
        local parts = {}
        for k, val in pairs(v) do
            table.insert(parts, json_encode(k) .. ":" .. json_encode(val))
        end
        return "{" .. table.concat(parts, ",") .. "}"
    end
    return "null"
end

local function run_battle_exec()
    battle_output_buffer = {}
    _G.wh3_battle_exec_result = nil

    local script = io.open(EXEC_SCRIPT_PATH, "r")
    if not script then
        write_file(EXEC_RESULT_PATH, '{"ok":false,"error":"exec_battle_script.lua not found","output":"","timestamp":' .. os.time() .. '}')
        return
    end
    local chunk = script:read("*a")
    script:close()

    local original_out = out
    out = function(text)
        table.insert(battle_output_buffer, tostring(text))
        return original_out(text)
    end

    local run_ok, run_err = pcall(function()
        local fn, perr = loadstring(chunk, "wh3_battle_exec")
        if not fn then error(perr or "loadstring failed") end
        fn()
    end)

    out = original_out

    local result_json = nil
    if _G.wh3_battle_exec_result ~= nil then
        local r_ok, encoded = pcall(json_encode, _G.wh3_battle_exec_result)
        if r_ok then result_json = encoded end
    end

    local res = {
        ok = run_ok,
        error = run_ok and "" or tostring(run_err),
        output = table.concat(battle_output_buffer, "\n"),
        result = result_json,
        timestamp = os.time(),
    }
    write_file(EXEC_RESULT_PATH, json_encode(res))
    out("WH3 BATTLE EXEC: ran, ok=" .. tostring(run_ok))
end

local function check_battle_exec_trigger()
    local f = io.open(EXEC_TRIGGER_PATH, "r")
    if f then
        local content = f:read("*a")
        f:close()
        local trigger_time = tonumber(content) or 0
        if trigger_time > last_trigger_time then
            last_trigger_time = trigger_time
            pcall(run_battle_exec)
        end
    end
end

-- Start polling with the battle manager's real-time callback (per-battle
-- context: re-registers automatically on every new battle).
bm:callback(
    function()
        pcall(check_battle_exec_trigger)
    end,
    POLL_INTERVAL
)

out("WH3 BATTLE EXEC: bridge active (poll " .. POLL_INTERVAL .. "s)")
