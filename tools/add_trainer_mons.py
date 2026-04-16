#!/usr/bin/env python3
"""
Add a thematic pokemon to trainers with odd party counts.
Also set doubleBattle = TRUE for all trainers.

Usage: python3 tools/add_trainer_mons.py
"""

import re
import random

random.seed(42)  # Reproducible results

# Trainer class -> list of species to pick from (thematic additions)
# These are reasonable complementary pokemon for each trainer class
TRAINER_CLASS_POKEMON = {
    "TRAINER_CLASS_HIKER": [
        "SPECIES_GEODUDE", "SPECIES_GRAVELER", "SPECIES_NOSEPASS", "SPECIES_MACHOP",
        "SPECIES_NUMEL", "SPECIES_SLUGMA", "SPECIES_ARON", "SPECIES_RHYHORN",
    ],
    "TRAINER_CLASS_TEAM_AQUA": [
        "SPECIES_CARVANHA", "SPECIES_POOCHYENA", "SPECIES_ZUBAT", "SPECIES_GOLBAT",
        "SPECIES_MIGHTYENA", "SPECIES_WAILMER", "SPECIES_TENTACOOL", "SPECIES_GRIMER",
    ],
    "TRAINER_CLASS_TEAM_MAGMA": [
        "SPECIES_NUMEL", "SPECIES_POOCHYENA", "SPECIES_ZUBAT", "SPECIES_GOLBAT",
        "SPECIES_MIGHTYENA", "SPECIES_SLUGMA", "SPECIES_KOFFING", "SPECIES_BALTOY",
    ],
    "TRAINER_CLASS_BIRD_KEEPER": [
        "SPECIES_WINGULL", "SPECIES_SWELLOW", "SPECIES_TAILLOW", "SPECIES_SWABLU",
        "SPECIES_DODUO", "SPECIES_SKARMORY", "SPECIES_TROPIUS", "SPECIES_NATU",
    ],
    "TRAINER_CLASS_BUG_MANIAC": [
        "SPECIES_WURMPLE", "SPECIES_SILCOON", "SPECIES_CASCOON", "SPECIES_BEAUTIFLY",
        "SPECIES_DUSTOX", "SPECIES_SURSKIT", "SPECIES_NINCADA", "SPECIES_VOLBEAT",
        "SPECIES_ILLUMISE", "SPECIES_PINSIR", "SPECIES_HERACROSS",
    ],
    "TRAINER_CLASS_BUG_CATCHER": [
        "SPECIES_WURMPLE", "SPECIES_SILCOON", "SPECIES_CASCOON", "SPECIES_BEAUTIFLY",
        "SPECIES_DUSTOX", "SPECIES_SURSKIT", "SPECIES_NINCADA",
    ],
    "TRAINER_CLASS_FISHERMAN": [
        "SPECIES_MAGIKARP", "SPECIES_TENTACOOL", "SPECIES_BARBOACH", "SPECIES_CORPHISH",
        "SPECIES_FEEBAS", "SPECIES_GOLDEEN", "SPECIES_WAILMER", "SPECIES_CARVANHA",
    ],
    "TRAINER_CLASS_SWIMMER_M": [
        "SPECIES_TENTACOOL", "SPECIES_WINGULL", "SPECIES_WAILMER", "SPECIES_CARVANHA",
        "SPECIES_SEALEO", "SPECIES_LUVDISC", "SPECIES_HORSEA", "SPECIES_STARYU",
    ],
    "TRAINER_CLASS_SWIMMER_F": [
        "SPECIES_TENTACOOL", "SPECIES_WINGULL", "SPECIES_WAILMER", "SPECIES_LUVDISC",
        "SPECIES_SEALEO", "SPECIES_HORSEA", "SPECIES_STARYU", "SPECIES_GOLDEEN",
    ],
    "TRAINER_CLASS_BLACK_BELT": [
        "SPECIES_MACHOP", "SPECIES_MACHOKE", "SPECIES_MAKUHITA", "SPECIES_HARIYAMA",
        "SPECIES_MEDITITE", "SPECIES_MEDICHAM", "SPECIES_BRELOOM",
    ],
    "TRAINER_CLASS_BATTLE_GIRL": [
        "SPECIES_MEDITITE", "SPECIES_MEDICHAM", "SPECIES_MAKUHITA", "SPECIES_HARIYAMA",
        "SPECIES_MACHOP", "SPECIES_BRELOOM",
    ],
    "TRAINER_CLASS_HEX_MANIAC": [
        "SPECIES_SHUPPET", "SPECIES_DUSKULL", "SPECIES_SABLEYE", "SPECIES_BANETTE",
        "SPECIES_DUSCLOPS", "SPECIES_MISDREAVUS",
    ],
    "TRAINER_CLASS_PSYCHIC": [
        "SPECIES_ABRA", "SPECIES_KADABRA", "SPECIES_RALTS", "SPECIES_KIRLIA",
        "SPECIES_SPOINK", "SPECIES_NATU", "SPECIES_LUNATONE", "SPECIES_SOLROCK",
    ],
    "TRAINER_CLASS_KINDLER": [
        "SPECIES_NUMEL", "SPECIES_SLUGMA", "SPECIES_TORKOAL", "SPECIES_VULPIX",
        "SPECIES_GROWLITHE", "SPECIES_MAGBY",
    ],
    "TRAINER_CLASS_YOUNGSTER": [
        "SPECIES_ZIGZAGOON", "SPECIES_POOCHYENA", "SPECIES_TAILLOW", "SPECIES_WURMPLE",
        "SPECIES_LOTAD", "SPECIES_SEEDOT", "SPECIES_RALTS", "SPECIES_MARILL",
    ],
    "TRAINER_CLASS_LASS": [
        "SPECIES_ZIGZAGOON", "SPECIES_MARILL", "SPECIES_SKITTY", "SPECIES_SHROOMISH",
        "SPECIES_LOTAD", "SPECIES_ODDISH", "SPECIES_RALTS", "SPECIES_ROSELIA",
    ],
    "TRAINER_CLASS_SAILOR": [
        "SPECIES_TENTACOOL", "SPECIES_WINGULL", "SPECIES_MACHOP", "SPECIES_PELIPPER",
        "SPECIES_WAILMER", "SPECIES_HARIYAMA",
    ],
    "TRAINER_CLASS_COOLTRAINER": [
        "SPECIES_SWELLOW", "SPECIES_BRELOOM", "SPECIES_MANECTRIC", "SPECIES_AGGRON",
        "SPECIES_FLYGON", "SPECIES_ALTARIA", "SPECIES_GARDEVOIR", "SPECIES_SLAKING",
        "SPECIES_ZANGOOSE", "SPECIES_SEVIPER", "SPECIES_ABSOL",
    ],
    "TRAINER_CLASS_COOLTRAINER_2": [
        "SPECIES_SWELLOW", "SPECIES_BRELOOM", "SPECIES_MANECTRIC", "SPECIES_AGGRON",
        "SPECIES_FLYGON", "SPECIES_ALTARIA", "SPECIES_GARDEVOIR",
    ],
    "TRAINER_CLASS_PKMN_BREEDER": [
        "SPECIES_ZIGZAGOON", "SPECIES_POOCHYENA", "SPECIES_SKITTY", "SPECIES_NUMEL",
        "SPECIES_MARILL", "SPECIES_WINGULL", "SPECIES_SHROOMISH", "SPECIES_ELECTRIKE",
    ],
    "TRAINER_CLASS_DRAGON_TAMER": [
        "SPECIES_BAGON", "SPECIES_SHELGON", "SPECIES_SWABLU", "SPECIES_ALTARIA",
        "SPECIES_HORSEA", "SPECIES_VIBRAVA", "SPECIES_FLYGON",
    ],
    "TRAINER_CLASS_NINJA_BOY": [
        "SPECIES_NINCADA", "SPECIES_NINJASK", "SPECIES_KOFFING", "SPECIES_VOLTORB",
    ],
    "TRAINER_CLASS_AROMA_LADY": [
        "SPECIES_ROSELIA", "SPECIES_ODDISH", "SPECIES_GLOOM", "SPECIES_SHROOMISH",
        "SPECIES_TROPIUS", "SPECIES_BELLOSSOM",
    ],
    "TRAINER_CLASS_RUIN_MANIAC": [
        "SPECIES_GEODUDE", "SPECIES_GRAVELER", "SPECIES_SANDSHREW", "SPECIES_BALTOY",
        "SPECIES_CLAYDOL", "SPECIES_NOSEPASS",
    ],
    "TRAINER_CLASS_GENTLEMAN": [
        "SPECIES_SLAKOTH", "SPECIES_ROSELIA", "SPECIES_ZANGOOSE", "SPECIES_KECLEON",
        "SPECIES_MANECTRIC",
    ],
    "TRAINER_CLASS_SCHOOL_KID": [
        "SPECIES_RALTS", "SPECIES_ABRA", "SPECIES_MAGNEMITE", "SPECIES_VOLTORB",
        "SPECIES_SHROOMISH", "SPECIES_SEEDOT",
    ],
    "TRAINER_CLASS_POKEFAN": [
        "SPECIES_SKITTY", "SPECIES_ZIGZAGOON", "SPECIES_AZURILL", "SPECIES_MARILL",
        "SPECIES_PLUSLE", "SPECIES_MINUN",
    ],
    "TRAINER_CLASS_EXPERT": [
        "SPECIES_MEDICHAM", "SPECIES_HARIYAMA", "SPECIES_MACHAMP", "SPECIES_GARDEVOIR",
        "SPECIES_ALAKAZAM",
    ],
    "TRAINER_CLASS_TRIATHLETE": [
        "SPECIES_DODUO", "SPECIES_DODRIO", "SPECIES_MAGNEMITE", "SPECIES_VOLTORB",
        "SPECIES_ELECTRODE", "SPECIES_STARYU", "SPECIES_STARMIE",
    ],
    "TRAINER_CLASS_COLLECTOR": [
        "SPECIES_KECLEON", "SPECIES_CASTFORM", "SPECIES_RELICANTH", "SPECIES_ZANGOOSE",
        "SPECIES_SEVIPER",
    ],
    "TRAINER_CLASS_POKEMANIAC": [
        "SPECIES_LAIRON", "SPECIES_RHYHORN", "SPECIES_LOUDRED", "SPECIES_KECLEON",
    ],
    "TRAINER_CLASS_PKMN_RANGER": [
        "SPECIES_SWELLOW", "SPECIES_BRELOOM", "SPECIES_MANECTRIC", "SPECIES_ROSELIA",
        "SPECIES_TROPIUS",
    ],
    "TRAINER_CLASS_PARASOL_LADY": [
        "SPECIES_CASTFORM", "SPECIES_LOTAD", "SPECIES_ROSELIA", "SPECIES_LOMBRE",
        "SPECIES_GOLDEEN",
    ],
    "TRAINER_CLASS_GUITARIST": [
        "SPECIES_VOLTORB", "SPECIES_MAGNEMITE", "SPECIES_ELECTRIKE", "SPECIES_MANECTRIC",
        "SPECIES_ELECTRODE", "SPECIES_PLUSLE", "SPECIES_MINUN",
    ],
    "TRAINER_CLASS_BEAUTY": [
        "SPECIES_ROSELIA", "SPECIES_SKITTY", "SPECIES_MILOTIC", "SPECIES_LUVDISC",
        "SPECIES_DELCATTY", "SPECIES_BEAUTIFLY",
    ],
    "TRAINER_CLASS_LADY": [
        "SPECIES_SKITTY", "SPECIES_ROSELIA", "SPECIES_DELCATTY", "SPECIES_ZIGZAGOON",
    ],
    "TRAINER_CLASS_RICH_BOY": [
        "SPECIES_ZIGZAGOON", "SPECIES_LINOONE", "SPECIES_AZURILL", "SPECIES_MARILL",
    ],
    "TRAINER_CLASS_CAMPER": [
        "SPECIES_ZIGZAGOON", "SPECIES_POOCHYENA", "SPECIES_TAILLOW", "SPECIES_NUZLEAF",
        "SPECIES_SANDSHREW", "SPECIES_GEODUDE",
    ],
    "TRAINER_CLASS_PICNICKER": [
        "SPECIES_SHROOMISH", "SPECIES_MARILL", "SPECIES_SKITTY", "SPECIES_ODDISH",
        "SPECIES_LOTAD",
    ],
    "TRAINER_CLASS_TUBER_F": [
        "SPECIES_MARILL", "SPECIES_AZURILL", "SPECIES_WINGULL",
    ],
    "TRAINER_CLASS_TUBER_M": [
        "SPECIES_MARILL", "SPECIES_AZURILL", "SPECIES_WINGULL",
    ],
    "TRAINER_CLASS_WINSTRATE": [
        "SPECIES_ZIGZAGOON", "SPECIES_LINOONE", "SPECIES_TAILLOW", "SPECIES_SWELLOW",
        "SPECIES_ROSELIA", "SPECIES_MANECTRIC",
    ],
    "TRAINER_CLASS_INTERVIEWER": [
        "SPECIES_MAGNEMITE", "SPECIES_LOUDRED", "SPECIES_EXPLOUD",
    ],
    # Special classes - use diverse pokemon
    "TRAINER_CLASS_ELITE_FOUR": [
        "SPECIES_ABSOL", "SPECIES_GARDEVOIR", "SPECIES_FLYGON", "SPECIES_AGGRON",
        "SPECIES_MILOTIC", "SPECIES_METAGROSS", "SPECIES_SALAMENCE", "SPECIES_SLAKING",
    ],
    "TRAINER_CLASS_LEADER": [
        "SPECIES_LINOONE", "SPECIES_KECLEON", "SPECIES_SWELLOW", "SPECIES_MANECTRIC",
        "SPECIES_GARDEVOIR", "SPECIES_AGGRON", "SPECIES_FLYGON",
    ],
    "TRAINER_CLASS_CHAMPION": [
        "SPECIES_METAGROSS", "SPECIES_SALAMENCE", "SPECIES_AGGRON", "SPECIES_GARDEVOIR",
        "SPECIES_FLYGON", "SPECIES_MILOTIC",
    ],
    "TRAINER_CLASS_RIVAL": [
        "SPECIES_SWELLOW", "SPECIES_BRELOOM", "SPECIES_MANECTRIC", "SPECIES_AGGRON",
        "SPECIES_GARDEVOIR", "SPECIES_FLYGON",
    ],
    "TRAINER_CLASS_AQUA_ADMIN": [
        "SPECIES_SHARPEDO", "SPECIES_MIGHTYENA", "SPECIES_GOLBAT", "SPECIES_CRAWDAUNT",
    ],
    "TRAINER_CLASS_AQUA_LEADER": [
        "SPECIES_SHARPEDO", "SPECIES_MIGHTYENA", "SPECIES_CRAWDAUNT", "SPECIES_TENTACRUEL",
    ],
    "TRAINER_CLASS_MAGMA_ADMIN": [
        "SPECIES_CAMERUPT", "SPECIES_MIGHTYENA", "SPECIES_GOLBAT", "SPECIES_TORKOAL",
    ],
    "TRAINER_CLASS_MAGMA_LEADER": [
        "SPECIES_CAMERUPT", "SPECIES_MIGHTYENA", "SPECIES_TORKOAL", "SPECIES_CLAYDOL",
    ],
    "TRAINER_CLASS_YOUNG_COUPLE": [
        "SPECIES_PLUSLE", "SPECIES_MINUN", "SPECIES_LUVDISC", "SPECIES_ROSELIA",
    ],
    "TRAINER_CLASS_OLD_COUPLE": [
        "SPECIES_MEDICHAM", "SPECIES_HARIYAMA", "SPECIES_GARDEVOIR",
    ],
    "TRAINER_CLASS_SIS_AND_BRO": [
        "SPECIES_WINGULL", "SPECIES_MARILL", "SPECIES_AZURILL",
    ],
    "TRAINER_CLASS_SR_AND_JR": [
        "SPECIES_ROSELIA", "SPECIES_GARDEVOIR", "SPECIES_BEAUTIFLY",
    ],
    "TRAINER_CLASS_TWINS": [
        "SPECIES_PLUSLE", "SPECIES_MINUN", "SPECIES_ROSELIA", "SPECIES_LOTAD",
    ],
}

