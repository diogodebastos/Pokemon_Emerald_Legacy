#include "global.h"
#include "bg.h"
#include "battle_main.h"
#include "event_data.h"
#include "gpu_regs.h"
#include "main.h"
#include "menu.h"
#include "palette.h"
#include "party_menu.h"
#include "pokemon.h"
#include "pokemon_summary_screen.h"
#include "pokemon_stat_editor.h"
#include "scanline_effect.h"
#include "sound.h"
#include "sprite.h"
#include "string_util.h"
#include "strings.h"
#include "task.h"
#include "text.h"
#include "text_window.h"
#include "window.h"
#include "constants/abilities.h"
#include "constants/pokemon.h"
#include "constants/rgb.h"
#include "constants/songs.h"

enum {
    STAT_EDITOR_HP,
    STAT_EDITOR_ATK,
    STAT_EDITOR_DEF,
    STAT_EDITOR_SPEED,
    STAT_EDITOR_SPATK,
    STAT_EDITOR_SPDEF,
    STAT_EDITOR_COUNT
};

enum {
    CONTEST_EDITOR_COOL,
    CONTEST_EDITOR_BEAUTY,
    CONTEST_EDITOR_CUTE,
    CONTEST_EDITOR_SMART,
    CONTEST_EDITOR_TOUGH,
    CONTEST_EDITOR_SHEEN,
    CONTEST_EDITOR_COUNT
};

enum {
    MODE_IV,
    MODE_EV,
    MODE_MISC,
    MODE_CONTEST,
    MODE_COUNT
};

enum {
    WIN_TITLE,
    WIN_STATS
};

#define tCursorPos  data[0]
#define tMode       data[1]
#define tSlotId     data[2]
#define tState      data[3]
#define tRepeatTimer data[4]

#define MAX_COMPETITIVE_EVS 252

static void Task_StatEditorFadeIn(u8 taskId);
static void Task_StatEditorProcessInput(u8 taskId);
static void Task_StatEditorSave(u8 taskId);
static void Task_StatEditorFadeOut(u8 taskId);
static void DrawStatEditorTitle(u8 taskId);
static void DrawStatEditorStats(u8 taskId);
static void MainCB2(void);
static void VBlankCB(void);
void ChangeMonNature(void);
void MakeMonShiny(void);
void MakeMonNotShiny(void);

static EWRAM_DATA u16 sEditIVs[STAT_EDITOR_COUNT] = {0};
static EWRAM_DATA u16 sEditEVs[STAT_EDITOR_COUNT] = {0};
static EWRAM_DATA u16 sEditLevel = 0;
static EWRAM_DATA u16 sEditFriendship = 0;
static EWRAM_DATA u8 sEditAbilityNum = 0;
static EWRAM_DATA u8 sEditNature = 0;
static EWRAM_DATA u8 sEditIsShiny = 0;
static EWRAM_DATA u8 sEditContestStats[CONTEST_EDITOR_COUNT] = {0};

static const u8 sText_ModeIVs[] = _("IVs");
static const u8 sText_ModeEVs[] = _("EVs");
static const u8 sText_ModeMisc[] = _("MISC");
static const u8 sText_ModeContest[] = _("CONTEST");
static const u8 sText_EditStats[] = _("EDIT STATS");
static const u8 sText_HP[] = _("HP");
static const u8 sText_Attack[] = _("ATTACK");
static const u8 sText_Defense[] = _("DEFENSE");
static const u8 sText_Speed[] = _("SPEED");
static const u8 sText_SpAtk[] = _("SP.ATK");
static const u8 sText_SpDef[] = _("SP.DEF");
static const u8 sText_Level[] = _("LEVEL");
static const u8 sText_Happiness[] = _("HAPPINESS");
static const u8 sText_Ability[] = _("ABILITY");
static const u8 sText_Nature[] = _("NATURE");
static const u8 sText_Color[] = _("COLOR");
static const u8 sText_Normal[] = _("NORMAL");
static const u8 sText_Shiny[] = _("SHINY");
static const u8 sText_Cool[] = _("COOL");
static const u8 sText_Beauty[] = _("BEAUTY");
static const u8 sText_Cute[] = _("CUTE");
static const u8 sText_Smart[] = _("SMART");
static const u8 sText_Tough[] = _("TOUGH");
static const u8 sText_Sheen[] = _("SHEEN");
static const u8 sText_Space[] = _(" ");
static const u8 sText_Slash[] = _("/");
static const u8 sText_Hint[] = _("{DPAD_LEFTRIGHT} Val SEL:Toggle L/R:Tab");

