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

# --- Parse base stats ---

def parse_base_stats(path):
    with open(path) as f:
        content = f.read()
    result = {}
    blocks = re.split(r'\[SPECIES_(\w+)\]\s*=\s*\{', content)
    stat_fields = {
        'baseHP':        'hp',
        'baseAttack':    'atk',
        'baseDefense':   'def',
        'baseSpeed':     'spe',
        'baseSpAttack':  'spa',
        'baseSpDefense': 'spd',
    }
    i = 1
    while i < len(blocks) - 1:
        key = blocks[i].strip()
        body = blocks[i + 1]
        if key != 'NONE':
            stats = {}
            for field, short in stat_fields.items():
                m = re.search(rf'\.{field}\s*=\s*(\d+)', body)
                if m:
                    stats[short] = int(m.group(1))
            if stats:
                result[key] = stats
        i += 2
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

# --- Event / scripted legendary encounters ---
# Sourced from data/maps/*/scripts.inc (seteventmon / setwildbattle commands)
EVENT_ENCOUNTERS = {
    'ARTICUNO':  [{'map': 'Shoal Cave',        'method': 'Event', 'minLvl': 50, 'maxLvl': 50, 'postgame': True}],
    'ZAPDOS':    [{'map': 'New Mauville',       'method': 'Event', 'minLvl': 50, 'maxLvl': 50, 'postgame': True}],
    'MOLTRES':   [{'map': 'Magma Hideout',      'method': 'Event', 'minLvl': 50, 'maxLvl': 50, 'postgame': True}],
    'MEWTWO':    [{'map': 'Altering Cave',      'method': 'Event', 'minLvl': 50, 'maxLvl': 50, 'postgame': True}],
    'MEW':       [{'map': 'Faraway Island',     'method': 'Event', 'minLvl': 30, 'maxLvl': 30, 'postgame': True}],
    'RAIKOU':    [{'map': 'Space Center',       'method': 'Event', 'minLvl': 40, 'maxLvl': 40, 'postgame': True}],
    'ENTEI':     [{'map': 'Scorched Slab',      'method': 'Event', 'minLvl': 40, 'maxLvl': 40, 'postgame': True}],
    'SUICUNE':   [{'map': 'Abandoned Ship',     'method': 'Event', 'minLvl': 40, 'maxLvl': 40, 'postgame': True}],
    'LUGIA':     [{'map': 'Navel Rock',         'method': 'Event', 'minLvl': 70, 'maxLvl': 70, 'postgame': True}],
    'HO_OH':     [{'map': 'Navel Rock',         'method': 'Event', 'minLvl': 70, 'maxLvl': 70, 'postgame': True}],
    'CELEBI':    [{'map': 'Route 130',          'method': 'Event', 'minLvl': 30, 'maxLvl': 30, 'postgame': True}],
    'JIRACHI':   [{'map': 'Mossdeep City',      'method': 'Event', 'minLvl': 30, 'maxLvl': 30, 'postgame': True}],
    'REGIROCK':  [{'map': 'Desert Ruins',       'method': 'Event', 'minLvl': 40, 'maxLvl': 40, 'postgame': True}],
    'REGICE':    [{'map': 'Island Cave',        'method': 'Event', 'minLvl': 40, 'maxLvl': 40, 'postgame': True}],
    'REGISTEEL': [{'map': 'Ancient Tomb',       'method': 'Event', 'minLvl': 40, 'maxLvl': 40, 'postgame': True}],
    'LATIAS':    [{'map': 'Southern Island',    'method': 'Event', 'minLvl': 50, 'maxLvl': 50, 'postgame': True}],
    'LATIOS':    [{'map': 'Southern Island',    'method': 'Event', 'minLvl': 50, 'maxLvl': 50, 'postgame': True}],
    'KYOGRE':    [{'map': 'Marine Cave',        'method': 'Event', 'minLvl': 70, 'maxLvl': 70, 'postgame': False}],
    'GROUDON':   [{'map': 'Terra Cave',         'method': 'Event', 'minLvl': 70, 'maxLvl': 70, 'postgame': False}],
    'RAYQUAZA':  [{'map': 'Sky Pillar',         'method': 'Event', 'minLvl': 70, 'maxLvl': 70, 'postgame': False}],
    'DEOXYS':    [{'map': 'Birth Island',       'method': 'Event', 'minLvl': 30, 'maxLvl': 30, 'postgame': True}],
}

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
    for sp, entries in EVENT_ENCOUNTERS.items():
        locs.setdefault(sp, []).extend(entries)
    print(f"  {len(locs)} species in wild/events")

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

    print("Parsing base stats...")
    base_stats = parse_base_stats(os.path.join(BASE, 'src/data/pokemon/species_info.h'))
    print(f"  {len(base_stats)} species")

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
            'stats': base_stats.get(key, {}),
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
            'stats': base_stats.get(key, {}),
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
                'stats': entry['stats'],
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
<title>Pokédex — Emerald Legacy</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght,SOFT,WONK@0,9..144,300..900,0..100,0..1;1,9..144,300..900,0..100,0..1&family=Instrument+Sans:ital,wght@0,400..700;1,400..700&family=IBM+Plex+Mono:ital,wght@0,400;0,500;0,700;1,400&display=swap" rel="stylesheet">
<style>
  :root {
    --paper-0: #0a140e;
    --paper-1: #0e1b14;
    --paper-2: #13221a;
    --paper-3: #1a2c22;
    --paper-4: #233829;

    --ink:     #ece3d0;
    --ink-dim: #b5a98f;
    --ink-mut: #7b705c;
    --ink-fnt: #534a3b;

    --rule:    #2d3d33;
    --rule-2:  #1e2a23;

    --jade:       #1a8d5a;
    --jade-bright:#2eb070;
    --jade-deep:  #0d6b40;
    --jade-soft:  rgba(46,176,112,0.13);

    --ruby:    #b3272b;
    --dusk:    #e8a530;
    --dusk-soft: rgba(232,165,48,0.13);

    --cat-lv:    #7fbaf0;
    --cat-tm:    #4ecc88;
    --cat-egg:   #e8a530;
    --cat-tutor: #c4a8f5;

    --f-serif: 'Fraunces', 'Iowan Old Style', Georgia, serif;
    --f-sans:  'Instrument Sans', system-ui, -apple-system, sans-serif;
    --f-mono:  'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace;

    --grain: url("data:image/svg+xml;utf8,<svg viewBox='0 0 240 240' xmlns='http://www.w3.org/2000/svg'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.1  0 0 0 0 0.1  0 0 0 0 0.1  0 0 0 0.55 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/></svg>");

    /* legacy aliases for anything lingering */
    --bg: var(--paper-1); --bg-panel: var(--paper-2); --bg-nav: var(--paper-3);
    --bg-hover: var(--paper-4); --text: var(--ink); --text-dim: var(--ink-dim);
    --text-muted: var(--ink-mut); --border: var(--rule); --border-dim: var(--rule-2);
    --gold: var(--jade-bright); --red: var(--jade); --mono: var(--f-mono);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: var(--f-sans);
    background: var(--paper-1);
    color: var(--ink);
    display: flex;
    height: 100vh;
    overflow: hidden;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    font-size: 14px;
    letter-spacing: 0.005em;
  }

  body::before {
    content: "";
    position: fixed;
    inset: 0;
    background-image: var(--grain);
    background-size: 240px 240px;
    opacity: 0.3;
    pointer-events: none;
    mix-blend-mode: overlay;
    z-index: 9999;
  }

  /* ── Catalog Rail (sidebar) ───────────────────────────── */
  #sidebar {
    width: 280px;
    min-width: 240px;
    background: var(--paper-0);
    border-right: 1px solid var(--rule);
    display: flex;
    flex-direction: column;
    height: 100vh;
    min-height: 0;
  }

  #sidebar-header {
    padding: 22px 20px 14px;
    border-bottom: 1px solid var(--rule);
  }

  #sidebar-header h1 {
    font-family: var(--f-serif);
    font-variation-settings: "opsz" 48, "SOFT" 40, "WONK" 1;
    font-style: italic;
    font-weight: 400;
    font-size: 22px;
    color: var(--ink);
    letter-spacing: -0.01em;
    line-height: 1;
    margin-bottom: 4px;
  }
  #sidebar-header .volume {
    display: block;
    font-family: var(--f-mono);
    font-size: 9px;
    color: var(--jade-bright);
    letter-spacing: 0.3em;
    text-transform: uppercase;
    margin-bottom: 14px;
  }

  #search {
    width: 100%;
    padding: 8px 2px 8px 20px;
    border: 0;
    border-bottom: 1px solid var(--rule);
    background: transparent url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%237b705c' stroke-width='2' stroke-linecap='round'><circle cx='11' cy='11' r='7'/><line x1='21' y1='21' x2='16.65' y2='16.65'/></svg>") no-repeat left center;
    color: var(--ink);
    font-family: var(--f-serif);
    font-style: italic;
    font-size: 15px;
    outline: none;
    transition: border-color 0.2s;
  }
  #search::placeholder { color: var(--ink-mut); font-style: italic; }
  #search:focus { border-color: var(--jade-bright); }

  #pokemon-count {
    font-family: var(--f-mono);
    font-size: 9px;
    color: var(--ink-mut);
    padding: 10px 20px;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    border-bottom: 1px solid var(--rule);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  #pokemon-count::before {
    content: "Index";
    color: var(--jade-bright);
  }

  #pokemon-list {
    overflow-y: auto;
    flex: 1;
    padding: 8px 8px 24px;
    display: flex;
    flex-direction: column;
  }

  #pokemon-list::-webkit-scrollbar { width: 10px; }
  #pokemon-list::-webkit-scrollbar-track { background: transparent; }
  #pokemon-list::-webkit-scrollbar-thumb {
    background: var(--paper-3);
    border: 3px solid var(--paper-0);
    border-radius: 10px;
  }
  #pokemon-list::-webkit-scrollbar-thumb:hover { background: var(--paper-4); }

  .poke-item {
    display: grid;
    grid-template-columns: 32px 36px 1fr;
    align-items: center;
    gap: 10px;
    padding: 6px 12px;
    cursor: pointer;
    border-left: 2px solid transparent;
    transition: background 0.15s, border-color 0.15s;
    position: relative;
  }
  .poke-item:hover { background: var(--paper-1); }
  .poke-item.active {
    background: var(--jade-soft);
    border-left-color: var(--jade-bright);
  }

  .poke-item img {
    width: 36px;
    height: 36px;
    image-rendering: pixelated;
    justify-self: center;
  }

  .poke-item .poke-num {
    font-family: var(--f-mono);
    font-size: 10px;
    color: var(--ink-mut);
    letter-spacing: 0.04em;
  }
  .poke-item .poke-name {
    font-family: var(--f-serif);
    font-style: italic;
    font-weight: 400;
    font-size: 15px;
    color: var(--ink-dim);
    letter-spacing: -0.005em;
    line-height: 1.15;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .poke-item:hover .poke-name { color: var(--ink); }
  .poke-item.active .poke-num  { color: var(--jade-bright); }
  .poke-item.active .poke-name { color: var(--ink); font-style: normal; font-weight: 500; }

  /* ── Main — the editorial spread ──────────────────────── */
  #main {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    background:
      radial-gradient(1000px 500px at 100% -100px, rgba(46,176,112,0.05), transparent 55%),
      var(--paper-1);
    padding: 48px 56px 64px;
  }
  #main::-webkit-scrollbar { width: 12px; }
  #main::-webkit-scrollbar-track { background: transparent; }
  #main::-webkit-scrollbar-thumb {
    background: var(--paper-3);
    border: 3px solid var(--paper-1);
    border-radius: 12px;
  }

  #welcome {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    text-align: center;
    gap: 12px;
    max-width: 480px;
    margin: 0 auto;
  }
  #welcome h2 {
    font-family: var(--f-serif);
    font-variation-settings: "opsz" 144, "SOFT" 50, "WONK" 1;
    font-weight: 400;
    font-style: italic;
    font-size: 54px;
    color: var(--ink);
    letter-spacing: -0.03em;
    line-height: 0.95;
  }
  #welcome h2 em {
    font-style: normal;
    color: var(--jade-bright);
  }
  #welcome p {
    font-family: var(--f-mono);
    font-size: 10px;
    color: var(--ink-mut);
    letter-spacing: 0.3em;
    text-transform: uppercase;
    padding-top: 8px;
    border-top: 1px solid var(--rule);
    margin-top: 8px;
  }

  #pokemon-detail { display: none; max-width: 860px; margin: 0 auto; }

  /* Detail — tabloid spread */
  .spread {
    display: grid;
    grid-template-columns: 240px 1fr;
    gap: 40px;
    align-items: start;
    margin-bottom: 36px;
  }

  /* Sprite frame as a paper plate */
  .sprite-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }
  .plate {
    position: relative;
    padding: 20px;
    background:
      radial-gradient(circle at 30% 25%, rgba(46,176,112,0.10), transparent 60%),
      var(--paper-2);
    border: 1px solid var(--rule);
  }
  .plate::before {
    /* halftone dot pattern */
    content: "";
    position: absolute;
    inset: 0;
    background-image: radial-gradient(rgba(236,227,208,0.08) 1px, transparent 1.4px);
    background-size: 6px 6px;
    pointer-events: none;
    mix-blend-mode: overlay;
  }
  .plate::after {
    /* specimen tag mark */
    content: "";
    position: absolute;
    top: 10px; left: 10px;
    width: 8px; height: 8px;
    border-top: 1px solid var(--ink-mut);
    border-left: 1px solid var(--ink-mut);
    opacity: 0.5;
  }

  .detail-sprite {
    image-rendering: pixelated;
    width: 160px;
    height: 160px;
    background-color: transparent;
    background-repeat: no-repeat;
    background-size: 144px auto;
    background-origin: content-box;
    background-clip: content-box;
    background-position: 0 0;
    padding: 8px;
    position: relative;
  }
  .detail-sprite.shiny + .plate-tag { color: var(--dusk); border-color: var(--dusk); }
  .detail-sprite.shiny { filter: drop-shadow(0 0 12px rgba(232,165,48,0.3)); }

  .plate-tag {
    font-family: var(--f-mono);
    font-size: 9px;
    color: var(--jade-bright);
    border: 1px solid var(--rule);
    border-color: var(--jade-bright);
    padding: 4px 10px;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    background: var(--paper-1);
    margin-top: -8px;
    position: relative;
    z-index: 2;
  }

  .shiny-toggle {
    font-family: var(--f-mono);
    font-size: 9px;
    padding: 6px 12px;
    border: 1px solid var(--rule);
    background: transparent;
    color: var(--ink-dim);
    cursor: pointer;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    transition: all 0.2s;
  }
  .shiny-toggle:hover { border-color: var(--dusk); color: var(--dusk); }
  .shiny-toggle.active {
    background: var(--dusk-soft);
    border-color: var(--dusk);
    color: var(--dusk);
  }

  /* Detail text column */
  .detail-info { min-width: 0; padding-top: 4px; }

  .dex-num {
    font-family: var(--f-mono);
    font-size: 10px;
    color: var(--jade-bright);
    letter-spacing: 0.26em;
    text-transform: uppercase;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .dex-num::after {
    content: "";
    flex: 1;
    height: 1px;
    background: var(--rule);
  }

  .detail-info h2 {
    font-family: var(--f-serif);
    font-variation-settings: "opsz" 144, "SOFT" 60, "WONK" 1;
    font-weight: 400;
    font-style: italic;
    font-size: 64px;
    line-height: 0.92;
    color: var(--ink);
    letter-spacing: -0.03em;
    margin-bottom: 8px;
  }

  .category-line {
    font-family: var(--f-serif);
    font-style: italic;
    font-size: 15px;
    color: var(--ink-dim);
    margin-bottom: 20px;
  }
  .category-line b { color: var(--jade-bright); font-weight: 400; }

  /* Pull-quote dex description */
  .dex-desc {
    font-family: var(--f-serif);
    font-variation-settings: "opsz" 36, "SOFT" 50;
    font-weight: 400;
    font-size: 17px;
    line-height: 1.6;
    color: var(--ink);
    margin: 24px 0;
    padding-left: 16px;
    border-left: 2px solid var(--jade-bright);
  }

  /* Spec table — hairline rules */
  .spec-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    border-top: 1px solid var(--rule);
    border-bottom: 1px solid var(--rule);
    margin: 20px 0;
  }
  .spec-grid > div {
    padding: 10px 14px;
    border-right: 1px solid var(--rule);
  }
  .spec-grid > div:last-child { border-right: 0; }
  .spec-grid dt {
    font-family: var(--f-mono);
    font-size: 9px;
    color: var(--ink-mut);
    letter-spacing: 0.22em;
    text-transform: uppercase;
    margin-bottom: 4px;
  }
  .spec-grid dd {
    font-family: var(--f-serif);
    font-style: italic;
    font-size: 15px;
    color: var(--ink);
  }
  .spec-grid dd.mono {
    font-family: var(--f-mono);
    font-style: normal;
    font-size: 13px;
    color: var(--ink-dim);
  }

  /* Section labels */
  .section-title {
    font-family: var(--f-mono);
    font-size: 10px;
    color: var(--jade-bright);
    letter-spacing: 0.3em;
    text-transform: uppercase;
    margin-bottom: 12px;
    margin-top: 28px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-weight: 500;
  }
  .section-title::before { content: "§"; color: var(--ink-mut); font-weight: 400; font-size: 13px; }
  .section-title::after {
    content: "";
    flex: 1;
    height: 1px;
    background: var(--rule);
  }

  /* Locations — paper tags */
  .location-list { display: flex; flex-wrap: wrap; gap: 8px; }
  .location-tag {
    font-family: var(--f-sans);
    font-size: 12px;
    color: var(--ink-dim);
    padding: 6px 12px;
    border: 1px solid var(--rule);
    background: var(--paper-2);
    display: inline-flex;
    align-items: center;
    gap: 8px;
    letter-spacing: 0.01em;
  }
  .location-tag .method {
    font-family: var(--f-mono);
    font-size: 10px;
    color: var(--jade-bright);
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }
  .location-tag .lvl {
    font-family: var(--f-mono);
    font-size: 11px;
    color: var(--ink-mut);
  }
  .location-tag .postgame-badge {
    display: inline-block;
    font-family: var(--f-mono);
    font-size: 8px;
    font-weight: 700;
    color: var(--dusk);
    border: 1px solid var(--dusk);
    padding: 1px 5px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }

  /* Base stats bars */
  .stats-grid {
    display: grid;
    grid-template-columns: 36px 32px 1fr;
    gap: 6px 10px;
    align-items: center;
    margin-top: 4px;
    max-width: 420px;
  }
  .stat-label {
    font-family: var(--f-mono);
    font-size: 9px;
    color: var(--ink-mut);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    text-align: right;
  }
  .stat-val {
    font-family: var(--f-mono);
    font-size: 11px;
    color: var(--ink-dim);
    text-align: right;
  }
  .stat-bar-track {
    height: 5px;
    background: var(--paper-3);
    border-radius: 2px;
    overflow: hidden;
  }
  .stat-bar-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  }

  /* Form switcher */
  .form-switcher { display: inline-flex; gap: 0; border: 1px solid var(--rule); margin-bottom: 16px; }
  .form-btn {
    padding: 7px 14px;
    border: 0;
    background: transparent;
    color: var(--ink-mut);
    font-family: var(--f-mono);
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    cursor: pointer;
    border-right: 1px solid var(--rule);
    transition: all 0.2s;
  }
  .form-btn:last-child { border-right: 0; }
  .form-btn:hover { color: var(--ink); }
  .form-btn.active { background: var(--jade); color: var(--paper-0); }

  /* Evolution — editorial timeline */
  .evo-chain {
    display: flex;
    flex-direction: column;
    gap: 14px;
    margin-top: 6px;
    padding: 18px 20px;
    border-top: 1px solid var(--rule);
    border-bottom: 1px solid var(--rule);
    background:
      linear-gradient(180deg, rgba(236,227,208,0.01), transparent);
  }
  .evo-row {
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
  }
  .evo-node {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 8px 14px 10px;
    border: 1px solid var(--rule);
    background: var(--paper-2);
    min-width: 84px;
    text-align: center;
    transition: all 0.2s;
  }
  .evo-node img {
    image-rendering: pixelated;
    width: 48px;
    height: 48px;
  }
  .evo-node span {
    font-family: var(--f-serif);
    font-style: italic;
    font-size: 12px;
    color: var(--ink-dim);
    line-height: 1.1;
  }
  .evo-node.current {
    border-color: var(--jade-bright);
    background: var(--jade-soft);
  }
  .evo-node.current span {
    color: var(--jade-bright);
    font-style: normal;
    font-weight: 500;
  }
  .evo-node:not(.current) { cursor: pointer; }
  .evo-node:not(.current):hover {
    border-color: var(--ink-dim);
    transform: translateY(-1px);
  }
  .evo-arrow {
    font-family: var(--f-mono);
    font-size: 9px;
    color: var(--ink-mut);
    white-space: nowrap;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    text-align: center;
    line-height: 1.4;
    position: relative;
    padding: 0 4px;
  }
  .evo-arrow::before {
    content: "→";
    display: block;
    font-family: var(--f-serif);
    font-size: 18px;
    color: var(--jade-bright);
    font-style: normal;
    line-height: 1;
    margin-bottom: 2px;
  }

  /* Tabs as editorial nav */
  .tabs {
    border-top: 1px solid var(--rule);
    border-bottom: 1px solid var(--rule);
  }
  .tab-bar {
    display: flex;
    border-bottom: 1px solid var(--rule);
    background: transparent;
  }
  .tab-btn {
    flex: 1;
    padding: 14px 12px;
    border: 0;
    background: transparent;
    color: var(--ink-mut);
    font-family: var(--f-mono);
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    cursor: pointer;
    border-right: 1px solid var(--rule);
    position: relative;
    transition: color 0.2s, background 0.2s;
  }
  .tab-btn:last-child { border-right: 0; }
  .tab-btn:hover { color: var(--ink-dim); background: rgba(236,227,208,0.02); }
  .tab-btn.active {
    color: var(--ink);
    background: rgba(46,176,112,0.04);
  }
  .tab-btn.active::before {
    content: "";
    position: absolute;
    left: 0; right: 0; top: -1px;
    height: 2px;
    background: var(--jade-bright);
  }

  .tab-content { padding: 22px 26px 28px; }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }

  /* Move tables — spec sheet */
  .level-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  .level-table th {
    text-align: left;
    padding: 10px 14px 10px 0;
    color: var(--ink-mut);
    font-family: var(--f-mono);
    font-size: 9px;
    font-weight: 500;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    border-bottom: 1px solid var(--rule);
  }
  .level-table td {
    padding: 10px 14px 10px 0;
    border-bottom: 1px solid var(--rule-2);
    color: var(--ink);
    font-family: var(--f-serif);
    font-size: 15px;
    font-style: italic;
    font-weight: 400;
  }
  .level-table tr:last-child td { border-bottom: 0; }
  .level-table tbody tr { transition: background 0.15s; }
  .level-table tbody tr:hover { background: var(--jade-soft); }

  .level-badge {
    display: inline-block;
    font-family: var(--f-mono);
    font-size: 11px;
    font-weight: 500;
    color: var(--jade-bright);
    border: 1px solid var(--jade-bright);
    padding: 1px 8px;
    letter-spacing: 0.1em;
    width: 54px;
    text-align: center;
    white-space: nowrap !important;
    word-spacing: -0.15em;
  }

  /* Pills — paper labels */
  .pill-list { display: flex; flex-wrap: wrap; gap: 6px; }
  .pill {
    font-family: var(--f-serif);
    font-style: italic;
    font-size: 13px;
    padding: 4px 12px;
    border: 1px solid var(--rule);
    background: var(--paper-2);
    color: var(--ink-dim);
    transition: all 0.15s;
  }
  .pill:hover { color: var(--ink); border-color: var(--ink-mut); transform: translateY(-1px); }
  .pill-tm    { border-color: rgba(78,204,136,0.4); color: var(--cat-tm); }
  .pill-egg   { border-color: rgba(232,165,48,0.4); color: var(--cat-egg); }
  .pill-tutor { border-color: rgba(196,168,245,0.4); color: var(--cat-tutor); }

  .empty-msg {
    font-family: var(--f-serif);
    font-style: italic;
    font-size: 14px;
    color: var(--ink-mut);
    padding: 10px 0;
  }
  .no-results {
    color: var(--ink-mut);
    text-align: center;
    padding: 40px 20px;
    font-family: var(--f-serif);
    font-style: italic;
    font-size: 14px;
  }

  /* All-moves table */
  .all-table { table-layout: fixed; width: 100%; }
  .all-table th:nth-child(1) { width: 36%; }
  .all-table th:nth-child(2) { width: 14%; }
  .all-table th:nth-child(3) { width: 8%; }
  .all-table th:nth-child(4) { width: 10%; }
  .all-table th:nth-child(5) { width: 32%; }

  .all-move-name { cursor: help; }
  .all-move-name:hover { color: var(--jade-bright); }

  .all-type {
    display: inline-block;
    padding: 2px 8px;
    font-family: var(--f-mono);
    font-size: 9px;
    font-weight: 500;
    color: #fff;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }
  .all-stat {
    color: var(--ink-dim);
    font-size: 13px;
    text-align: center;
    font-family: var(--f-mono) !important;
    font-style: normal !important;
  }

  .src-badge {
    display: inline-block;
    font-family: var(--f-mono);
    font-size: 9px;
    font-weight: 500;
    padding: 1px 6px;
    margin-right: 3px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border: 1px solid;
    background: transparent;
  }
  .src-lv    { color: var(--cat-lv);    border-color: rgba(127,186,240,0.4); }
  .src-tm    { color: var(--cat-tm);    border-color: rgba(78,204,136,0.4); }
  .src-egg   { color: var(--cat-egg);   border-color: rgba(232,165,48,0.4); }
  .src-tutor { color: var(--cat-tutor); border-color: rgba(196,168,245,0.4); }

  /* Tooltip — marginalia card */
  #move-tooltip {
    position: fixed;
    display: none;
    z-index: 9999;
    background: var(--paper-0);
    border: 1px solid var(--jade-bright);
    padding: 14px 16px;
    min-width: 240px;
    max-width: 300px;
    pointer-events: none;
    box-shadow: 0 30px 60px -20px rgba(0,0,0,0.7);
  }
  #move-tooltip::before {
    content: "MOVE";
    position: absolute;
    top: -7px;
    left: 14px;
    font-family: var(--f-mono);
    font-size: 9px;
    color: var(--jade-bright);
    background: var(--paper-0);
    padding: 0 6px;
    letter-spacing: 0.3em;
  }
  #move-tooltip .tt-name {
    font-family: var(--f-serif);
    font-variation-settings: "opsz" 48;
    font-style: italic;
    font-weight: 400;
    font-size: 22px;
    color: var(--ink);
    letter-spacing: -0.01em;
    margin-bottom: 10px;
    line-height: 1;
  }
  #move-tooltip .tt-type {
    display: inline-block;
    padding: 2px 10px;
    font-family: var(--f-mono);
    font-size: 9px;
    font-weight: 500;
    color: #fff;
    margin-bottom: 12px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }
  #move-tooltip .tt-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    margin-bottom: 10px;
    border-top: 1px solid var(--rule);
    border-bottom: 1px solid var(--rule);
  }
  #move-tooltip .tt-stat {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding: 8px 10px;
    border-right: 1px solid var(--rule);
  }
  #move-tooltip .tt-stat:last-child { border-right: 0; }
  #move-tooltip .tt-stat-label {
    font-family: var(--f-mono);
    font-size: 8px;
    color: var(--ink-mut);
    letter-spacing: 0.22em;
    text-transform: uppercase;
    margin-bottom: 3px;
  }
  #move-tooltip .tt-stat-val {
    font-family: var(--f-serif);
    font-style: italic;
    font-size: 18px;
    color: var(--jade-bright);
    line-height: 1;
  }
  #move-tooltip .tt-desc {
    font-family: var(--f-serif);
    font-size: 13px;
    color: var(--ink-dim);
    line-height: 1.5;
    padding-top: 2px;
    font-style: italic;
  }

  [data-move] { cursor: help; }
  [data-move]:hover { opacity: 0.82; }

  /* Back button (mobile) */
  #btn-back {
    display: none;
    align-items: center;
    gap: 8px;
    margin-bottom: 20px;
    padding: 7px 14px;
    border: 1px solid var(--rule);
    background: transparent;
    color: var(--jade-bright);
    font-family: var(--f-mono);
    font-size: 10px;
    font-weight: 500;
    cursor: pointer;
    letter-spacing: 0.22em;
    text-transform: uppercase;
  }
  #btn-back:active { background: var(--paper-3); }

  /* Responsive */
  @media (max-width: 700px) {
    body { flex-direction: column; overflow: auto; height: auto; min-height: 100dvh; }
    #sidebar {
      width: 100%; min-width: unset; height: auto; max-height: 100dvh;
      border-right: none; border-bottom: 1px solid var(--rule);
    }
    #sidebar.hidden { display: none; }
    #main { width: 100%; overflow-y: visible; padding: 24px 18px 40px; }
    #main.hidden { display: none; }
    #btn-back { display: inline-flex; }

    .spread { grid-template-columns: 1fr; gap: 24px; text-align: center; }
    .sprite-col { justify-self: center; }
    .detail-info h2 { font-size: 42px; }
    .spec-grid { grid-template-columns: repeat(2, 1fr); text-align: left; }
    .spec-grid > div:nth-child(2n) { border-right: 0; }
    .spec-grid > div:nth-child(-n+2) { border-bottom: 1px solid var(--rule); }
  }