# Default fallback for unrecognized classes
DEFAULT_POKEMON = [
    "SPECIES_ZIGZAGOON", "SPECIES_POOCHYENA", "SPECIES_TAILLOW", "SPECIES_WINGULL",
    "SPECIES_MARILL", "SPECIES_SHROOMISH", "SPECIES_ELECTRIKE", "SPECIES_SKITTY",
    "SPECIES_NUMEL", "SPECIES_GEODUDE",
]

# Evolution lines for level-appropriate selections
EVOLUTION_LEVEL_MAP = {
    # Base forms (use at low levels)
    "SPECIES_GEODUDE": ("SPECIES_GRAVELER", 25), "SPECIES_GRAVELER": ("SPECIES_GOLEM", 40),
    "SPECIES_MACHOP": ("SPECIES_MACHOKE", 28), "SPECIES_MACHOKE": ("SPECIES_MACHAMP", 42),
    "SPECIES_ZUBAT": ("SPECIES_GOLBAT", 22), "SPECIES_GOLBAT": ("SPECIES_CROBAT", 35),
    "SPECIES_TENTACOOL": ("SPECIES_TENTACRUEL", 30),
    "SPECIES_POOCHYENA": ("SPECIES_MIGHTYENA", 18),
    "SPECIES_ZIGZAGOON": ("SPECIES_LINOONE", 20),
    "SPECIES_TAILLOW": ("SPECIES_SWELLOW", 22),
    "SPECIES_WINGULL": ("SPECIES_PELIPPER", 25),
    "SPECIES_LOTAD": ("SPECIES_LOMBRE", 14), "SPECIES_LOMBRE": ("SPECIES_LUDICOLO", 35),
    "SPECIES_SEEDOT": ("SPECIES_NUZLEAF", 14), "SPECIES_NUZLEAF": ("SPECIES_SHIFTRY", 35),
    "SPECIES_RALTS": ("SPECIES_KIRLIA", 20), "SPECIES_KIRLIA": ("SPECIES_GARDEVOIR", 30),
    "SPECIES_SHROOMISH": ("SPECIES_BRELOOM", 23),
    "SPECIES_MAKUHITA": ("SPECIES_HARIYAMA", 24),
    "SPECIES_ARON": ("SPECIES_LAIRON", 32), "SPECIES_LAIRON": ("SPECIES_AGGRON", 42),
    "SPECIES_ELECTRIKE": ("SPECIES_MANECTRIC", 26),
    "SPECIES_NUMEL": ("SPECIES_CAMERUPT", 33),
    "SPECIES_SLUGMA": ("SPECIES_MAGCARGO", 38),
    "SPECIES_CARVANHA": ("SPECIES_SHARPEDO", 30),
    "SPECIES_WAILMER": ("SPECIES_WAILORD", 40),
    "SPECIES_ABRA": ("SPECIES_KADABRA", 16), "SPECIES_KADABRA": ("SPECIES_ALAKAZAM", 37),
    "SPECIES_ODDISH": ("SPECIES_GLOOM", 21),
    "SPECIES_MEDITITE": ("SPECIES_MEDICHAM", 37),
    "SPECIES_SWABLU": ("SPECIES_ALTARIA", 35),
    "SPECIES_MAGNEMITE": ("SPECIES_MAGNETON", 30),
    "SPECIES_VOLTORB": ("SPECIES_ELECTRODE", 30),
    "SPECIES_MARILL": ("SPECIES_AZUMARILL", 18),
    "SPECIES_SKITTY": ("SPECIES_DELCATTY", 30),
    "SPECIES_SPOINK": ("SPECIES_GRUMPIG", 32),
    "SPECIES_SHUPPET": ("SPECIES_BANETTE", 37),
    "SPECIES_DUSKULL": ("SPECIES_DUSCLOPS", 37),
    "SPECIES_NINCADA": ("SPECIES_NINJASK", 20),
    "SPECIES_WURMPLE": ("SPECIES_SILCOON", 7),
    "SPECIES_BAGON": ("SPECIES_SHELGON", 30), "SPECIES_SHELGON": ("SPECIES_SALAMENCE", 50),
    "SPECIES_HORSEA": ("SPECIES_SEADRA", 32), "SPECIES_SEADRA": ("SPECIES_KINGDRA", 45),
    "SPECIES_BARBOACH": ("SPECIES_WHISCASH", 30),
    "SPECIES_CORPHISH": ("SPECIES_CRAWDAUNT", 30),
    "SPECIES_MAGIKARP": ("SPECIES_GYARADOS", 20),
    "SPECIES_GOLDEEN": ("SPECIES_SEAKING", 33),
    "SPECIES_SLAKOTH": ("SPECIES_VIGOROTH", 18), "SPECIES_VIGOROTH": ("SPECIES_SLAKING", 36),
    "SPECIES_SANDSHREW": ("SPECIES_SANDSLASH", 22),
    "SPECIES_RHYHORN": ("SPECIES_RHYDON", 42),
    "SPECIES_KOFFING": ("SPECIES_WEEZING", 35),
    "SPECIES_BALTOY": ("SPECIES_CLAYDOL", 36),
    "SPECIES_DODUO": ("SPECIES_DODRIO", 31),
    "SPECIES_STARYU": ("SPECIES_STARMIE", 30),
    "SPECIES_ROSELIA": ("SPECIES_ROSELIA", 999),  # No evo in gen3
    "SPECIES_LOUDRED": ("SPECIES_EXPLOUD", 40),
    "SPECIES_VIBRAVA": ("SPECIES_FLYGON", 45),
    "SPECIES_SILCOON": ("SPECIES_BEAUTIFLY", 10),
    "SPECIES_CASCOON": ("SPECIES_DUSTOX", 10),
    "SPECIES_SURSKIT": ("SPECIES_MASQUERAIN", 22),
    "SPECIES_VULPIX": ("SPECIES_NINETALES", 35),
    "SPECIES_GROWLITHE": ("SPECIES_ARCANINE", 35),
    "SPECIES_AZURILL": ("SPECIES_MARILL", 15),
}