static const u8 *const sStatNames[STAT_EDITOR_COUNT] = {
    [STAT_EDITOR_HP]    = sText_HP,
    [STAT_EDITOR_ATK]   = sText_Attack,
    [STAT_EDITOR_DEF]   = sText_Defense,
    [STAT_EDITOR_SPEED] = sText_Speed,
    [STAT_EDITOR_SPATK] = sText_SpAtk,
    [STAT_EDITOR_SPDEF] = sText_SpDef,
};

static const u8 sIVDataIds[STAT_EDITOR_COUNT] = {
    MON_DATA_HP_IV,
    MON_DATA_ATK_IV,
    MON_DATA_DEF_IV,
    MON_DATA_SPEED_IV,
    MON_DATA_SPATK_IV,
    MON_DATA_SPDEF_IV,
};

static const u8 sEVDataIds[STAT_EDITOR_COUNT] = {
    MON_DATA_HP_EV,
    MON_DATA_ATK_EV,
    MON_DATA_DEF_EV,
    MON_DATA_SPEED_EV,
    MON_DATA_SPATK_EV,
    MON_DATA_SPDEF_EV,
};

static const u8 *const sContestNames[CONTEST_EDITOR_COUNT] = {
    [CONTEST_EDITOR_COOL]   = sText_Cool,
    [CONTEST_EDITOR_BEAUTY] = sText_Beauty,
    [CONTEST_EDITOR_CUTE]   = sText_Cute,
    [CONTEST_EDITOR_SMART]  = sText_Smart,
    [CONTEST_EDITOR_TOUGH]  = sText_Tough,
    [CONTEST_EDITOR_SHEEN]  = sText_Sheen,
};

static const u8 sContestDataIds[CONTEST_EDITOR_COUNT] = {
    MON_DATA_COOL,
    MON_DATA_BEAUTY,
    MON_DATA_CUTE,
    MON_DATA_SMART,
    MON_DATA_TOUGH,
    MON_DATA_SHEEN,
};

enum {
    MISC_EDITOR_LEVEL,
    MISC_EDITOR_HAPPINESS,
    MISC_EDITOR_ABILITY,
    MISC_EDITOR_NATURE,
    MISC_EDITOR_COLOR,
    MISC_EDITOR_COUNT
};

static const u8 *const sMiscNames[MISC_EDITOR_COUNT] = {
    [MISC_EDITOR_LEVEL] = sText_Level,
    [MISC_EDITOR_HAPPINESS] = sText_Happiness,
    [MISC_EDITOR_ABILITY] = sText_Ability,
    [MISC_EDITOR_NATURE] = sText_Nature,
    [MISC_EDITOR_COLOR] = sText_Color,
};

static const struct WindowTemplate sStatEditorWinTemplates[] = {
    [WIN_TITLE] = {
        .bg = 1,
        .tilemapLeft = 2,
        .tilemapTop = 1,
        .width = 26,
        .height = 2,
        .paletteNum = 1,
        .baseBlock = 2
    },
    [WIN_STATS] = {
        .bg = 0,
        .tilemapLeft = 2,
        .tilemapTop = 5,
        .width = 26,
        .height = 14,
        .paletteNum = 1,
        .baseBlock = 0x36
    },
    DUMMY_WIN_TEMPLATE
};

static const struct BgTemplate sStatEditorBgTemplates[] = {
    {
        .bg = 1,
        .charBaseIndex = 1,
        .mapBaseIndex = 30,
        .screenSize = 0,
        .paletteMode = 0,
        .priority = 0,
        .baseTile = 0
    },
    {
        .bg = 0,
        .charBaseIndex = 1,
        .mapBaseIndex = 31,
        .screenSize = 0,
        .paletteMode = 0,
        .priority = 1,
        .baseTile = 0
    }
};

static const u16 sStatEditorBg_Pal[] = {RGB(17, 18, 31)};

static void MainCB2(void)
{
    RunTasks();
    AnimateSprites();
    BuildOamBuffer();
    DoScheduledBgTilemapCopiesToVram();
    UpdatePaletteFade();
}

static void VBlankCB(void)
{
    LoadOam();
    ProcessSpriteCopyRequests();
    TransferPlttBuffer();
}

static u16 GetTotalEditEVs(void)
{
    u16 total = 0;
    u8 i;

    for (i = 0; i < STAT_EDITOR_COUNT; i++)
        total += sEditEVs[i];
    return total;
}

