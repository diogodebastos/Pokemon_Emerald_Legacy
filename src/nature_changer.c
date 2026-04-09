#include "global.h"
#include "event_data.h"
#include "list_menu.h"
#include "main.h"
#include "menu.h"
#include "party_menu.h"
#include "pokemon.h"
#include "script.h"
#include "script_menu.h"
#include "sound.h"
#include "string_util.h"
#include "task.h"
#include "window.h"
#include "constants/songs.h"
#include "constants/pokemon.h"

static void Task_HandleNatureListInput(u8 taskId);
static void NatureListMoveCursorFunc(s32 itemIndex, bool8 onInit, struct ListMenu *list);

#define tListTaskId data[0]
#define tWindowId   data[1]

extern const u8 *const gNatureNamePointers[];

static struct ListMenuItem sNatureListItems[NUM_NATURES];

static const struct ListMenuTemplate sNatureListMenuTemplate = {
    .items = sNatureListItems,
    .moveCursorFunc = NatureListMoveCursorFunc,
    .itemPrintFunc = NULL,
    .totalItems = NUM_NATURES,
    .maxShowed = 8,
    .windowId = 0,
    .header_X = 0,
    .item_X = 8,
    .cursor_X = 0,
    .upText_Y = 1,
    .cursorPal = 2,
    .fillValue = 1,
    .cursorShadowPal = 3,
    .lettersSpacing = 0,
    .itemVerticalPadding = 0,
    .scrollMultiple = LIST_NO_MULTIPLE_SCROLL,
    .fontId = FONT_NORMAL,
    .cursorKind = CURSOR_BLACK_ARROW,
};

/* Substruct order table matching GetSubstruct in pokemon.c.
   sSubstructOrder[personality % 24][substructType] = physical position */
static const u8 sSubstructOrder[24][4] = {
    {0, 1, 2, 3},
    {0, 1, 3, 2},
    {0, 2, 1, 3},
    {0, 3, 1, 2},
    {0, 2, 3, 1},
    {0, 3, 2, 1},
    {1, 0, 2, 3},
    {1, 0, 3, 2},
    {2, 0, 1, 3},
    {3, 0, 1, 2},
    {2, 0, 3, 1},
    {3, 0, 2, 1},
    {1, 2, 0, 3},
    {1, 3, 0, 2},
    {2, 1, 0, 3},
    {3, 1, 0, 2},
    {2, 3, 0, 1},
    {3, 2, 0, 1},
    {1, 2, 3, 0},
    {1, 3, 2, 0},
    {2, 1, 3, 0},
    {3, 1, 2, 0},
    {2, 3, 1, 0},
    {3, 2, 1, 0},
};

static void NatureListMoveCursorFunc(s32 itemIndex, bool8 onInit, struct ListMenu *list)
{
    if (onInit != TRUE)
        PlaySE(SE_SELECT);
}

static void BuildNatureListItems(void)
{
    u8 i;

    for (i = 0; i < NUM_NATURES; i++)
    {
        sNatureListItems[i].name = gNatureNamePointers[i];
        sNatureListItems[i].id = i;
    }
}

/* Called from script via special. Opens a scrollable nature list.
   Stores selected nature in VAR_0x8005, or NUM_NATURES if cancelled. */
void ShowNatureChanger(void)
{
    u8 windowId;
    u8 listTaskId;
    u8 taskId;

    BuildNatureListItems();

    windowId = CreateWindowFromRect(1, 1, 10, 16);
    SetStandardWindowBorderStyle(windowId, FALSE);

    gMultiuseListMenuTemplate = sNatureListMenuTemplate;
    gMultiuseListMenuTemplate.windowId = windowId;

    listTaskId = ListMenuInit(&gMultiuseListMenuTemplate, 0, 0);
    ScheduleBgCopyTilemapToVram(0);

    taskId = CreateTask(Task_HandleNatureListInput, 80);
    gTasks[taskId].tListTaskId = listTaskId;
    gTasks[taskId].tWindowId = windowId;

    ScriptContext_Stop();
}

static void Task_HandleNatureListInput(u8 taskId)
{
    s32 input;

    input = ListMenu_ProcessInput(gTasks[taskId].tListTaskId);

    if (JOY_NEW(A_BUTTON))
    {
        PlaySE(SE_SELECT);
        gSpecialVar_0x8005 = input;
        DestroyListMenuTask(gTasks[taskId].tListTaskId, NULL, NULL);
        ClearToTransparentAndRemoveWindow(gTasks[taskId].tWindowId);
        DestroyTask(taskId);
        ScriptContext_Enable();
    }
    else if (JOY_NEW(B_BUTTON))
    {
        PlaySE(SE_SELECT);
        gSpecialVar_0x8005 = NUM_NATURES;
        DestroyListMenuTask(gTasks[taskId].tListTaskId, NULL, NULL);
        ClearToTransparentAndRemoveWindow(gTasks[taskId].tWindowId);
        DestroyTask(taskId);
        ScriptContext_Enable();
    }
}

/* Changes a mon's nature by modifying its personality value.
   Properly handles substructure reordering and re-encryption. */
void ChangeMonNature(void)
{
    struct BoxPokemon *boxMon;
    u32 oldPersonality;
    u32 newPersonality;
    u32 oldKey;
    u32 newKey;
    u32 oldOrder;
    u32 newOrder;
    u32 currentNature;
    u32 desiredNature;
    u32 i;
    u8 type;
    union PokemonSubstruct temp[4];

    boxMon = &gPlayerParty[gSpecialVar_0x8004].box;
    desiredNature = gSpecialVar_0x8005;
    oldPersonality = boxMon->personality;
    currentNature = oldPersonality % NUM_NATURES;
    newPersonality = oldPersonality - currentNature + desiredNature;

    oldKey = oldPersonality ^ boxMon->otId;
    newKey = newPersonality ^ boxMon->otId;
    oldOrder = oldPersonality % 24;
    newOrder = newPersonality % 24;

    /* Decrypt secure data with old key */
    for (i = 0; i < ARRAY_COUNT(boxMon->secure.raw); i++)
    {
        boxMon->secure.raw[i] ^= oldKey;
    }

    /* Read substructs from old physical positions into logical order */
    for (type = 0; type < 4; type++)
    {
        temp[type] = boxMon->secure.substructs[sSubstructOrder[oldOrder][type]];
    }

    /* Write substructs to new physical positions */
    for (type = 0; type < 4; type++)
    {
        boxMon->secure.substructs[sSubstructOrder[newOrder][type]] = temp[type];
    }

    /* Re-encrypt secure data with new key */
    for (i = 0; i < ARRAY_COUNT(boxMon->secure.raw); i++)
    {
        boxMon->secure.raw[i] ^= newKey;
    }

    boxMon->personality = newPersonality;
    CalculateMonStats(&gPlayerParty[gSpecialVar_0x8004]);
}

void BufferNatureChangerMonAndNature(void)
{
    struct Pokemon *mon;

    mon = &gPlayerParty[gSpecialVar_0x8004];
    GetMonNickname(mon, gStringVar1);
    StringCopy(gStringVar2, gNatureNamePointers[gSpecialVar_0x8005]);
}

#undef tListTaskId
#undef tWindowId
