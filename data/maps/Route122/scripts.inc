Route122_MapScripts::
	.byte 0


Route122_EventScript_FrontierJoyce::
	trainerbattle_single TRAINER_FRONTIER_JOYCE, BattleRoyale_Text_Morty_Intro, BattleRoyale_Text_Morty_Defeated
	msgbox BattleRoyale_Text_Morty_PostBattle, MSGBOX_AUTOCLOSE
	end
