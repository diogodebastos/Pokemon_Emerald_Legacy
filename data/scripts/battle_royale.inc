EventScript_BattleRoyaleVictory::
	lockall
	playfanfare MUS_LEVEL_UP
	waitfanfare
	msgbox Text_BattleRoyaleComplete, MSGBOX_DEFAULT
	closemessage
	dofieldeffect FLDEFF_HALL_OF_FAME_RECORD
	waitfieldeffect FLDEFF_HALL_OF_FAME_RECORD
	delay 40
	special GameClear
	waitstate
	releaseall
	end

Text_BattleRoyaleComplete:
	.string "You defeated every TRAINER in HOENN!\p"
	.string "Your name and your partners will be\n"
	.string "recorded for all time!$"

BattleRoyale_Text_GenericIntro:
	.string "I've been waiting for a challenger!$"

BattleRoyale_Text_GenericDefeated:
	.string "You really are something…$"

BattleRoyale_Text_GenericPostBattle:
	.string "I won't forget this battle.$"

@ Shared dialogue for the Kanto Gym Leaders / Elite Four / Champion (issue #5)
BattleRoyale_Text_KantoIntro:
	.string "So you've climbed to face one of\n"
	.string "KANTO's finest.\p"
	.string "Show me the power that carried you\n"
	.string "all the way here!$"

BattleRoyale_Text_KantoDefeated:
	.string "Incredible…\p"
	.string "You battle like a true KANTO\n"
	.string "CHAMPION!$"

BattleRoyale_Text_KantoPostBattle:
	.string "KANTO would be proud of a battle\n"
	.string "like that one.$"

@ Shared dialogue for the Johto Gym Leaders (issue #5)
BattleRoyale_Text_JohtoIntro:
	.string "A challenger from far away!\p"
	.string "Let me show you the strength of\n"
	.string "a JOHTO GYM LEADER!$"

BattleRoyale_Text_JohtoDefeated:
	.string "Well done…\p"
	.string "You've earned the respect of\n"
	.string "JOHTO's very best.$"

BattleRoyale_Text_JohtoPostBattle:
	.string "Visit JOHTO someday. That battle\n"
	.string "was unforgettable.$"

BattleRoyale_Text_SupertrainerIntro:
	.string "So you've climbed your way up to\n"
	.string "face a SUPERTRAINER.\p"
	.string "Only the elite of the ORRE\n"
	.string "COLOSSEUM earn this title.\p"
	.string "Show me you belong here!$"

BattleRoyale_Text_SupertrainerDefeated:
	.string "Incredible…!\p"
	.string "You battle like a true\n"
	.string "COLOSSEUM champion!$"

BattleRoyale_Text_SupertrainerPostBattle:
	.string "A SUPERTRAINER never forgets a\n"
	.string "battle like that.\p"
	.string "ORRE would be proud.$"

BattleRoyale_Text_InfinIntro:
	.string "I am INFIN, a MYTH TRAINER.\p"
	.string "Legends are not born. They are\n"
	.string "forged in battle.\p"
	.string "Let us see which legend stands\n"
	.string "when this is over!$"

BattleRoyale_Text_InfinDefeated:
	.string "So… a new legend is born today.\p"
	.string "The myth lives on through you.$"

BattleRoyale_Text_InfinPostBattle:
	.string "Remember this battle, challenger.\p"
	.string "You have written yourself into\n"
	.string "the legends of ORRE.$"

BattleRoyale_Text_InityIntro:
	.string "I am INITY, the final MYTH\n"
	.string "TRAINER.\p"
	.string "Beyond me there is nothing but\n"
	.string "legend itself.\p"
	.string "Prove you are worthy of it!$"

BattleRoyale_Text_InityDefeated:
	.string "Unbelievable…\p"
	.string "You have surpassed the myth!$"

BattleRoyale_Text_InityPostBattle:
	.string "There is no one left to stand\n"
	.string "in your way.\p"
	.string "Today, you became the legend.$"

BattleRoyale_Text_NolandIntro:
	.string "I'm NOLAND, the FACTORY HEAD!\p"
	.string "I've studied the data on every\n"
	.string "TRAINER in HOENN.\p"
	.string "Let's see if you match the numbers!$"

BattleRoyale_Text_NolandDefeated:
	.string "The data didn't lie…\p"
	.string "You really are that strong.$"

BattleRoyale_Text_NolandPostBattle:
	.string "No amount of analysis could have\n"
	.string "predicted your battling.\p"
	.string "You've gone beyond the data.$"

BattleRoyale_Text_GretaIntro:
	.string "I'm GRETA! The ARENA TYCOON!\p"
	.string "I can feel your fighting spirit\n"
	.string "burning from here!\p"
	.string "Show me everything you've got!$"

BattleRoyale_Text_GretaDefeated:
	.string "What incredible spirit!\p"
	.string "I haven't felt a blaze like\n"
	.string "that in ages!$"

BattleRoyale_Text_GretaPostBattle:
	.string "Your courage burns brighter than\n"
	.string "any TRAINER I've faced.\p"
	.string "Never let that fire go out!$"

BattleRoyale_Text_TuckerIntro:
	.string "I am the one, the only, DOME ACE\n"
	.string "TUCKER!\p"
	.string "The crowd demands a show, and\n"
	.string "I never disappoint!\p"
	.string "Prepare for a spectacular battle!$"

BattleRoyale_Text_TuckerDefeated:
	.string "What a performance…!\p"
	.string "The audience would be on their\n"
	.string "feet right now!$"

BattleRoyale_Text_TuckerPostBattle:
	.string "You stole the spotlight, and I\n"
	.string "can't even be mad about it.\p"
	.string "Bravo… truly bravo!$"

BattleRoyale_Text_LucyIntro:
	.string "…I am LUCY, the PIKE QUEEN.\p"
	.string "Luck won't save you here.\n"
	.string "Only strength matters.$"

BattleRoyale_Text_LucyDefeated:
	.string "…So it wasn't luck after all.\p"
	.string "You have real venom in your\n"
	.string "battling.$"

BattleRoyale_Text_LucyPostBattle:
	.string "…I underestimated you.\p"
	.string "That is a mistake I do not\n"
	.string "make twice.$"

BattleRoyale_Text_SpenserIntro:
	.string "Ho ho! I'm SPENSER, PALACE MAVEN!\p"
	.string "The bond between a TRAINER and\n"
	.string "their POKéMON is everything.\p"
	.string "Show me yours!$"

BattleRoyale_Text_SpenserDefeated:
	.string "Ho ho ho!\p"
	.string "What a magnificent bond you\n"
	.string "share with your POKéMON!$"

BattleRoyale_Text_SpenserPostBattle:
	.string "Nature rewards those who walk\n"
	.string "alongside their partners.\p"
	.string "You and your POKéMON are proof.$"

BattleRoyale_Text_AnabelIntro:
	.string "I am ANABEL, the SALON MAIDEN.\p"
	.string "I can sense the feelings of\n"
	.string "POKéMON… and TRAINERS.\p"
	.string "Your heart burns with resolve.$"

BattleRoyale_Text_AnabelDefeated:
	.string "I felt it… the unbreakable\n"
	.string "trust between you and your\l"
	.string "POKéMON.$"

BattleRoyale_Text_AnabelPostBattle:
	.string "Your heart speaks louder than\n"
	.string "any words could.\p"
	.string "I will remember this feeling.$"

BattleRoyale_Text_BrandonIntro:
	.string "I am BRANDON, PYRAMID KING!\p"
	.string "I have traveled here to test\n"
	.string "the strength of HOENN's trainers!$"

BattleRoyale_Text_BrandonDefeated:
	.string "Superb!\p"
	.string "Your strength is the real thing!$"

BattleRoyale_Text_BrandonPostBattle:
	.string "You have bested the PYRAMID KING.\p"
	.string "I look forward to our next\n"
	.string "encounter!$"

LittlerootTown_Text_RedIntro:
	.string "...$"

LittlerootTown_Text_RedDefeated:
	.string "...$"

LittlerootTown_Text_RedPostBattle:
	.string "... ... ...$"

LittlerootTown_Text_LeafIntro:
	.string "I raised these POKéMON from\n"
	.string "JOHTO all by myself!\p"
	.string "Think you can handle them?$"

LittlerootTown_Text_LeafDefeated:
	.string "No way! My partners...$"

LittlerootTown_Text_LeafPostBattle:
	.string "You're really something.\p"
	.string "RED was right about you.$"
