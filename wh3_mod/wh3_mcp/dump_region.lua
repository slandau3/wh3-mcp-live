--[[
    Region Dumper for WH3 MCP
    Extracts region data including buildings from the campaign model.
--]]
local dump_region = {}

function dump_region.run(region)
    if not region then return nil end
    local ok, result = pcall(function()
        local province_name = ""
        local prov_ok, prov = pcall(function() return region:province() end)
        if prov_ok and prov then
            pcall(function() province_name = prov:name() end)
        end

        local owner_name = ""
        local own_ok, own = pcall(function() return region:owning_faction() end)
        if own_ok and own then
            pcall(function() owner_name = own:name() end)
        end

        local garrison_size = 0
        pcall(function()
            local gar = region:garrison_residence()
            if gar and gar:army() then
                garrison_size = gar:army():unit_list():num_items()
            end
        end)

        local pub_order = 0
        pcall(function() pub_order = region:public_order() end)

        local corruption_val = 0
        pcall(function() corruption_val = region:corruption_level() end)

        local is_cap = false
        pcall(function() is_cap = region:is_province_capital() end)

        local active_edict = ""
        pcall(function()
            if not region:is_null_interface() then
                active_edict = region:get_active_edict_key() or ""
            end
        end)

        local rkey = ""
        pcall(function() rkey = region:name() end)
        local rx = 0
        pcall(function() rx = region:logical_position_x() end)
        local ry = 0
        pcall(function() ry = region:logical_position_y() end)

        local buildings = {}
        local total_slots = 0
        pcall(function()
            local slots = region:slot_list()
            total_slots = slots:num_items()
            for i = 0, slots:num_items() - 1 do
                local slot = slots:item_at(i)
                if slot:active() then
                    local bld = {}
                    bld.slot_index = i
                    pcall(function() bld.slot_type = slot:type() end)
                    if slot:has_building() then
                        local b = slot:building()
                        bld.name = b:name()
                        pcall(function() bld.chain = b:chain() end)
                        pcall(function() bld.superchain = b:superchain() end)
                        pcall(function() bld.building_level = b:building_level() end)
                        pcall(function() bld.percent_health = b:percent_health() end)
                    else
                        bld.name = ""
                    end
                    table.insert(buildings, bld)
                end
            end
        end)

        return {
            key = rkey,
            province = province_name,
            owner_key = owner_name,
            public_order = pub_order,
            corruption = corruption_val,
            x = rx,
            y = ry,
            is_capital = is_cap,
            garrison_size = garrison_size,
            total_slots = total_slots,
            active_edict = active_edict,
            buildings = buildings,
        }
    end)
    if not ok then out("WH3 MCP: dump_region error: " .. tostring(result)) end
    if ok then return result end
    return nil
end

return dump_region
