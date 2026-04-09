LilycoveCity_DepartmentStore_4F_MapScripts::
	.byte 0

LilycoveCity_DepartmentStore_4F_EventScript_Gentleman::
	lock
	faceplayer
	message gText_HowMayIServeYou
	waitmessage
	pokemart LilycoveCity_DepartmentStore_4F_Pokemart_Berries1
	msgbox gText_PleaseComeAgain, MSGBOX_DEFAULT
	release
	end

	.align 2
LilycoveCity_DepartmentStore_4F_Pokemart_Berries1:
	.2byte ITEM_CHERI_BERRY
	.2byte ITEM_CHESTO_BERRY
	.2byte ITEM_PECHA_BERRY
	.2byte ITEM_RAWST_BERRY
	.2byte ITEM_ASPEAR_BERRY
	.2byte ITEM_LEPPA_BERRY
	.2byte ITEM_ORAN_BERRY
	.2byte ITEM_PERSIM_BERRY
	.2byte ITEM_LUM_BERRY
	.2byte ITEM_SITRUS_BERRY
	.2byte ITEM_FIGY_BERRY
	.2byte ITEM_WIKI_BERRY
	.2byte ITEM_MAGO_BERRY
	.2byte ITEM_AGUAV_BERRY
	.2byte ITEM_IAPAPA_BERRY
	.2byte ITEM_RAZZ_BERRY
	.2byte ITEM_BLUK_BERRY
	.2byte ITEM_NANAB_BERRY
	.2byte ITEM_WEPEAR_BERRY
	.2byte ITEM_PINAP_BERRY
	.2byte ITEM_POMEG_BERRY
	.2byte ITEM_KELPSY_BERRY
	.2byte ITEM_NONE
	release
	end

LilycoveCity_DepartmentStore_4F_EventScript_Woman::
	lock
	faceplayer
	message gText_HowMayIServeYou
	waitmessage
	pokemart LilycoveCity_DepartmentStore_4F_Pokemart_Berries2
	msgbox gText_PleaseComeAgain, MSGBOX_DEFAULT
	release
	end

	.align 2
LilycoveCity_DepartmentStore_4F_Pokemart_Berries2:
	.2byte ITEM_QUALOT_BERRY
	.2byte ITEM_HONDEW_BERRY
	.2byte ITEM_GREPA_BERRY
	.2byte ITEM_TAMATO_BERRY
	.2byte ITEM_CORNN_BERRY
	.2byte ITEM_MAGOST_BERRY
	.2byte ITEM_RABUTA_BERRY
	.2byte ITEM_NOMEL_BERRY
	.2byte ITEM_SPELON_BERRY
	.2byte ITEM_PAMTRE_BERRY
	.2byte ITEM_WATMEL_BERRY
	.2byte ITEM_DURIN_BERRY
	.2byte ITEM_BELUE_BERRY
	.2byte ITEM_LIECHI_BERRY
	.2byte ITEM_GANLON_BERRY
	.2byte ITEM_SALAC_BERRY
	.2byte ITEM_PETAYA_BERRY
	.2byte ITEM_APICOT_BERRY
	.2byte ITEM_LANSAT_BERRY
	.2byte ITEM_STARF_BERRY
	.2byte ITEM_ENIGMA_BERRY
	.2byte ITEM_NONE
	release
	end

LilycoveCity_DepartmentStore_4F_EventScript_Youngster::
	msgbox LilycoveCity_DepartmentStore_4F_Text_PokemonOnlyHaveFourMoves, MSGBOX_NPC
	end

LilycoveCity_DepartmentStore_4F_Text_PokemonOnlyHaveFourMoves:
	.string "I'd like to get all the different TMs,\n"
	.string "but a POKéMON learns only four moves.$"

LilycoveCity_DepartmentStore_4F_EventScript_ClerkLeft::
	lock
	faceplayer
	message gText_HowMayIServeYou
	waitmessage
	pokemart LilycoveCity_DepartmentStore_4F_Pokemart_AllTMs
	msgbox gText_PleaseComeAgain, MSGBOX_DEFAULT
	release
	end

	.align 2
LilycoveCity_DepartmentStore_4F_Pokemart_AllTMs:
	.2byte ITEM_TM_FOCUS_PUNCH
	.2byte ITEM_TM_DRAGON_CLAW
	.2byte ITEM_TM_WATER_PULSE
	.2byte ITEM_TM_CALM_MIND
	.2byte ITEM_TM_ROAR
	.2byte ITEM_TM_TOXIC
	.2byte ITEM_TM_HAIL
	.2byte ITEM_TM_BULK_UP
	.2byte ITEM_TM_BULLET_SEED
	.2byte ITEM_TM_HIDDEN_POWER
	.2byte ITEM_TM_SUNNY_DAY
	.2byte ITEM_TM_TAUNT
	.2byte ITEM_TM_ICE_BEAM
	.2byte ITEM_TM_BLIZZARD
	.2byte ITEM_TM_HYPER_BEAM
	.2byte ITEM_TM_LIGHT_SCREEN
	.2byte ITEM_TM_PROTECT
	.2byte ITEM_TM_RAIN_DANCE
	.2byte ITEM_TM_GIGA_DRAIN
	.2byte ITEM_TM_SAFEGUARD
	.2byte ITEM_TM_FRUSTRATION
	.2byte ITEM_TM_SOLAR_BEAM
	.2byte ITEM_TM_IRON_TAIL
	.2byte ITEM_TM_THUNDERBOLT
	.2byte ITEM_TM_THUNDER
	.2byte ITEM_TM_EARTHQUAKE
	.2byte ITEM_TM_RETURN
	.2byte ITEM_TM_DIG
	.2byte ITEM_TM_PSYCHIC
	.2byte ITEM_TM_SHADOW_BALL
	.2byte ITEM_TM_BRICK_BREAK
	.2byte ITEM_TM_DOUBLE_TEAM
	.2byte ITEM_TM_REFLECT
	.2byte ITEM_TM_SHOCK_WAVE
	.2byte ITEM_TM_FLAMETHROWER
	.2byte ITEM_TM_SLUDGE_BOMB
	.2byte ITEM_TM_SANDSTORM
	.2byte ITEM_TM_FIRE_BLAST
	.2byte ITEM_TM_ROCK_TOMB
	.2byte ITEM_TM_AERIAL_ACE
	.2byte ITEM_TM_TORMENT
	.2byte ITEM_TM_FACADE
	.2byte ITEM_TM_SECRET_POWER
	.2byte ITEM_TM_REST
	.2byte ITEM_TM_ATTRACT
	.2byte ITEM_TM_THIEF
	.2byte ITEM_TM_STEEL_WING
	.2byte ITEM_TM_SKILL_SWAP
	.2byte ITEM_TM_SNATCH
	.2byte ITEM_TM_OVERHEAT
	.2byte ITEM_NONE
	release
	end

LilycoveCity_DepartmentStore_4F_EventScript_ClerkRight::
	lock
	faceplayer
	message gText_HowMayIServeYou
	waitmessage
	pokemart LilycoveCity_DepartmentStore_4F_Pokemart_AllTMs
	msgbox gText_PleaseComeAgain, MSGBOX_DEFAULT
	release
	end

