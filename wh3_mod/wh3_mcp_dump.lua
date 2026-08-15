--[[
    WH3 Real-Time MCP State Dumper
    -------------------------------
    Modular entry point. Pack structure:
      script/campaign/mod/wh3_mcp_dump.lua       (this file)
      script/campaign/mod/wh3_mcp/json.lua
      script/campaign/mod/wh3_mcp/dump_character.lua
      script/campaign/mod/wh3_mcp/dump_region.lua
      script/campaign/mod/wh3_mcp/dump_faction.lua
      script/campaign/mod/wh3_mcp/dump_diplomacy.lua
      script/campaign/mod/wh3_mcp/dump_caravans.lua
      script/campaign/mod/wh3_mcp/dump_technology.lua
      script/campaign/mod/wh3_mcp/dump_compass.lua

    Installation:
      Create a .pack file (script type) with RPFM containing these files.
--]]

-- ============================================================
-- CONFIGURATION
-- ============================================================
-- EDIT THIS: absolute folder where the mod writes state dumps and the agent
-- exchanges files (create it beforehand, e.g. C:\wh3-mcp-data)
local OUTPUT_DIR = [[C:\wh3-mcp-data]]
local TRIGGER_PATH = OUTPUT_DIR .. [[\dump_trigger.txt]]
local DUMP_INTERVAL = 30

-- Agent exec bridge (AI-driven mod development)
local EXEC_DIR = OUTPUT_DIR .. [[\exec]]
local EXEC_SCRIPT_PATH = EXEC_DIR .. [[\exec_script.lua]]
local EXEC_TRIGGER_PATH = EXEC_DIR .. [[\exec_trigger.txt]]
local EXEC_RESULT_PATH = EXEC_DIR .. [[\exec_result.json]]

-- ============================================================
-- MODULES
-- ============================================================
local json = require("wh3_mcp.json")
local dump_faction = require("wh3_mcp.dump_faction")
local dump_diplomacy = require("wh3_mcp.dump_diplomacy")
local dump_caravans = require("wh3_mcp.dump_caravans")
local dump_technology = require("wh3_mcp.dump_technology")
local dump_compass = require("wh3_mcp.dump_compass")

-- ============================================================
-- HELPERS
-- ============================================================

local function write_json(filename, data)
    local path = OUTPUT_DIR .. [[\]] .. filename
    local json_str = json.encode(data)
    local file = io.open(path, "w")
    if file then
        file:write(json_str)
        file:close()
        return #json_str
    else
        out("WH3 MCP: ERROR - Could not open " .. path .. " for writing")
        return 0
    end
end

-- ============================================================
-- GAME STATE DUMPING
-- ============================================================

