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
local function json_escape(s)
    s = s:gsub('[%z\1-\31"\\]', function(c)
        if c == '"' then return '\\"' end
        if c == "\\" then return "\\\\" end
        if c == "\n" then return "\\n" end
        if c == "\r" then return "\\r" end
        if c == "\t" then return "\\t" end
        return string.format("\\u%04x", string.byte(c))
    end)
    return s
end

local function json_encode(v)
    if type(v) == "string" then
        return '"' .. json_escape(v) .. '"'
    elseif type(v) == "number" then
        if v ~= v or v == math.huge or v == -math.huge then return "null" end
        return tostring(v)
    elseif type(v) == "boolean" then
        return tostring(v)
    elseif type(v) == "nil" then
        return "null"
    elseif type(v) == "table" then
        local is_array = true
        local n = 0
        local max_index = 0
        for k in pairs(v) do
            n = n + 1
            if type(k) ~= "number" or k < 1 or k ~= math.floor(k) then
                is_array = false
            elseif k > max_index then
                max_index = k
            end
        end
        if is_array and max_index == n then
            -- dense 1..n array only; holes and sparse tables fall through
            local parts = {}
            for i = 1, n do
                parts[i] = json_encode(v[i])
            end
            return "[" .. table.concat(parts, ",") .. "]"
        end
        local parts = {}
        for k, val in pairs(v) do
            if type(k) == "string" then
                table.insert(parts, json_encode(k) .. ":" .. json_encode(val))
            end
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
        write_file(EXEC_RESULT_PATH, '{"ok":false,"error":"exec_battle_script.lua not found","output":"","request":' .. tostring(last_trigger_time) .. ',"timestamp":' .. os.time() .. '}')
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

    local res = {
        ok = run_ok,
        error = run_ok and "" or tostring(run_err),
        output = table.concat(battle_output_buffer, "\n"),
        result = _G.wh3_battle_exec_result,
        request = last_trigger_time,
        timestamp = os.time(),
    }
    local enc_ok, encoded = pcall(json_encode, res)
    if enc_ok then
        write_file(EXEC_RESULT_PATH, encoded)
    else
        res.result = tostring(_G.wh3_battle_exec_result)
        write_file(EXEC_RESULT_PATH, json_encode(res))
    end
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

-- Seed watermark so a stale trigger never replays on battle start
local function seed_battle_watermark()
    local f = io.open(EXEC_TRIGGER_PATH, "r")
    if f then
        last_trigger_time = tonumber(f:read("*a")) or 0
        f:close()
    end
end
seed_battle_watermark()

-- Repeating real-time poll (per-battle context; re-registers each battle).
-- bm:callback is single-shot; repeat_real_callback repeats with ms intervals.
bm:repeat_real_callback(
    function()
        pcall(check_battle_exec_trigger)
    end,
    POLL_INTERVAL * 1000,
    "wh3_battle_exec_poll"
)

out("WH3 BATTLE EXEC: bridge active (poll " .. POLL_INTERVAL .. "s)")
