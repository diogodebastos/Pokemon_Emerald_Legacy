#include "global.h"
#include "battle_royale.h"
#include "battle_setup.h"
#include "bg.h"
#include "event_data.h"
#include "gpu_regs.h"
#include "menu.h"
#include "overworld.h"
#include "palette.h"
#include "script.h"
#include "string_util.h"
#include "task.h"
#include "text.h"
#include "text_window.h"
#include "window.h"
#include "constants/characters.h"
#include "constants/game_stat.h"
#include "constants/opponents.h"
#include "gym_leader_rematch.h"
#include "constants/flags.h"
#include "constants/vars.h"

static void Task_BattleRoyaleHud(u8 taskId);
static void DrawBattleRoyaleHud(void);
static void CreateBattleRoyaleHudWindow(void);

static EWRAM_DATA u8 sBattleRoyaleHudWindowId = WINDOW_NONE;
static EWRAM_DATA bool8 sBattleRoyaleJustCompleted = FALSE;
static EWRAM_DATA u8 sRematchVariantBits[(TRAINERS_COUNT + 7) / 8] = {0};
static EWRAM_DATA bool8 sRematchCacheBuilt = FALSE;

static const u8 sText_Left[] = _("LEFT: ");
static const u8 sText_Deaths[] = _("DIES: ");
static const u8 sText_Complete[] = _("COMPLETE!");

#define HUD_WIDTH  9
#define HUD_HEIGHT 3
#define HUD_LEFT   19

static void BuildRematchVariantCache(void)
{
    s32 i;
    s32 j;
    u16 id;

    for (i = 0; i < REMATCH_TABLE_ENTRIES; i++)
    {
        for (j = 1; j < REMATCHES_COUNT; j++)
        {
            id = gRematchTable[i].trainerIds[j];
            if (id != TRAINER_NONE && id < TRAINERS_COUNT)
                sRematchVariantBits[id / 8] |= 1 << (id % 8);
        }
    }
    sRematchCacheBuilt = TRUE;
}

static bool32 IsRematchVariant(u16 trainerId)
{
    if (!sRematchCacheBuilt)
        BuildRematchVariantCache();

    return (sRematchVariantBits[trainerId / 8] >> (trainerId % 8)) & 1;
}

