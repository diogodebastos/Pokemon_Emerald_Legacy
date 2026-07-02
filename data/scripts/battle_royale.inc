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

@ Per-leader dialogue for the Kanto/Johto Gym Leaders (issue #7)
BattleRoyale_Text_Brock_Intro:
	.string "My rock-hard defense won't crumble\nto a challenger like you!$"
BattleRoyale_Text_Brock_Defeated:
	.string "I took your best hit... and I'm\nthe one left standing? No...\pyou've won.$"
BattleRoyale_Text_Brock_PostBattle:
	.string "Temper your defense like your\noffense. That's the rock-solid\pway.$"

BattleRoyale_Text_Misty_Intro:
	.string "I'm the tomboyish mermaid! Don't\nthink I'll go easy on you!$"
BattleRoyale_Text_Misty_Defeated:
	.string "Okay, okay! You're tougher than a\nhooked GYARADOS!$"
BattleRoyale_Text_Misty_PostBattle:
	.string "My water POKéMON and I will train\neven harder. Count on it!$"

BattleRoyale_Text_LtSurge_Intro:
	.string "Ten-hut! Let's see if you can\nhandle my voltage, civilian!$"
BattleRoyale_Text_LtSurge_Defeated:
	.string "Gaah! Short-circuited by a kid...!$"
BattleRoyale_Text_LtSurge_PostBattle:
	.string "You've got the firepower, soldier.\nSURGE approves.$"

BattleRoyale_Text_Erika_Intro:
	.string "Welcome... I had dozed off. But I\nam wide awake now. Shall we?$"
BattleRoyale_Text_Erika_Defeated:
	.string "Oh my... I have lost. How\nstrangely refreshing.$"
BattleRoyale_Text_Erika_PostBattle:
	.string "The scent of victory suits you.\nPlease, visit again.$"

BattleRoyale_Text_Koga_Intro:
	.string "Fwahaha! A taste of a genuine\nninja's poison awaits you!$"
BattleRoyale_Text_Koga_Defeated:
	.string "...You have seen through my\nsmokescreen.$"
BattleRoyale_Text_Koga_PostBattle:
	.string "A true ninja knows when to vanish.\nUntil we meet again.$"

BattleRoyale_Text_Sabrina_Intro:
	.string "I foresaw your arrival... and your\ndefeat. Let us test the vision.$"
BattleRoyale_Text_Sabrina_Defeated:
	.string "My prediction... was wrong? That\nis not possible...$"
BattleRoyale_Text_Sabrina_PostBattle:
	.string "You have bent the future I saw. I\nshall not forget this.$"

BattleRoyale_Text_Blaine_Intro:
	.string "Hah! My POKéMON are red-hot. Think\nyou can take the heat?$"
BattleRoyale_Text_Blaine_Defeated:
	.string "Yeeowch! You doused my flames!$"
BattleRoyale_Text_Blaine_PostBattle:
	.string "Here's a hot tip: that was the\nfinest battle in ages!$"

BattleRoyale_Text_Giovanni_Intro:
	.string "So. You challenge the boss.\nBold... and foolish.$"
BattleRoyale_Text_Giovanni_Defeated:
	.string "...Hmph. You have power. I respect\nonly power.$"
BattleRoyale_Text_Giovanni_PostBattle:
	.string "Remember this name. Our paths may\ncross once more.$"

BattleRoyale_Text_Lorelei_Intro:
	.string "No one bests me when it comes to\nicy POKéMON.$"
BattleRoyale_Text_Lorelei_Defeated:
	.string "How could my chill be melted...?$"
BattleRoyale_Text_Lorelei_PostBattle:
	.string "A warm heart and a cool head. A\nrare and dangerous pair.$"

BattleRoyale_Text_Bruno_Intro:
	.string "We will grind you down with raw\npower! Hoo hah!$"
BattleRoyale_Text_Bruno_Defeated:
	.string "Why...? How could I lose...?$"
BattleRoyale_Text_Bruno_PostBattle:
	.string "I must train body and mind\nfurther. You have shown me that.$"

BattleRoyale_Text_Agatha_Intro:
	.string "Heh heh! OAK's little prodigy\nthinks they can beat me?$"
BattleRoyale_Text_Agatha_Defeated:
	.string "You're stronger than your years...\nbah!$"
BattleRoyale_Text_Agatha_PostBattle:
	.string "You remind me of OAK when he was\nyoung. Take that as praise, brat.$"

BattleRoyale_Text_Lance_Intro:
	.string "I am LANCE, master of dragons.\nWitness their fury!$"
BattleRoyale_Text_Lance_Defeated:
	.string "There is no shame in this\ndefeat... you are magnificent.$"
BattleRoyale_Text_Lance_PostBattle:
	.string "A new dragon-tamer's spirit burns\nin you. Soar high.$"

BattleRoyale_Text_Blue_Intro:
	.string "First I'll crush you, then I'll\nsmell ya later. I'm the best,\pafter all!$"
BattleRoyale_Text_Blue_Defeated:
	.string "What?! I picked the wrong... no.\nYou were just better.$"
BattleRoyale_Text_Blue_PostBattle:
	.string "...Heh. Don't let it go to your\nhead. I'll be back on top.$"

BattleRoyale_Text_Falkner_Intro:
	.string "I'll show you the real power of my\nmagnificent birds!$"
BattleRoyale_Text_Falkner_Defeated:
	.string "My father's birds... brought down\nto earth.$"
BattleRoyale_Text_Falkner_PostBattle:
	.string "I'll carry on VIOLET GYM's legacy,\nstronger than ever.$"

BattleRoyale_Text_Bugsy_Intro:
	.string "I never lose when it comes to bug\nPOKéMON. It's all research!$"
BattleRoyale_Text_Bugsy_Defeated:
	.string "Whoa! I have to rethink my entire\nthesis!$"
BattleRoyale_Text_Bugsy_PostBattle:
	.string "So much data! Bug POKéMON are\ndeeper than you'd ever think!$"

BattleRoyale_Text_Whitney_Intro:
	.string "Hiii! Everyone loves cute POKéMON,\nright? Now battle me!$"
BattleRoyale_Text_Whitney_Defeated:
	.string "Waaah! You meanie! ...sniff...\nfine, you won.$"
BattleRoyale_Text_Whitney_PostBattle:
	.string "Okay, I'm done crying. That was\nactually really fun!$"

BattleRoyale_Text_Morty_Intro:
	.string "I see it. A great trainer. But can\nyou see my ghosts?$"
BattleRoyale_Text_Morty_Defeated:
	.string "So... the one in my visions was\nyou all along.$"
BattleRoyale_Text_Morty_PostBattle:
	.string "HO-OH willing, we shall battle\nagain one day.$"

BattleRoyale_Text_Chuck_Intro:
	.string "RAAAH! My training under the\nwaterfall ends in YOUR defeat!$"
BattleRoyale_Text_Chuck_Defeated:
	.string "GWAAH! Beaten! My wife was right\nto nag me!$"
BattleRoyale_Text_Chuck_PostBattle:
	.string "You've got fighting spirit! Train\nwith me at the falls sometime!$"

BattleRoyale_Text_Jasmine_Intro:
	.string "Um... I'll do my best. My steel\nPOKéMON are very dear to me.$"
BattleRoyale_Text_Jasmine_Defeated:
	.string "Oh... thank you for such a\nwonderful battle.$"
BattleRoyale_Text_Jasmine_PostBattle:
	.string "I feel a little braver now. Thank\nyou, truly.$"

BattleRoyale_Text_Pryce_Intro:
	.string "I've weathered countless winters.\nYour warmth won't melt me.$"
BattleRoyale_Text_Pryce_Defeated:
	.string "Even the oldest ice... must thaw\nsomeday.$"
BattleRoyale_Text_Pryce_PostBattle:
	.string "You endured the cold. That is the\nheart of a champion.$"

BattleRoyale_Text_Clair_Intro:
	.string "I am CLAIR, the world's finest\ndragon master. Bow before me!$"
BattleRoyale_Text_Clair_Defeated:
	.string "...! This can't be! I am... I\nwas... beaten?$"
BattleRoyale_Text_Clair_PostBattle:
	.string "Hmph. You've earned my respect.\nDon't expect it twice.$"

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
