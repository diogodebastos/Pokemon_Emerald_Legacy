#include "global.h"
#include "battle_royale.h"
#include "battle_royale_tracker.h"
#include "battle_setup.h"
#include "bg.h"
#include "gpu_regs.h"
#include "international_string_util.h"
#include "list_menu.h"
#include "main.h"
#include "malloc.h"
#include "menu.h"
#include "palette.h"
#include "region_map.h"
#include "scanline_effect.h"
#include "sprite.h"
#include "string_util.h"
#include "task.h"
#include "text.h"
#include "text_window.h"
#include "window.h"
#include "constants/characters.h"
#include "constants/opponents.h"
#include "constants/region_map_sections.h"
#include "constants/rgb.h"

#include "data/battle_royale/trainer_map_sections.h"

/* Forward declarations */
static void Task_TrackerFadeIn(u8 taskId);
static void Task_TrackerProcessInput(u8 taskId);
static void Task_TrackerFadeOut(u8 taskId);
static void TrackerPrintItem(u8 windowId, u32 itemId, u8 y);
static void AggregateTrackerData(void);
static void DrawTrackerWindowFrames(void);

enum
{
    WIN_HEADER,
    WIN_LIST
};

#define MAX_VISIBLE_ITEMS 6

struct TrackerAreaEntry
{
    u8 mapsecId;
    u16 defeated;
    u16 total;
};

static EWRAM_DATA struct
{
    struct TrackerAreaEntry areas[MAPSEC_COUNT];
    struct ListMenuItem listItems[MAPSEC_COUNT];
    u8 nameBuffers[MAPSEC_COUNT][MAP_NAME_LENGTH + 10];
    u16 totalCounts[MAPSEC_COUNT];
    u16 defeatedCounts[MAPSEC_COUNT];
    u16 areaCount;
    u8 listTaskId;
    u8 arrowTaskId;
    u16 scrollOffset;
    u16 totalTrainerCount;
} *sTrackerData = NULL;