bool32 IsTrainerEligibleForBattleRoyale(u16 trainerId)
{
    if (trainerId == TRAINER_NONE
     || trainerId >= TRAINERS_COUNT)
        return FALSE;

    /* Exclude rematch variants (_2 through _5) — they have no
     * overworld placement and are only used by the Match Call system. */
    if (IsRematchVariant(trainerId))
        return FALSE;

    /* Exclude event-scripted trainers whose map presence is story-gated.
     * These trainers disappear after their story event, so clearing their
     * trainer flag won't make them reappear. */
    switch (trainerId)
    {
    /* Team Aqua admins/leader */
    case TRAINER_MATT:
    case TRAINER_SHELLY_WEATHER_INSTITUTE:
    case TRAINER_SHELLY_SEAFLOOR_CAVERN:
    case TRAINER_ARCHIE:
    /* Team Magma admins/leader */
    case TRAINER_TABITHA_MOSSDEEP:
    case TRAINER_TABITHA_MT_CHIMNEY:
    case TRAINER_TABITHA_MAGMA_HIDEOUT:
    case TRAINER_MAXIE_MAGMA_HIDEOUT:
    case TRAINER_MAXIE_MT_CHIMNEY:
    case TRAINER_MAXIE_MOSSDEEP:
    /* Wally */
    case TRAINER_WALLY_VR_1:
    case TRAINER_WALLY_MAUVILLE:
    case TRAINER_WALLY_VR_2:
    case TRAINER_WALLY_VR_3:
    case TRAINER_WALLY_VR_4:
    case TRAINER_WALLY_VR_5:
    /* Brendan */
    case TRAINER_BRENDAN_ROUTE_103_MUDKIP:
    case TRAINER_BRENDAN_ROUTE_110_MUDKIP:
    case TRAINER_BRENDAN_ROUTE_119_MUDKIP:
    case TRAINER_BRENDAN_ROUTE_103_TREECKO:
    case TRAINER_BRENDAN_ROUTE_110_TREECKO:
    case TRAINER_BRENDAN_ROUTE_119_TREECKO:
    case TRAINER_BRENDAN_ROUTE_103_TORCHIC:
    case TRAINER_BRENDAN_ROUTE_110_TORCHIC:
    case TRAINER_BRENDAN_ROUTE_119_TORCHIC:
    case TRAINER_BRENDAN_RUSTBORO_TREECKO:
    case TRAINER_BRENDAN_RUSTBORO_MUDKIP:
    case TRAINER_BRENDAN_RUSTBORO_TORCHIC:
    case TRAINER_BRENDAN_LILYCOVE_MUDKIP:
    case TRAINER_BRENDAN_LILYCOVE_TREECKO:
    case TRAINER_BRENDAN_LILYCOVE_TORCHIC:
    case TRAINER_BRENDAN_EVERGRANDE_TREECKO:
    case TRAINER_BRENDAN_EVERGRANDE_TORCHIC:
    case TRAINER_BRENDAN_EVERGRANDE_MUDKIP:
    /* May */
    case TRAINER_MAY_ROUTE_103_MUDKIP:
    case TRAINER_MAY_ROUTE_110_MUDKIP:
    case TRAINER_MAY_ROUTE_119_MUDKIP:
    case TRAINER_MAY_ROUTE_103_TREECKO:
    case TRAINER_MAY_ROUTE_110_TREECKO:
    case TRAINER_MAY_ROUTE_119_TREECKO:
    case TRAINER_MAY_ROUTE_103_TORCHIC:
    case TRAINER_MAY_ROUTE_110_TORCHIC:
    case TRAINER_MAY_ROUTE_119_TORCHIC:
    case TRAINER_MAY_RUSTBORO_MUDKIP:
    case TRAINER_MAY_RUSTBORO_TREECKO:
    case TRAINER_MAY_RUSTBORO_TORCHIC:
    case TRAINER_MAY_LILYCOVE_MUDKIP:
    case TRAINER_MAY_LILYCOVE_TREECKO:
    case TRAINER_MAY_LILYCOVE_TORCHIC:
    case TRAINER_MAY_EVERGRANDE_TREECKO:
    case TRAINER_MAY_EVERGRANDE_TORCHIC:
    case TRAINER_MAY_EVERGRANDE_MUDKIP:
    /* Steven */
    case TRAINER_STEVEN_1:
    /* Placeholder / unused trainer IDs */
    // case TRAINER_RED:
    // case TRAINER_LEAF:
    case TRAINER_BRENDAN_PLACEHOLDER:
    case TRAINER_MAY_PLACEHOLDER:
    /* Unused / roaming trainers with no fixed overworld placement */
    case TRAINER_GRUNT_UNUSED:
    case TRAINER_GABBY_AND_TY_1:
    case TRAINER_GABBY_AND_TY_6:
    case TRAINER_AMY_AND_LIV_6:
    case TRAINER_CINDY_6:
    /* Elite Four / Champion rematch-only variants */
    case TRAINER_SIDNEY_2:
    case TRAINER_PHOEBE_2:
    case TRAINER_GLACIA_2:
    case TRAINER_DRAKE_2:
    case TRAINER_WALLACE_2:
    /* Grinding NPC — always-rematchable, not a real route trainer */
    case TRAINER_GRINDING_NURSE:
        return FALSE;
    }

    return TRUE;
}

static u16 CountTotalEligibleTrainers(void)
{
    u16 count = 0;
    u16 i;

    for (i = 1; i < TRAINERS_COUNT; i++)
    {
        if (IsTrainerEligibleForBattleRoyale(i))
            count++;
    }
    return count;
}

static u16 CountDefeatedEligibleTrainers(void)
{
    u16 count = 0;
    u16 i;

    for (i = 1; i < TRAINERS_COUNT; i++)
    {
        if (IsTrainerEligibleForBattleRoyale(i) && HasTrainerBeenFought(i))
            count++;
    }
    return count;
}

bool32 IsBattleRoyaleModeActive(void)
{
    return VarGet(VAR_BATTLE_ROYALE_MODE) == 1;
}

void ActivateBattleRoyaleMode(void)
{
    // u16 total = CountTotalEligibleTrainers();
    u16 total = TRAINER_BATTLE_ROYALE_COUNT;
    u16 defeated = CountDefeatedEligibleTrainers();

    VarSet(VAR_BATTLE_ROYALE_MODE, 1);
    VarSet(VAR_BATTLE_ROYALE_TOTAL, total);
    VarSet(VAR_BATTLE_ROYALE_REMAINING, total - defeated);
    FlagClear(FLAG_HIDE_BATTLE_ROYALE_TRAINERS);
    ShowBattleRoyaleHud();
}

