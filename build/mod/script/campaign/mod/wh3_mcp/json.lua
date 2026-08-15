--[[
    JSON Serializer for WH3 MCP
    No external dependencies.
--]]
local json = {}

function json.encode(val)
    local t = type(val)
    if t == "nil" then
        return "null"
    elseif t == "boolean" then
        return val and "true" or "false"
    elseif t == "number" then
        return tostring(val)
    elseif t == "string" then
        local escaped = val
        escaped = escaped:gsub('\\', '\\\\')
        escaped = escaped:gsub('"', '\\"')
        escaped = escaped:gsub('\n', '\\n')
        escaped = escaped:gsub('\r', '\\r')
        escaped = escaped:gsub('\t', '\\t')
        return '"' .. escaped .. '"'
    elseif t == "table" then
        local is_array = false
        local max_index = 0
        local count = 0
        for k, _ in pairs(val) do
            count = count + 1
            if type(k) == "number" and k > 0 and math.floor(k) == k then
                if k > max_index then max_index = k end
                is_array = true
            elseif type(k) == "string" then
                is_array = false
            end
        end

        if count == 0 then
            return "{}"
        end

        if is_array and max_index == count then
            local parts = {}
            for i = 1, max_index do
                parts[i] = json.encode(val[i])
            end
            return "[" .. table.concat(parts, ",") .. "]"
        else
            local parts = {}
            for k, v in pairs(val) do
                if type(k) == "string" then
                    table.insert(parts, json.encode(k) .. ":" .. json.encode(v))
                end
            end
            return "{" .. table.concat(parts, ",") .. "}"
        end
    else
        return '"' .. tostring(val) .. '"'
    end
end

return json