static u8 GetEntryCountForMode(u8 mode)
{
    if (mode == MODE_MISC)
        return MISC_EDITOR_COUNT;
    if (mode == MODE_CONTEST)
        return CONTEST_EDITOR_COUNT;
    return STAT_EDITOR_COUNT;
}

static u16 GetMiscValue(u8 cursor)
{
    switch (cursor)
    {
    case MISC_EDITOR_LEVEL:
        return sEditLevel;
    case MISC_EDITOR_HAPPINESS:
        return sEditFriendship;
    case MISC_EDITOR_ABILITY:
        return sEditAbilityNum;
    case MISC_EDITOR_NATURE:
        return sEditNature;
    case MISC_EDITOR_COLOR:
        return sEditIsShiny;
    default:
        return sEditFriendship;
    }
}

static bool8 SpeciesHasSecondAbility(u16 species)
{
    return gSpeciesInfo[species].abilities[1] != ABILITY_NONE
        && gSpeciesInfo[species].abilities[1] != gSpeciesInfo[species].abilities[0];
}

static u8 GetAbilityOptionCount(u16 species)
{
    return SpeciesHasSecondAbility(species) ? 2 : 1;
}

static u8 GetClampedAbilityNum(u16 species, u8 abilityNum)
{
    if (!SpeciesHasSecondAbility(species))
        return 0;

    return (abilityNum != 0);
}

static u8 GetEditedAbility(u16 species)
{
    return gSpeciesInfo[species].abilities[GetClampedAbilityNum(species, sEditAbilityNum)];
}

static u8 CycleAbilityNum(u16 species, u8 abilityNum, s8 direction)
{
    u8 optionCount = GetAbilityOptionCount(species);

    if (optionCount <= 1)
        return 0;

    if (direction > 0)
        return (abilityNum + 1) % optionCount;

    return (abilityNum == 0) ? optionCount - 1 : abilityNum - 1;
}

static bool8 IsAbilityCursor(u8 mode, u8 cursor)
{
    return mode == MODE_MISC && cursor == MISC_EDITOR_ABILITY;
}

static bool8 IsNatureCursor(u8 mode, u8 cursor)
{
    return mode == MODE_MISC && cursor == MISC_EDITOR_NATURE;
}

static bool8 IsColorCursor(u8 mode, u8 cursor)
{
    return mode == MODE_MISC && cursor == MISC_EDITOR_COLOR;
}

static u16 GetMiscMaxValue(u8 cursor)
{
    switch (cursor)
    {
    case MISC_EDITOR_LEVEL:
        return MAX_LEVEL;
    case MISC_EDITOR_HAPPINESS:
        return MAX_FRIENDSHIP;
    case MISC_EDITOR_ABILITY:
        return 1;
    case MISC_EDITOR_NATURE:
        return NUM_NATURES - 1;
    case MISC_EDITOR_COLOR:
        return 1;
    default:
        return MAX_FRIENDSHIP;
    }
}

static u16 GetMiscMinValue(u8 cursor)
{
    switch (cursor)
    {
    case MISC_EDITOR_LEVEL:
        return 1;
    case MISC_EDITOR_HAPPINESS:
    default:
        return 0;
    }
}

static void SanitizeEditedValues(u16 species)
{
    u16 totalEVs = 0;
    u8 i;

    for (i = 0; i < STAT_EDITOR_COUNT; i++)
    {
        if (sEditIVs[i] > MAX_PER_STAT_IVS)
            sEditIVs[i] = MAX_PER_STAT_IVS;

        if (sEditEVs[i] > MAX_COMPETITIVE_EVS)
            sEditEVs[i] = MAX_COMPETITIVE_EVS;

        if (totalEVs + sEditEVs[i] > MAX_TOTAL_EVS)
            sEditEVs[i] = MAX_TOTAL_EVS - totalEVs;

        totalEVs += sEditEVs[i];
    }

    if (sEditLevel < 1)
        sEditLevel = 1;
    else if (sEditLevel > MAX_LEVEL)
        sEditLevel = MAX_LEVEL;

    if (sEditFriendship > MAX_FRIENDSHIP)
        sEditFriendship = MAX_FRIENDSHIP;

    sEditAbilityNum = GetClampedAbilityNum(species, sEditAbilityNum);
    sEditNature %= NUM_NATURES;
    sEditIsShiny = (sEditIsShiny != 0);
}

