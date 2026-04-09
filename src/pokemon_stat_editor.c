#include "global.h"
#include "bg.h"
#include "gpu_regs.h"
#include "main.h"
#include "menu.h"
#include "palette.h"
#include "party_menu.h"
#include "pokemon.h"
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
    MODE_IV,
    MODE_EV
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

static EWRAM_DATA u16 sEditIVs[STAT_EDITOR_COUNT] = {0};
static EWRAM_DATA u16 sEditEVs[STAT_EDITOR_COUNT] = {0};

static const u8 sText_ModeIVs[] = _("IVs");
static const u8 sText_ModeEVs[] = _("EVs");
static const u8 sText_EditStats[] = _("EDIT STATS");
static const u8 sText_HP[] = _("HP");
static const u8 sText_Attack[] = _("ATTACK");
static const u8 sText_Defense[] = _("DEFENSE");
static const u8 sText_Speed[] = _("SPEED");
static const u8 sText_SpAtk[] = _("SP.ATK");
static const u8 sText_SpDef[] = _("SP.DEF");
static const u8 sText_Space[] = _(" ");
static const u8 sText_Slash[] = _("/");
static const u8 sText_Hint[] = _("{DPAD_LEFTRIGHT} Val SEL:Min/Max L/R:IV/EV");

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

static void LoadMonStats(u8 slotId)
{
    struct Pokemon *mon = &gPlayerParty[slotId];
    u8 i;

    for (i = 0; i < STAT_EDITOR_COUNT; i++)
    {
        sEditIVs[i] = GetMonData(mon, sIVDataIds[i], NULL);
        sEditEVs[i] = GetMonData(mon, sEVDataIds[i], NULL);
    }
}

static void ApplyMonStats(u8 slotId)
{
    struct Pokemon *mon = &gPlayerParty[slotId];
    u8 i;
    u32 val;

    for (i = 0; i < STAT_EDITOR_COUNT; i++)
    {
        val = sEditIVs[i];
        SetMonData(mon, sIVDataIds[i], &val);
        val = sEditEVs[i];
        SetMonData(mon, sEVDataIds[i], &val);
    }
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

    modeStr = (gTasks[taskId].tMode == MODE_IV) ? sText_ModeIVs : sText_ModeEVs;

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
        AddTextPrinterParameterized(WIN_TITLE, FONT_NORMAL, modeStr, 168, 1, TEXT_SKIP_DRAW, NULL);
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

    FillWindowPixelBuffer(WIN_STATS, PIXEL_FILL(1));

    for (i = 0; i < STAT_EDITOR_COUNT; i++)
    {
        u8 y = (i * 16) + 1;

        /* Cursor indicator */
        if (i == cursor)
        {
            const u8 cursorStr[] = _("▶");
            AddTextPrinterParameterized(WIN_STATS, FONT_NORMAL, cursorStr, 0, y, TEXT_SKIP_DRAW, NULL);
        }

        /* Stat name */
        AddTextPrinterParameterized(WIN_STATS, FONT_NORMAL, sStatNames[i], 12, y, TEXT_SKIP_DRAW, NULL);

        /* Value */
        if (mode == MODE_IV)
        {
            value = sEditIVs[i];
            maxVal = MAX_PER_STAT_IVS;
        }
        else
        {
            value = sEditEVs[i];
            maxVal = MAX_COMPETITIVE_EVS;
        }

        ConvertIntToDecimalStringN(numBuf, value, STR_CONV_MODE_RIGHT_ALIGN, 3);
        ConvertIntToDecimalStringN(maxBuf, maxVal, STR_CONV_MODE_RIGHT_ALIGN, 3);
        StringCopy(lineBuf, numBuf);
        StringAppend(lineBuf, sText_Slash);
        StringAppend(lineBuf, maxBuf);
        AddTextPrinterParameterized(WIN_STATS, FONT_NORMAL, lineBuf, 140, y, TEXT_SKIP_DRAW, NULL);
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
    s16 value;
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

    /* Toggle IV/EV mode */
    if (JOY_NEW(L_BUTTON) || JOY_NEW(R_BUTTON))
    {
        PlaySE(SE_SELECT);
        gTasks[taskId].tMode = (mode == MODE_IV) ? MODE_EV : MODE_IV;
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
            cursor = STAT_EDITOR_COUNT - 1;
        gTasks[taskId].tCursorPos = cursor;
        DrawStatEditorStats(taskId);
        return;
    }
    if (JOY_REPEAT(DPAD_DOWN))
    {
        PlaySE(SE_SELECT);
        if (cursor < STAT_EDITOR_COUNT - 1)
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
        maxVal = MAX_PER_STAT_IVS;
    }
    else
    {
        value = (s16)sEditEVs[cursor];
        maxVal = MAX_COMPETITIVE_EVS;
    }

    if (JOY_NEW(SELECT_BUTTON))
    {
        if (value == 0)
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
            value = 0;
        }

        changed = TRUE;
    }
    else if (JOY_REPEAT(DPAD_RIGHT))
    {
        value += (mode == MODE_IV) ? 1 : 4;
        if (value > maxVal)
            value = maxVal;

        /* EV total cap */
        if (mode == MODE_EV)
        {
            u16 total = GetTotalEditEVs() - sEditEVs[cursor] + (u16)value;
            if (total > MAX_TOTAL_EVS)
                value = MAX_TOTAL_EVS - (GetTotalEditEVs() - sEditEVs[cursor]);
        }

        changed = TRUE;
    }
    else if (JOY_REPEAT(DPAD_LEFT))
    {
        value -= (mode == MODE_IV) ? 1 : 4;
        if (value < 0)
            value = 0;

        changed = TRUE;
    }

    if (changed)
    {
        PlaySE(SE_SELECT);
        if (mode == MODE_IV)
            sEditIVs[cursor] = (u16)value;
        else
            sEditEVs[cursor] = (u16)value;
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
