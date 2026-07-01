Route122_MapScripts::
	.byte 0


Route122_EventScript_FrontierJoyce::
	trainerbattle_single TRAINER_FRONTIER_JOYCE, BattleRoyale_Text_JohtoIntro, BattleRoyale_Text_JohtoDefeated
	msgbox BattleRoyale_Text_JohtoPostBattle, MSGBOX_AUTOCLOSE
	end
