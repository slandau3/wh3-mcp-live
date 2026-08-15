--[[
    Character Dumper for WH3 MCP
    Extracts character data from the campaign model.
--]]
local dump_character = {}

function dump_character.run(char)
    if not char then return nil end

    local ok, result = pcall(function()
        local details = char:character_details()
        local faction = char:faction()
        local region = char:region()
        local mf = nil
        local has_army = char:has_military_force()
        if has_army then
            mf = char:military_force()
        end

        local units = {}
        if has_army and mf then
            local unit_list = mf:unit_list()
            for i = 0, unit_list:num_items() - 1 do
                local unit = unit_list:item_at(i)
                local ukey = ""
                pcall(function() ukey = unit:unit_key() end)
                local ustr = 0
                pcall(function() ustr = unit:percentage_proportion_of_full_strength() end)
                local uexp = 0
                pcall(function() uexp = unit:experience_level() end)
                local urank = 0
                pcall(function() urank = unit:rank() end)
                table.insert(units, {
                    key = ukey,
                    strength = ustr,
                    experience = uexp,
                    rank = urank,
                })
            end
        end

        local ancillaries = {}
        pcall(function()
            local cqi = char:cqi()
            local anc_size = common.get_context_value("CcoCampaignCharacter", cqi, "AncillaryList.Size")
            if anc_size and anc_size > 0 then
                for i = 0, anc_size - 1 do
                    local anc_key = ""
                    pcall(function()
                        anc_key = common.get_context_value("CcoCampaignCharacter", cqi, "AncillaryList.At(" .. i .. ").AncillaryRecordContext.Key")
                    end)
                    local anc_category = ""
                    pcall(function()
                        anc_category = common.get_context_value("CcoCampaignCharacter", cqi, "AncillaryList.At(" .. i .. ").AncillaryRecordContext.CategoryContext.Key")
                    end)
                    if anc_key ~= "" then
                        table.insert(ancillaries, {
                            key = anc_key,
                            category = anc_category,
                        })
                    end
                end
            end
        end)

        local region_name = ""
        pcall(function() if region then region_name = region:name() end end)
        local faction_name = ""
        pcall(function() if faction then faction_name = faction:name() end end)

        local char_cqi = 0
        pcall(function() char_cqi = char:cqi() end)
        local char_rank = 0
        pcall(function() char_rank = char:rank() end)
        local char_loyalty = 0
        pcall(function() char_loyalty = char:loyalty() end)
        local char_x = 0
        pcall(function() char_x = char:logical_position_x() end)
        local char_y = 0
        pcall(function() char_y = char:logical_position_y() end)
        local char_type = ""
        pcall(function() char_type = char:character_type_key() end)

        local char_name = ""
        local detail_subtype = ""
        pcall(function()
            char_name = common.get_context_value("CcoCampaignCharacter", char_cqi, "Name") or ""
        end)
        pcall(function()
            detail_subtype = details:agent_subtype_key() or ""
        end)
        -- Fallback: try direct character methods
        if detail_subtype == "" then
            pcall(function() detail_subtype = char:character_subtype_key() or "" end)
        end
        if detail_subtype == "" then
            pcall(function() detail_subtype = char:agent_subtype_key() or "" end)
        end
        -- Fallback: try context API
        if detail_subtype == "" then
            pcall(function()
                detail_subtype = common.get_context_value("CcoCampaignCharacter", char_cqi, "AgentSubtype.Key") or ""
            end)
        end

        -- Extract lore from unit key (e.g. wh3_main_ksl_frost_maiden_tempest_0)
        local lore = ""
        if has_army and mf then
            pcall(function()
                local unit_list = mf:unit_list()
                for i = 0, unit_list:num_items() - 1 do
                    local ukey = unit_list:item_at(i):unit_key()
                    if ukey and ukey:find("frost_maiden") then
                        if ukey:find("tempest") then lore = "Tempest"
                        elseif ukey:find("ice") then lore = "Ice"
                        end
                        break
                    end
                end
            end)
        end

        local stance = ""
        pcall(function() if has_army and mf then stance = mf:stance() end end)

        local is_leader = false
        pcall(function()
            if faction then
                local leader = faction:faction_leader()
                if leader and leader:cqi() == char_cqi then
                    is_leader = true
                end
            end
        end)

        return {
            cqi = char_cqi,
            name = char_name,
            character_type = char_type,
            subtype = detail_subtype,
            lore = lore,
            rank = char_rank,
            loyalty = char_loyalty,
            x = char_x,
            y = char_y,
            region_key = region_name,
            faction_key = faction_name,
            is_leader = is_leader,
            has_army = has_army,
            army_stance = stance,
            units = units,
            ancillaries = ancillaries,
        }
    end)
    if not ok then out("WH3 MCP: dump_character error: " .. tostring(result)) end
    if ok then return result end
    return nil
end

return dump_character