</style>
</head>
<body>

<div id="sidebar">
  <div id="sidebar-header">
    <h1>Pokédex</h1>
    <span class="volume">Vol. I · National Dex</span>
    <input type="text" id="search" placeholder="Search the index…" oninput="filterList(this.value)">
  </div>
  <div id="pokemon-count"></div>
  <div id="pokemon-list"></div>
</div>

<div id="move-tooltip"></div>

<div id="main">
  <div id="welcome">
    <h2>The <em>National</em><br>Pokédex</h2>
    <p>Select a specimen from the index</p>
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
      <div class="tt-stat"><span class="tt-stat-label">Acc.</span><span class="tt-stat-val">${accStr}</span></div>
      <div class="tt-stat"><span class="tt-stat-label">PP</span><span class="tt-stat-val">${info.pp}</span></div>
    </div>
    ${info.desc ? `<div class="tt-desc">${info.desc}</div>` : ''}
  `;
  tt.style.display = 'block';
  positionTooltip(e.clientX, e.clientY);
}

function positionTooltip(cx, cy) {
  const margin = 14;
  const w = tt.offsetWidth || 300;
  const h = tt.offsetHeight || 160;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  let x = cx + margin;
  let y = cy + margin;
  if (x + w > vw - margin) x = cx - w - margin;
  if (x < margin) x = margin;
  if (y + h > vh - margin) y = cy - h - margin;
  if (y < margin) y = margin;
  tt.style.left = x + 'px';
  tt.style.top = y + 'px';
}

document.addEventListener('mousemove', e => {
  if (tt.style.display === 'block') positionTooltip(e.clientX, e.clientY);
});

document.addEventListener('mouseover', e => {
  const el = e.target.closest('[data-move]');
  if (el) {
    clearTimeout(ttTimeout);
    const raw = el.dataset.move;
    const moveName = raw.replace(/^(?:TM|HM)\d+\s+/, '');
    showTooltip({ clientX: e.clientX, clientY: e.clientY }, moveName);
  }
});

document.addEventListener('mouseout', e => {
  if (e.target.closest('[data-move]')) {
    ttTimeout = setTimeout(() => { tt.style.display = 'none'; }, 80);
  }
});

document.addEventListener('touchstart', e => {
  const el = e.target.closest('[data-move]');
  if (el) {
    e.preventDefault();
    clearTimeout(ttTimeout);
    const t = e.touches[0];
    const raw = el.dataset.move;
    const moveName = raw.replace(/^(?:TM|HM)\d+\s+/, '');
    showTooltip({ clientX: t.clientX, clientY: t.clientY }, moveName);
  }
}, { passive: false });

document.addEventListener('touchend', e => {
  if (e.target.closest('[data-move]')) {
    ttTimeout = setTimeout(() => { tt.style.display = 'none'; }, 1800);
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
    el.style.backgroundPositionY = `${frame * -144}px`;
  }, 500);
}

function renderList(items) {
  const list = document.getElementById('pokemon-list');
  const count = document.getElementById('pokemon-count');
  list.innerHTML = '';
  count.innerHTML = `<span>${items.length} entries</span>`;
  if (items.length === 0) {
    list.innerHTML = '<div class="no-results">No specimens match.</div>';
    return;
  }
  items.forEach((p) => {
    const div = document.createElement('div');
    div.className = 'poke-item' + (p._origIdx === currentIdx ? ' active' : '');
    div.dataset.idx = p._origIdx;
    div.innerHTML = `
      <span class="poke-num">${String(p.dexNum).padStart(3, '0')}</span>
      ${p.sprite ? `<img src="${p.sprite}" alt="${p.name}">` : `<div style="width:36px;height:36px;"></div>`}
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

