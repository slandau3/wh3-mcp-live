"""Campaign event log tools - read and categorize in-game events."""
import json
from mcp.server.fastmcp import FastMCP
from config import EVENTS_LOG_FILE

EVENT_CATEGORIES = {
    "character": [
        "CharacterAncillaryGained", "CharacterArmoryItemEquipped",
        "CharacterArmoryItemUnequipped", "CharacterArmoryItemUnlocked",
        "CharacterAssignedToPost", "CharacterAttacksAlly",
        "CharacterBecomesFactionLeader", "CharacterBesiegesSettlement",
        "CharacterBlockadedPort", "CharacterBrokePortBlockade",
        "CharacterCanLiberate", "CharacterCandidateBecomesMinister",
        "CharacterCapturedSettlementUnopposed", "CharacterCharacterTargetAction",
        "CharacterComesOfAge", "CharacterCompletedBattle",
        "CharacterConvalescedOrKilled", "CharacterCreated",
        "CharacterDamagedByDisaster", "CharacterDestroyed",
        "CharacterDiscovered", "CharacterDisembarksNavy",
        "CharacterEmbarksNavy", "CharacterEntersAttritionalArea",
        "CharacterEntersGarrison", "CharacterEntersLimboEvent",
        "CharacterFactionChangeEvent", "CharacterFactionCompletesResearch",
        "CharacterFamilyRelationDied", "CharacterFinishedMovingEvent",
        "CharacterGarrisonTargetAction",
        "CharacterInitiativeActivationChangedEvent",
        "CharacterInitiativePresetActivatedEvent",
        "CharacterLeavesGarrison", "CharacterLeavesMilitaryForce",
        "CharacterLoanedEvent", "CharacterLootedSettlement",
        "CharacterMarriage",
        "CharacterMilitaryForceTraditionPointAllocated",
        "CharacterMilitaryForceTraditionPointAvailable",
        "CharacterPaidForUsingPreBattleAbilityOnUnits",
        "CharacterParticipatedAsSecondaryGeneralInBattle",
        "CharacterPerformsActionAgainstFriendlyTarget",
        "CharacterPerformsSettlementOccupationDecision",
        "CharacterPostBattleCaptureOption", "CharacterPreBattleChallenge",
        "CharacterPromoted", "CharacterRankUp", "CharacterRankUpNeedsAncillary",
        "CharacterRazedSettlement", "CharacterRecruited",
        "CharacterRelativeKilled", "CharacterReplacingGeneral",
        "CharacterSackedSettlement",
        "CharacterSettlementBesieged", "CharacterSettlementBlockaded",
        "CharacterSkillPointAllocated", "CharacterSkillPointAvailable",
        "CharacterSuccessfulArmyBribe", "CharacterSuccessfulConvert",
        "CharacterSuccessfulDemoralise", "CharacterSuccessfulInciteRevolt",
        "CharacterTurnEnd", "CharacterTurnStart",
        "CharacterUsedPreBattleAbilityOnUnit",
        "CharacterWaaaghOccurred", "CharacterWithdrewFromBattle",
        "HeroCharacterParticipatedInBattle",
        "NewCharacterEnteredRecruitmentPool",
        "ScriptedAgentCreated", "ScriptedAgentCreationFailed",
        "ScriptedCharacterUnhidden", "ScriptedCharacterUnhiddenFailed",
    ],
    "faction": [
        "FactionAboutToEndTurn", "FactionBecomesIdleHuman",
        "FactionBecomesLiberationProtectorate", "FactionBecomesLiberationVassal",
        "FactionBecomesWorldLeader", "FactionBeginTurnPhaseNormal",
        "FactionBribesUnit", "FactionCapturesWorldCapital",
        "FactionCharacterTagAddedEvent", "FactionCharacterTagEntryEvent",
        "FactionCharacterTagRemovedEvent",
        "FactionCivilWarOccured", "FactionCookedDish",
        "FactionDeath", "FactionEncountersOtherFaction",
        "FactionFameLevelUp", "FactionGainedAncillary", "FactionHordeStatusChange",
        "FactionJoinsConfederation", "FactionLeaderDeclaresWar",
        "FactionLeaderIssuesEdict", "FactionLeaderSignsPeaceTreaty",
        "FactionLiberated", "FactionRoundStart",
        "FactionSubjugatesOtherFaction",
        "FactionTurnEnd", "FactionTurnStart",
    ],
    "region": [
        "RegionAbandonedWithBuildingEvent", "RegionBuildingCancelled",
        "RegionFactionChangeEvent", "RegionGainedDevelopmentPoint",
        "RegionInfectionEvent", "RegionIssuesDemands",
        "RegionPlagueStateChanged", "RegionRebels", "RegionRiots",
        "RegionStrikes", "RegionTurnEnd", "RegionTurnStart",
        "RegionWindsOfMagicChanged", "PreRegionFactionChangeEvent",
        "CorruptionCounterIntervalEvent", "ClimatePhaseChange",
        "SettlementClimateChanged",
    ],
    "diplomacy": [
        "DiplomacyManipulationExecutedEvent", "DiplomacyNegotiationStarted",
        "DiplomaticOfferRejected", "DuelDemanded",
        "NegativeDiplomaticEvent", "PositiveDiplomaticEvent",
        "TradeLinkEstablished", "TradeNodeConnected", "TradeRouteEstablished",
        "LandTradeRouteRaided", "SeaTradeRouteRaided",
        "WarCoordinationRequestIssued",
    ],
    "battle": [
        "PendingBattle", "PreBattle",
        "CharacterCompletedBattle", "CharacterWithdrewFromBattle",
        "PostBattleCaptiveOptionOutcomeApplied", "PostbattleRewardAnimationsFinished",
        "CampaignSettlementAttacked", "CampaignCoastalAssaultOnCharacter",
        "CampaignCoastalAssaultOnGarrison",
        "GarrisonAttackedEvent", "GarrisonOccupiedEvent",
        "GarrisonResidenceCaptured", "GarrisonResidenceExposedToFaction",
        "SiegeLifted", "UngarrisonedFort",
        "HistoricBattleEvent",
    ],
    "building": [
        "BuildingCancelled", "BuildingCompleted",
        "BuildingConstructionIssuedByPlayer", "BuildingLifecycleDevelops",
        "CampaignBuildingDamaged",
        "MilitaryForceBuildingCancelled", "MilitaryForceBuildingCompleteEvent",
        "ForeignSlotBuildingCompleteEvent", "ForeignSlotBuildingDamagedEvent",
        "ForeignSlotManagerCreatedEvent", "ForeignSlotManagerDiscoveredEvent",
    ],
    "military": [
        "CampaignArmiesMerge", "CampaignArmiesMergeCompleted",
        "ForceAdoptsStance", "MilitaryForceCreated", "MilitaryForceDestroyed",
        "MilitaryForceDevelopmentPointChange", "MilitaryForceInfectionEvent",
        "SpawnableForceCreatedEvent", "ScriptedForceCreated",
    ],
    "unit": [
        "UnitAboutToBeDestroyedByBattle", "UnitCompletedBattle",
        "UnitConverted", "UnitCreated", "UnitDisbanded",
        "UnitDisembarkCompleted", "UnitEffectPurchased",
        "UnitEffectUnpurchased", "UnitMergedAndDestroyed",
        "UnitTrained", "UnitTurnEnd", "UnitUpgraded",
    ],
    "mission": [
        "MissionCancelled", "MissionFailed", "MissionGenerationFailed",
        "MissionIssued", "MissionNearingExpiry", "MissionSucceeded",
        "HaveCharacterWithinRangeOfPositionMissionEvaluationResultEvent",
        "DilemmaChoiceMadeEvent", "DilemmaGenerationFailedEvent",
        "DilemmaIssuedEvent", "DilemmaOrIncidentStarted", "DillemaOrIncidentStarted",
        "IncidentEvent", "IncidentFailedEvent", "IncidentOccuredEvent",
    ],
    "research": [
        "ResearchCompleted", "ResearchStarted",
    ],
    "caravan": [
        "CaravanCompleted", "CaravanEvent", "CaravanMoved", "CaravanReturned",
        "CaravanSpawned", "CaravanWaylaid", "QueryShouldWaylayCaravan",
    ],
    "settlement": [
        "SettlementMarkedForTypeConversionEvent", "SettlementOccupied",
        "SettlementUnMarkedForTypeConversionEvent",
        "SlotOpens", "SlotRoundStart", "SlotTurnStart",
    ],
    "recruitment": [
        "RecruitmentItemCancelledByPlayer", "RecruitmentItemIssuedByPlayer",
    ],
    "resource": [
        "PooledResourceChanged", "PooledResourceEffectChangedEvent",
        "PooledResourceRegularIncome", "CampaignEffectsBundleAwarded",
        "ForcePlagueStateChanged",
    ],
    "ritual": [
        "RitualCancelledEvent", "RitualCompletedEvent",
        "RitualEvent", "RitualStartedEvent",
    ],
    "teleportation": [
        "QueryTeleportationNetworkShouldHandoverCharacterNodeClosure",
        "TeleportationNetworkCharacterInteractionStarted",
        "TeleportationNetworkCharacterNodeClosureHandedOver",
        "TeleportationNetworkMoveCompleted", "TeleportationNetworkMoveStart",
        "TeleportationNetworkNodeClosed", "TeleportationNetworkNodeEvent",
        "TeleportationNetworkNodeOpened",
    ],
    "ancillary": [
        "AncillariesFused", "FactionGainedAncillary", "TriggerPostBattleAncillaries",
    ],
    "agent_action": [
        "ArmyBribeAttemptFailure", "ArmySabotageAttemptFailure",
        "ArmySabotageAttemptSuccess", "ConvertAttemptFailure",
        "DemoraliseAttemptFailure", "InciteRevoltAttemptFailure",
        "SabotageAttemptFailure", "SabotageAttemptSuccess",
    ],
    "lifecycle": [
        "CampaignSessionEnded", "FirstTickAfterNewCampaignStarted",
        "FirstTickAfterWorldCreated", "LoadingGame", "ModelCreated",
        "NewCampaignStarted", "SavingGame", "WorldCreated",
        "WorldStartRound", "WorldStartTurn", "EndOfRound",
    ],
    "governor": [
        "ProvinceGovernorAppointed", "ProvinceGovernorMoved",
        "ProvinceGovernorshipNewDecisionAvailable",
    ],
    "imprisonment": [
        "ImprisonmenRejectiontEvent", "ImprisonmentEvent",
        "ImprisonmentRejectionEvent",
    ],
    "compass": [
        "WoMCompassUserActionTriggeredEvent", "WoMCompassUserDirectionSelectedEvent",
    ],
    "victory": [
        "VictoryConditionFailed", "VictoryConditionMet",
    ],
    "movement": [
        "LocationEntered", "LocationUnveiled", "MovementPointsExhausted", "MultiTurnMove",
    ],
    "historical": [
        "HistoricBattleEvent", "HistoricalCharacters", "HistoricalEvents",
    ],
}