static void LoadMonStats(u8 slotId)
{
    struct Pokemon *mon = &gPlayerParty[slotId];
    u8 i;

    for (i = 0; i < STAT_EDITOR_COUNT; i++)
    {
        sEditIVs[i] = GetMonData(mon, sIVDataIds[i], NULL);
        sEditEVs[i] = GetMonData(mon, sEVDataIds[i], NULL);
    }

    sEditLevel = GetMonData(mon, MON_DATA_LEVEL, NULL);
    sEditFriendship = GetMonData(mon, MON_DATA_FRIENDSHIP, NULL);
    sEditAbilityNum = GetClampedAbilityNum(GetMonData(mon, MON_DATA_SPECIES, NULL), GetMonData(mon, MON_DATA_ABILITY_NUM, NULL));
    sEditNature = GetNatureFromPersonality(GetMonData(mon, MON_DATA_PERSONALITY, NULL));
    sEditIsShiny = IsMonShiny(mon);

    for (i = 0; i < CONTEST_EDITOR_COUNT; i++)
        sEditContestStats[i] = GetMonData(mon, sContestDataIds[i], NULL);
}

static void ApplyMonStats(u8 slotId)
{
    struct Pokemon *mon = &gPlayerParty[slotId];
    u8 i;
    u32 val;
    u16 species;
    u32 exp;

    for (i = 0; i < STAT_EDITOR_COUNT; i++)
    {
        val = sEditIVs[i];
        SetMonData(mon, sIVDataIds[i], &val);
        val = sEditEVs[i];
        SetMonData(mon, sEVDataIds[i], &val);
    }

    species = GetMonData(mon, MON_DATA_SPECIES, NULL);
    SanitizeEditedValues(species);
    exp = gExperienceTables[gSpeciesInfo[species].growthRate][sEditLevel];
    SetMonData(mon, MON_DATA_EXP, &exp);

    val = sEditFriendship;
    SetMonData(mon, MON_DATA_FRIENDSHIP, &val);

    val = sEditAbilityNum;
    SetMonData(mon, MON_DATA_ABILITY_NUM, &val);

    if (GetNatureFromPersonality(GetMonData(mon, MON_DATA_PERSONALITY, NULL)) != sEditNature)
    {
        gSpecialVar_0x8004 = slotId;
        gSpecialVar_0x8005 = sEditNature;
        ChangeMonNature();
    }

    for (i = 0; i < CONTEST_EDITOR_COUNT; i++)
    {
        val = sEditContestStats[i];
        SetMonData(mon, sContestDataIds[i], &val);
    }

    gSpecialVar_0x8004 = slotId;
    if (sEditIsShiny && !IsMonShiny(mon))
        MakeMonShiny();
    else if (!sEditIsShiny && IsMonShiny(mon))
        MakeMonNotShiny();
    else
        CalculateMonStats(mon);
}

#define TILE_TOP_CORNER_L 0x1A2
#define TILE_TOP_EDGE     0x1A3
#define TILE_TOP_CORNER_R 0x1A4
#define TILE_LEFT_EDGE    0x1A5
#define TILE_RIGHT_EDGE   0x1A7
#define TILE_BOT_CORNER_L 0x1A8
#define TILE_BOT_EDGE     0x1A9
#define TILE_BOT_CORNER_R 0x1AA

static void DrawBgWindowFrames(void)
{
    /* Title frame (rows 0-3) */
    FillBgTilemapBufferRect(1, TILE_TOP_CORNER_L,  1,  0,  1,  1,  7);
    FillBgTilemapBufferRect(1, TILE_TOP_EDGE,       2,  0, 26,  1,  7);
    FillBgTilemapBufferRect(1, TILE_TOP_CORNER_R,  28,  0,  1,  1,  7);
    FillBgTilemapBufferRect(1, TILE_LEFT_EDGE,      1,  1,  1,  2,  7);
    FillBgTilemapBufferRect(1, TILE_RIGHT_EDGE,    28,  1,  1,  2,  7);
    FillBgTilemapBufferRect(1, TILE_BOT_CORNER_L,   1,  3,  1,  1,  7);
    FillBgTilemapBufferRect(1, TILE_BOT_EDGE,       2,  3, 26,  1,  7);
    FillBgTilemapBufferRect(1, TILE_BOT_CORNER_R,  28,  3,  1,  1,  7);

    /* Stats frame (rows 4-19) */
    FillBgTilemapBufferRect(1, TILE_TOP_CORNER_L,   1,  4,  1,  1,  7);
    FillBgTilemapBufferRect(1, TILE_TOP_EDGE,        2,  4, 26,  1,  7);
    FillBgTilemapBufferRect(1, TILE_TOP_CORNER_R,   28,  4,  1,  1,  7);
    FillBgTilemapBufferRect(1, TILE_LEFT_EDGE,       1,  5,  1, 14,  7);
    FillBgTilemapBufferRect(1, TILE_RIGHT_EDGE,     28,  5,  1, 14,  7);
    FillBgTilemapBufferRect(1, TILE_BOT_CORNER_L,    1, 19,  1,  1,  7);
    FillBgTilemapBufferRect(1, TILE_BOT_EDGE,        2, 19, 26,  1,  7);
    FillBgTilemapBufferRect(1, TILE_BOT_CORNER_R,   28, 19,  1,  1,  7);

    CopyBgTilemapBufferToVram(1);
}

