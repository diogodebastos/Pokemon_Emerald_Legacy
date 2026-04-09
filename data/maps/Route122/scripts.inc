Route122_MapScripts::
	.byte 0


Route122_EventScript_FrontierJoyce::
	trainerbattle_single TRAINER_FRONTIER_JOYCE, BattleRoyale_Text_GenericIntro, BattleRoyale_Text_GenericDefeated
	msgbox BattleRoyale_Text_GenericPostBattle, MSGBOX_AUTOCLOSE
	end