const isMobile = () => window.innerWidth <= 700;

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
  document.getElementById('main').scrollTop = 0;
}

function renderDetail(p, formIdx, shiny) {
  formIdx = formIdx || 0;
  shiny = shiny || false;
  const form = p.forms && p.forms.length ? p.forms[formIdx] : null;
  const src = form || p;

  const dexNum = String(p.dexNum).padStart(3, '0');
  const sprite = shiny ? (src.shinySprite || src.sprite || p.sprite) : (src.sprite || p.sprite);

  const formSwitcher = p.forms && p.forms.length ? `
    <div class="form-switcher">
      ${p.forms.map((f, i) => `<button class="form-btn${i === formIdx ? ' active' : ''}" onclick="switchForm(${p._origIdx}, ${i}, ${shiny})">${f.name}</button>`).join('')}
    </div>` : '';

  const shinyToggle = `<button class="shiny-toggle${shiny ? ' active' : ''}" onclick="toggleShiny(${p._origIdx}, ${formIdx}, ${shiny})" title="Toggle shiny">${shiny ? '★ Shiny' : '☆ Shiny'}</button>`;

  const locHtml = p.locations.length === 0
    ? '<span class="empty-msg">Not observed in the wild.</span>'
    : '<div class="location-list">' + p.locations.map(l => {
        const lvl = l.minLvl === l.maxLvl ? `Lv.${l.minLvl}` : `Lv.${l.minLvl}–${l.maxLvl}`;
        const pg = l.postgame ? `<span class="postgame-badge">Post</span>` : '';
        return `<span class="location-tag"><span>${l.map}</span><span class="method">${l.method}</span><span class="lvl">${lvl}</span>${pg}</span>`;
      }).join('') + '</div>';

  const STAT_META = [
    {key:'hp',  label:'HP',  color:'#e05555'},
    {key:'atk', label:'ATK', color:'#e07030'},
    {key:'def', label:'DEF', color:'#e0c030'},
    {key:'spa', label:'SpA', color:'#6890f0'},
    {key:'spd', label:'SpD', color:'#78c850'},
    {key:'spe', label:'SPE', color:'#f85888'},
  ];
  const statsHtml = (() => {
    const s = src.stats || p.stats || {};
    if (!Object.keys(s).length) return '';
    const total = STAT_META.reduce((n, m) => n + (s[m.key] || 0), 0);
    const rows = STAT_META.map(m => {
      const v = s[m.key] || 0;
      const pct = Math.round(v / 255 * 100);
      return `<span class="stat-label">${m.label}</span><span class="stat-val">${v}</span><div class="stat-bar-track"><div class="stat-bar-fill" style="width:${pct}%;background:${m.color}"></div></div>`;
    }).join('');
    return `<div class="section-title" style="margin-top:28px">Base Statistics</div>
    <div class="stats-grid">${rows}</div>
    <div style="font-family:var(--f-mono);font-size:9px;color:var(--ink-mut);letter-spacing:0.15em;margin-top:10px;max-width:420px;text-align:right">TOTAL <span style="color:var(--ink-dim)">${total}</span></div>`;
  })();

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

  const ancestors = [];
  let walker = p;
  while (walker.evolvesFrom && walker.evolvesFrom.length > 0) {
    const preEvo = walker.evolvesFrom[0];
    const idx = dexIdx[preEvo.dexNum];
    if (idx === undefined) break;
    ancestors.unshift({p: DATA[idx], method: preEvo.method});
    walker = DATA[idx];
  }

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
        cells.push(`<div class="evo-arrow">${a.method}</div>`);
      });
      cells.push(evoNode(currentNode, true));
      path.forEach(step => {
        cells.push(`<div class="evo-arrow">${step.method}</div>`);
        cells.push(evoNode(step.p, false));
      });
      return `<div class="evo-row">${cells.join('')}</div>`;
    });
    evoHtml = `<div class="section-title">Evolutionary Line</div><div class="evo-chain">${rows.join('')}</div>`;
  }

  const levelUpRows = src.levelUp.length === 0
    ? '<tr><td colspan="2" class="empty-msg" style="padding:16px 0">—</td></tr>'
    : src.levelUp.map(m => `<tr><td style="width:1%;white-space:nowrap;padding-right:14px"><span class="level-badge">Lv&nbsp;${m.level}</span></td><td><span data-move="${m.move}">${m.move}</span></td></tr>`).join('');

  const pillList = (arr, cls) => arr.length === 0
    ? '<span class="empty-msg">—</span>'
    : arr.map(m => `<span class="pill ${cls}" data-move="${m}">${m}</span>`).join('');

  const category = p.category ? `${p.category} Pokémon` : '';
  const specs = p.category ? `
    <dl class="spec-grid">
      <div><dt>Category</dt><dd>${p.category}</dd></div>
      <div><dt>Height</dt><dd class="mono">${p.height ? (p.height/10).toFixed(1) + ' m' : '—'}</dd></div>
      <div><dt>Weight</dt><dd class="mono">${p.weight ? (p.weight/10).toFixed(1) + ' kg' : '—'}</dd></div>
      <div><dt>Region</dt><dd>Hoenn</dd></div>
    </dl>` : '';

  const detail = document.getElementById('pokemon-detail');
  detail.innerHTML = `
    <button id="btn-back" onclick="goBack()">← Return to Index</button>

    <div class="spread">
      <div class="sprite-col">
        <div class="plate">
          <div class="detail-sprite${shiny ? ' shiny' : ''}" id="detail-sprite-el"
               style="background-image:url('${shiny ? (src.animShinySprite || src.animSprite || sprite) : (src.animSprite || sprite)}');background-position-y:0px">
          </div>
        </div>
        <span class="plate-tag">${shiny ? '★ Shiny Plate' : `Plate Nº ${dexNum}`}</span>
        ${shinyToggle}
      </div>

      <div class="detail-info">
        <div class="dex-num">Specimen Nº ${dexNum}${category ? ' · ' + category : ''}</div>
        <h2>${p.name}</h2>
        ${formSwitcher}
        ${p.dexDesc ? `<div class="dex-desc">${p.dexDesc}</div>` : ''}
        ${specs}
      </div>
    </div>

    ${evoHtml}

    <div class="section-title">Where Observed</div>
    ${locHtml}

    ${statsHtml}

    <div class="section-title" style="margin-top:28px">Learned Techniques</div>
    <div class="tabs">
      <div class="tab-bar">
        <button class="tab-btn active" onclick="switchTab(this,'levelup')">By Level</button>
        <button class="tab-btn" onclick="switchTab(this,'tmhm')">TM / HM</button>
        <button class="tab-btn" onclick="switchTab(this,'egg')">Egg</button>
        <button class="tab-btn" onclick="switchTab(this,'tutor')">Tutor</button>
        <button class="tab-btn" onclick="switchTab(this,'all')">Full Ledger</button>
      </div>
      <div class="tab-content">
        <div class="tab-panel active" id="tab-levelup">
          <table class="level-table">
            <thead><tr><th>Level</th><th>Technique</th></tr></thead>
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
  const moveMap = new Map();

  const ensure = name => {
    if (!moveMap.has(name)) moveMap.set(name, {lv: null, tm: null, egg: false, tutor: false});
  };

  p.levelUp.forEach(m => {
    ensure(m.move);
    const cur = moveMap.get(m.move);
    if (cur.lv === null || m.level < cur.lv) cur.lv = m.level;
  });

  p.tmhm.forEach(m => {
    const moveName = m.replace(/^(?:TM|HM)\d+\s+/, '');
    ensure(moveName);
    moveMap.get(moveName).tm = m;
  });

  p.egg.forEach(m => { ensure(m); moveMap.get(m).egg = true; });
  p.tutor.forEach(m => { ensure(m); moveMap.get(m).tutor = true; });

  if (moveMap.size === 0) return '<span class="empty-msg">—</span>';

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
    <thead><tr><th>Technique</th><th>Type</th><th>Pwr</th><th>Acc</th><th>Source</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

function switchTab(btn, tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('tab-' + tabId).classList.add('active');
}

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
