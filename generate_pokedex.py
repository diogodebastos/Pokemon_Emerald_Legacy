#!/usr/bin/env python3
"""Generates pokedex.html from Pokemon Emerald Legacy source files."""

import re
import json
import os
import base64
from collections import OrderedDict

BASE = os.path.dirname(os.path.abspath(__file__))

# --- Name mapping helpers ---

CAMEL_TO_SPECIES = {
    'NidoranF': 'NIDORAN_F',
    'NidoranM': 'NIDORAN_M',
    'MrMime': 'MR_MIME',
    'HoOh': 'HO_OH',
    'Farfetchd': 'FARFETCHD',
    'Deoxys_Speed': 'DEOXYS_SPEED',
    'Deoxys_Attack': 'DEOXYS_ATTACK',
    'Deoxys_Defense': 'DEOXYS_DEFENSE',
}

# Species that are alternate forms of another — merged into the base entry
# key: alternate species key -> (base key, form display name)
FORM_OF = {
    'DEOXYS_ATTACK':  ('DEOXYS', 'Attack'),
    'DEOXYS_DEFENSE': ('DEOXYS', 'Defense'),
    'DEOXYS_SPEED':   ('DEOXYS', 'Speed'),
}

FORM_FOLDER = {
    'DEOXYS':         'deoxys',
    'DEOXYS_ATTACK':  'deoxys_attack',
    'DEOXYS_DEFENSE': 'deoxys_defense',
    'DEOXYS_SPEED':   'deoxys_speed',
}

SPECIES_DISPLAY = {
    'NIDORAN_F': 'Nidoran♀',
    'NIDORAN_M': 'Nidoran♂',
    'MR_MIME': 'Mr. Mime',
    'HO_OH': 'Ho-Oh',
    'FARFETCHD': "Farfetch'd",
}

SPECIES_FOLDER = {
    'NIDORAN_F': 'nidoran_f',
    'NIDORAN_M': 'nidoran_m',
    'MR_MIME': 'mr_mime',
    'HO_OH': 'ho_oh',
}

HYPHEN_MOVES = {'WILL_O_WISP', 'LOCK_ON', 'FOLLOW_ME', 'WAKE_UP_SLAP'}

def camel_to_species_key(camel):
    if camel in CAMEL_TO_SPECIES:
        return CAMEL_TO_SPECIES[camel]
    result = re.sub(r'([A-Z])', r'_\1', camel).upper().lstrip('_')
    return result

def species_display_name(key):
    if key in SPECIES_DISPLAY:
        return SPECIES_DISPLAY[key]
    name = key.replace('_', ' ').title()
    return name

def species_folder(key):
    if key in SPECIES_FOLDER:
        return SPECIES_FOLDER[key]
    return key.lower()

def fmt_move(move_const):
    """MOVE_FIRE_PUNCH -> 'Fire Punch', MOVE_WILL_O_WISP -> 'Will-O-Wisp'"""
    name = move_const.replace('MOVE_', '')
    if name == 'WILL_O_WISP':
        return 'Will-O-Wisp'
    if name == 'LOCK_ON':
        return 'Lock-On'
    parts = name.split('_')
    return ' '.join(p.capitalize() for p in parts)

def fmt_tmhm(name_const):
    """CUT -> 'Cut (HM)', FLAMETHROWER -> 'Flamethrower (TM)'"""
    # We'll just return the move name; TM/HM distinction needs TM list
    parts = name_const.split('_')
    return ' '.join(p.capitalize() for p in parts)

# --- TM/HM move names (from game data - TMs 01-50, HMs 01-08) ---
# These are the actual TM/HM move assignments for Emerald
TM_LIST = [
    'FOCUS_PUNCH', 'DRAGON_CLAW', 'WATER_PULSE', 'CALM_MIND', 'ROAR',
    'TOXIC', 'HAIL', 'BULK_UP', 'BULLET_SEED', 'HIDDEN_POWER',
    'SUNNY_DAY', 'TAUNT', 'ICE_BEAM', 'BLIZZARD', 'HYPER_BEAM',
    'LIGHT_SCREEN', 'PROTECT', 'RAIN_DANCE', 'GIGA_DRAIN', 'SAFEGUARD',
    'FRUSTRATION', 'SOLAR_BEAM', 'IRON_TAIL', 'THUNDERBOLT', 'THUNDER',
    'EARTHQUAKE', 'RETURN', 'DIG', 'PSYCHIC', 'SHADOW_BALL',
    'BRICK_BREAK', 'DOUBLE_TEAM', 'REFLECT', 'SHOCK_WAVE', 'FLAMETHROWER',
    'SLUDGE_BOMB', 'SANDSTORM', 'FIRE_BLAST', 'ROCK_TOMB', 'AERIAL_ACE',
    'TORMENT', 'FACADE', 'SECRET_POWER', 'REST', 'ATTRACT',
    'THIEF', 'STEEL_WING', 'SKILL_SWAP', 'SNATCH', 'OVERHEAT',
]
HM_LIST = [
    'CUT', 'FLY', 'SURF', 'STRENGTH', 'FLASH',
    'ROCK_SMASH', 'WATERFALL', 'DIVE',
]
TM_SET = set(TM_LIST)
HM_SET = set(HM_LIST)

def tmhm_label(move_const):
    if move_const in TM_SET:
        idx = TM_LIST.index(move_const) + 1
        return f"TM{idx:02d} {fmt_tmhm(move_const)}"
    if move_const in HM_SET:
        idx = HM_LIST.index(move_const) + 1
        return f"HM{idx:02d} {fmt_tmhm(move_const)}"
    return fmt_tmhm(move_const)

# --- Parse level-up learnsets ---

def parse_level_up(path):
    with open(path) as f:
        content = f.read()
    result = OrderedDict()
    pattern = re.compile(
        r'static const u16 s(\w+?)LevelUpLearnset\[\]\s*=\s*\{(.*?)\};',
        re.DOTALL
    )
    move_pattern = re.compile(r'LEVEL_UP_MOVE\(\s*(\d+)\s*,\s*(MOVE_\w+)\s*\)')
    for m in pattern.finditer(content):
        camel = m.group(1)
        body = m.group(2)
        key = camel_to_species_key(camel)
        if key == 'UNOWN' and key in result:
            continue
        moves = []
        seen = set()
        for mm in move_pattern.finditer(body):
            lvl = int(mm.group(1))
            move = mm.group(2)
            entry = (lvl, move)
            if entry not in seen:
                seen.add(entry)
                moves.append({'level': lvl, 'move': fmt_move(move)})
        result[key] = moves
    return result

# --- Parse tutor learnsets ---

def parse_tutor(path):
    with open(path) as f:
        content = f.read()

    result = {}
    # Split by [SPECIES_XXX] markers to get per-species blocks
    blocks = re.split(r'\[SPECIES_(\w+)\]', content)
    tutor_ref = re.compile(r'TUTOR\(MOVE_(\w+)\)')

    i = 1
    while i < len(blocks) - 1:
        key = blocks[i]
        body = blocks[i + 1]
        if key != 'NONE':
            moves = [fmt_move('MOVE_' + m.group(1)) for m in tutor_ref.finditer(body)]
            result[key] = moves
        i += 2
    return result

# --- Parse TMHM learnsets ---

