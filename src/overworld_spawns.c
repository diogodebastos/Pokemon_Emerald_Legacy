#include "global.h"
#include "overworld_spawns.h"
#include "event_object_movement.h"
#include "field_player_avatar.h"
#include "fieldmap.h"
#include "metatile_behavior.h"
#include "random.h"
#include "script_pokemon_util.h"
#include "battle_setup.h"
#include "wild_encounter.h"
#include "constants/event_objects.h"
#include "constants/event_object_movement.h"
#include "constants/items.h"
#include "constants/flags.h"
#include "event_data.h"

// Visible wild Pokemon spawning. See include/overworld_spawns.h.

#define MAX_OVERWORLD_SPAWNS    4
// localId range reserved for overworld spawns. Must not collide with map-local
// ids (small), the player (0xFF), follower (0xFE), or camera (0x7F).
#define OW_SPAWN_LOCALID_BASE   0xF8

#define SPAWN_INTERVAL_MIN      4   // steps between spawn attempts
#define SPAWN_INTERVAL_RAND     5
#define SPAWN_RING_MIN          3   // min/max tile distance from player to spawn
#define SPAWN_RING_MAX          6
#define SPAWN_PLACEMENT_TRIES   8
#define OW_SHINY_CHANCE         512 // 1-in-N chance a spawn is shiny

struct OverworldSpawn
{
    bool8 active;
    u8 localId;
    u16 species;
    u8 level;
    bool8 shiny;
};

static struct OverworldSpawn sOverworldSpawns[MAX_OVERWORLD_SPAWNS];
static u8 sSpawnStepTimer;

static bool8 OverworldSpawnsEnabled(void)
{
    return gSaveBlock2Ptr->optionsOverworldSpawns;
}

static struct OverworldSpawn *FindSpawnByLocalId(u8 localId)
{
    u8 i;

    for (i = 0; i < MAX_OVERWORLD_SPAWNS; i++)
    {
        if (sOverworldSpawns[i].active && sOverworldSpawns[i].localId == localId)
            return &sOverworldSpawns[i];
    }
    return NULL;
}

static void ClearSpawnSlot(struct OverworldSpawn *spawn)
{
    spawn->active = FALSE;
    spawn->species = SPECIES_NONE;
    spawn->level = 0;
    spawn->shiny = FALSE;
}

void RemoveAllOverworldSpawns(void)
{
    u8 i;

    for (i = 0; i < MAX_OVERWORLD_SPAWNS; i++)
    {
        if (!sOverworldSpawns[i].active)
            continue;
        RemoveObjectEventByLocalIdAndMap(sOverworldSpawns[i].localId,
                                         gSaveBlock1Ptr->location.mapNum,
                                         gSaveBlock1Ptr->location.mapGroup);
        ClearSpawnSlot(&sOverworldSpawns[i]);
    }
    sSpawnStepTimer = 0;
}

// Remove any spawns whose object event has scrolled off-screen or otherwise
// vanished, freeing the slot for a fresh spawn near the player.
static void DespawnDistantMons(void)
{
    u8 i, objId;

    for (i = 0; i < MAX_OVERWORLD_SPAWNS; i++)
    {
        if (!sOverworldSpawns[i].active)
            continue;
        objId = GetObjectEventIdByLocalIdAndMap(sOverworldSpawns[i].localId,
                                                gSaveBlock1Ptr->location.mapNum,
                                                gSaveBlock1Ptr->location.mapGroup);
        if (objId == OBJECT_EVENTS_COUNT)
        {
            ClearSpawnSlot(&sOverworldSpawns[i]);
        }
        else if (gObjectEvents[objId].offScreen)
        {
            RemoveObjectEventByLocalIdAndMap(sOverworldSpawns[i].localId,
                                             gSaveBlock1Ptr->location.mapNum,
                                             gSaveBlock1Ptr->location.mapGroup);
            ClearSpawnSlot(&sOverworldSpawns[i]);
        }
    }
}

static struct OverworldSpawn *GetFreeSpawnSlot(void)
{
    u8 i;

    for (i = 0; i < MAX_OVERWORLD_SPAWNS; i++)
    {
        if (!sOverworldSpawns[i].active)
            return &sOverworldSpawns[i];
    }
    return NULL;
}

// Classify a metatile for spawning: returns TRUE if spawnable and sets
// *waterMon. Uses the same predicates as the vanilla RNG encounter check
// (MetatileBehavior_IsLandWildEncounter covers tall grass, cave floors, ash,
// etc.; IsWaterWildEncounter covers surfable water), so spawns appear anywhere
// vanilla wild battles could trigger.
static bool8 ClassifySpawnTile(u8 behavior, bool8 *waterMon)
{
    if (MetatileBehavior_IsLandWildEncounter(behavior))
    {
        *waterMon = FALSE;
        return TRUE;
    }
    if (MetatileBehavior_IsWaterWildEncounter(behavior))
    {
        *waterMon = TRUE;
        return TRUE;
    }
    return FALSE;
}

