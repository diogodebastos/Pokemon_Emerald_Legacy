EverGrandeCity_MapScripts::
	map_script MAP_SCRIPT_ON_TRANSITION, EverGrandeCity_OnTransition
	.byte 0

EverGrandeCity_OnTransition:
	call_if_set FLAG_SYS_WEATHER_CTRL, Common_EventScript_SetAbnormalWeather
	end

EverGrandeCity_EventScript_VictoryRoadSign::
	msgbox EverGrandeCity_Text_EnteringVictoryRoad, MSGBOX_SIGN
	end

EverGrandeCity_EventScript_CitySign::
	msgbox EverGrandeCity_Text_CitySign, MSGBOX_SIGN
	end

EverGrandeCity_EventScript_PokemonLeagueSign::
	msgbox EverGrandeCity_Text_EnteringPokemonLeague, MSGBOX_SIGN
	end

EverGrandeCity_EventScript_SetVisitedEverGrande::
	setflag FLAG_VISITED_EVER_GRANDE_CITY
	setvar VAR_TEMP_1, 1
	end

EverGrandeCity_Text_EnteringVictoryRoad:
	.string "ENTERING VICTORY ROAD$"

EverGrandeCity_Text_EnteringPokemonLeague:
	.string "ENTERING POKéMON LEAGUE\n"
	.string "CENTER GATE$"

EverGrandeCity_Text_CitySign:
	.string "EVER GRANDE CITY\p"
	.string "“The paradise of flowers, the sea,\n"
	.string "and POKéMON.”$"

EverGrandeCity_EventScript_GrindingNurse::
	lock
	faceplayer
	cleartrainerflag TRAINER_GRINDING_NURSE
	trainerbattle_single TRAINER_GRINDING_NURSE, EverGrandeCity_Text_NurseIntro, EverGrandeCity_Text_NurseDefeat, EverGrandeCity_EventScript_NursePostBattle
	release
	end

EverGrandeCity_EventScript_NursePostBattle::
	msgbox EverGrandeCity_Text_NurseReady, MSGBOX_DEFAULT
	release
	end

EverGrandeCity_Text_NurseIntro:
	.string "I'm here to help you train!\n"
	.string "My BLISSEY team is ready!$"

EverGrandeCity_Text_NurseDefeat:
	.string "Great work! Your POKéMON are\n"
	.string "getting stronger!$"

EverGrandeCity_Text_NurseReady:
	.string "Your POKéMON are looking good!\n"
	.string "I'm ready whenever you are!$"

EverGrandeCity_EventScript_MrMimic::
	lock
	faceplayer
	cleartrainerflag TRAINER_BATTLE_ROYALE_MR_MIMIC
	trainerbattle_single TRAINER_BATTLE_ROYALE_MR_MIMIC, EverGrandeCity_Text_MimicIntro, EverGrandeCity_Text_MimicDefeat, EverGrandeCity_EventScript_MimicPostBattle
	release
	end

EverGrandeCity_EventScript_MimicPostBattle::
	msgbox EverGrandeCity_Text_MimicReady, MSGBOX_DEFAULT
	release
	end

EverGrandeCity_Text_MimicIntro:
	.string "Heh heh… I am MR. MIMIC.\n"
	.string "I shall fight you… as YOU!\p"
	.string "Behold a perfect copy of your\n"
	.string "own team!$"

EverGrandeCity_Text_MimicDefeat:
	.string "To lose to yourself…\n"
	.string "how delicious!$"

EverGrandeCity_Text_MimicReady:
	.string "Come again whenever you wish to\n"
	.string "face your mirror.$"

EverGrandeCity_EventScript_BattleRoyaleInity::
	trainerbattle_single TRAINER_BATTLE_ROYALE_INITY, BattleRoyale_Text_InityIntro, BattleRoyale_Text_InityDefeated
	msgbox BattleRoyale_Text_InityPostBattle, MSGBOX_AUTOCLOSE
	end