def parse_tmhm(path):
    with open(path) as f:
        content = f.read()
    result = {}
    # Match species blocks - they can span multiple } levels
    # Find each [SPECIES_XXX] = { .learnset = { ... } }
    sp_pattern = re.compile(
        r'\[SPECIES_(\w+)\]\s*=\s*\{[^}]*\.learnset\s*=\s*\{([^}]+)\}',
        re.DOTALL
    )
    move_pattern = re.compile(r'\.(\w+)\s*=\s*TRUE')
    for m in sp_pattern.finditer(content):
        key = m.group(1)
        body = m.group(2)
        if key == 'NONE':
            continue
        moves = []
        for mm in move_pattern.finditer(body):
            move_const = mm.group(1)
            moves.append(tmhm_label(move_const))
        result[key] = moves
    return result

# --- Parse egg moves ---

def parse_egg_moves(path):
    with open(path) as f:
        content = f.read()
    result = {}
    pattern = re.compile(r'egg_moves\((\w+),(.*?)\)', re.DOTALL)
    move_pattern = re.compile(r'MOVE_(\w+)')
    for m in pattern.finditer(content):
        species_raw = m.group(1)
        body = m.group(2)
        # egg_moves uses species name without SPECIES_ prefix, like BULBASAUR
        key = species_raw
        moves = [fmt_move('MOVE_' + mm.group(1)) for mm in move_pattern.finditer(body)]
        result[key] = moves
    return result

# --- Parse national dex order ---

def parse_national_dex_order(path):
    with open(path) as f:
        content = f.read()
    enum_body = re.search(r'enum\s*\{(.*?)\}', content, re.DOTALL).group(1)
    entries = re.findall(r'NATIONAL_DEX_(\w+)', enum_body)
    skip = {'NONE', 'COUNT'}
    valid = [e for e in entries if e not in skip and not e.startswith('OLD_UNOWN')]
    # Returns {SPECIES_KEY: dex_number} (1-indexed)
    return {name: idx + 1 for idx, name in enumerate(valid)}

# --- Parse Pokédex entries ---

