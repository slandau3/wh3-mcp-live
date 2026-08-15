--[[
    Caravan Dumper for WH3 MCP
    Extracts caravan master and active caravan data.
    API: cm:model():world():caravans_system():faction_caravans_by_key(faction_key)
--]]
local dump_caravans = {}

function dump_caravans.run(world)
    local result = {}

    -- Get caravans system
    pcall(function()
        local sys = world:caravans_system()
        if not sys then return end
        result.system_available = true

        -- Local player's faction
        local local_faction = cm:get_local_faction_name(true)
        if not local_faction then return end

        -- Get caravans for the player's faction
        pcall(function()
            local caravans = sys:faction_caravans_by_key(local_faction)
            if not caravans then return end

            -- Active caravans
            pcall(function()
                local active = caravans:active_caravans()
                if active then
                    result.active_caravans = {}
                    for i = 0, active:num_items() - 1 do
                        local cv = active:item_at(i)
                        if cv then
                            local entry = {}
                            pcall(function() entry.force_cqi = cv:caravan_force():command_queue_index() end)
                            pcall(function() entry.cargo = cv:cargo() end)

                            -- Caravan master character
                            pcall(function()
                                local master = cv:caravan_master()
                                if master then
                                    pcall(function()
                                        local char = master:character()
                                        if char then
                                            local mcqi = char:command_queue_index()
                                            entry.master_cqi = mcqi
                                            entry.master_rank = char:rank()
                                            -- CCO for localized name
                                            pcall(function()
                                                entry.master_name = common.get_context_value("CcoCampaignCharacter", mcqi, "Name") or ""
                                            end)
                                            -- force info
                                            local force = char:military_force()
                                            if force then
                                                entry.force_cqi = force:command_queue_index()
                                                entry.force_x = force:x()
                                                entry.force_y = force:y()
                                                -- unit list
                                                local units = force:unit_list()
                                                if units then
                                                    entry.units = {}
                                                    for j = 0, units:num_items() - 1 do
                                                        local u = units:item_at(j)
                                                        if u then
                                                            local ue = { key = u:unit_key(), strength = u:strength() }
                                                            pcall(function() ue.experience = u:experience() end)
                                                            table.insert(entry.units, ue)
                                                        end
                                                    end
                                                end
                                            end
                                        end
                                    end)
                                end
                            end)

                            -- Force directly
                            pcall(function()
                                local force = cv:caravan_force()
                                if force then
                                    entry.force_cqi = force:command_queue_index()
                                    entry.force_x = force:x()
                                    entry.force_y = force:y()
                                    entry.force_faction = force:faction():name()
                                end
                            end)

                            table.insert(result.active_caravans, entry)
                        end
                    end
                end
            end)

            -- Check for other caravan lists (e.g., all caravans)
            pcall(function()
                local all = caravans:all_caravans()
                if all then
                    result.total_caravans = all:num_items()
                end
            end)
        end)
    end)

    return result
end

return dump_caravans