def pick_species_for_level(species_pool, avg_level):
    """Pick a species from pool and evolve it if avg_level is high enough."""
    base = random.choice(species_pool)
    current = base

    # Walk evolution chain until we can't evolve further at this level
    while current in EVOLUTION_LEVEL_MAP:
        evo, evo_level = EVOLUTION_LEVEL_MAP[current]
        if avg_level >= evo_level:
            current = evo
        else:
            break

    return current


def parse_trainer_parties(filepath):
    """Parse trainer_parties.h and return dict of party_name -> list of mons."""
    with open(filepath) as f:
        content = f.read()

    parties = {}
    # Match: static const struct TrainerMon sParty_Name[] = { ... };
    pattern = r'static const struct TrainerMon (s\w+)\[\] = \{(.*?)\};'
    for match in re.finditer(pattern, content, re.DOTALL):
        party_name = match.group(1)
        body = match.group(2)

        mons = []
        # Find each mon block
        mon_pattern = r'\{([^}]*\.species\s*=\s*(\w+)[^}]*\.lvl\s*=\s*(\d+)[^}]*)\}'
        # More flexible: species and lvl can be in any order
        for mon_match in re.finditer(r'\{([^}]+)\}', body, re.DOTALL):
            mon_block = mon_match.group(1)
            species_m = re.search(r'\.species\s*=\s*(\w+)', mon_block)
            lvl_m = re.search(r'\.lvl\s*=\s*(\d+)', mon_block)
            if species_m and lvl_m:
                mons.append({
                    'species': species_m.group(1),
                    'level': int(lvl_m.group(1)),
                    'block': mon_match.group(0),
                })

        parties[party_name] = mons

    return parties


