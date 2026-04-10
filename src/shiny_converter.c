#include "global.h"
#include "event_data.h"
#include "party_menu.h"
#include "pokemon.h"
#include "string_util.h"
#include "constants/pokemon.h"

/*
 * Makes the selected party Pokémon shiny by finding a new personality value
 * that passes the shiny check while preserving nature, gender, and ability.
 *
 * Only the upper 16 bits of personality are changed. The lower 16 bits are
 * kept intact so gender (determined by personality & 0xFF vs the species
 * gender threshold) and ability slot (personality & 1) are unaffected.
 *
 * The search iterates over shiny-qualifying high halves until one is found
 * whose full personality has the same nature (personality % 25) as the
 * original. With SHINY_ODDS candidates, at least ~SHINY_ODDS/25 will
 * match, so a solution is always found.
 *
 * Substruct reordering (personality % 24) and re-encryption are handled
 * identically to ChangeMonNature in nature_changer.c.
 */

/* Substruct order table — same as nature_changer.c / GetSubstruct in pokemon.c */
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

void MakeMonShiny(void)
{
    struct BoxPokemon *boxMon;
    u32 oldPersonality;
    u32 newPersonality;
    u32 otId;
    u32 tid;
    u32 pidLo;
    u32 oldNature;
    u32 oldKey;
    u32 newKey;
    u32 oldOrder;
    u32 newOrder;
    u32 v;
    u32 h;
    u32 i;
    u8 type;
    union PokemonSubstruct temp[4];

    boxMon = &gPlayerParty[gSpecialVar_0x8004].box;
    oldPersonality = boxMon->personality;
    otId = boxMon->otId;

    /* Already shiny — nothing to do */
    if (IsShinyOtIdPersonality(otId, oldPersonality))
    {
        gSpecialVar_Result = FALSE;
        return;
    }

    oldNature = oldPersonality % NUM_NATURES;
    pidLo = oldPersonality & 0xFFFF;
    tid = HIHALF(otId) ^ LOHALF(otId);

    /*
     * Find a high-half value that yields a shiny personality with
     * the same nature. For each shiny value v (0 .. SHINY_ODDS-1),
     * compute what the high half must be: h = tid ^ pidLo ^ v.
     * Then check if ((h << 16) | pidLo) % 25 == oldNature.
     */
    newPersonality = oldPersonality; /* fallback, should never be used */
    for (v = 0; v < SHINY_ODDS; v++)
    {
        h = tid ^ pidLo ^ v;
        newPersonality = (h << 16) | pidLo;
        if (newPersonality % NUM_NATURES == oldNature)
            break;
    }

    /* Reorder encrypted substructs for the new personality */
    oldKey = oldPersonality ^ otId;
    newKey = newPersonality ^ otId;
    oldOrder = oldPersonality % 24;
    newOrder = newPersonality % 24;

    /* Decrypt with old key */
    for (i = 0; i < ARRAY_COUNT(boxMon->secure.raw); i++)
        boxMon->secure.raw[i] ^= oldKey;

    /* Read substructs from old physical positions into logical order */
    for (type = 0; type < 4; type++)
        temp[type] = boxMon->secure.substructs[sSubstructOrder[oldOrder][type]];

    /* Write substructs to new physical positions */
    for (type = 0; type < 4; type++)
        boxMon->secure.substructs[sSubstructOrder[newOrder][type]] = temp[type];

    /* Re-encrypt with new key */
    for (i = 0; i < ARRAY_COUNT(boxMon->secure.raw); i++)
        boxMon->secure.raw[i] ^= newKey;

    boxMon->personality = newPersonality;
    CalculateMonStats(&gPlayerParty[gSpecialVar_0x8004]);
    gSpecialVar_Result = TRUE;
}

void MakeMonNotShiny(void)
{
    struct BoxPokemon *boxMon;
    u32 oldPersonality;
    u32 newPersonality;
    u32 otId;
    u32 pidLo;
    u32 oldNature;
    u32 oldKey;
    u32 newKey;
    u32 oldOrder;
    u32 newOrder;
    u32 h;
    u32 i;
    u8 type;
    union PokemonSubstruct temp[4];

    boxMon = &gPlayerParty[gSpecialVar_0x8004].box;
    oldPersonality = boxMon->personality;
    otId = boxMon->otId;

    if (!IsShinyOtIdPersonality(otId, oldPersonality))
    {
        gSpecialVar_Result = FALSE;
        return;
    }

    oldNature = oldPersonality % NUM_NATURES;
    pidLo = oldPersonality & 0xFFFF;
    newPersonality = oldPersonality;

    for (h = 0; h <= 0xFFFF; h++)
    {
        newPersonality = (h << 16) | pidLo;
        if (!IsShinyOtIdPersonality(otId, newPersonality)
         && newPersonality % NUM_NATURES == oldNature)
            break;
    }

    oldKey = oldPersonality ^ otId;
    newKey = newPersonality ^ otId;
    oldOrder = oldPersonality % 24;
    newOrder = newPersonality % 24;

    for (i = 0; i < ARRAY_COUNT(boxMon->secure.raw); i++)
        boxMon->secure.raw[i] ^= oldKey;

    for (type = 0; type < 4; type++)
        temp[type] = boxMon->secure.substructs[sSubstructOrder[oldOrder][type]];

    for (type = 0; type < 4; type++)
        boxMon->secure.substructs[sSubstructOrder[newOrder][type]] = temp[type];

    for (i = 0; i < ARRAY_COUNT(boxMon->secure.raw); i++)
        boxMon->secure.raw[i] ^= newKey;

    boxMon->personality = newPersonality;
    CalculateMonStats(&gPlayerParty[gSpecialVar_0x8004]);
    gSpecialVar_Result = TRUE;
}

void BufferShinyMonName(void)
{
    GetMonNickname(&gPlayerParty[gSpecialVar_0x8004], gStringVar1);
}