static void DrawStatEditorTitle(u8 taskId)
{
    u8 nickname[POKEMON_NAME_LENGTH + 1];
    u8 buf[64];
    u8 numBuf[8];
    u8 maxBuf[8];
    struct Pokemon *mon = &gPlayerParty[gTasks[taskId].tSlotId];
    const u8 *modeStr;

    FillWindowPixelBuffer(WIN_TITLE, PIXEL_FILL(1));

    GetMonData(mon, MON_DATA_NICKNAME, nickname);
    StringGet_Nickname(nickname);

    StringCopy(buf, nickname);
    AddTextPrinterParameterized(WIN_TITLE, FONT_NORMAL, buf, 8, 1, TEXT_SKIP_DRAW, NULL);

    switch (gTasks[taskId].tMode)
    {
    case MODE_IV:
        modeStr = sText_ModeIVs;
        break;
    case MODE_EV:
        modeStr = sText_ModeEVs;
        break;
    case MODE_CONTEST:
        modeStr = sText_ModeContest;
        break;
    case MODE_MISC:
    default:
        modeStr = sText_ModeMisc;
        break;
    }

    if (gTasks[taskId].tMode == MODE_EV)
    {
        u16 total = GetTotalEditEVs();

        StringCopy(buf, modeStr);
        StringAppend(buf, sText_Space);
        ConvertIntToDecimalStringN(numBuf, total, STR_CONV_MODE_RIGHT_ALIGN, 3);
        StringAppend(buf, numBuf);
        StringAppend(buf, sText_Slash);
        ConvertIntToDecimalStringN(maxBuf, MAX_TOTAL_EVS, STR_CONV_MODE_RIGHT_ALIGN, 3);
        StringAppend(buf, maxBuf);
        AddTextPrinterParameterized(WIN_TITLE, FONT_NORMAL, buf, 120, 1, TEXT_SKIP_DRAW, NULL);
    }
    else
    {
        AddTextPrinterParameterized(WIN_TITLE, FONT_NORMAL, modeStr, 136, 1, TEXT_SKIP_DRAW, NULL);
    }

    CopyWindowToVram(WIN_TITLE, COPYWIN_GFX);
}

