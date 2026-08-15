-- Exec-bridge logic tests for wh3_mcp_dump.lua (campaign bridge).
-- Runs outside the game: stubs the CA scripting globals, loads the real
-- bridge section, and verifies trigger handling, output capture, error
-- capture, result serialization and watermark seeding.
--
-- Requires: lua (any 5.x; loadstring is shimmed to load).
-- Usage: lua test/exec_bridge_test.lua

package.path = "wh3_mod/?.lua;" .. package.path

local TMP = "/tmp/wh3-exec-test"
os.execute("rm -rf " .. TMP)
os.execute("mkdir -p " .. TMP .. "/exec")

-- ---- CA globals stubs ----
function out() end
cm = {
    add_first_tick_callback = function() end,
    real_callback = function() end,
    repeat_real_callback = function() end,
    turn_number = function() return 42 end,
    get_local_faction_name = function() return "wh3_main_ksl_the_ice_court" end,
    model = function()
        return { world = function() return { faction_list = function() return { num_items = function() return 0 end } end } end }
    end,
}
core = { add_listener = function() end }
loadstring = load

local json = dofile("wh3_mod/wh3_mcp/json.lua")
local function dump_game_state() end

-- ---- Load the real bridge section (paths rewritten to TMP) ----
local src = io.open("wh3_mod/wh3_mcp_dump.lua", "r"):read("*a")
local start = src:find("local OUTPUT_DIR = ")
local init = src:find("-- INITIALIZATION", 1, true)
assert(start and init, "bridge section markers not found — mod layout changed?")
local sep = src:sub(1, init):match(".*()%-%- ====\n%-%- INITIALIZATION")
local stop = sep or (init - 1)
local section = src:sub(start, stop)
section = section:gsub([[C:\wh3%-mcp%-data]], TMP)
section = section:gsub([[\]], [[/]])

local trailer = "\n_G.check_exec_trigger = check_exec_trigger\n_G.seed_exec_watermark = seed_exec_watermark\n_G.run_exec_script = run_exec_script\n_G.px = function() return OUTPUT_DIR, EXEC_DIR, EXEC_SCRIPT_PATH, EXEC_TRIGGER_PATH, EXEC_RESULT_PATH end\n"
local chunk, perr = load(section .. trailer, "exec_bridge")
assert(chunk, perr)
chunk()
print("DEBUG paths:", table.concat({px()}, " | "))

local function exec_request(n, script_body, skip_write)
    if not skip_write then
        local f = io.open(TMP .. "/exec/exec_script.lua", "w")
        f:write(script_body)
        f:close()
    end
    io.open(TMP .. "/exec/exec_trigger.txt", "w"):write(tostring(n)):close()
    check_exec_trigger()
    local r = io.open(TMP .. "/exec/exec_result.json", "r")
    if not r then return nil end
    local result = r:read("*a")
    r:close()
    return result
end

local failures = 0
local function expect(cond, name, detail)
    if cond then
        print("PASS " .. name)
    else
        failures = failures + 1
        print("FAIL " .. name .. (detail and (" — " .. tostring(detail)) or ""))
    end
end

-- TEST 1: output capture + structured result + request id
local result = exec_request(1, [[wh3_exec_out("hello from test 1")
wh3_exec_result = { total = 3, alive = 2, label = "skaven" }
]])
print("TEST1:", result)
expect(result and result:find('"ok":true') ~= nil, "ok true", result)
expect(result and result:find("hello from test 1") ~= nil, "output captured", result)
expect(result and result:find('"label":"skaven"') ~= nil, "structured result", result)
expect(result and result:find('"request":1') ~= nil, "request id", result)

-- TEST 2: runtime error + pre-crash output
result = exec_request(2, [[wh3_exec_out("before crash")
error("boom")
]])
print("TEST2:", result)
expect(result and result:find('"ok":false') ~= nil, "ok false", result)
expect(result and result:find("boom") ~= nil, "error captured", result)
expect(result and result:find("before crash") ~= nil, "pre-crash output", result)

-- TEST 3: syntax error
result = exec_request(3, [[this is not lua ()))
]])
print("TEST3:", result)
expect(result and result:find('"ok":false') ~= nil, "ok false", result)
expect(result and result:find("syntax") ~= nil, "syntax error reported", result)

-- TEST 4: missing script
os.remove(TMP .. "/exec/exec_script.lua")
result = exec_request(4, "", true)
print("TEST4:", result)
expect(result and result:find("not found") ~= nil, "missing script handled", result)

-- TEST 5: stale trigger ignored (monotonicity)
os.remove(TMP .. "/exec/exec_result.json")
local stale = exec_request(2, [[wh3_exec_out("should NOT run")]])
expect(stale == nil, "stale trigger ignored", stale)

-- TEST 6: watermark seeding — leftover trigger must NOT execute on load
os.remove(TMP .. "/exec/exec_result.json")
io.open(TMP .. "/exec/exec_trigger.txt", "w"):write("99"):close()
io.open(TMP .. "/exec/exec_script.lua", "w"):write([[wh3_exec_out("should NOT replay")]]):close()
seed_exec_watermark()
local seeded = io.open(TMP .. "/exec/exec_result.json", "r")
expect(seeded == nil, "no execution from seeding", seeded)
if seeded then seeded:close() end

-- TEST 7: post-seed execution works (100 > seeded 99)
result = exec_request(100, [[wh3_exec_out("after seed ok")]])
print("TEST7:", result)
expect(result and result:find("after seed ok") ~= nil, "post-seed execution works", result)

if failures == 0 then
    print("=== ALL EXEC BRIDGE TESTS PASSED ===")
else
    print("=== " .. failures .. " TEST(S) FAILED ===")
end
os.exit(failures == 0 and 0 or 1)
