--[[
    Diplomacy Dumper for WH3 MCP
    Extracts diplomatic relationships between all alive factions.
    Also captures pending diplomatic offers/demands.
--]]
local dump_diplomacy = {}

function dump_diplomacy.run(world)
    local diplomacy = {}

    local faction_list = world:faction_list()
    local factions = {}
    for i = 0, faction_list:num_items() - 1 do
        local f = faction_list:item_at(i)
        if not f:is_dead() then
            table.insert(factions, f)
        end
    end

    -- Build lookup of met factions per faction
    for _, faction in ipairs(factions) do
        local fkey = faction:name()
        diplomacy[fkey] = {
            met = {},
            at_war = {},
            allied = {},
            nap = {},
            trade = {},
            standing = {},
            pending_offers = {},
            pending_demands = {},
        }

        -- Factions met
        pcall(function()
            local met_list = faction:factions_met()
            if met_list then
                for i = 0, met_list:num_items() - 1 do
                    local met = met_list:item_at(i)
                    if not met:is_dead() then
                        table.insert(diplomacy[fkey].met, met:name())
                    end
                end
            end
        end)

        -- Non-aggression pacts
        pcall(function()
            local nap_list = faction:factions_non_aggression_pact_with()
            if nap_list then
                for i = 0, nap_list:num_items() - 1 do
                    local nap = nap_list:item_at(i)
                    if not nap:is_dead() then
                        table.insert(diplomacy[fkey].nap, nap:name())
                    end
                end
            end
        end)

        -- Trade agreements
        pcall(function()
            local trade_list = faction:factions_trading_with()
            if trade_list then
                for i = 0, trade_list:num_items() - 1 do
                    local trade = trade_list:item_at(i)
                    if not trade:is_dead() then
                        table.insert(diplomacy[fkey].trade, trade:name())
                    end
                end
            end
        end)

        -- War and alliances (check against all other alive factions)
        for _, other in ipairs(factions) do
            if other:name() ~= fkey then
                pcall(function()
                    if faction:at_war_with(other) then
                        table.insert(diplomacy[fkey].at_war, other:name())
                    end
                end)
                pcall(function()
                    if faction:allied_with(other) then
                        table.insert(diplomacy[fkey].allied, other:name())
                    end
                end)
                -- Diplomatic standing (attitude value, -1 to 1)
                pcall(function()
                    local standing = faction:diplomatic_standing_with(other)
                    if standing then
                        diplomacy[fkey].standing[other:name()] = standing
                    end
                end)

                -- Pending diplomatic offers from this faction to other
                pcall(function()
                    if cm.is_diplomacy_offer_pending_to_faction then
                        local pending = cm:is_diplomacy_offer_pending_to_faction(faction, other)
                        if pending then
                            local offer = {
                                target = other:name(),
                                proposer = fkey,
                            }
                            -- Try to extract deal type from the pending offer
                            pcall(function()
                                if pending.is_trade_agreement then offer.type = "trade" end
                                if pending.is_non_aggression_pact then offer.type = "nap" end
                                if pending.is_defensive_alliance then offer.type = "defensive_alliance" end
                                if pending.is_military_alliance then offer.type = "military_alliance" end
                                if pending.is_peace_treaty then offer.type = "peace" end
                                if pending.is_war_declaration then offer.type = "war" end
                                if pending.is_confederation then offer.type = "confederation" end
                                if pending.is_vassalage then offer.type = "vassal" end
                            end)
                            -- Acceptance value
                            pcall(function()
                                if pending.acceptance then offer.acceptance = pending:acceptance() end
                            end)
                            table.insert(diplomacy[fkey].pending_offers, offer)
                        end
                    end
                end)

                -- Pending diplomatic demands from this faction to other
                pcall(function()
                    if cm.is_diplomacy_demand_pending_to_faction then
                        local demand = cm:is_diplomacy_demand_pending_to_faction(faction, other)
                        if demand then
                            local d = {
                                target = other:name(),
                                proposer = fkey,
                                is_demand = true,
                            }
                            pcall(function()
                                if demand.is_trade_agreement then d.type = "trade" end
                                if demand.is_non_aggression_pact then d.type = "nap" end
                                if demand.is_defensive_alliance then d.type = "defensive_alliance" end
                                if demand.is_military_alliance then d.type = "military_alliance" end
                                if demand.is_peace_treaty then d.type = "peace" end
                                if demand.is_war_declaration then d.type = "war" end
                                if demand.is_confederation then d.type = "confederation" end
                                if demand.is_vassalage then d.type = "vassal" end
                            end)
                            pcall(function()
                                if demand.acceptance then d.acceptance = demand:acceptance() end
                            end)
                            table.insert(diplomacy[fkey].pending_demands, d)
                        end
                    end
                end)
            end
        end
    end

    -- Also try to get pending deals via cm-level functions
    local all_pending = {}
    pcall(function()
        if cm.get_pending_diplomatic_deals then
            local deals = cm:get_pending_diplomatic_deals()
            if deals then
                for i = 0, deals:num_items() - 1 do
                    pcall(function()
                        local deal = deals:item_at(i)
                        local entry = {}
                        pcall(function() entry.proposer = deal:proposer():name() end)
                        pcall(function() entry.target = deal:target():name() end)
                        pcall(function() entry.is_trade = deal:is_trade_agreement() end)
                        pcall(function() entry.is_nap = deal:is_non_aggression_pact() end)
                        pcall(function() entry.is_defensive = deal:is_defensive_alliance() end)
                        pcall(function() entry.is_military = deal:is_military_alliance() end)
                        pcall(function() entry.is_peace = deal:is_peace_treaty() end)
                        pcall(function() entry.is_war = deal:is_war_declaration() end)
                        pcall(function() entry.is_confederation = deal:is_confederation() end)
                        pcall(function() entry.is_vassal = deal:is_vassalage() end)
                        pcall(function() entry.acceptance = deal:acceptance() end)
                        table.insert(all_pending, entry)
                    end)
                end
            end
        end
    end)

    return {
        factions = diplomacy,
        pending_deals = all_pending,
    }
end

return dump_diplomacy