# Build reverse lookup: event_name -> category
_EVENT_TO_CATEGORY: dict = {}
for _cat, _events in EVENT_CATEGORIES.items():
    for _ev in _events:
        _EVENT_TO_CATEGORY[_ev] = _cat


def _read_events(limit: int = 0, category: str = "", event_name: str = "",
                 after_turn: int = 0, before_turn: int = 0) -> list:
    """Read events from JSONL log file with optional filters."""
    if not EVENTS_LOG_FILE.exists():
        return []
    events = []
    try:
        with open(EVENTS_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if event_name and entry.get("event") != event_name:
                    continue
                if category:
                    cat = _EVENT_TO_CATEGORY.get(entry.get("event"), "other")
                    if cat != category:
                        continue
                turn = entry.get("turn", 0)
                if after_turn and turn < after_turn:
                    continue
                if before_turn and turn > before_turn:
                    continue

                entry["category"] = _EVENT_TO_CATEGORY.get(entry.get("event"), "other")
                events.append(entry)
    except Exception:
        return []

    if limit and limit > 0:
        events = events[-limit:]
    return events


def register(mcp: FastMCP):

    @mcp.tool()
    def get_latest_events(limit: int = 20, category: str = "",
                         event_name: str = "", after_turn: int = 0,
                         before_turn: int = 0) -> str:
        """Get latest campaign events, optionally filtered and categorized.

        Args:
            limit: Max events to return (default 20, 0 for all)
            category: Filter by category. Options: character, faction, region, diplomacy,
                      battle, building, military, unit, mission, research, caravan, settlement,
                      recruitment, resource, ritual, teleportation, ancillary, agent_action,
                      lifecycle, governor, imprisonment, compass, victory, movement, historical
            event_name: Filter by exact event name (e.g. "FactionTurnStart")
            after_turn: Only events on or after this turn
            before_turn: Only events on or before this turn
        """
        events = _read_events(limit, category, event_name, after_turn, before_turn)
        return json.dumps({"count": len(events), "events": events}, indent=2)

    @mcp.tool()
    def get_event_categories() -> str:
        """List all event categories and their event counts."""
        summary = {}
        for cat, evts in EVENT_CATEGORIES.items():
            summary[cat] = len(evts)
        # Count actual logged events per category
        if EVENTS_LOG_FILE.exists():
            counts: dict = {}
            try:
                with open(EVENTS_LOG_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            cat = _EVENT_TO_CATEGORY.get(entry.get("event"), "other")
                            counts[cat] = counts.get(cat, 0) + 1
                        except json.JSONDecodeError:
                            continue
            except Exception:
                pass
            summary["logged_counts"] = counts
        return json.dumps(summary, indent=2)

    @mcp.tool()
    def get_events_by_turn(turn: int) -> str:
        """Get all events for a specific turn number.

        Args:
            turn: Turn number to filter by
        """
        events = _read_events(after_turn=turn, before_turn=turn)
        return json.dumps({"turn": turn, "count": len(events), "events": events}, indent=2)
