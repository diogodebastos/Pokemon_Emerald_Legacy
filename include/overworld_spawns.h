#ifndef GUARD_OVERWORLD_SPAWNS_H
#define GUARD_OVERWORLD_SPAWNS_H

// Visible wild Pokemon that wander the overworld. Gated behind the
// gSaveBlock2Ptr->optionsOverworldSpawns toggle (Options menu). When enabled,
// these replace the invisible step-based RNG encounters.

void UpdateOverworldSpawns(void);          // step-driven tick: spawn/despawn
void RemoveAllOverworldSpawns(void);       // clear all spawns (call on warp/map change)
bool8 TryStartOverworldSpawnBattle(u8 direction); // collision -> wild battle
// TRUE when visible spawns are actually active here (toggle on AND not a
// force-disabled map). Use this to gate RNG-encounter suppression so maps where
// spawns are blocked (e.g. the desert) fall back to invisible RNG encounters.
bool8 AreOverworldSpawnsActive(void);

#endif // GUARD_OVERWORLD_SPAWNS_H
