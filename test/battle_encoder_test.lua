-- Battle-context encoder tests for wh3_mod_battle (module-free json_encode).
-- Extracts json_encode + json_escape from battle_start.lua and verifies
-- strings, controls, numbers, arrays, objects, and sparse tables.
-- Usage: lua test/battle_encoder_test.lua

local src = io.open("wh3_mod_battle/script/battle/default_battle/battle_start.lua", "r"):read("*a")
local marker = "local function json_escape"
local start = src:find(marker)
assert(start, "json_escape not found — battle layout changed?")
local stop = src:find("local function run_battle_exec", start)
assert(stop, "encoder end marker not found")
local encoder_src = src:sub(start, stop - 1)
local chunk = assert(load(encoder_src .. "\n_G.json_encode = json_encode\n_G.json_escape = json_escape\n", "battle_encoder"))
chunk()

local failures = 0
local function expect(cond, name, detail)
    if cond then
        print("PASS " .. name)
    else
        failures = failures + 1
        print("FAIL " .. name .. (detail and (" — " .. tostring(detail)) or ""))
    end
end

expect(json_encode("hi") == '"hi"', "plain string")
expect(json_encode('a"b') == '"a\\"b"', "quote escaped")
expect(json_encode("a\\b") == '"a\\\\b"', "backslash escaped")
expect(json_encode("line1\nline2") == '"line1\\nline2"', "newline escaped")
expect(json_encode("x" .. string.char(1) .. "y") == '"x\\u0001y"', "control char escaped")
expect(json_encode(3.5) == "3.5", "number")
expect(json_encode(math.huge) == "null", "inf -> null")
expect(json_encode(0/0) == "null", "nan -> null")
expect(json_encode(true) == "true", "bool")
expect(json_encode(nil) == "null", "nil")
expect(json_encode({1,2,3}) == "[1,2,3]", "dense array")
local obj = json_encode({a=1,b="x"})
expect(obj == '{"a":1,"b":"x"}' or obj == '{"b":"x","a":1}', "object", obj)
local e = json_encode({}); expect(e == "{}" or e == "[]", "empty table", e)
expect(json_encode({[2]="x"}) == "{}", "sparse table -> {}", json_encode({[2]="x"}))
expect(json_encode({1,2,nil,4}) == "{}", "holey array -> {}", json_encode({1,2,nil,4}))

if failures == 0 then
    print("=== ALL BATTLE ENCODER TESTS PASSED ===")
else
    print("=== " .. failures .. " TEST(S) FAILED ===")
end
os.exit(failures == 0 and 0 or 1)