static void DrawStatEditorStats(u8 taskId)
{
    u8 i;
    u8 numBuf[8];
    u8 maxBuf[8];
    u8 lineBuf[32];
    u16 value;
    u16 maxVal;
    u8 cursor = gTasks[taskId].tCursorPos;
    u8 mode = gTasks[taskId].tMode;
    u8 entryCount = GetEntryCountForMode(mode);
    u16 species = GetMonData(&gPlayerParty[gTasks[taskId].tSlotId], MON_DATA_SPECIES, NULL);

    FillWindowPixelBuffer(WIN_STATS, PIXEL_FILL(1));

    for (i = 0; i < entryCount; i++)
    {
        u8 y = (i * 16) + 1;

        /* Cursor indicator */
        if (i == cursor)
        {
            const u8 cursorStr[] = _("▶");
            AddTextPrinterParameterized(WIN_STATS, FONT_NORMAL, cursorStr, 0, y, TEXT_SKIP_DRAW, NULL);
        }

        /* Stat name */
        if (mode == MODE_MISC)
            AddTextPrinterParameterized(WIN_STATS, FONT_NORMAL, sMiscNames[i], 12, y, TEXT_SKIP_DRAW, NULL);
        else if (mode == MODE_CONTEST)
            AddTextPrinterParameterized(WIN_STATS, FONT_NORMAL, sContestNames[i], 12, y, TEXT_SKIP_DRAW, NULL);
        else
            AddTextPrinterParameterized(WIN_STATS, FONT_NORMAL, sStatNames[i], 12, y, TEXT_SKIP_DRAW, NULL);

        /* Value */
        if (mode == MODE_IV)
        {
            value = sEditIVs[i];
            maxVal = MAX_PER_STAT_IVS;
        }
        else if (mode == MODE_EV)
        {
            value = sEditEVs[i];
            maxVal = MAX_COMPETITIVE_EVS;
        }
        else if (mode == MODE_CONTEST)
        {
            value = sEditContestStats[i];
            maxVal = 255;
        }
        else
        {
            value = GetMiscValue(i);
            maxVal = (i == MISC_EDITOR_ABILITY) ? GetAbilityOptionCount(species) : GetMiscMaxValue(i);
        }

        if (mode == MODE_MISC && i == MISC_EDITOR_ABILITY)
        {
            AddTextPrinterParameterized(WIN_STATS, FONT_NORMAL, gAbilityNames[GetEditedAbility(species)], 108, y, TEXT_SKIP_DRAW, NULL);
        }
        else if (mode == MODE_MISC && i == MISC_EDITOR_NATURE)
        {
            AddTextPrinterParameterized(WIN_STATS, FONT_NORMAL, gNatureNamePointers[sEditNature], 108, y, TEXT_SKIP_DRAW, NULL);
        }
        else if (mode == MODE_MISC && i == MISC_EDITOR_COLOR)
        {
            AddTextPrinterParameterized(WIN_STATS, FONT_NORMAL, sEditIsShiny ? sText_Shiny : sText_Normal, 108, y, TEXT_SKIP_DRAW, NULL);
        }
        else
        {
            ConvertIntToDecimalStringN(numBuf, value, STR_CONV_MODE_RIGHT_ALIGN, 3);
            ConvertIntToDecimalStringN(maxBuf, maxVal, STR_CONV_MODE_RIGHT_ALIGN, 3);
            StringCopy(lineBuf, numBuf);
            StringAppend(lineBuf, sText_Slash);
            StringAppend(lineBuf, maxBuf);
            AddTextPrinterParameterized(WIN_STATS, FONT_NORMAL, lineBuf, 140, y, TEXT_SKIP_DRAW, NULL);
        }
    }

    /* Hint line below the stats */
    AddTextPrinterParameterized(WIN_STATS, FONT_SMALL, sText_Hint, 4, (STAT_EDITOR_COUNT * 16) + 4, TEXT_SKIP_DRAW, NULL);

    CopyWindowToVram(WIN_STATS, COPYWIN_GFX);
}

void CB2_ShowStatEditor(void)
{
    switch (gMain.state)
    {
    default:
    case 0:
        SetVBlankCallback(NULL);
        gMain.state++;
        break;
    case 1:
        DmaClearLarge16(3, (void *)(VRAM), VRAM_SIZE, 0x1000);
        DmaClear32(3, OAM, OAM_SIZE);
        DmaClear16(3, PLTT, PLTT_SIZE);
        SetGpuReg(REG_OFFSET_DISPCNT, 0);
        ResetBgsAndClearDma3BusyFlags(0);
        InitBgsFromTemplates(0, sStatEditorBgTemplates, ARRAY_COUNT(sStatEditorBgTemplates));
        ChangeBgX(0, 0, BG_COORD_SET);
        ChangeBgY(0, 0, BG_COORD_SET);
        ChangeBgX(1, 0, BG_COORD_SET);
        ChangeBgY(1, 0, BG_COORD_SET);
        InitWindows(sStatEditorWinTemplates);
        DeactivateAllTextPrinters();
        SetGpuReg(REG_OFFSET_DISPCNT, DISPCNT_OBJ_ON | DISPCNT_OBJ_1D_MAP);
        ShowBg(0);
        ShowBg(1);
        gMain.state++;
        break;
    case 2:
        ResetPaletteFade();
        ScanlineEffect_Stop();
        ResetTasks();
        ResetSpriteData();
        gMain.state++;
        break;
    case 3:
        LoadBgTiles(1, GetWindowFrameTilesPal(gSaveBlock2Ptr->optionsWindowFrameType)->tiles, 0x120, 0x1A2);
        gMain.state++;
        break;
    case 4:
        LoadPalette(sStatEditorBg_Pal, BG_PLTT_ID(0), sizeof(sStatEditorBg_Pal));
        LoadPalette(GetOverworldTextboxPalettePtr(), BG_PLTT_ID(1), PLTT_SIZE_4BPP);
        LoadPalette(GetWindowFrameTilesPal(gSaveBlock2Ptr->optionsWindowFrameType)->pal, BG_PLTT_ID(7), PLTT_SIZE_4BPP);
        gMain.state++;
        break;
    case 5:
        PutWindowTilemap(WIN_TITLE);
        gMain.state++;
        break;
    case 6:
        PutWindowTilemap(WIN_STATS);
        gMain.state++;
        break;
    case 7:
        DrawBgWindowFrames();
        gMain.state++;
        break;
    case 8:
    {
        u8 taskId = CreateTask(Task_StatEditorFadeIn, 0);

        gTasks[taskId].tCursorPos = 0;
        gTasks[taskId].tMode = MODE_IV;
        gTasks[taskId].tSlotId = gPartyMenu.slotId;
        gTasks[taskId].tState = 0;
        gTasks[taskId].tRepeatTimer = 0;

        LoadMonStats(gPartyMenu.slotId);
        DrawStatEditorTitle(taskId);
        DrawStatEditorStats(taskId);

        CopyWindowToVram(WIN_TITLE, COPYWIN_FULL);
        CopyWindowToVram(WIN_STATS, COPYWIN_FULL);
        gMain.state++;
        break;
    }
    case 9:
        BeginNormalPaletteFade(PALETTES_ALL, 0, 16, 0, RGB_BLACK);
        SetVBlankCallback(VBlankCB);
        SetMainCallback2(MainCB2);
        return;
    }
}

