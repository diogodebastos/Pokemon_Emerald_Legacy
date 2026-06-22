#include "global.h"
#include "overworld_spawns.h"
#include "event_object_movement.h"
#include "field_player_avatar.h"
#include "fieldmap.h"
#include "metatile_behavior.h"
#include "random.h"
#include "battle_setup.h"
#include "wild_encounter.h"
#include "pokemon.h"
#include "constants/event_objects.h"
#include "constants/event_object_movement.h"
#include "constants/pokemon.h"
#include "constants/maps.h"

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

struct OverworldSpawn
{
    bool8 active;
    u8 localId;
    u16 species;
    u8 level;
    bool8 shiny;
    u32 personality; // rolled at spawn; battle mon is created with this exact PID
};

// Encodes shininess into a spawn template's script the way map-placed
// overworld Pokémon do: a leading `bufferspeciesname` (0x7d) command whose
// species halfword carries form (bits 10-14) and shiny (bit 15). Read once by
// InitObjectEventStateFromTemplate to set objectEvent->shiny BEFORE the sprite
// and palette are created, so the shiny palette loads from the start and every
// sprite-recreate path honors it. Never executed (special spawns have no
// map-template interaction script).
static const u8 sShinyOverworldSpawnScript[] = { 0x7d, 0x00, 0x00, 0x80 };

static struct OverworldSpawn sOverworldSpawns[MAX_OVERWORLD_SPAWNS];
static u8 sSpawnStepTimer;

// Maps where overworld spawns are force-disabled regardless of the option.
// The Route 111 desert is all deep sand under a sandstorm: wandering TRACKS_FOOT
// spawns flood the sprite pool with footprint field effects on top of the
// weather sprites and break the map, so spawns are suppressed there.
static bool8 IsOverworldSpawnsBlockedMap(void)
{
    return gSaveBlock1Ptr->location.mapGroup == MAP_GROUP(ROUTE111)
        && gSaveBlock1Ptr->location.mapNum == MAP_NUM(ROUTE111);
}

bool8 AreOverworldSpawnsActive(void)
{
    return gSaveBlock2Ptr->optionsOverworldSpawns && !IsOverworldSpawnsBlockedMap();
}

static bool8 OverworldSpawnsEnabled(void)
{
    return AreOverworldSpawnsActive();
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
    spawn->personality = 0;
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

// Per-step upkeep for active spawns: remove ones that scrolled off-screen or
// vanished (freeing the slot), and re-assert shininess on the rest. A wandering
// shiny's palette can otherwise get reset to normal when its sprite is touched
// by the object-event system; followers avoid this via continuous
// FollowerSetGraphics upkeep, so we mirror that here.
static void MaintainSpawns(void)
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
        else if (sOverworldSpawns[i].shiny)
        {
            SetOverworldMonShiny(&gObjectEvents[objId], TRUE);
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
        u32 personality;
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

        // Land spawns must land on a walkable (collision-free) tile so mons
        // never appear inside cave walls or other impassable terrain that still
        // carries an encounter behavior. Water spawns are exempt: surfable water
        // metatiles carry a collision bit, so this check would reject them all.
        if (!waterMon && MapGridGetCollisionAt(cx, cy) != 0)
            continue;

        // Tile already occupied by another object event.
        if (GetObjectEventIdByXY(cx, cy) != OBJECT_EVENTS_COUNT)
            continue;

        if (!GetOverworldSpawnMon(waterMon, &species, &level))
            continue;

        // Roll the personality (PID) once and derive shininess from it against the
        // player's OT ID — the same way the battle mon's shininess is determined.
        // The battle mon is later created with this exact PID (see
        // StartOverworldSpawnBattle), so overworld and battle shininess always match,
        // at the game's natural shiny rate (SHINY_ODDS / 65536).
        personality = Random32();
        shiny = IsShinyOtIdPersonality(T1_READ_32(gSaveBlock2Ptr->playerTrainerId), personality);

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
            // Bake shininess in so the shiny palette loads at sprite creation.
            .script = shiny ? sShinyOverworldSpawnScript : NULL,
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
        slot->personality = personality;
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

    MaintainSpawns();

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

    // Create the battle mon with the exact PID rolled at spawn (and the player's OT
    // ID, which spawn-time shininess was computed against), so its shininess matches
    // the overworld sprite. Building it with a fixed personality keeps the encrypted
    // substructures consistent (unlike stamping the PID after creation).
    ZeroEnemyPartyMons();
    CreateMon(&gEnemyParty[0], spawn->species, spawn->level, USE_RANDOM_IVS,
              TRUE, spawn->personality, OT_ID_PLAYER_ID, 0);

    RemoveObjectEventByLocalIdAndMap(spawn->localId,
                                     gSaveBlock1Ptr->location.mapNum,
                                     gSaveBlock1Ptr->location.mapGroup);
    ClearSpawnSlot(spawn);
    BattleSetup_StartScriptedWildBattle();
    return TRUE;
}
