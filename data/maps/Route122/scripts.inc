Route122_MapScripts::
	.byte 0


Route122_EventScript_BattleRoyaleMorty::
	trainerbattle_single TRAINER_BATTLE_ROYALE_MORTY, BattleRoyale_Text_Morty_Intro, BattleRoyale_Text_Morty_Defeated
	msgbox BattleRoyale_Text_Morty_PostBattle, MSGBOX_AUTOCLOSE
	end