void DeactivateBattleRoyaleMode(void)
{
    VarSet(VAR_BATTLE_ROYALE_MODE, 0);
    FlagSet(FLAG_HIDE_BATTLE_ROYALE_TRAINERS);
    RemoveBattleRoyaleHud();
}

// Normal/Hard mode: reset all defeated trainers on faint
void BattleRoyale_ResetAllTrainerFlags(void)
{
    u16 i;

    for (i = 1; i < TRAINERS_COUNT; i++)
        ClearTrainerFlag(i);
}
// In current mode, defeated trainers remain defeated after fainting.

void BattleRoyale_OnTrainerDefeated(u16 trainerIdA, u16 trainerIdB)
{
    u16 remaining;

    if (!IsBattleRoyaleModeActive())
        return;

    remaining = VarGet(VAR_BATTLE_ROYALE_REMAINING);

    if (IsTrainerEligibleForBattleRoyale(trainerIdA) && remaining > 0)
        remaining--;
    if (trainerIdB != 0 && IsTrainerEligibleForBattleRoyale(trainerIdB) && remaining > 0)
        remaining--;

    VarSet(VAR_BATTLE_ROYALE_REMAINING, remaining);

    if (remaining == 0)
    {
        VarSet(VAR_BATTLE_ROYALE_MODE, 2);
        sBattleRoyaleJustCompleted = TRUE;
    }
}

void GetHallOfFameEntries(void)
{
    gSpecialVar_Result = GetGameStat(GAME_STAT_ENTERED_HOF);
}

// HUD

static void DrawBattleRoyaleHud(void)
{
    u8 text[32];
    u8 *ptr;
    u16 remaining = VarGet(VAR_BATTLE_ROYALE_REMAINING);
    u16 total = VarGet(VAR_BATTLE_ROYALE_TOTAL);
    u16 deaths = VarGet(VAR_BATTLE_ROYALE_DEATHS);
    u16 mode = VarGet(VAR_BATTLE_ROYALE_MODE);

    if (sBattleRoyaleHudWindowId == WINDOW_NONE)
        return;

    LoadMessageBoxGfx(sBattleRoyaleHudWindowId, 0x200, BG_PLTT_ID(15));
    DrawDialogueFrame(sBattleRoyaleHudWindowId, FALSE);

    if (mode == 2)
    {
        AddTextPrinterParameterized(sBattleRoyaleHudWindowId, FONT_SMALL, sText_Complete, 2, 1, TEXT_SKIP_DRAW, NULL);
    }
    else
    {
        ptr = StringCopy(text, sText_Left);
        ptr = ConvertIntToDecimalStringN(ptr, remaining, STR_CONV_MODE_LEFT_ALIGN, 3);
        *ptr++ = CHAR_SLASH;
        ptr = ConvertIntToDecimalStringN(ptr, total, STR_CONV_MODE_LEFT_ALIGN, 3);
        *ptr = EOS;
        AddTextPrinterParameterized(sBattleRoyaleHudWindowId, FONT_SMALL, text, 2, 1, TEXT_SKIP_DRAW, NULL);
    }

    ptr = StringCopy(text, sText_Deaths);
    ptr = ConvertIntToDecimalStringN(ptr, deaths, STR_CONV_MODE_LEFT_ALIGN, 4);
    *ptr = EOS;
    AddTextPrinterParameterized(sBattleRoyaleHudWindowId, FONT_SMALL, text, 2, 13, TEXT_SKIP_DRAW, NULL);

    CopyWindowToVram(sBattleRoyaleHudWindowId, COPYWIN_FULL);
}

// data[4] tracks whether the HUD is currently hidden due to script/dialogue
#define tHidden data[4]