static const struct WindowTemplate sTrackerWinTemplates[] =
{
    [WIN_HEADER] = {
        .bg = 1,
        .tilemapLeft = 2,
        .tilemapTop = 1,
        .width = 26,
        .height = 2,
        .paletteNum = 1,
        .baseBlock = 2
    },
    [WIN_LIST] = {
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

static const struct BgTemplate sTrackerBgTemplates[] =
{
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

static const u16 sTrackerBg_Pal[] = {RGB(17, 18, 31)};

static const u8 sText_TrackerHeader[] = _("BATTLE ROYALE TRACKER");

/* Window frame tile definitions - same as option_menu */
#define TILE_TOP_CORNER_L 0x1A2
#define TILE_TOP_EDGE     0x1A3
#define TILE_TOP_CORNER_R 0x1A4
#define TILE_LEFT_EDGE    0x1A5
#define TILE_RIGHT_EDGE   0x1A7
#define TILE_BOT_CORNER_L 0x1A8
#define TILE_BOT_EDGE     0x1A9
#define TILE_BOT_CORNER_R 0x1AA

static void MainCB2_Tracker(void)
{
    RunTasks();
    AnimateSprites();
    BuildOamBuffer();
    DoScheduledBgTilemapCopiesToVram();
    UpdatePaletteFade();
}

static void VBlankCB_Tracker(void)
{
    LoadOam();
    ProcessSpriteCopyRequests();
    TransferPlttBuffer();
}

void CB2_InitBattleRoyaleTracker(void)
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
        InitBgsFromTemplates(0, sTrackerBgTemplates, ARRAY_COUNT(sTrackerBgTemplates));
        ChangeBgX(0, 0, BG_COORD_SET);
        ChangeBgY(0, 0, BG_COORD_SET);
        ChangeBgX(1, 0, BG_COORD_SET);
        ChangeBgY(1, 0, BG_COORD_SET);
        InitWindows(sTrackerWinTemplates);
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
        sTrackerData = AllocZeroed(sizeof(*sTrackerData));
        if (sTrackerData == NULL)
        {
            SetMainCallback2(gMain.savedCallback);
            return;
        }
        gMain.state++;
        break;
    case 4:
        LoadBgTiles(1, GetWindowFrameTilesPal(gSaveBlock2Ptr->optionsWindowFrameType)->tiles, 0x120, 0x1A2);
        gMain.state++;
        break;
    case 5:
        LoadPalette(sTrackerBg_Pal, BG_PLTT_ID(0), sizeof(sTrackerBg_Pal));
        LoadPalette(GetOverworldTextboxPalettePtr(), BG_PLTT_ID(1), PLTT_SIZE_4BPP);
        LoadPalette(GetWindowFrameTilesPal(gSaveBlock2Ptr->optionsWindowFrameType)->pal, BG_PLTT_ID(7), PLTT_SIZE_4BPP);
        gMain.state++;
        break;
    case 6:
        AggregateTrackerData();
        gMain.state++;
        break;
    case 7:
        PutWindowTilemap(WIN_HEADER);
        FillWindowPixelBuffer(WIN_HEADER, PIXEL_FILL(1));
        AddTextPrinterParameterized(WIN_HEADER, FONT_NORMAL, sText_TrackerHeader, 8, 1, TEXT_SKIP_DRAW, NULL);
        CopyWindowToVram(WIN_HEADER, COPYWIN_FULL);
        gMain.state++;
        break;
    case 8:
    {
        struct ListMenuTemplate listTemplate;

        PutWindowTilemap(WIN_LIST);

        listTemplate.items = sTrackerData->listItems;
        listTemplate.moveCursorFunc = ListMenuDefaultCursorMoveFunc;
        listTemplate.itemPrintFunc = TrackerPrintItem;
        listTemplate.totalItems = sTrackerData->areaCount;
        listTemplate.maxShowed = MAX_VISIBLE_ITEMS;
        listTemplate.windowId = WIN_LIST;
        listTemplate.header_X = 0;
        listTemplate.item_X = 8;
        listTemplate.cursor_X = 0;
        listTemplate.upText_Y = 1;
        listTemplate.cursorPal = 2;
        listTemplate.fillValue = 1;
        listTemplate.cursorShadowPal = 3;
        listTemplate.lettersSpacing = 0;
        listTemplate.itemVerticalPadding = 2;
        listTemplate.scrollMultiple = LIST_MULTIPLE_SCROLL_L_R;
        listTemplate.fontId = FONT_NARROW;
        listTemplate.cursorKind = CURSOR_BLACK_ARROW;

        sTrackerData->listTaskId = ListMenuInit(&listTemplate, 0, 0);
        CopyBgTilemapBufferToVram(0);
        gMain.state++;
        break;
    }
    case 9:
    {
        struct ScrollArrowsTemplate arrowTemplate;

        arrowTemplate.firstArrowType = SCROLL_ARROW_UP;
        arrowTemplate.firstX = 120;
        arrowTemplate.firstY = 36;
        arrowTemplate.secondArrowType = SCROLL_ARROW_DOWN;
        arrowTemplate.secondX = 120;
        arrowTemplate.secondY = 156;
        arrowTemplate.fullyUpThreshold = 0;
        arrowTemplate.fullyDownThreshold = sTrackerData->areaCount > MAX_VISIBLE_ITEMS
            ? sTrackerData->areaCount - MAX_VISIBLE_ITEMS : 0;
        arrowTemplate.tileTag = 111;
        arrowTemplate.palTag = 111;
        arrowTemplate.palNum = 0;

        sTrackerData->arrowTaskId = AddScrollIndicatorArrowPair(&arrowTemplate, &sTrackerData->scrollOffset);
        gMain.state++;
        break;
    }
    case 10:
        DrawTrackerWindowFrames();
        gMain.state++;
        break;
    case 11:
    {
        u8 taskId = CreateTask(Task_TrackerFadeIn, 0);
        (void)taskId;
        BeginNormalPaletteFade(PALETTES_ALL, 0, 16, 0, RGB_BLACK);
        SetVBlankCallback(VBlankCB_Tracker);
        SetMainCallback2(MainCB2_Tracker);
        return;
    }
    }
}

static void Task_TrackerFadeIn(u8 taskId)
{
    if (!gPaletteFade.active)
        gTasks[taskId].func = Task_TrackerProcessInput;
}

static void Task_TrackerProcessInput(u8 taskId)
{
    s32 input = ListMenu_ProcessInput(sTrackerData->listTaskId);

    ListMenuGetScrollAndRow(sTrackerData->listTaskId, &sTrackerData->scrollOffset, NULL);

    if (JOY_NEW(B_BUTTON) || input == LIST_CANCEL)
    {
        BeginNormalPaletteFade(PALETTES_ALL, 0, 0, 16, RGB_BLACK);
        gTasks[taskId].func = Task_TrackerFadeOut;
    }
}

static void Task_TrackerFadeOut(u8 taskId)
{
    if (!gPaletteFade.active)
    {
        RemoveScrollIndicatorArrowPair(sTrackerData->arrowTaskId);
        DestroyListMenuTask(sTrackerData->listTaskId, NULL, NULL);
        DestroyTask(taskId);
        Free(sTrackerData);
        sTrackerData = NULL;
        FreeAllWindowBuffers();
        SetMainCallback2(gMain.savedCallback);
    }
}

static void TrackerPrintItem(u8 windowId, u32 itemId, u8 y)
{
    u8 text[16];
    u8 *ptr;
    struct TrackerAreaEntry *area;
    s32 xPos;

    area = &sTrackerData->areas[itemId];

    ptr = ConvertIntToDecimalStringN(text, area->defeated, STR_CONV_MODE_LEFT_ALIGN, 3);
    *ptr++ = CHAR_SLASH;
    ptr = ConvertIntToDecimalStringN(ptr, area->total, STR_CONV_MODE_LEFT_ALIGN, 3);
    *ptr = EOS;

    xPos = GetStringRightAlignXOffset(FONT_NARROW, text, 196);
    AddTextPrinterParameterized(windowId, FONT_NARROW, text, xPos, y, TEXT_SKIP_DRAW, NULL);
}

static void AggregateTrackerData(void)
{
    u16 i;
    u8 mapsec;
    u16 totalTrainerCount = 0;

    /* totalCounts/defeatedCounts are in sTrackerData (EWRAM heap) to avoid
     * stack overflow — they would require 852 bytes, but only ~756 bytes of
     * IWRAM stack are available. AllocZeroed already zeroed them. */

    for (i = 1; i < TRAINERS_COUNT; i++)
    {
        if (!IsTrainerEligibleForBattleRoyale(i))
            continue;

        mapsec = sTrainerMapSections[i];
        if (mapsec == MAPSEC_NONE)
            continue;

        sTrackerData->totalCounts[mapsec]++;
        totalTrainerCount++;
        if (HasTrainerBeenFought(i))
            sTrackerData->defeatedCounts[mapsec]++;
    }

    sTrackerData->totalTrainerCount = totalTrainerCount;

    sTrackerData->areaCount = 0;
    for (i = 0; i < MAPSEC_COUNT; i++)
    {
        u16 idx;

        if (sTrackerData->totalCounts[i] == 0)
            continue;

        idx = sTrackerData->areaCount;
        sTrackerData->areas[idx].mapsecId = i;
        sTrackerData->areas[idx].total = sTrackerData->totalCounts[i];
        sTrackerData->areas[idx].defeated = sTrackerData->defeatedCounts[i];

        GetMapNameGeneric(sTrackerData->nameBuffers[idx], i);

        sTrackerData->listItems[idx].name = sTrackerData->nameBuffers[idx];
        sTrackerData->listItems[idx].id = idx;

        sTrackerData->areaCount++;
    }
}

static void DrawTrackerWindowFrames(void)
{
    /* Draw header frame on BG1 */
    FillBgTilemapBufferRect(1, TILE_TOP_CORNER_L,  1,  0,  1,  1,  7);
    FillBgTilemapBufferRect(1, TILE_TOP_EDGE,       2,  0, 26,  1,  7);
    FillBgTilemapBufferRect(1, TILE_TOP_CORNER_R,  28,  0,  1,  1,  7);
    FillBgTilemapBufferRect(1, TILE_LEFT_EDGE,      1,  1,  1,  2,  7);
    FillBgTilemapBufferRect(1, TILE_RIGHT_EDGE,    28,  1,  1,  2,  7);
    FillBgTilemapBufferRect(1, TILE_BOT_CORNER_L,   1,  3,  1,  1,  7);
    FillBgTilemapBufferRect(1, TILE_BOT_EDGE,       2,  3, 26,  1,  7);
    FillBgTilemapBufferRect(1, TILE_BOT_CORNER_R,  28,  3,  1,  1,  7);

    /* Draw list frame on BG1 */
    FillBgTilemapBufferRect(1, TILE_TOP_CORNER_L,   1,  4,  1,  1,  7);
    FillBgTilemapBufferRect(1, TILE_TOP_EDGE,        2,  4, 26,  1,  7);
    FillBgTilemapBufferRect(1, TILE_TOP_CORNER_R,  28,  4,  1,  1,  7);
    FillBgTilemapBufferRect(1, TILE_LEFT_EDGE,       1,  5,  1, 14,  7);
    FillBgTilemapBufferRect(1, TILE_RIGHT_EDGE,     28,  5,  1, 14,  7);
    FillBgTilemapBufferRect(1, TILE_BOT_CORNER_L,    1, 19,  1,  1,  7);
    FillBgTilemapBufferRect(1, TILE_BOT_EDGE,        2, 19, 26,  1,  7);
    FillBgTilemapBufferRect(1, TILE_BOT_CORNER_R,  28, 19,  1,  1,  7);

    CopyBgTilemapBufferToVram(1);
}
