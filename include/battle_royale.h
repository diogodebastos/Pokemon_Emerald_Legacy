#ifndef GUARD_BATTLE_ROYALE_H
#define GUARD_BATTLE_ROYALE_H

bool32 IsTrainerEligibleForBattleRoyale(u16 trainerId);
void ActivateBattleRoyaleMode(void);
void DeactivateBattleRoyaleMode(void);
bool32 IsBattleRoyaleModeActive(void);
void BattleRoyale_ResetAllTrainerFlags(void);
void BattleRoyale_OnTrainerDefeated(u16 trainerIdA, u16 trainerIdB);
void ShowBattleRoyaleHud(void);
void RemoveBattleRoyaleHud(void);
void ResetBattleRoyaleTransientState(void);
void GetHallOfFameEntries(void);

extern const u8 EventScript_BattleRoyaleVictory[];

#endif // GUARD_BATTLE_ROYALE_H