static void Task_StatEditorFadeIn(u8 taskId)
{
    if (!gPaletteFade.active)
        gTasks[taskId].func = Task_StatEditorProcessInput;
}

static void Task_StatEditorProcessInput(u8 taskId)
{
    u8 cursor = gTasks[taskId].tCursorPos;
    u8 mode = gTasks[taskId].tMode;
    u8 entryCount = GetEntryCountForMode(mode);
    u16 species = GetMonData(&gPlayerParty[gTasks[taskId].tSlotId], MON_DATA_SPECIES, NULL);
    s16 value;
    s16 minVal;
    s16 maxVal;
    bool8 changed = FALSE;

    if (JOY_NEW(A_BUTTON))
    {
        PlaySE(SE_SAVE);
        gTasks[taskId].func = Task_StatEditorSave;
        return;
    }

    if (JOY_NEW(B_BUTTON))
    {
        PlaySE(SE_SELECT);
        /* Discard changes — just fade out */
        BeginNormalPaletteFade(PALETTES_ALL, 0, 0, 16, RGB_BLACK);
        gTasks[taskId].func = Task_StatEditorFadeOut;
        return;
    }

    /* Toggle IV/EV/MISC/CONTEST mode */
    if (JOY_NEW(L_BUTTON))
    {
        PlaySE(SE_SELECT);
        gTasks[taskId].tMode = (mode == MODE_IV) ? MODE_COUNT - 1 : mode - 1;
        if (gTasks[taskId].tCursorPos >= GetEntryCountForMode(gTasks[taskId].tMode))
            gTasks[taskId].tCursorPos = GetEntryCountForMode(gTasks[taskId].tMode) - 1;
        DrawStatEditorTitle(taskId);
        DrawStatEditorStats(taskId);
        return;
    }
    if (JOY_NEW(R_BUTTON))
    {
        PlaySE(SE_SELECT);
        gTasks[taskId].tMode = (mode + 1) % MODE_COUNT;
        if (gTasks[taskId].tCursorPos >= GetEntryCountForMode(gTasks[taskId].tMode))
            gTasks[taskId].tCursorPos = GetEntryCountForMode(gTasks[taskId].tMode) - 1;
        DrawStatEditorTitle(taskId);
        DrawStatEditorStats(taskId);
        return;
    }

    /* Move cursor up/down */
    if (JOY_REPEAT(DPAD_UP))
    {
        PlaySE(SE_SELECT);
        if (cursor > 0)
            cursor--;
        else
            cursor = entryCount - 1;
        gTasks[taskId].tCursorPos = cursor;
        DrawStatEditorStats(taskId);
        return;
    }
    if (JOY_REPEAT(DPAD_DOWN))
    {
        PlaySE(SE_SELECT);
        if (cursor < entryCount - 1)
            cursor++;
        else
            cursor = 0;
        gTasks[taskId].tCursorPos = cursor;
        DrawStatEditorStats(taskId);
        return;
    }

    /* Change value left/right */
    if (mode == MODE_IV)
    {
        value = (s16)sEditIVs[cursor];
        minVal = 0;
        maxVal = MAX_PER_STAT_IVS;
    }
    else if (mode == MODE_EV)
    {
        value = (s16)sEditEVs[cursor];
        minVal = 0;
        maxVal = MAX_COMPETITIVE_EVS;
    }
    else if (mode == MODE_CONTEST)
    {
        value = (s16)sEditContestStats[cursor];
        minVal = 0;
        maxVal = 255;
    }
    else
    {
        value = (s16)GetMiscValue(cursor);
        minVal = GetMiscMinValue(cursor);
        if (IsAbilityCursor(mode, cursor))
            maxVal = GetAbilityOptionCount(species);
        else
            maxVal = GetMiscMaxValue(cursor);
    }

    if (JOY_NEW(SELECT_BUTTON))
    {
        if (IsAbilityCursor(mode, cursor))
        {
            value = CycleAbilityNum(species, sEditAbilityNum, 1);
        }
        else if (IsNatureCursor(mode, cursor))
        {
            value = (sEditNature + 1) % NUM_NATURES;
        }
        else if (IsColorCursor(mode, cursor))
        {
            value = !sEditIsShiny;
        }
        else if (value == minVal)
        {
            value = maxVal;

            if (mode == MODE_EV)
            {
                u16 total = GetTotalEditEVs() - sEditEVs[cursor] + (u16)value;
                if (total > MAX_TOTAL_EVS)
                    value = MAX_TOTAL_EVS - (GetTotalEditEVs() - sEditEVs[cursor]);
            }
        }
        else
        {
            value = minVal;
        }

        changed = TRUE;
    }
    else if (JOY_REPEAT(DPAD_RIGHT))
    {
        if (IsAbilityCursor(mode, cursor))
        {
            value = CycleAbilityNum(species, sEditAbilityNum, 1);
        }
        else if (IsNatureCursor(mode, cursor))
        {
            value = (sEditNature + 1) % NUM_NATURES;
        }
        else if (IsColorCursor(mode, cursor))
        {
            value = !sEditIsShiny;
        }
        else
        {
            value += (mode == MODE_EV) ? 4 : 1;
            if (value > maxVal)
                value = maxVal;

            /* EV total cap */
            if (mode == MODE_EV)
            {
                u16 total = GetTotalEditEVs() - sEditEVs[cursor] + (u16)value;
                if (total > MAX_TOTAL_EVS)
                    value = MAX_TOTAL_EVS - (GetTotalEditEVs() - sEditEVs[cursor]);
            }
        }

        changed = TRUE;
    }
    else if (JOY_REPEAT(DPAD_LEFT))
    {
        if (IsAbilityCursor(mode, cursor))
        {
            value = CycleAbilityNum(species, sEditAbilityNum, -1);
        }
        else if (IsNatureCursor(mode, cursor))
        {
            value = (sEditNature == 0) ? NUM_NATURES - 1 : sEditNature - 1;
        }
        else if (IsColorCursor(mode, cursor))
        {
            value = !sEditIsShiny;
        }
        else
        {
            value -= (mode == MODE_EV) ? 4 : 1;
            if (value < minVal)
                value = minVal;
        }

        changed = TRUE;
    }

    if (changed)
    {
        PlaySE(SE_SELECT);
        if (mode == MODE_IV)
            sEditIVs[cursor] = (u16)value;
        else if (mode == MODE_EV)
            sEditEVs[cursor] = (u16)value;
        else if (mode == MODE_CONTEST)
            sEditContestStats[cursor] = (u8)value;
        else if (cursor == MISC_EDITOR_LEVEL)
            sEditLevel = (u16)value;
        else if (cursor == MISC_EDITOR_HAPPINESS)
            sEditFriendship = (u16)value;
        else if (cursor == MISC_EDITOR_NATURE)
            sEditNature = (u8)value;
        else if (cursor == MISC_EDITOR_COLOR)
            sEditIsShiny = (u8)value;
        else
            sEditAbilityNum = (u8)value;
        DrawStatEditorStats(taskId);
        if (mode == MODE_EV)
            DrawStatEditorTitle(taskId);
    }
}

static void Task_StatEditorSave(u8 taskId)
{
    ApplyMonStats(gTasks[taskId].tSlotId);
    BeginNormalPaletteFade(PALETTES_ALL, 0, 0, 16, RGB_BLACK);
    gTasks[taskId].func = Task_StatEditorFadeOut;
}

static void Task_StatEditorFadeOut(u8 taskId)
{
    if (!gPaletteFade.active)
    {
        DestroyTask(taskId);
        FreeAllWindowBuffers();
        CB2_ReturnToPartyMenuFromStatEditor();
    }
}