def parse_trainers(filepath):
    """Parse trainers.h and return dict of party_name -> trainer_class."""
    with open(filepath) as f:
        content = f.read()

    party_to_class = {}
    # Split by trainer entries (each starts with [TRAINER_...)
    entries = re.split(r'\n\s*\[TRAINER_', content)
    for entry in entries[1:]:  # Skip preamble before first entry
        class_m = re.search(r'\.trainerClass\s*=\s*(\w+)', entry)
        party_m = re.search(r'\.party\s*=\s*TRAINER_MON\((\w+)\)', entry)
        if class_m and party_m:
            party_to_class[party_m.group(1)] = class_m.group(1)

    return party_to_class


def add_mon_to_party(content, party_name, new_species, level):
    """Insert a new mon entry at the end of a party array, before the closing };"""
    # Find the full array definition
    pattern = rf'static const struct TrainerMon {re.escape(party_name)}\[\] = \{{.*?\}};'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print(f"  WARNING: Could not find party {party_name}")
        return content

    full_text = match.group(0)
    # Find the position of the final }; which closes the array
    last_close = full_text.rfind('};')

    # Check if there's already a trailing comma after the last mon's closing }
    before_close = full_text[:last_close].rstrip()
    if before_close.endswith(','):
        # Already has trailing comma, just add new mon
        separator = "\n"
    elif before_close.endswith('}'):
        # No trailing comma, add one
        separator = ",\n"
    else:
        separator = ",\n"

    new_mon = f"""    {{
    .iv = 0,
    .lvl = {level},
    .species = {new_species},
    }}
"""

    modified = before_close + separator + new_mon + full_text[last_close:]
    return content[:match.start()] + modified + content[match.end():]