static bool8 TrySpawnOne(void)
{
    struct ObjectEvent *player = &gObjectEvents[gPlayerAvatar.objectEventId];
    struct OverworldSpawn *slot = GetFreeSpawnSlot();
    u8 try;

    if (slot == NULL)
        return FALSE;

    for (try = 0; try < SPAWN_PLACEMENT_TRIES; try++)
    {
        s16 dx = (Random() % (SPAWN_RING_MAX * 2 + 1)) - SPAWN_RING_MAX;
        s16 dy = (Random() % (SPAWN_RING_MAX * 2 + 1)) - SPAWN_RING_MAX;
        s16 cx, cy;
        u8 behavior;
        bool8 waterMon;
        u16 species;
        u8 level;
        bool8 shiny;
        struct ObjectEventTemplate template;
        u8 objId;

        // Keep spawns out of the player's immediate vicinity.
        if (abs(dx) < SPAWN_RING_MIN && abs(dy) < SPAWN_RING_MIN)
            continue;

        cx = player->currentCoords.x + dx;
        cy = player->currentCoords.y + dy;

        behavior = MapGridGetMetatileBehaviorAt(cx, cy);
        if (!ClassifySpawnTile(behavior, &waterMon))
            continue;

        // Tile already occupied by another object event.
        if (GetObjectEventIdByXY(cx, cy) != OBJECT_EVENTS_COUNT)
            continue;

        if (!GetOverworldSpawnMon(waterMon, &species, &level))
            continue;

        shiny = (Random() % OW_SHINY_CHANCE) == 0;

        template = (struct ObjectEventTemplate){
            .localId = slot->localId,
            .graphicsId = OBJ_EVENT_GFX_MON_BASE + species,
            .flagId = 0,
            .x = cx - MAP_OFFSET,
            .y = cy - MAP_OFFSET,
            .elevation = player->currentElevation,
            .movementType = MOVEMENT_TYPE_WANDER_AROUND,
            .movementRangeX = 2,
            .movementRangeY = 2,
        };

        objId = SpawnSpecialObjectEvent(&template);
        if (objId >= OBJECT_EVENTS_COUNT)
            return FALSE; // out of object event slots

        if (shiny)
            SetOverworldMonShiny(&gObjectEvents[objId], TRUE);

        slot->active = TRUE;
        slot->species = species;
        slot->level = level;
        slot->shiny = shiny;
        return TRUE;
    }
    return FALSE;
}

void UpdateOverworldSpawns(void)
{
    u8 i;

    // Assign stable localIds once.
    for (i = 0; i < MAX_OVERWORLD_SPAWNS; i++)
        sOverworldSpawns[i].localId = OW_SPAWN_LOCALID_BASE + i;

    if (!OverworldSpawnsEnabled())
    {
        RemoveAllOverworldSpawns();
        return;
    }

    DespawnDistantMons();

    if (sSpawnStepTimer != 0)
    {
        sSpawnStepTimer--;
        return;
    }

    TrySpawnOne();
    sSpawnStepTimer = SPAWN_INTERVAL_MIN + (Random() % SPAWN_INTERVAL_RAND);
}

// Called from the player collision path. If the object event the player walked
// into is an overworld spawn, start the wild battle and return TRUE.
bool8 TryStartOverworldSpawnBattle(u8 direction)
{
    struct ObjectEvent *player = &gObjectEvents[gPlayerAvatar.objectEventId];
    s16 x = player->currentCoords.x;
    s16 y = player->currentCoords.y;
    u8 objId;
    struct OverworldSpawn *spawn;

    if (!OverworldSpawnsEnabled())
        return FALSE;

    MoveCoords(direction, &x, &y);
    objId = GetObjectEventIdByXY(x, y);
    if (objId == OBJECT_EVENTS_COUNT)
        return FALSE;

    spawn = FindSpawnByLocalId(gObjectEvents[objId].localId);
    if (spawn == NULL)
        return FALSE;

    // Force the battle mon shiny to match the overworld sprite. CreateScriptedWildMon
    // uses OT_ID_PLAYER_ID, which honors FLAG_SHINY_CREATION (cleared after use).
    if (spawn->shiny)
        FlagSet(FLAG_SHINY_CREATION);

    CreateScriptedWildMon(spawn->species, spawn->level, ITEM_NONE);
    RemoveObjectEventByLocalIdAndMap(spawn->localId,
                                     gSaveBlock1Ptr->location.mapNum,
                                     gSaveBlock1Ptr->location.mapGroup);
    ClearSpawnSlot(spawn);
    BattleSetup_StartScriptedWildBattle();
    return TRUE;
}
