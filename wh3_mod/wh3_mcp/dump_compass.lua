--[[
    Compass Dumper for WH3 MCP
    Tracks Wu Xing Compass direction changes via events.
--]]
local dump_compass = {}

local current_direction = ""

function dump_compass.on_direction_selected(context)
    pcall(function()
        local faction = context:faction()
        if faction and faction:is_human() then
            current_direction = context:direction()
        end
    end)
end

function dump_compass.run(faction)
    if not faction then return {} end

    local faction_cooldown = 0
    local compass_cooldown = 0
    local power_level = 0
    pcall(function()
        local f_cqi = faction:command_queue_index()
        faction_cooldown = common.get_context_value("CcoCampaignFactionWomCompass", f_cqi, "FactionCooldown") or 0
        compass_cooldown = common.get_context_value("CcoCampaignFactionWomCompass", f_cqi, "CompassCooldown") or 0
        power_level = common.get_context_value("CcoCampaignFactionWomCompass", f_cqi, "PowerLevel") or 0
    end)

    return {
        current_direction = current_direction,
        faction_cooldown = faction_cooldown,
        compass_cooldown = compass_cooldown,
        cooldown_turns = math.max(faction_cooldown, compass_cooldown),
        power_level = power_level,
    }
end

return dump_compass