local function dump_game_state()
    out("WH3 MCP: Starting state dump...")
    local ok, err = pcall(function()
        local model = cm:model()
        local world = model:world()

        local turn_number = cm:turn_number()
        local local_faction = cm:get_local_faction_name(true)
        local turn_faction = ""

        if cm.turn_restricted_to_faction then
            local turn_fac = cm:turn_restricted_to_faction()
            if turn_fac then
                turn_faction = turn_fac:name()
            end
        end

        out("WH3 MCP: Turn " .. turn_number .. ", faction: " .. local_faction)

        -- 1. Campaign metadata
        local meta = {
            timestamp = os.time(),
            turn_number = turn_number,
            turn_faction = turn_faction,
            local_faction = local_faction,
        }
        local meta_size = write_json("campaign_state.json", meta)
        out("WH3 MCP: campaign_state.json (" .. meta_size .. " bytes)")

        -- 2. Factions: collect metadata, regions, characters separately
        local factions = {}
        local all_regions = {}
        local all_characters = {}
        local faction_list = world:faction_list()
        for i = 0, faction_list:num_items() - 1 do
            local faction = faction_list:item_at(i)
            if not faction:is_dead() then
                local f = dump_faction.run(faction)
                if f then
                    -- Extract regions and characters, keep rest in faction meta
                    local fkey = f.key
                    for _, r in ipairs(f.regions or {}) do
                        r.owner_key = fkey
                        table.insert(all_regions, r)
                    end
                    for _, c in ipairs(f.characters or {}) do
                        c.faction_key = fkey
                        table.insert(all_characters, c)
                    end
                    f.regions = nil
                    f.characters = nil
                    table.insert(factions, f)
                end
            end
        end
        local factions_size = write_json("factions_state.json", {factions = factions})
        local regions_size = write_json("regions_state.json", {regions = all_regions})
        local chars_size = write_json("characters_state.json", {characters = all_characters})
        out("WH3 MCP: factions_state.json (" .. factions_size .. " bytes, " .. #factions .. " factions)")
        out("WH3 MCP: regions_state.json (" .. regions_size .. " bytes, " .. #all_regions .. " regions)")
        out("WH3 MCP: characters_state.json (" .. chars_size .. " bytes, " .. #all_characters .. " characters)")

        -- 3. Diplomacy
        local dip_ok, dip = pcall(function() return dump_diplomacy.run(world) end)
        if dip_ok and dip then
            local dip_size = write_json("diplomacy_state.json", dip)
            out("WH3 MCP: diplomacy_state.json (" .. dip_size .. " bytes)")
        else
            out("WH3 MCP: Diplomacy dump failed: " .. tostring(dip))
        end

        -- 4. Caravans
        local cv_ok, cv = pcall(function() return dump_caravans.run(world) end)
        if cv_ok and cv then
            local cv_size = write_json("caravans_state.json", cv)
            out("WH3 MCP: caravans_state.json (" .. cv_size .. " bytes)")
        else
            out("WH3 MCP: Caravan dump failed: " .. tostring(cv))
        end

        -- 5. Technology
        local tech_ok, tech = pcall(function()
            local local_faction_name = cm:get_local_faction_name(true)
            local faction = world:faction_by_key(local_faction_name)
            return dump_technology.run(faction)
        end)
        if tech_ok and tech then
            local tech_size = write_json("technology_state.json", tech)
            out("WH3 MCP: technology_state.json (" .. tech_size .. " bytes)")
        else
            out("WH3 MCP: Technology dump failed: " .. tostring(tech))
        end

        -- 6. Compass
        local compass_ok, compass = pcall(function()
            local local_faction_name = cm:get_local_faction_name(true)
            local faction = world:faction_by_key(local_faction_name)
            return dump_compass.run(faction)
        end)
        if compass_ok and compass then
            local compass_size = write_json("compass_state.json", compass)
            out("WH3 MCP: compass_state.json (" .. compass_size .. " bytes)")
        else
            out("WH3 MCP: Compass dump failed: " .. tostring(compass))
        end

        out("WH3 MCP: State dumped successfully!")
    end)
    if not ok then
        out("WH3 MCP: CRASH - " .. tostring(err))
    end
end

-- ============================================================
-- CAMPAIGN EVENT LOGGER (inlined — cannot be a separate module)
-- ============================================================

local event_buffer = {}
local event_counter = 0
local EVENTS_STATE_PATH = OUTPUT_DIR .. [[\events_state.json]]
local EVENTS_MAX_BUFFER = 50

local function try_string(context, method)
    local ok, val = pcall(function() return context[method](context) end)
    if ok and val ~= nil and type(val) == "string" and val ~= "" then return val end
    return nil
end

local function try_number(context, method)
    local ok, val = pcall(function() return context[method](context) end)
    if ok and val ~= nil and type(val) == "number" then return val end
    return nil
end

local function try_bool(context, method)
    local ok, val = pcall(function() return context[method](context) end)
    if ok and type(val) == "boolean" then return val end
    return nil
end

local function extract_faction(faction)
    if not faction then return nil end
    local data = {}
    pcall(function() data.key = faction:name() end)
    pcall(function() data.is_human = faction:is_human() end)
    pcall(function() data.is_dead = faction:is_dead() end)
    pcall(function() data.treasury = math.floor(faction:treasury()) end)
    local culture = ""
    pcall(function() culture = faction:culture():name() end)
    if culture ~= "" then data.culture = culture end
    local subculture = ""
    pcall(function() subculture = faction:subculture():name() end)
    if subculture ~= "" then data.subculture = subculture end
    return data
end

local function extract_character(char)
    if not char then return nil end
    local data = {}
    pcall(function() data.cqi = char:cqi() end)
    pcall(function() data.rank = char:rank() end)
    pcall(function() data.character_type = char:character_type_key() end)
    pcall(function() data.x = char:logical_position_x() end)
    pcall(function() data.y = char:logical_position_y() end)
    pcall(function() data.faction_key = char:faction():name() end)
    pcall(function()
        if char:has_region() then data.region_key = char:region():name() end
    end)
    pcall(function()
        if char:has_military_force() then
            data.has_army = true
            data.army_stance = char:military_force():stance()
        end
    end)
    return data
end

local function extract_region(region)
    if not region then return nil end
    local data = {}
    pcall(function() data.key = region:name() end)
    pcall(function()
        if region:owning_faction() then data.owner_key = region:owning_faction():name() end
    end)
    pcall(function() data.province = region:province_name() end)
    pcall(function() data.is_capital = region:is_province_capital() end)
    return data
end

local function extract_mf(mf)
    if not mf then return nil end
    local data = {}
    pcall(function() data.cqi = mf:command_queue_index() end)
    pcall(function() data.stance = mf:stance() end)
    pcall(function() data.strength = mf:strength_of_military_force() end)
    pcall(function() data.num_units = mf:unit_list():num_items() end)
    return data
end

local function extract_event_context(context)
    if not context then return {} end
    local data = {}
    pcall(function()
        if context.faction then
            local f = context:faction()
            if f then data.faction = extract_faction(f) end
        end
    end)
    pcall(function()
        if context.character then
            local c = context:character()
            if c then data.character = extract_character(c) end
        end
    end)
    pcall(function()
        if context.region then
            local r = context:region()
            if r then data.region = extract_region(r) end
        end
    end)
    pcall(function()
        if context.military_force then
            local mf = context:military_force()
            if mf then data.military_force = extract_mf(mf) end
        end
    end)
    pcall(function()
        if context.building then
            local b = context:building()
            if b then
                data.building = {}
                pcall(function() data.building.key = b:name() end)
                pcall(function() data.building.level = b:building_level() end)
            end
        end
    end)
    pcall(function()
        if context.unit then
            local u = context:unit()
            if u then
                data.unit = {}
                pcall(function() data.unit.key = u:unit_key() end)
                pcall(function() data.unit.experience = u:experience_level() end)
            end
        end
    end)
    for _, field in ipairs({"faction_key", "character_key", "region_key", "building_key", "dilemma", "mission_key", "ancillary_key", "technology_key", "agent_action_key", "stance", "reason", "string"}) do
        local val = try_string(context, field)
        if val then data[field] = val end
    end
    for _, field in ipairs({"character_cqi", "faction_cqi", "cqi", "index"}) do
        local val = try_number(context, field)
        if val then data[field] = val end
    end
    for _, field in ipairs({"is_human", "is_victory"}) do
        local val = try_bool(context, field)
        if val ~= nil then data[field] = val end
    end
    -- Diplomacy context
    pcall(function()
        if context.proposing_faction then
            local pf = context:proposing_faction()
            if pf then data.proposing_faction = extract_faction(pf) end
        end
    end)
    pcall(function()
        if context.target_faction then
            local tf = context:target_faction()
            if tf then data.target_faction = extract_faction(tf) end
        end
    end)
    pcall(function()
        if context.proposer then
            local pr = context:proposer()
            if pr then
                data.proposer = {}
                pcall(function() data.proposer.key = pr:name() end)
            end
        end
    end)
    pcall(function()
        if context.target then
            local tg = context:target()
            if tg then
                data.target = {}
                pcall(function() data.target.key = tg:name() end)
            end
        end
    end)
    for _, fn in ipairs({
        "is_trade_agreement", "is_non_aggression_pact",
        "is_defensive_alliance", "is_military_alliance",
        "is_peace_treaty", "is_war_declaration",
        "is_confederation", "is_vassalage",
        "is_payment", "is_join_war",
    }) do
        local val = try_bool(context, fn)
        if val ~= nil then data[fn] = val end
    end
    local acc = try_number(context, "acceptance")
    if acc then data.acceptance = acc end
    return data
end

local function flush_events()
    if #event_buffer == 0 then return end

    local current_turn = 0
    pcall(function() current_turn = cm:turn_number() end)

    local existing = {}
    local file = io.open(EVENTS_STATE_PATH, "r")
    if file then
        for line in file:lines() do
            if line ~= "" then
                local ok, entry = pcall(function()
                    local t = line:match('"turn"%s*:%s*(%d+)')
                    return { line = line, turn = tonumber(t) or 0 }
                end)
                if ok and entry then table.insert(existing, entry) end
            end
        end
        file:close()
    end

    -- Find max turn in existing file
    local max_stored_turn = 0
    for _, e in ipairs(existing) do
        if e.turn > max_stored_turn then max_stored_turn = e.turn end
    end

    -- If current turn is less than stored turns, user reloaded an older save — clear old data
    if current_turn < max_stored_turn then
        existing = {}
    end

    for _, entry in ipairs(event_buffer) do
        table.insert(existing, { line = json.encode(entry), turn = entry.turn or 0 })
    end
    event_buffer = {}

    local turns = {}
    for _, e in ipairs(existing) do turns[e.turn] = true end
    local sorted_turns = {}
    for t in pairs(turns) do table.insert(sorted_turns, t) end
    table.sort(sorted_turns, function(a, b) return a > b end)
    local keep_turn1 = sorted_turns[1] or -1
    local keep_turn2 = sorted_turns[2] or -1
    local filtered = {}
    for _, e in ipairs(existing) do
        if e.turn == keep_turn1 or e.turn == keep_turn2 then
            table.insert(filtered, e.line)
        end
    end
    local out_file = io.open(EVENTS_STATE_PATH, "w")
    if out_file then
        for _, line in ipairs(filtered) do
            out_file:write(line .. "\n")
        end
        out_file:close()
    end
end

local function add_event(event_name, context)
    event_counter = event_counter + 1
    local entry = {
        id = event_counter,
        event = event_name,
        timestamp = os.time(),
        turn = 0,
        data = {},
    }
    pcall(function() entry.turn = cm:turn_number() end)
    local ed_ok, ed_data = pcall(function() return extract_event_context(context) end)
    if ed_ok and ed_data then entry.data = ed_data end
    table.insert(event_buffer, entry)
    if #event_buffer >= EVENTS_MAX_BUFFER then flush_events() end
end

local ALL_EVENTS = {
    "AncillariesFused", "CharacterAncillaryGained", "FactionGainedAncillary", "TriggerPostBattleAncillaries",
    "ArmyBribeAttemptFailure", "ArmySabotageAttemptFailure", "ArmySabotageAttemptSuccess",
    "ConvertAttemptFailure", "DemoraliseAttemptFailure", "InciteRevoltAttemptFailure",
    "SabotageAttemptFailure", "SabotageAttemptSuccess",
    "CharacterSuccessfulArmyBribe", "CharacterSuccessfulConvert",
    "CharacterSuccessfulDemoralise", "CharacterSuccessfulInciteRevolt",
    "CharacterPerformsActionAgainstFriendlyTarget", "CharacterCharacterTargetAction", "CharacterGarrisonTargetAction",
    "CampaignArmiesMerge", "CampaignArmiesMergeCompleted", "ForceAdoptsStance",
    "MilitaryForceCreated", "MilitaryForceDestroyed",
    "MilitaryForceBuildingCancelled", "MilitaryForceBuildingCompleteEvent",
    "MilitaryForceDevelopmentPointChange", "MilitaryForceInfectionEvent",
    "SpawnableForceCreatedEvent", "ScriptedForceCreated",
    "BuildingCancelled", "BuildingCompleted", "BuildingConstructionIssuedByPlayer",
    "BuildingLifecycleDevelops", "CampaignBuildingDamaged", "RegionBuildingCancelled",
    "RegionAbandonedWithBuildingEvent",
    "CampaignSessionEnded", "FirstTickAfterNewCampaignStarted", "FirstTickAfterWorldCreated",
    "LoadingGame", "ModelCreated", "NewCampaignStarted", "SavingGame",
    "WorldCreated", "WorldStartRound", "WorldStartTurn", "EndOfRound",
    "CaravanCompleted", "CaravanEvent", "CaravanMoved", "CaravanReturned",
    "CaravanSpawned", "CaravanWaylaid", "QueryShouldWaylayCaravan",
    "CharacterArmoryItemEquipped", "CharacterArmoryItemUnequipped", "CharacterArmoryItemUnlocked",
    "CharacterAssignedToPost", "CharacterAttacksAlly", "CharacterBecomesFactionLeader",
    "CharacterBesiegesSettlement", "CharacterBlockadedPort", "CharacterBrokePortBlockade",
    "CharacterCanLiberate", "CharacterCandidateBecomesMinister", "CharacterCapturedSettlementUnopposed",
    "CharacterComesOfAge", "CharacterCompletedBattle", "CharacterConvalescedOrKilled",
    "CharacterCreated", "CharacterDamagedByDisaster", "CharacterDestroyed",
    "CharacterDiscovered", "CharacterDisembarksNavy", "CharacterEmbarksNavy",
    "CharacterEntersAttritionalArea", "CharacterEntersGarrison", "CharacterEntersLimboEvent",
    "CharacterFactionChangeEvent", "CharacterFactionCompletesResearch", "CharacterFamilyRelationDied",
    "CharacterFinishedMovingEvent", "CharacterInitiativeActivationChangedEvent",
    "CharacterInitiativePresetActivatedEvent", "CharacterLeavesGarrison", "CharacterLeavesMilitaryForce",
    "CharacterLoanedEvent", "CharacterLootedSettlement", "CharacterMarriage",
    "CharacterMilitaryForceTraditionPointAllocated", "CharacterMilitaryForceTraditionPointAvailable",
    "CharacterPaidForUsingPreBattleAbilityOnUnits", "CharacterParticipatedAsSecondaryGeneralInBattle",
    "CharacterPerformsSettlementOccupationDecision", "CharacterPostBattleCaptureOption",
    "CharacterPreBattleChallenge", "CharacterPromoted", "CharacterRankUp", "CharacterRankUpNeedsAncillary",
    "CharacterRazedSettlement", "CharacterRecruited", "CharacterRelativeKilled",
    "CharacterReplacingGeneral", "CharacterSackedSettlement",
    "CharacterSettlementBesieged", "CharacterSettlementBlockaded",
    "CharacterSkillPointAllocated", "CharacterSkillPointAvailable",
    "CharacterTurnEnd", "CharacterTurnStart", "CharacterUsedPreBattleAbilityOnUnit",
    "CharacterWaaaghOccurred", "CharacterWithdrewFromBattle",
    "HeroCharacterParticipatedInBattle", "NewCharacterEnteredRecruitmentPool",
    "ScriptedAgentCreated", "ScriptedAgentCreationFailed",
    "ScriptedCharacterUnhidden", "ScriptedCharacterUnhiddenFailed",
    "ClimatePhaseChange", "CorruptionCounterIntervalEvent", "RegionWindsOfMagicChanged", "SettlementClimateChanged",
    "DilemmaChoiceMadeEvent", "DilemmaGenerationFailedEvent", "DilemmaIssuedEvent",
    "DilemmaOrIncidentStarted", "DillemaOrIncidentStarted",
    "IncidentEvent", "IncidentFailedEvent", "IncidentOccuredEvent",
    "DiplomacyManipulationExecutedEvent", "DiplomacyNegotiationStarted", "DiplomaticOfferRejected",
    "DuelDemanded", "NegativeDiplomaticEvent", "PositiveDiplomaticEvent",
    "TradeLinkEstablished", "TradeNodeConnected", "TradeRouteEstablished",
    "LandTradeRouteRaided", "SeaTradeRouteRaided", "WarCoordinationRequestIssued",
    "FactionAboutToEndTurn", "FactionBecomesIdleHuman", "FactionBecomesLiberationProtectorate",
    "FactionBecomesLiberationVassal", "FactionBecomesWorldLeader", "FactionBeginTurnPhaseNormal",
    "FactionBribesUnit", "FactionCapturesWorldCapital",
    "FactionCharacterTagAddedEvent", "FactionCharacterTagEntryEvent", "FactionCharacterTagRemovedEvent",
    "FactionCivilWarOccured", "FactionCookedDish", "FactionDeath", "FactionEncountersOtherFaction",
    "FactionFameLevelUp", "FactionHordeStatusChange", "FactionJoinsConfederation",
    "FactionLeaderDeclaresWar", "FactionLeaderIssuesEdict", "FactionLeaderSignsPeaceTreaty",
    "FactionLiberated", "FactionRoundStart", "FactionSubjugatesOtherFaction",
    "FactionTurnEnd", "FactionTurnStart",
    "CampaignCoastalAssaultOnCharacter", "CampaignCoastalAssaultOnGarrison", "CampaignSettlementAttacked",
    "GarrisonAttackedEvent", "GarrisonOccupiedEvent", "GarrisonResidenceCaptured",
    "GarrisonResidenceExposedToFaction", "SiegeLifted", "UngarrisonedFort",
    "ForeignSlotBuildingCompleteEvent", "ForeignSlotBuildingDamagedEvent",
    "ForeignSlotManagerCreatedEvent", "ForeignSlotManagerDiscoveredEvent",
    "HistoricBattleEvent", "HistoricalCharacters", "HistoricalEvents",
    "ImprisonmenRejectiontEvent", "ImprisonmentEvent", "ImprisonmentRejectionEvent",
    "LocationEntered", "LocationUnveiled", "MovementPointsExhausted", "MultiTurnMove",
    "HaveCharacterWithinRangeOfPositionMissionEvaluationResultEvent",
    "MissionCancelled", "MissionFailed", "MissionGenerationFailed",
    "MissionIssued", "MissionNearingExpiry", "MissionSucceeded",
    "PooledResourceChanged", "PooledResourceEffectChangedEvent", "PooledResourceRegularIncome",
    "PendingBattle", "PreBattle", "PostBattleCaptiveOptionOutcomeApplied", "PostbattleRewardAnimationsFinished",
    "ProvinceGovernorAppointed", "ProvinceGovernorMoved", "ProvinceGovernorshipNewDecisionAvailable",
    "RecruitmentItemCancelledByPlayer", "RecruitmentItemIssuedByPlayer",
    "RegionFactionChangeEvent", "RegionGainedDevelopmentPoint", "RegionInfectionEvent",
    "RegionIssuesDemands", "RegionPlagueStateChanged", "RegionRebels", "RegionRiots",
    "RegionStrikes", "RegionTurnEnd", "RegionTurnStart", "PreRegionFactionChangeEvent",
    "CampaignEffectsBundleAwarded", "ForcePlagueStateChanged",
    "ResearchCompleted", "ResearchStarted",
    "RitualCancelledEvent", "RitualCompletedEvent", "RitualEvent", "RitualStartedEvent",
    "SettlementMarkedForTypeConversionEvent", "SettlementOccupied", "SettlementUnMarkedForTypeConversionEvent",
    "SlotOpens", "SlotRoundStart", "SlotTurnStart",
    "QueryTeleportationNetworkShouldHandoverCharacterNodeClosure",
    "TeleportationNetworkCharacterInteractionStarted", "TeleportationNetworkCharacterNodeClosureHandedOver",
    "TeleportationNetworkMoveCompleted", "TeleportationNetworkMoveStart",
    "TeleportationNetworkNodeClosed", "TeleportationNetworkNodeEvent", "TeleportationNetworkNodeOpened",
    "UnitAboutToBeDestroyedByBattle", "UnitCompletedBattle", "UnitConverted", "UnitCreated",
    "UnitDisbanded", "UnitDisembarkCompleted", "UnitEffectPurchased", "UnitEffectUnpurchased",
    "UnitMergedAndDestroyed", "UnitTrained", "UnitTurnEnd", "UnitUpgraded",
    "VictoryConditionFailed", "VictoryConditionMet",
    "WoMCompassUserActionTriggeredEvent", "WoMCompassUserDirectionSelectedEvent",
}

local function register_event_listeners()
    for _, event_name in ipairs(ALL_EVENTS) do
        core:add_listener(
            "WH3MCP_Event_" .. event_name,
            event_name,
            true,
            function(context)
                pcall(function() add_event(event_name, context) end)
            end,
            true
        )
    end
    out("WH3 MCP: Event logger registered (" .. #ALL_EVENTS .. " campaign events)")
end

-- ============================================================
-- TRIGGER WATCHER (for on-demand dumps)
-- ============================================================

local last_trigger_time = 0

local function check_trigger()
    local file = io.open(TRIGGER_PATH, "r")
    if file then
        local content = file:read("*a")
        file:close()
        local trigger_time = tonumber(content) or 0
        if trigger_time > last_trigger_time then
            last_trigger_time = trigger_time
            dump_game_state()
        end
    end
end

-- ============================================================
-- AGENT EXEC BRIDGE (AI-driven live Lua execution)
-- ============================================================

local last_exec_trigger_time = 0
local exec_output_buffer = {}
local original_out = out

-- Agent scripts call this to send data back to the result file.
function wh3_exec_out(text)
    table.insert(exec_output_buffer, tostring(text))
end

local function write_file(path, data)
    local file = io.open(path, "w")
    if file then
        file:write(data)
        file:close()
        return true
    end
    return false
end

local function run_exec_script()
    exec_output_buffer = {}
    _G.wh3_exec_result = nil

    local script = io.open(EXEC_SCRIPT_PATH, "r")
    if not script then
        local res = {
            ok = false,
            error = "exec_script.lua not found",
            output = "",
            timestamp = os.time(),
        }
        write_file(EXEC_RESULT_PATH, json.encode(res))
        return
    end
    local chunk = script:read("*a")
    script:close()

    -- Capture any out() calls made by the exec script into the buffer
    out = function(text)
        table.insert(exec_output_buffer, tostring(text))
        return original_out(text)
    end

    local ok, err = pcall(function()
        local fn, perr = loadstring(chunk, "wh3_exec")
        if not fn then error(perr or "loadstring failed") end
        fn()
    end)

    out = original_out

    local result_json = nil
    if _G.wh3_exec_result ~= nil then
        local r_ok, encoded = pcall(json.encode, _G.wh3_exec_result)
        if r_ok then result_json = encoded end
    end

    local res = {
        ok = ok,
        error = ok and "" or tostring(err),
        output = table.concat(exec_output_buffer, "\n"),
        result = result_json,
        timestamp = os.time(),
    }
    write_file(EXEC_RESULT_PATH, json.encode(res))
    out("WH3 MCP: Exec ran, ok=" .. tostring(ok) .. ", output lines=" .. #exec_output_buffer)

    -- Refresh state so the agent immediately sees the effects
    pcall(dump_game_state)
end

local function check_exec_trigger()
    local file = io.open(EXEC_TRIGGER_PATH, "r")
    if file then
        local content = file:read("*a")
        file:close()
        local trigger_time = tonumber(content) or 0
        if trigger_time > last_exec_trigger_time then
            last_exec_trigger_time = trigger_time
            pcall(run_exec_script)
        end
    end
end

-- ============================================================
-- INITIALIZATION
-- ============================================================

cm:add_first_tick_callback(function()
    out("WH3 MCP: ====== MOD LOADED ======")
    out("WH3 MCP: Output dir: " .. OUTPUT_DIR)
    out("WH3 MCP: Dump interval: " .. DUMP_INTERVAL .. "s")
    dump_game_state()

    -- Register campaign event logger
    register_event_listeners()

    -- Flush events + check exec bridge periodically (fast poll)
    cm:real_callback(
        function()
            pcall(flush_events)
            pcall(check_exec_trigger)
        end,
        5,
        "wh3_mcp_events_flush"
    )

    -- Use real_callback for periodic dumps
    cm:real_callback(
        function()
            pcall(function()
                check_trigger()
                dump_game_state()
            end)
        end,
        DUMP_INTERVAL,
        "wh3_mcp_auto_dump"
    )
    out("WH3 MCP: Auto-dump timer started (interval: " .. DUMP_INTERVAL .. "s)")

    -- Also use FactionTurnStart as a backup trigger
    core:add_listener(
        "WH3MCP_TurnStartDump",
        "FactionTurnStart",
        function(context)
            return context:faction():is_human()
        end,
        function(context)
            dump_game_state()
        end,
        true
    )
end)

-- Dump on turn end
core:add_listener(
    "WH3MCP_TurnEndDump",
    "FactionTurnEnd",
    true,
    function(context)
        dump_game_state()
    end,
    true
)

-- Track technology research
core:add_listener(
    "WH3MCP_ResearchStarted",
    "ResearchStarted",
    true,
    function(context)
        pcall(function() dump_technology.on_research_started(context) end)
        dump_game_state()
    end,
    true
)

core:add_listener(
    "WH3MCP_ResearchCompleted",
    "ResearchCompleted",
    true,
    function(context)
        pcall(function() dump_technology.on_research_completed(context) end)
        dump_game_state()
    end,
    true
)

-- Track compass direction changes
core:add_listener(
    "WH3MCP_CompassDirection",
    "WoMCompassUserDirectionSelectedEvent",
    true,
    function(context)
        pcall(function() dump_compass.on_direction_selected(context) end)
        dump_game_state()
    end,
    true
)

-- Dump on game save
core:add_listener(
    "WH3MCP_GameSaved",
    "SavingGame",
    true,
    function(context)
        flush_events()
        dump_game_state()
    end,
    true
)

out("WH3 MCP: State dumper loaded (interval: " .. DUMP_INTERVAL .. "s)")
