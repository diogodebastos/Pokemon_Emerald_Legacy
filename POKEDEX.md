# Pokédex Website

Wiki-style page showing all Pokémon movesets and locations for Pokemon Emerald Legacy.

## Updating

Whenever you change move data or wild encounters, regenerate the page:

```bash
python3 generate_pokedex.py
```

Then open `docs/pokedex.html` in any browser. No server needed — it's fully self-contained.

## What gets parsed

| Source file | Data |
|---|---|
| `src/data/pokemon/level_up_learnsets.h` | Level-up moves |
| `src/data/pokemon/tmhm_learnsets.h` | TM/HM compatibility |
| `src/data/pokemon/egg_moves.h` | Egg moves |
| `src/data/pokemon/tutor_learnsets.h` | Move tutor moves |
| `src/data/wild_encounters.json` | Wild locations (lines 1–17100 only) |
| `graphics/pokemon/*/front.png` | Sprites |

## Requirements

Python 3 + Pillow (`pip install Pillow`) for sprite processing.
