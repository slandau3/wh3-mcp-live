--[[
    Faction Dumper for WH3 MCP
    Extracts faction data including regions, characters, and military forces.
--]]
local dump_character = require("wh3_mcp.dump_character")
local dump_region = require("wh3_mcp.dump_region")

local dump_faction = {}

function dump_faction.run(faction)
    if not faction then return nil end

    local ok, result = pcall(function()
        local regions = {}
        local region_list = faction:region_list()
        for i = 0, region_list:num_items() - 1 do
            local r = dump_region.run(region_list:item_at(i))
            if r then table.insert(regions, r) end
        end

        local characters = {}
        local char_list = faction:character_list()
        for i = 0, char_list:num_items() - 1 do
            local c = dump_character.run(char_list:item_at(i))
            if c then table.insert(characters, c) end
        end

        local military_forces = {}
        local mf_list = faction:military_force_list()
        for i = 0, mf_list:num_items() - 1 do
            local mf_ok, mf_data = pcall(function()
                local mf = mf_list:item_at(i)
                if mf:is_armed_citizenry() then return nil end
                local region_standing = ""
                local rs_ok, rs = pcall(function()
                    if mf.has_region_of_standing and mf:has_region_of_standing() then
                        return mf:region_of_standing():name()
                    end
                    return ""
                end)
                if rs_ok then region_standing = rs end
                return {
                    cqi = mf:command_queue_index(),
                    stance = mf:stance(),
                    strength = mf:strength_of_military_force(),
                    region_key = region_standing,
                    num_units = mf:unit_list():num_items(),
                }
            end)
            if mf_ok and mf_data then table.insert(military_forces, mf_data) end
        end

        local culture_name = ""
        pcall(function() culture_name = faction:culture():name() end)
        local subculture_name = ""
        pcall(function() subculture_name = faction:subculture():name() end)

        local inventory_ancillaries = {}
        pcall(function()
            local f_cqi = faction:command_queue_index()
            local anc_size = common.get_context_value("CcoCampaignFaction", f_cqi, "AncillaryList.Size")
            if anc_size and anc_size > 0 then
                for i = 0, anc_size - 1 do
                    local anc_key = ""
                    pcall(function()
                        anc_key = common.get_context_value("CcoCampaignFaction", f_cqi, "AncillaryList.At(" .. i .. ").AncillaryRecordContext.Key")
                    end)
                    local anc_category = ""
                    pcall(function()
                        anc_category = common.get_context_value("CcoCampaignFaction", f_cqi, "AncillaryList.At(" .. i .. ").AncillaryRecordContext.CategoryContext.Key")
                    end)
                    if anc_key ~= "" then
                        table.insert(inventory_ancillaries, {
                            key = anc_key,
                            category = anc_category,
                        })
                    end
                end
            end
        end)

        return {
            key = faction:name(),
            culture = culture_name,
            subculture = subculture_name,
            treasury = faction:treasury(),
            num_regions = region_list:num_items(),
            regions = regions,
            characters = characters,
            military_forces = military_forces,
            inventory_ancillaries = inventory_ancillaries,
            is_human = faction:is_human(),
            is_dead = faction:is_dead(),
        }
    end)
    if ok then return result end
    out("WH3 MCP: Failed to dump faction: " .. tostring(result))
    return nil
end

return dump_faction
