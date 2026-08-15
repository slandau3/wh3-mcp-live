--[[
    Technology Dumper for WH3 MCP
    Extracts research state for the player's faction.
    Tracks researched technologies and current research.
--]]
local dump_technology = {}

-- Tracked via events
local current_research_key = ""
local researched_techs = {}
local initialized = false

function dump_technology.on_research_started(context)
    pcall(function()
        local faction = context:faction()
        if faction and faction:is_human() then
            current_research_key = context:technology()
        end
    end)
end

function dump_technology.on_research_completed(context)
    pcall(function()
        local faction = context:faction()
        if faction and faction:is_human() then
            local tech = context:technology()
            researched_techs[tech] = true
            current_research_key = ""
        end
    end)
end

local function scan_faction_techs(faction)
    if initialized then return end
    initialized = true

    local f_cqi = faction:command_queue_index()

    pcall(function()
        local num_techs = common.get_context_value("CcoCampaignFaction", f_cqi, "TechnologyList.Size")
        if num_techs and num_techs > 0 then
            for i = 0, num_techs - 1 do
                local key = nil
                local is_researched = false
                local is_researching = false
                pcall(function()
                    key = common.get_context_value("CcoCampaignFaction", f_cqi, "TechnologyList.At(" .. i .. ").RecordContext.Key")
                end)
                pcall(function()
                    is_researched = common.get_context_value("CcoCampaignFaction", f_cqi, "TechnologyList.At(" .. i .. ").IsResearched")
                end)
                pcall(function()
                    is_researching = common.get_context_value("CcoCampaignFaction", f_cqi, "TechnologyList.At(" .. i .. ").IsResearching")
                end)
                if key and key ~= "" then
                    if is_researched then
                        researched_techs[key] = true
                    end
                    if is_researching then
                        current_research_key = key
                    end
                end
            end
        end
    end)
end

function dump_technology.run(faction)
    if not faction then return {} end

    scan_faction_techs(faction)

    local result = {
        current_research = current_research_key,
        researched = {},
    }

    for tech, _ in pairs(researched_techs) do
        table.insert(result.researched, tech)
    end

    return result
end

return dump_technology
