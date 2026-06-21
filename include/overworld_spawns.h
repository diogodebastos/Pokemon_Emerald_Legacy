#ifndef GUARD_OVERWORLD_SPAWNS_H
#define GUARD_OVERWORLD_SPAWNS_H

// Visible wild Pokemon that wander the overworld. Gated behind the
// gSaveBlock2Ptr->optionsOverworldSpawns toggle (Options menu). When enabled,
// these replace the invisible step-based RNG encounters.

void UpdateOverworldSpawns(void);          // step-driven tick: spawn/despawn
void RemoveAllOverworldSpawns(void);       // clear all spawns (call on warp/map change)
bool8 TryStartOverworldSpawnBattle(u8 direction); // collision -> wild battle

#endif // GUARD_OVERWORLD_SPAWNS_H