static void Task_BattleRoyaleHud(u8 taskId)
{
    u16 remaining = VarGet(VAR_BATTLE_ROYALE_REMAINING);
    u16 deaths = VarGet(VAR_BATTLE_ROYALE_DEATHS);
    u16 mode = VarGet(VAR_BATTLE_ROYALE_MODE);
    u16 bg0vofs = GetGpuReg(REG_OFFSET_BG0VOFS);
    bool8 shouldHide = ArePlayerFieldControlsLocked()
                    || ScriptContext_IsEnabled()
                    || GetMapNamePopUpWindowId() != WINDOW_NONE;

    if (mode == 0)
    {
        RemoveBattleRoyaleHud();
        return;
    }

    // Hide HUD when dialogue/script/map popup is active
    if (shouldHide)
    {
        if (!gTasks[taskId].tHidden)
        {
            gTasks[taskId].tHidden = TRUE;
            if (sBattleRoyaleHudWindowId != WINDOW_NONE)
            {
                ClearDialogWindowAndFrameToTransparent(sBattleRoyaleHudWindowId, FALSE);
                ScheduleBgCopyTilemapToVram(0);
            }
        }
        return;
    }

    // Script just ended — restore HUD
    if (gTasks[taskId].tHidden)
    {
        gTasks[taskId].tHidden = FALSE;
        gTasks[taskId].data[0] = 0xFFFF; // Force redraw
        gTasks[taskId].data[3] = -1;     // Force reposition
    }

    // Reposition window if BG0 scroll changed
    if (gTasks[taskId].data[3] != (s16)bg0vofs)
    {
        gTasks[taskId].data[3] = bg0vofs;
        CreateBattleRoyaleHudWindow();
        gTasks[taskId].data[0] = 0xFFFF; // Force redraw
    }

    if (gTasks[taskId].data[0] != remaining
     || gTasks[taskId].data[1] != deaths
     || gTasks[taskId].data[2] != mode)
    {
        gTasks[taskId].data[0] = remaining;
        gTasks[taskId].data[1] = deaths;
        gTasks[taskId].data[2] = mode;
        DrawBattleRoyaleHud();
    }

    if (sBattleRoyaleJustCompleted && !shouldHide)
    {
        sBattleRoyaleJustCompleted = FALSE;
        ScriptContext_SetupScript(EventScript_BattleRoyaleVictory);
    }
}

static void CreateBattleRoyaleHudWindow(void)
{
    struct WindowTemplate template;
    u16 bg0vofs = GetGpuReg(REG_OFFSET_BG0VOFS);
    u8 topRow = (bg0vofs / 8) % 32;

    template.bg = 0;
    template.tilemapLeft = HUD_LEFT;
    template.tilemapTop = topRow;
    template.width = HUD_WIDTH;
    template.height = HUD_HEIGHT;
    template.paletteNum = 15;
    template.baseBlock = 0x0A0;

    if (sBattleRoyaleHudWindowId != WINDOW_NONE)
    {
        ClearDialogWindowAndFrameToTransparent(sBattleRoyaleHudWindowId, FALSE);
        RemoveWindow(sBattleRoyaleHudWindowId);
    }
    sBattleRoyaleHudWindowId = AddWindow(&template);
}

void ShowBattleRoyaleHud(void)
{
    u16 mode = VarGet(VAR_BATTLE_ROYALE_MODE);

    if (mode == 0 || FuncIsActiveTask(Task_BattleRoyaleHud))
        return;

    // Discard stale window ID from before the map transition.
    // InitWindows resets all window slots, so the old ID may now
    // refer to the standard textbox (window 0). Calling RemoveWindow
    // with it would destroy the textbox and let the HUD take slot 0,
    // causing all msgbox text to render in the HUD's small top-right window.
    sBattleRoyaleHudWindowId = WINDOW_NONE;

    CreateBattleRoyaleHudWindow();

    {
        u8 taskId = CreateTask(Task_BattleRoyaleHud, 90);
        gTasks[taskId].data[0] = 0xFFFF; // Force initial draw
        gTasks[taskId].data[1] = 0xFFFF;
        gTasks[taskId].data[2] = 0xFFFF;
        gTasks[taskId].data[3] = -1;     // Last known BG0VOFS
    }
}

void RemoveBattleRoyaleHud(void)
{
    if (FuncIsActiveTask(Task_BattleRoyaleHud))
        DestroyTask(FindTaskIdByFunc(Task_BattleRoyaleHud));

    if (sBattleRoyaleHudWindowId != WINDOW_NONE)
    {
        ClearWindowTilemap(sBattleRoyaleHudWindowId);
        CopyWindowToVram(sBattleRoyaleHudWindowId, COPYWIN_MAP);
        RemoveWindow(sBattleRoyaleHudWindowId);
        sBattleRoyaleHudWindowId = WINDOW_NONE;
    }
}

void ResetBattleRoyaleTransientState(void)
{
    if (FuncIsActiveTask(Task_BattleRoyaleHud))
        DestroyTask(FindTaskIdByFunc(Task_BattleRoyaleHud));

    sBattleRoyaleHudWindowId = WINDOW_NONE;
    sBattleRoyaleJustCompleted = FALSE;
    sRematchCacheBuilt = FALSE;
    CpuFill16(0, sRematchVariantBits, sizeof(sRematchVariantBits));
}