def main():
    parties_file = "src/data/trainer_parties.h"
    trainers_file = "src/data/trainers.h"

    parties = parse_trainer_parties(parties_file)
    party_to_class = parse_trainers(trainers_file)

    print(f"Found {len(parties)} parties")
    print(f"Found {len(party_to_class)} trainer->party mappings")

    # Count odd parties
    odd_parties = {name: mons for name, mons in parties.items() if len(mons) % 2 == 1}
    print(f"Odd-count parties: {len(odd_parties)}")

    # Size distribution
    sizes = {}
    for name, mons in odd_parties.items():
        s = len(mons)
        sizes[s] = sizes.get(s, 0) + 1
    print(f"Size distribution: {sizes}")

    # Read file content for modification
    with open(parties_file) as f:
        content = f.read()

    changes = 0
    skipped = []
    for party_name, mons in sorted(odd_parties.items()):
        trainer_class = party_to_class.get(party_name, None)
        if not trainer_class:
            skipped.append(party_name)
            continue

        # Get species pool for this trainer class
        species_pool = TRAINER_CLASS_POKEMON.get(trainer_class, DEFAULT_POKEMON)

        # Calculate average level
        avg_level = sum(m['level'] for m in mons) / len(mons)
        target_level = int(avg_level)

        # Don't duplicate existing species if possible
        existing_species = {m['species'] for m in mons}
        available = [s for s in species_pool if s not in existing_species]
        if not available:
            available = species_pool  # Fall back to full pool

        new_species = pick_species_for_level(available, target_level)

        content = add_mon_to_party(content, party_name, new_species, target_level)
        changes += 1

    # Write modified parties file
    with open(parties_file, 'w') as f:
        f.write(content)

    print(f"\nAdded pokemon to {changes} parties")
    if skipped:
        print(f"Skipped {len(skipped)} parties (no trainer mapping): {skipped[:10]}...")

    # Now set doubleBattle = TRUE for all trainers
    with open(trainers_file) as f:
        trainers_content = f.read()

    double_count = trainers_content.count('.doubleBattle = FALSE')
    trainers_content = trainers_content.replace('.doubleBattle = FALSE', '.doubleBattle = TRUE')
    with open(trainers_file, 'w') as f:
        f.write(trainers_content)

    print(f"Set doubleBattle = TRUE for {double_count} trainers")


if __name__ == '__main__':
    main()