def parse_pokedex(text_path, entries_path):
    with open(text_path) as f:
        text_content = f.read()
    with open(entries_path) as f:
        entries_content = f.read()

    # Parse flavor text: gBulbasaurPokedexText -> BULBASAUR
    texts = {}
    text_pattern = re.compile(
        r'const u8 g(\w+?)PokedexText\[\]\s*=\s*_\((.*?)\);',
        re.DOTALL
    )
    for m in text_pattern.finditer(text_content):
        camel = m.group(1)
        raw = m.group(2)
        text = re.sub(r'"', '', raw)
        text = re.sub(r'\\n', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        key = camel_to_species_key(camel)
        texts[key] = text

    # Parse entries: [NATIONAL_DEX_XXX] = { .categoryName, .height, .weight }
    entries = {}
    block_pattern = re.compile(
        r'\[NATIONAL_DEX_(\w+)\]\s*=\s*\{([^}]+)\}',
        re.DOTALL
    )
    cat_re = re.compile(r'\.categoryName\s*=\s*_\("([^"]+)"\)')
    ht_re  = re.compile(r'\.height\s*=\s*(\d+)')
    wt_re  = re.compile(r'\.weight\s*=\s*(\d+)')
    for m in block_pattern.finditer(entries_content):
        dex_name = m.group(1)
        body = m.group(2)
        if dex_name == 'NONE':
            continue
        cat = cat_re.search(body)
        ht  = ht_re.search(body)
        wt  = wt_re.search(body)
        # NATIONAL_DEX_BULBASAUR -> BULBASAUR (same key space)
        entries[dex_name] = {
            'category': cat.group(1) if cat else '',
            'height': int(ht.group(1)) if ht else 0,
            'weight': int(wt.group(1)) if wt else 0,
        }

    # Merge texts into entries keyed by species name
    result = {}
    for key, info in entries.items():
        result[key] = {**info, 'desc': texts.get(key, '')}
    # Also add any texts not in entries
    for key, t in texts.items():
        if key not in result:
            result[key] = {'category': '', 'height': 0, 'weight': 0, 'desc': t}
    return result

# --- Parse battle moves ---

def parse_battle_moves(path):
    with open(path) as f:
        content = f.read()
    result = {}
    blocks = re.split(r'\[MOVE_(\w+)\]', content)
    power_re = re.compile(r'\.power\s*=\s*(\d+)')
    type_re = re.compile(r'\.type\s*=\s*TYPE_(\w+)')
    acc_re = re.compile(r'\.accuracy\s*=\s*(\d+)')
    pp_re = re.compile(r'\.pp\s*=\s*(\d+)')
    i = 1
    while i < len(blocks) - 1:
        key = blocks[i]
        body = blocks[i + 1]
        pw = power_re.search(body)
        ty = type_re.search(body)
        ac = acc_re.search(body)
        pp = pp_re.search(body)
        result[key] = {
            'power': int(pw.group(1)) if pw else 0,
            'type': ty.group(1) if ty else 'NORMAL',
            'accuracy': int(ac.group(1)) if ac else 0,
            'pp': int(pp.group(1)) if pp else 0,
        }
        i += 2
    return result

# --- Parse move descriptions ---

def _desc_camel_to_key(camel):
    """FirePunch -> FIRE_PUNCH, WillOWisp -> WILL_O_WISP"""
    s = re.sub(r'([A-Z])', r'_\1', camel).upper().lstrip('_')
    return s

def parse_move_descriptions(path):
    with open(path) as f:
        content = f.read()
    result = {}
    pattern = re.compile(
        r'static const u8 s(\w+?)Description\[\]\s*=\s*_\((.*?)\);',
        re.DOTALL
    )
    for m in pattern.finditer(content):
        camel = m.group(1)
        raw = m.group(2)
        # Strip quotes, escape sequences, collapse whitespace
        text = re.sub(r'"', '', raw)
        text = re.sub(r'\\n', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        key = _desc_camel_to_key(camel)
        result[key] = text
    return result

# --- Build move info dict (keyed by display name) ---

def build_move_info(moves_path, desc_path):
    battle = parse_battle_moves(moves_path)
    descs = parse_move_descriptions(desc_path)
    move_info = {}
    for key, stats in battle.items():
        display = fmt_move('MOVE_' + key)
        desc = descs.get(key, '')
        move_info[display] = {
            'type': stats['type'],
            'power': stats['power'],
            'accuracy': stats['accuracy'],
            'pp': stats['pp'],
            'desc': desc,
        }
    return move_info

# --- Parse evolutions ---

ITEM_DISPLAY = {
    'ITEM_KINGS_ROCK':      "King's Rock",
    'ITEM_UP_GRADE':        'Up-Grade',
    'ITEM_DEEP_SEA_TOOTH':  'Deep Sea Tooth',
    'ITEM_DEEP_SEA_SCALE':  'Deep Sea Scale',
    'ITEM_DRAGON_SCALE':    'Dragon Scale',
    'ITEM_METAL_COAT':      'Metal Coat',
    'ITEM_MOON_STONE':      'Moon Stone',
    'ITEM_FIRE_STONE':      'Fire Stone',
    'ITEM_THUNDER_STONE':   'Thunder Stone',
    'ITEM_WATER_STONE':     'Water Stone',
    'ITEM_LEAF_STONE':      'Leaf Stone',
    'ITEM_SUN_STONE':       'Sun Stone',
    'ITEM_BRICK_PIECE':     'Brick Piece',
}

def fmt_evo_method(method, param):
    if method == 'EVO_LEVEL':
        return f'Lv. {param}'
    if method in ('EVO_LEVEL_NINJASK', 'EVO_LEVEL_SHEDINJA', 'EVO_LEVEL_SILCOON', 'EVO_LEVEL_CASCOON'):
        return f'Lv. {param}'
    if method == 'EVO_LEVEL_ATK_LT_DEF':
        return f'Lv. {param} (ATK < DEF)'
    if method == 'EVO_LEVEL_ATK_GT_DEF':
        return f'Lv. {param} (ATK > DEF)'
    if method == 'EVO_LEVEL_ATK_EQ_DEF':
        return f'Lv. {param} (ATK = DEF)'
    if method == 'EVO_ITEM':
        return 'Use ' + ITEM_DISPLAY.get(param, param.replace('ITEM_', '').replace('_', ' ').title())
    if method == 'EVO_FRIENDSHIP':
        return 'Friendship'
    if method == 'EVO_FRIENDSHIP_DAY':
        return 'Friendship (Day)'
    if method == 'EVO_FRIENDSHIP_NIGHT':
        return 'Friendship (Night)'
    if method == 'EVO_BEAUTY':
        return f'Beauty ≥ {param}'
    return method.replace('EVO_', '').replace('_', ' ').title()

def parse_evolution(path):
    text = open(path).read()
    evolutions = {}  # species_key -> [{method, param, target}]
    chunks = re.split(r'\[SPECIES_', text)
    for chunk in chunks[1:]:
        m = re.match(r'(\w+)\]\s*=\s*\{(\{[^}]+\}(?:\s*,\s*\{[^}]+\})*)\}\s*,', chunk, re.DOTALL)
        if not m:
            continue
        species = m.group(1)
        block = m.group(2)
        evos = []
        for evo in re.finditer(r'\{(EVO_\w+),\s*(\w+),\s*SPECIES_(\w+)\}', block):
            evos.append({
                'method': evo.group(1),
                'param': evo.group(2),
                'target': evo.group(3),
            })
        if evos:
            evolutions[species] = evos
    return evolutions

# --- Parse wild encounters ---

def parse_encounters(path):
    with open(path) as f:
        lines = f.readlines()
    # Use lines 1-17100 (0-indexed: 0-17099)
    partial = ''.join(lines[:17100])
    partial = partial.rstrip().rstrip(',')
    partial += '\n  ]\n}'
    data = json.loads(partial)
    encounters = data['wild_encounter_groups'][0]['encounters']

    ENC_METHODS = {
        'land_mons': 'Land',
        'water_mons': 'Surfing',
        'rock_smash_mons': 'Rock Smash',
        'fishing_mons': 'Fishing',
    }

    species_locs = {}

    for enc in encounters:
        raw_map = enc.get('map', '')
        name_part = raw_map.replace('MAP_', '').replace('_', ' ')
        # Insert space between letters and digits: ROUTE101 -> Route 101
        name_part = re.sub(r'([A-Za-z])(\d)', r'\1 \2', name_part)
        pretty_map = name_part.title()

        for enc_type, method in ENC_METHODS.items():
            if enc_type not in enc:
                continue
            mons = enc[enc_type].get('mons', [])
            for mon in mons:
                sp = mon['species'].replace('SPECIES_', '')
                if sp not in species_locs:
                    species_locs[sp] = []
                entry = {
                    'map': pretty_map,
                    'method': method,
                    'minLvl': mon['min_level'],
                    'maxLvl': mon['max_level'],
                    'postgame': enc.get('base_label', '').endswith('_2'),
                }
                if entry not in species_locs[sp]:
                    species_locs[sp].append(entry)

    # Consolidate UNOWN variants
    unown_locs = []
    for key in list(species_locs.keys()):
        if key.startswith('UNOWN'):
            for e in species_locs[key]:
                if e not in unown_locs:
                    unown_locs.append(e)
            del species_locs[key]
    if unown_locs:
        species_locs['UNOWN'] = unown_locs

    return species_locs

# --- Load sprite as base64 ---

SPRITE_USE_ANIM = {'deoxys_attack', 'deoxys_defense', 'deoxys_speed'}

# Cosmetic-only forms: same moves, different sprite. folder_path relative to graphics/pokemon/
CASTFORM_COSMETIC = [
    ('Normal', 'castform/normal'),
    ('Sunny',  'castform/sunny'),
    ('Rainy',  'castform/rainy'),
    ('Snowy',  'castform/snowy'),
]

def _apply_shiny_palette(img, sprite_dir):
    """Swap the palette of a paletted PNG with shiny.pal from sprite_dir."""
    from PIL import Image
    pal_path = os.path.join(sprite_dir, 'shiny.pal')
    if not os.path.exists(pal_path) or img.mode != 'P':
        return img
    lines = open(pal_path).read().splitlines()
    # JASC-PAL: skip 3 header lines, then RGB triplets
    colors = []
    for line in lines[3:]:
        parts = line.split()
        if len(parts) == 3:
            colors.append(tuple(int(x) for x in parts))
    if not colors:
        return img
    # Build replacement palette (256 entries × RGB)
    old_pal = img.getpalette()  # 256×3 flat list
    new_pal = list(old_pal)
    for i, (r, g, b) in enumerate(colors[:16]):
        new_pal[i*3], new_pal[i*3+1], new_pal[i*3+2] = r, g, b
    img = img.copy()
    img.putpalette(new_pal)
    return img

def _img_to_b64(img):
    import io
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

def load_sprite_b64(folder_name, shiny=False):
    from PIL import Image
    base_dir = os.path.join(BASE, 'graphics', 'pokemon', folder_name)
    if folder_name in SPRITE_USE_ANIM:
        anim_path = os.path.join(base_dir, 'anim_front.png')
        if os.path.exists(anim_path):
            img = Image.open(anim_path)
            w, h = img.size
            img = img.crop((0, 0, w, min(64, h)))
            if shiny:
                img = _apply_shiny_palette(img, base_dir)
            return _img_to_b64(img)
    path = os.path.join(base_dir, 'front.png')
    sprite_dir = base_dir
    if not os.path.exists(path):
        # Try first subdirectory that contains front.png (e.g. castform/normal/)
        for sub in sorted(os.listdir(base_dir)) if os.path.isdir(base_dir) else []:
            candidate = os.path.join(base_dir, sub, 'front.png')
            if os.path.exists(candidate):
                path = candidate
                sprite_dir = os.path.join(base_dir, sub)
                break
        else:
            return ''
    img = Image.open(path)
    w, h = img.size
    if h > 64:
        img = img.crop((0, 0, w, 64))
    if shiny:
        img = _apply_shiny_palette(img, sprite_dir)
    return _img_to_b64(img)

def load_anim_b64(folder_name, shiny=False):
    """Load full anim_front.png strip. Returns (b64, frame_count)."""
    from PIL import Image
    base_dir = os.path.join(BASE, 'graphics', 'pokemon', folder_name)
    # Support subpaths like castform/normal
    anim_path = os.path.join(base_dir, 'anim_front.png')
    sprite_dir = base_dir
    if not os.path.exists(anim_path):
        if os.path.isdir(base_dir):
            for sub in sorted(os.listdir(base_dir)):
                candidate = os.path.join(base_dir, sub, 'anim_front.png')
                if os.path.exists(candidate):
                    anim_path = candidate
                    sprite_dir = os.path.join(base_dir, sub)
                    break
        if not os.path.exists(anim_path):
            return '', 1
    img = Image.open(anim_path)
    w, h = img.size
    frames = max(1, h // 64)
    if shiny:
        img = _apply_shiny_palette(img, sprite_dir)
    return _img_to_b64(img), frames

# --- Build combined data ---

def build_data():
    print("Parsing level-up learnsets...")
    level_up = parse_level_up(os.path.join(BASE, 'src/data/pokemon/level_up_learnsets.h'))
    print(f"  {len(level_up)} species")

    print("Parsing tutor learnsets...")
    tutor = parse_tutor(os.path.join(BASE, 'src/data/pokemon/tutor_learnsets.h'))
    print(f"  {len(tutor)} species")

    print("Parsing TM/HM learnsets...")
    tmhm = parse_tmhm(os.path.join(BASE, 'src/data/pokemon/tmhm_learnsets.h'))
    print(f"  {len(tmhm)} species")

    print("Parsing egg moves...")
    egg = parse_egg_moves(os.path.join(BASE, 'src/data/pokemon/egg_moves.h'))
    print(f"  {len(egg)} species")

    print("Parsing wild encounters...")
    locs = parse_encounters(os.path.join(BASE, 'src/data/wild_encounters.json'))
    print(f"  {len(locs)} species in wild")

    print("Parsing national dex order...")
    dex_order = parse_national_dex_order(
        os.path.join(BASE, 'include/constants/pokedex.h')
    )
    print(f"  {len(dex_order)} valid species")

    print("Parsing Pokédex entries...")
    pokedex = parse_pokedex(
        os.path.join(BASE, 'src/data/pokemon/pokedex_text.h'),
        os.path.join(BASE, 'src/data/pokemon/pokedex_entries.h'),
    )
    print(f"  {len(pokedex)} entries")

    print("Parsing evolutions...")
    raw_evos = parse_evolution(os.path.join(BASE, 'src/data/pokemon/evolution.h'))
    print(f"  {len(raw_evos)} species with evolutions")

    print("Parsing move data...")
    move_info = build_move_info(
        os.path.join(BASE, 'src/data/battle_moves.h'),
        os.path.join(BASE, 'src/data/text/move_descriptions.h'),
    )
    print(f"  {len(move_info)} moves")

    print("Loading sprites...")
    pokemon_list = []
    # First pass: build all base entries
    entries_by_key = {}
    for key in level_up:
        if key not in dex_order or key in FORM_OF:
            continue  # skip placeholders and alternate forms (handled below)
        folder = FORM_FOLDER.get(key) or species_folder(key)
        sprite = load_sprite_b64(folder)
        shiny_sprite = load_sprite_b64(folder, shiny=True)
        anim_sprite, anim_frames = load_anim_b64(folder)
        anim_shiny_sprite, _ = load_anim_b64(folder, shiny=True)
        dex = pokedex.get(key, {})
        entry = {
            'key': key,
            'name': species_display_name(key),
            'dexNum': dex_order[key],
            'sprite': sprite,
            'shinySprite': shiny_sprite,
            'animSprite': anim_sprite,
            'animShinySprite': anim_shiny_sprite,
            'animFrames': anim_frames,
            'category': dex.get('category', ''),
            'height': dex.get('height', 0),
            'weight': dex.get('weight', 0),
            'dexDesc': dex.get('desc', ''),
            'levelUp': level_up.get(key, []),
            'tmhm': tmhm.get(key, []),
            'egg': egg.get(key, []),
            'tutor': tutor.get(key, []),
            'locations': locs.get(key, []),
            'forms': [],
        }
        entries_by_key[key] = entry
        pokemon_list.append(entry)

    # Second pass: attach alternate forms to their base entry
    for key in level_up:
        if key not in FORM_OF:
            continue
        base_key, form_name = FORM_OF[key]
        if base_key not in entries_by_key:
            continue
        folder = FORM_FOLDER.get(key) or species_folder(key)
        sprite = load_sprite_b64(folder)
        shiny_sprite = load_sprite_b64(folder, shiny=True)
        anim_sprite, anim_frames = load_anim_b64(folder)
        anim_shiny_sprite, _ = load_anim_b64(folder, shiny=True)
        entries_by_key[base_key]['forms'].append({
            'name': form_name,
            'sprite': sprite,
            'shinySprite': shiny_sprite,
            'animSprite': anim_sprite,
            'animShinySprite': anim_shiny_sprite,
            'animFrames': anim_frames,
            'levelUp': level_up.get(key, []),
            'tmhm': tmhm.get(key, []),
            'egg': egg.get(key, []),
            'tutor': tutor.get(key, []),
        })

    # Prepend Normal form to forms list for any entry that has forms
    for entry in pokemon_list:
        if entry['forms']:
            normal_form = {
                'name': 'Normal',
                'sprite': entry['sprite'],
                'shinySprite': entry['shinySprite'],
                'animSprite': entry['animSprite'],
                'animShinySprite': entry['animShinySprite'],
                'animFrames': entry['animFrames'],
                'levelUp': entry['levelUp'],
                'tmhm': entry['tmhm'],
                'egg': entry['egg'],
                'tutor': entry['tutor'],
            }
            entry['forms'].insert(0, normal_form)
            # Sort forms in a fixed order
            form_order = ['Normal', 'Attack', 'Defense', 'Speed']
            entry['forms'].sort(key=lambda f: form_order.index(f['name']) if f['name'] in form_order else 99)

    # Inject cosmetic forms for Castform (same moves, different sprite)
    for entry in pokemon_list:
        if entry['key'] == 'CASTFORM':
            entry['forms'] = []
            for form_name, folder_path in CASTFORM_COSMETIC:
                sprite = load_sprite_b64(folder_path)
                shiny_sprite = load_sprite_b64(folder_path, shiny=True)
                anim_sprite, anim_frames = load_anim_b64(folder_path)
                anim_shiny_sprite, _ = load_anim_b64(folder_path, shiny=True)
                entry['forms'].append({
                    'name': form_name,
                    'sprite': sprite,
                    'shinySprite': shiny_sprite,
                    'animSprite': anim_sprite,
                    'animShinySprite': anim_shiny_sprite,
                    'animFrames': anim_frames,
                    'levelUp': entry['levelUp'],
                    'tmhm': entry['tmhm'],
                    'egg': entry['egg'],
                    'tutor': entry['tutor'],
                })
            entry['sprite'] = entry['forms'][0]['sprite']
            entry['shinySprite'] = entry['forms'][0]['shinySprite']
            entry['animSprite'] = entry['forms'][0]['animSprite']
            entry['animShinySprite'] = entry['forms'][0]['animShinySprite']
            entry['animFrames'] = entry['forms'][0]['animFrames']
            break

    # Build evolution data — resolve species keys to dexNum
    # evolvesInto: [{dexNum, name, method}]  evolvesFrom: {dexNum, name, method} | None
    reverse_evo = {}  # target_key -> [{source_key, method, param}]
    for src_key, evos in raw_evos.items():
        for evo in evos:
            tgt = evo['target']
            reverse_evo.setdefault(tgt, []).append({
                'key': src_key,
                'method': evo['method'],
                'param': evo['param'],
            })

    for entry in pokemon_list:
        key = entry['key']
        # evolvesInto
        into = []
        for evo in raw_evos.get(key, []):
            tgt_key = evo['target']
            tgt_entry = entries_by_key.get(tgt_key)
            if tgt_entry:
                into.append({
                    'dexNum': tgt_entry['dexNum'],
                    'name': tgt_entry['name'],
                    'method': fmt_evo_method(evo['method'], evo['param']),
                })
        entry['evolvesInto'] = into
        # evolvesFrom
        frm = []
        for rev in reverse_evo.get(key, []):
            src_entry = entries_by_key.get(rev['key'])
            if src_entry:
                frm.append({
                    'dexNum': src_entry['dexNum'],
                    'name': src_entry['name'],
                    'method': fmt_evo_method(rev['method'], rev['param']),
                })
        entry['evolvesFrom'] = frm

    pokemon_list.sort(key=lambda p: p['dexNum'])
    print(f"  Total: {len(pokemon_list)} Pokémon")
    return pokemon_list, move_info

# --- Generate HTML ---

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pokémon Emerald Legacy Solo Leveling Colosseum — Pokédex</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Segoe UI', Arial, sans-serif;
    background: #1a1a2e;
    color: #e0e0e0;
    display: flex;
    height: 100vh;
    overflow: hidden;
  }

  /* Sidebar */
  #sidebar {
    width: 260px;
    min-width: 220px;
    background: #16213e;
    border-right: 2px solid #0f3460;
    display: flex;
    flex-direction: column;
    height: 100vh;
    min-height: 0;
  }

  #sidebar-header {
    padding: 14px 12px 10px;
    background: #0f3460;
    border-bottom: 2px solid #e94560;
  }

  #sidebar-header h1 {
    font-size: 14px;
    font-weight: 700;
    color: #ffd700;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
  }

  #search {
    width: 100%;
    padding: 7px 10px;
    border-radius: 20px;
    border: 1px solid #e94560;
    background: #1a1a2e;
    color: #e0e0e0;
    font-size: 13px;
    outline: none;
  }

  #search::placeholder { color: #888; }
  #search:focus { border-color: #ffd700; }

  #pokemon-count {
    font-size: 11px;
    color: #aaa;
    padding: 4px 12px;
    background: #0f3460;
    border-bottom: 1px solid #0f3460;
  }

  #pokemon-list {
    overflow-y: auto;
    flex: 1;
    padding: 6px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  #pokemon-list::-webkit-scrollbar { width: 6px; }
  #pokemon-list::-webkit-scrollbar-track { background: #16213e; }
  #pokemon-list::-webkit-scrollbar-thumb { background: #0f3460; border-radius: 3px; }

  .poke-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 8px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s;
    border: 1px solid transparent;
  }

  .poke-item:hover { background: #0f3460; }
  .poke-item.active {
    background: #0f3460;
    border-color: #e94560;
  }

  .poke-item img {
    width: 32px;
    height: 32px;
    image-rendering: pixelated;
    flex-shrink: 0;
  }

  .poke-item .poke-num {
    font-size: 10px;
    color: #888;
    width: 28px;
    flex-shrink: 0;
    text-align: right;
  }

  .poke-item .poke-name {
    font-size: 13px;
    color: #e0e0e0;
    flex: 1;
  }

  .poke-item.active .poke-name { color: #ffd700; font-weight: 600; }

  /* Main panel */
  #main {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 24px;
    background: #1a1a2e;
  }

  #main::-webkit-scrollbar { width: 8px; }
  #main::-webkit-scrollbar-track { background: #1a1a2e; }
  #main::-webkit-scrollbar-thumb { background: #0f3460; border-radius: 4px; }

  #welcome {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #666;
    text-align: center;
  }

  #welcome h2 { font-size: 28px; color: #ffd700; margin-bottom: 8px; }
  #welcome p { font-size: 15px; }

  /* Pokemon detail */
  #pokemon-detail { display: none; }

  .detail-header {
    display: flex;
    align-items: flex-start;
    gap: 24px;
    background: #16213e;
    border: 2px solid #0f3460;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 20px;
  }

  .sprite-col {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }

  .detail-sprite {
    image-rendering: pixelated;
    width: 96px;
    height: 96px;
    background-color: #0f3460;
    background-repeat: no-repeat;
    background-size: 88px auto;
    background-origin: content-box;
    background-clip: content-box;
    background-position: 0 0;
    border-radius: 8px;
    padding: 4px;
  }

  .detail-sprite.shiny {
    box-shadow: 0 0 12px 4px #ffd70066;
  }

  .shiny-toggle {
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 12px;
    border: 1px solid #0f3460;
    background: #0f3460;
    color: #a0a0c0;
    cursor: pointer;
    white-space: nowrap;
  }
  .shiny-toggle:hover { border-color: #ffd700; color: #ffd700; }
  .shiny-toggle.active { background: #2a1a4e; border-color: #ffd700; color: #ffd700; }

  .detail-info { flex: 1; }

  .detail-info h2 {
    font-size: 26px;
    font-weight: 700;
    color: #ffd700;
    margin-bottom: 6px;
  }

  .detail-info .dex-num {
    font-size: 13px;
    color: #888;
    margin-bottom: 12px;
  }

  /* Locations */
  .section-title {
    font-size: 13px;
    font-weight: 700;
    color: #e94560;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
    margin-top: 4px;
  }

  .location-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .location-tag {
    background: #0f3460;
    border: 1px solid #1a4f7a;
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 12px;
    color: #b0d0f0;
  }

  .location-tag .method {
    color: #ffd700;
    font-weight: 600;
    margin-left: 4px;
  }

  .location-tag .lvl {
    color: #aaa;
    font-size: 11px;
    margin-left: 3px;
  }

  .location-tag .postgame-badge {
    display: inline-block;
    background: #e94560;
    color: #fff;
    font-size: 9px;
    font-weight: 700;
    border-radius: 6px;
    padding: 1px 5px;
    margin-left: 5px;
    letter-spacing: 0.4px;
    vertical-align: middle;
    text-transform: uppercase;
  }

  /* Tabs */
  .tabs {
    background: #16213e;
    border: 2px solid #0f3460;
    border-radius: 12px;
    overflow: hidden;
  }

  .tab-bar {
    display: flex;
    background: #0f3460;
    border-bottom: 2px solid #0f3460;
  }

  .tab-btn {
    flex: 1;
    padding: 10px 8px;
    border: none;
    background: transparent;
    color: #aaa;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    border-bottom: 2px solid transparent;
    letter-spacing: 0.3px;
  }

  .tab-btn:hover { color: #e0e0e0; background: #1a4060; }
  .tab-btn.active {
    color: #ffd700;
    border-bottom-color: #e94560;
    background: #16213e;
  }

  .tab-content { padding: 16px; }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }

  /* Level-up table */
  .level-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }

  .level-table th {
    text-align: left;
    padding: 6px 12px;
    background: #0f3460;
    color: #ffd700;
    font-size: 11px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    border-bottom: 1px solid #1a4f7a;
  }

  .level-table td {
    padding: 6px 12px;
    border-bottom: 1px solid #0f3460;
    color: #e0e0e0;
  }

  .level-table tr:last-child td { border-bottom: none; }
  .level-table tr:hover td { background: #0f3460; }

  .level-badge {
    display: inline-block;
    background: #e94560;
    color: #fff;
    border-radius: 10px;
    padding: 1px 8px;
    font-size: 11px;
    font-weight: 700;
    min-width: 30px;
    text-align: center;
  }

  /* Pill list */
  .pill-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .pill {
    background: #0f3460;
    border: 1px solid #1a4f7a;
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 12px;
    color: #b0d0f0;
  }

  .pill-tm { border-color: #1a6f3a; color: #80e0a0; background: #0a2f1a; }
  .pill-egg { border-color: #6f3a1a; color: #e0b080; background: #2f1a0a; }
  .pill-tutor { border-color: #3a1a6f; color: #b080e0; background: #1a0a2f; }

  .empty-msg {
    color: #666;
    font-style: italic;
    font-size: 13px;
    padding: 8px 0;
  }

  .no-results {
    color: #888;
    text-align: center;
    padding: 20px;
    font-style: italic;
  }

  /* Form switcher */
  .form-switcher {
    display: flex;
    gap: 6px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }

  .form-btn {
    padding: 4px 14px;
    border-radius: 16px;
    border: 1px solid #0f3460;
    background: #0f3460;
    color: #aaa;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }

  .form-btn:hover { border-color: #ffd700; color: #e0e0e0; }
  .form-btn.active { background: #e94560; border-color: #e94560; color: #fff; }

  /* Evolution chain */
  .evo-chain { display: flex; flex-direction: column; gap: 4px; margin-top: 6px; }
  .evo-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .evo-node {
    display: flex; flex-direction: column; align-items: center; gap: 2px;
    padding: 4px 8px; border-radius: 8px; border: 1px solid #0f3460;
    background: #0f3460; min-width: 60px; text-align: center;
  }
  .evo-node img { image-rendering: pixelated; width: 40px; height: 40px; }
  .evo-node span { font-size: 10px; color: #ccc; }
  .evo-node.current { border-color: #ffd700; background: #1a2a4e; }
  .evo-node.current span { color: #ffd700; font-weight: 700; }
  .evo-node:not(.current) { cursor: pointer; }
  .evo-node:not(.current):hover { border-color: #e94560; }
  .evo-arrow { font-size: 11px; color: #888; text-align: center; white-space: nowrap; }

  /* Pokédex description */
  .dex-meta {
    display: flex;
    gap: 10px;
    margin-bottom: 10px;
    flex-wrap: wrap;
  }

  .dex-meta-item {
    background: #0f3460;
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 12px;
    color: #b0d0f0;
  }

  .dex-meta-item span {
    color: #888;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    display: block;
  }

  .dex-desc {
    font-size: 13px;
    color: #c0c8d8;
    line-height: 1.6;
    font-style: italic;
    margin-bottom: 12px;
    border-left: 3px solid #0f3460;
    padding-left: 10px;
  }

  /* All-moves tab */
  .all-table { table-layout: fixed; width: 100%; }
  .all-table th:nth-child(1) { width: 36%; }
  .all-table th:nth-child(2) { width: 14%; }
  .all-table th:nth-child(3) { width: 8%; }
  .all-table th:nth-child(4) { width: 10%; }
  .all-table th:nth-child(5) { width: 32%; }

  .all-move-name { cursor: help; }
  .all-move-name:hover { text-decoration: underline dotted; }

  .all-type {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 6px;
    font-size: 10px;
    font-weight: 700;
    color: #fff;
    text-shadow: 0 1px 2px rgba(0,0,0,0.4);
    letter-spacing: 0.4px;
  }

  .all-stat { color: #b0b0b0; font-size: 12px; text-align: center; }

  .src-badge {
    display: inline-block;
    border-radius: 8px;
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 700;
    margin-right: 3px;
    letter-spacing: 0.3px;
  }
  .src-lv    { background: #1a3a5a; color: #80c8ff; border: 1px solid #2a5a8a; }
  .src-tm    { background: #0a2f1a; color: #80e0a0; border: 1px solid #1a6f3a; }
  .src-egg   { background: #2f1a0a; color: #e0b080; border: 1px solid #6f3a1a; }
  .src-tutor { background: #1a0a2f; color: #b080e0; border: 1px solid #3a1a6f; }

  /* Move tooltip */
  #move-tooltip {
    position: fixed;
    display: none;
    z-index: 9999;
    background: #0d1b33;
    border: 1px solid #2a5080;
    border-radius: 10px;
    padding: 10px 14px;
    min-width: 200px;
    max-width: 260px;
    pointer-events: none;
    box-shadow: 0 4px 20px rgba(0,0,0,0.6);
  }

  #move-tooltip .tt-name {
    font-size: 14px;
    font-weight: 700;
    color: #ffd700;
    margin-bottom: 6px;
  }

  #move-tooltip .tt-type {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 8px;
    font-size: 11px;
    font-weight: 700;
    color: #fff;
    text-shadow: 0 1px 2px rgba(0,0,0,0.5);
    margin-bottom: 8px;
    letter-spacing: 0.5px;
  }

  #move-tooltip .tt-stats {
    display: flex;
    gap: 12px;
    margin-bottom: 8px;
  }

  #move-tooltip .tt-stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    background: #162040;
    border-radius: 6px;
    padding: 4px 6px;
  }

  #move-tooltip .tt-stat-label {
    font-size: 9px;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 2px;
  }

  #move-tooltip .tt-stat-val {
    font-size: 13px;
    font-weight: 700;
    color: #e0e0e0;
  }

  #move-tooltip .tt-desc {
    font-size: 11px;
    color: #aaa;
    line-height: 1.5;
    border-top: 1px solid #1e3050;
    padding-top: 7px;
  }

  [data-move] { cursor: help; }
  [data-move]:hover { opacity: 0.85; }

  /* ── Mobile ── */
  @media (max-width: 600px) {
    body { flex-direction: column; overflow: auto; height: auto; min-height: 100dvh; }

    #sidebar {
      width: 100%;
      min-width: unset;
      height: auto;
      max-height: 100dvh;
      border-right: none;
      border-bottom: 2px solid #0f3460;
    }

    #sidebar.hidden { display: none; }

    #main {
      width: 100%;
      overflow-y: visible;
      padding: 12px;
    }

    #main.hidden { display: none; }

    #btn-back {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 12px;
      padding: 6px 14px;
      border-radius: 20px;
      border: 1px solid #1a5080;
      background: #0f3460;
      color: #e0e0e0;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }

    #btn-back:active { background: #1a4070; }

    .detail-header { flex-direction: column; align-items: center; gap: 12px; }
    .detail-info { width: 100%; }
  }

  @media (min-width: 601px) {
    #btn-back { display: none; }
  }
</style>
</head>
<body>

<div id="sidebar">
  <div id="sidebar-header">
    <h1>Pokédex</h1>
    <input type="text" id="search" placeholder="Search Pokémon..." oninput="filterList(this.value)">
  </div>
  <div id="pokemon-count"></div>
  <div id="pokemon-list"></div>
</div>

<div id="move-tooltip"></div>

<div id="main">
  <div id="welcome">
    <h2>Pokédex</h2>
    <p>Select a Pokémon from the sidebar to view its moves and locations.</p>
  </div>
  <div id="pokemon-detail"></div>
</div>

<script>
const DATA = POKEMON_DATA_PLACEHOLDER;
const MOVES = MOVE_INFO_PLACEHOLDER;
const dexIdx = {};
DATA.forEach((p, i) => dexIdx[p.dexNum] = i);

const TYPE_COLORS = {
  NORMAL:'#9099A1',FIRE:'#E8554E',WATER:'#5598D8',ELECTRIC:'#F0C13A',
  GRASS:'#5DBE62',ICE:'#76C6D0',FIGHTING:'#CE4068',POISON:'#A55FA5',
  GROUND:'#D97845',FLYING:'#8FA8D8',PSYCHIC:'#E8547A',BUG:'#90B820',
  ROCK:'#C0AA48',GHOST:'#5060A8',DRAGON:'#6048E8',DARK:'#5060A8',
  STEEL:'#9898B8',MYSTERY:'#68A090',
};

// Tooltip
const tt = document.getElementById('move-tooltip');
let ttTimeout;

function showTooltip(e, moveName) {
  const info = MOVES[moveName];
  if (!info) return;
  const color = TYPE_COLORS[info.type] || '#888';
  const pwStr = info.power > 0 ? info.power : '—';
  const accStr = info.accuracy > 0 ? info.accuracy + '%' : '—';
  tt.innerHTML = `
    <div class="tt-name">${moveName}</div>
    <div class="tt-type" style="background:${color}">${info.type}</div>
    <div class="tt-stats">
      <div class="tt-stat"><span class="tt-stat-label">Power</span><span class="tt-stat-val">${pwStr}</span></div>
      <div class="tt-stat"><span class="tt-stat-label">Accuracy</span><span class="tt-stat-val">${accStr}</span></div>
      <div class="tt-stat"><span class="tt-stat-label">PP</span><span class="tt-stat-val">${info.pp}</span></div>
    </div>
    ${info.desc ? `<div class="tt-desc">${info.desc}</div>` : ''}
  `;
  positionTooltip(e);
  tt.style.display = 'block';
}

function positionTooltip(e) {
  const margin = 12;
  let x = e.clientX + margin;
  let y = e.clientY + margin;
  if (x + 270 > window.innerWidth) x = e.clientX - 270 - margin;
  if (y + tt.offsetHeight + 10 > window.innerHeight) y = e.clientY - tt.offsetHeight - margin;
  tt.style.left = x + 'px';
  tt.style.top = y + 'px';
}

document.addEventListener('mousemove', e => {
  if (tt.style.display === 'block') positionTooltip(e);
});

document.addEventListener('mouseover', e => {
  const el = e.target.closest('[data-move]');
  if (el) {
    clearTimeout(ttTimeout);
    // Strip TM/HM prefix if present: "TM35 Flamethrower" -> "Flamethrower"
    const raw = el.dataset.move;
    const moveName = raw.replace(/^(?:TM|HM)\d+\s+/, '');
    showTooltip(e, moveName);
  }
});

document.addEventListener('mouseout', e => {
  if (e.target.closest('[data-move]')) {
    ttTimeout = setTimeout(() => { tt.style.display = 'none'; }, 80);
  }
});

let currentIdx = -1;
let currentShinyState = false;
let animTimer = null;

function startSpriteAnim(animFrames) {
  if (animTimer) clearInterval(animTimer);
  animTimer = null;
  if (animFrames < 2) return;
  let frame = 0;
  animTimer = setInterval(() => {
    const el = document.getElementById('detail-sprite-el');
    if (!el) { clearInterval(animTimer); animTimer = null; return; }
    frame = (frame + 1) % animFrames;
    el.style.backgroundPositionY = `${frame * -88}px`;
  }, 500);
}

function renderList(items) {
  const list = document.getElementById('pokemon-list');
  const count = document.getElementById('pokemon-count');
  list.innerHTML = '';
  count.textContent = items.length + ' Pokémon';
  items.forEach((p, i) => {
    const div = document.createElement('div');
    div.className = 'poke-item' + (p._origIdx === currentIdx ? ' active' : '');
    div.dataset.idx = p._origIdx;
    div.innerHTML = `
      <span class="poke-num">#${String(p.dexNum).padStart(3, '0')}</span>
      ${p.sprite ? `<img src="${p.sprite}" alt="${p.name}">` : `<div style="width:32px;height:32px;background:#0f3460;border-radius:4px;flex-shrink:0"></div>`}
      <span class="poke-name">${p.name}</span>
    `;
    div.onclick = () => selectPokemon(p._origIdx);
    list.appendChild(div);
  });
}

function filterList(query) {
  const q = query.toLowerCase().trim();
  const filtered = DATA
    .map((p, i) => ({...p, _origIdx: i}))
    .filter(p => !q || p.name.toLowerCase().includes(q));
  renderList(filtered);
}

const isMobile = () => window.innerWidth <= 600;

function goBack() {
  document.getElementById('sidebar').classList.remove('hidden');
  document.getElementById('main').classList.add('hidden');
}

function selectPokemon(idx) {
  currentIdx = idx;
  document.querySelectorAll('.poke-item').forEach(el => {
    el.classList.toggle('active', parseInt(el.dataset.idx) === idx);
  });
  document.getElementById('welcome').style.display = 'none';
  document.getElementById('pokemon-detail').style.display = 'block';
  if (isMobile()) {
    document.getElementById('sidebar').classList.add('hidden');
    document.getElementById('main').classList.remove('hidden');
  }
  renderDetail({...DATA[idx], _origIdx: idx}, 0, currentShinyState);
}

function renderDetail(p, formIdx, shiny) {
  formIdx = formIdx || 0;
  shiny = shiny || false;
  const form = p.forms && p.forms.length ? p.forms[formIdx] : null;
  const src = form || p;  // use form data if available, else base

  const dexNum = String(p.dexNum).padStart(3, '0');
  const sprite = shiny ? (src.shinySprite || src.sprite || p.sprite) : (src.sprite || p.sprite);

  const formSwitcher = p.forms && p.forms.length ? `
    <div class="form-switcher">
      ${p.forms.map((f, i) => `<button class="form-btn${i === formIdx ? ' active' : ''}" onclick="switchForm(${p._origIdx}, ${i}, ${shiny})">${f.name}</button>`).join('')}
    </div>` : '';

  const shinyToggle = `<button class="shiny-toggle${shiny ? ' active' : ''}" onclick="toggleShiny(${p._origIdx}, ${formIdx}, ${shiny})" title="Toggle shiny">✨ Shiny</button>`;

  const locHtml = p.locations.length === 0
    ? '<span class="empty-msg">Not available in the wild</span>'
    : '<div class="location-list">' + p.locations.map(l => {
        const lvl = l.minLvl === l.maxLvl ? `Lv.${l.minLvl}` : `Lv.${l.minLvl}–${l.maxLvl}`;
        const pg = l.postgame ? `<span class="postgame-badge">Post-game</span>` : '';
        return `<span class="location-tag">${l.map}<span class="method">${l.method}</span><span class="lvl">${lvl}</span>${pg}</span>`;
      }).join('') + '</div>';

  const evoNode = (e, isCurrent) => {
    const idx = dexIdx[e.dexNum];
    const sp = idx !== undefined ? DATA[idx] : null;
    const sprite = sp ? (shiny ? (sp.shinySprite || sp.sprite) : sp.sprite) : '';
    const cls = isCurrent ? 'evo-node current' : 'evo-node';
    const click = (!isCurrent && idx !== undefined) ? `onclick="selectPokemon(${idx})"` : '';
    return `<div class="${cls}" ${click}>
      ${sprite ? `<img src="${sprite}" alt="${e.name}">` : ''}
      <span>${e.name}</span>
    </div>`;
  };

  // Walk up to root ancestor, collecting [{p, method_to_reach_next}]
  const ancestors = [];
  let walker = p;
  while (walker.evolvesFrom && walker.evolvesFrom.length > 0) {
    const preEvo = walker.evolvesFrom[0];
    const idx = dexIdx[preEvo.dexNum];
    if (idx === undefined) break;
    ancestors.unshift({p: DATA[idx], method: preEvo.method});
    walker = DATA[idx];
  }

  // Returns all paths from pokemon forward to its final forms: [[{p, method}, ...], ...]
  function descendantPaths(pokemon) {
    const evos = (pokemon.evolvesInto || []).map(evo => {
      const idx = dexIdx[evo.dexNum];
      return idx !== undefined ? {p: DATA[idx], method: evo.method} : null;
    }).filter(Boolean);
    if (evos.length === 0) return [[]];
    const paths = [];
    evos.forEach(evo => {
      descendantPaths(evo.p).forEach(sub => paths.push([{p: evo.p, method: evo.method}, ...sub]));
    });
    return paths;
  }

  const paths = descendantPaths(p);
  const currentNode = {dexNum: p.dexNum, name: p.name};

  let evoHtml = '';
  if (ancestors.length > 0 || paths.some(path => path.length > 0)) {
    const rows = (paths.length > 0 && paths[0].length > 0 ? paths : [[]]).map(path => {
      let cells = [];
      ancestors.forEach(a => {
        cells.push(evoNode(a.p, false));
        cells.push(`<div class="evo-arrow">${a.method}<br>↓</div>`);
      });
      cells.push(evoNode(currentNode, true));
      path.forEach(step => {
        cells.push(`<div class="evo-arrow">${step.method}<br>↓</div>`);
        cells.push(evoNode(step.p, false));
      });
      return `<div class="evo-row">${cells.join('')}</div>`;
    });
    evoHtml = `<div class="section-title" style="margin-top:12px">Evolution</div><div class="evo-chain">${rows.join('')}</div>`;
  }

  const levelUpRows = src.levelUp.length === 0
    ? '<tr><td colspan="2" class="empty-msg" style="padding:12px">—</td></tr>'
    : src.levelUp.map(m => `<tr><td><span class="level-badge">${m.level}</span></td><td><span data-move="${m.move}">${m.move}</span></td></tr>`).join('');

  const pillList = (arr, cls) => arr.length === 0
    ? '<span class="empty-msg">—</span>'
    : arr.map(m => `<span class="pill ${cls}" data-move="${m}">${m}</span>`).join('');

  const detail = document.getElementById('pokemon-detail');
  detail.innerHTML = `
    <button id="btn-back" onclick="goBack()">◀ Back</button>
    <div class="detail-header">
      <div class="sprite-col">
        <div class="detail-sprite${shiny ? ' shiny' : ''}" id="detail-sprite-el"
             style="background-image:url('${shiny ? (src.animShinySprite || src.animSprite || sprite) : (src.animSprite || sprite)}');background-position-y:0px">
        </div>
        ${shinyToggle}
      </div>
      <div class="detail-info">
        <div class="dex-num">#${dexNum}</div>
        <h2>${p.name}</h2>
        ${formSwitcher}
        ${p.category ? `<div class="dex-meta">
          <div class="dex-meta-item"><span>Category</span>${p.category} Pokémon</div>
          ${p.height ? `<div class="dex-meta-item"><span>Height</span>${(p.height/10).toFixed(1)} m</div>` : ''}
          ${p.weight ? `<div class="dex-meta-item"><span>Weight</span>${(p.weight/10).toFixed(1)} kg</div>` : ''}
        </div>` : ''}
        ${p.dexDesc ? `<div class="dex-desc">${p.dexDesc}</div>` : ''}
        ${evoHtml}
        <div class="section-title" style="margin-top:12px">Where to Find</div>
        ${locHtml}
      </div>
    </div>

    <div class="tabs">
      <div class="tab-bar">
        <button class="tab-btn active" onclick="switchTab(this,'levelup')">Level Up</button>
        <button class="tab-btn" onclick="switchTab(this,'tmhm')">TM / HM</button>
        <button class="tab-btn" onclick="switchTab(this,'egg')">Egg Moves</button>
        <button class="tab-btn" onclick="switchTab(this,'tutor')">Tutor</button>
        <button class="tab-btn" onclick="switchTab(this,'all')">All</button>
      </div>
      <div class="tab-content">
        <div class="tab-panel active" id="tab-levelup">
          <table class="level-table">
            <thead><tr><th>Level</th><th>Move</th></tr></thead>
            <tbody>${levelUpRows}</tbody>
          </table>
        </div>
        <div class="tab-panel" id="tab-tmhm">
          <div class="pill-list">${pillList(src.tmhm, 'pill-tm')}</div>
        </div>
        <div class="tab-panel" id="tab-egg">
          <div class="pill-list">${pillList(src.egg, 'pill-egg')}</div>
        </div>
        <div class="tab-panel" id="tab-tutor">
          <div class="pill-list">${pillList(src.tutor, 'pill-tutor')}</div>
        </div>
        <div class="tab-panel" id="tab-all">
          ${buildAllTab(src)}
        </div>
      </div>
    </div>
  `;
  startSpriteAnim(src.animFrames || p.animFrames || 1);
}

function switchForm(origIdx, formIdx, shiny) {
  const p = DATA[origIdx];
  renderDetail({...p, _origIdx: origIdx}, formIdx, shiny);
}

function toggleShiny(origIdx, formIdx, currentShiny) {
  currentShinyState = !currentShiny;
  const p = DATA[origIdx];
  renderDetail({...p, _origIdx: origIdx}, formIdx, currentShinyState);
}

function buildAllTab(p) {
  // Collect all moves with their sources
  const moveMap = new Map();

  const ensure = name => {
    if (!moveMap.has(name)) moveMap.set(name, {lv: null, tm: null, egg: false, tutor: false});
  };

  p.levelUp.forEach(m => {
    ensure(m.move);
    const cur = moveMap.get(m.move);
    // Keep lowest level
    if (cur.lv === null || m.level < cur.lv) cur.lv = m.level;
  });

  p.tmhm.forEach(m => {
    // strip display name from "TM35 Flamethrower" -> "Flamethrower"
    const moveName = m.replace(/^(?:TM|HM)\d+\s+/, '');
    ensure(moveName);
    moveMap.get(moveName).tm = m;
  });

  p.egg.forEach(m => { ensure(m); moveMap.get(m).egg = true; });
  p.tutor.forEach(m => { ensure(m); moveMap.get(m).tutor = true; });

  if (moveMap.size === 0) return '<span class="empty-msg">—</span>';

  // Sort: level-up moves first (by level), then TM/HM, then egg, then tutor-only
  const entries = [...moveMap.entries()].sort((a, b) => {
    const [an, as] = a, [bn, bs] = b;
    const aLv = as.lv !== null ? as.lv : 9999;
    const bLv = bs.lv !== null ? bs.lv : 9999;
    if (aLv !== bLv) return aLv - bLv;
    return an.localeCompare(bn);
  });

  const rows = entries.map(([name, src]) => {
    const info = MOVES[name];
    const typeColor = info ? (TYPE_COLORS[info.type] || '#888') : '#555';
    const typeBadge = info ? `<span class="all-type" style="background:${typeColor}">${info.type}</span>` : '';
    const pwStr = info && info.power > 0 ? info.power : '—';
    const accStr = info && info.accuracy > 0 ? info.accuracy + '%' : '—';

    const badges = [];
    if (src.lv !== null) badges.push(`<span class="src-badge src-lv">Lv.${src.lv}</span>`);
    if (src.tm) badges.push(`<span class="src-badge src-tm">${src.tm.split(' ')[0]}</span>`);
    if (src.egg) badges.push(`<span class="src-badge src-egg">Egg</span>`);
    if (src.tutor) badges.push(`<span class="src-badge src-tutor">Tutor</span>`);

    return `<tr>
      <td><span data-move="${name}" class="all-move-name">${name}</span></td>
      <td>${typeBadge}</td>
      <td class="all-stat">${pwStr}</td>
      <td class="all-stat">${accStr}</td>
      <td>${badges.join('')}</td>
    </tr>`;
  }).join('');

  return `<table class="level-table all-table">
    <thead><tr><th>Move</th><th>Type</th><th>Pwr</th><th>Acc</th><th>Learn</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

function switchTab(btn, tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('tab-' + tabId).classList.add('active');
}

// Initial render
const indexedData = DATA.map((p, i) => ({...p, _origIdx: i}));
renderList(indexedData);
</script>
</body>
</html>
'''

def generate():
    pokemon_list, move_info = build_data()

    data_json = json.dumps(pokemon_list, ensure_ascii=False, separators=(',', ':'))
    move_json = json.dumps(move_info, ensure_ascii=False, separators=(',', ':'))

    html = HTML_TEMPLATE.replace('POKEMON_DATA_PLACEHOLDER', data_json)
    html = html.replace('MOVE_INFO_PLACEHOLDER', move_json)

    docs_dir = os.path.join(BASE, 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    out_path = os.path.join(docs_dir, 'pokedex.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"\nGenerated: {out_path} ({size_mb:.1f} MB)")

if __name__ == '__main__':
    generate()
