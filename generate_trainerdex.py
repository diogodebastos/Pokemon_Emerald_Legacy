#!/usr/bin/env python3
"""Generates trainerdex.html — a field guide to notable trainers and their teams.

Mirrors generate_pokedex.py: parses the decomp source and bakes a single
self-contained HTML file (trainer data + sprites inlined as base64). Reuses the
pokedex generator's sprite/move/ability helpers via import.
"""

import re
import os
import json

import generate_pokedex as pdx

BASE = os.path.dirname(os.path.abspath(__file__))

# --- Which trainers count as "notable", and how they group in the sidebar ---
# class -> (category label, category sort order)
CATEGORY = {
    'LEADER':          ('Gym Leaders', 0),
    'ELITE_FOUR':      ('Elite Four', 1),
    'CHAMPION':        ('Champion', 2),
    'CHAMPION_STEVEN': ('Champion', 2),
    'RIVAL':           ('Rivals', 3),
    'RS_PROTAG':       ('Rivals', 3),
    'WALLY':           ('Rivals', 3),
    'AQUA_LEADER':     ('Team Aqua', 4),
    'AQUA_ADMIN':      ('Team Aqua', 4),
    'MAGMA_LEADER':    ('Team Magma', 5),
    'MAGMA_ADMIN':     ('Team Magma', 5),
    'SALON_MAIDEN':    ('Frontier Brains', 6),
    'DOME_ACE':        ('Frontier Brains', 6),
    'PALACE_MAVEN':    ('Frontier Brains', 6),
    'ARENA_TYCOON':    ('Frontier Brains', 6),
    'FACTORY_HEAD':    ('Frontier Brains', 6),
    'PIKE_QUEEN':      ('Frontier Brains', 6),
    'PYRAMID_KING':    ('Frontier Brains', 6),
    'LOREKEEPER':      ('Frontier Brains', 6),
    'SUPERTRAINER':    ('Supertrainers', 7),
    'MYTH_TRAINER':    ('Myth Trainers', 8),
}
NOTABLE_CLASSES = set(CATEGORY.keys())

# Battle Royale: the remaining TRAINER_FRONTIER_* overworld trainers that aren't
# Supertrainers / Myth Trainers / Frontier Brains (they wear ordinary disguise classes).
BATTLE_ROYALE = ('Battle Royale', 11)

# Battle Royale gauntlet leaders (issue #5/#7). These reuse ordinary trainer IDs and the
# canonical LEADER/... classes in-game, so pull them into dedicated Trainerdex groups by ID
# instead of merging them into Hoenn's Gym Leaders / Elite Four / Champion sections.
KANTO_GAUNTLET_CAT = ('Kanto Gauntlet', 9)
JOHTO_GAUNTLET_CAT = ('Johto Gauntlet', 10)
KANTO_GAUNTLET_IDS = {
    'TRAINER_FRONTIER_RUTH', 'TRAINER_FRONTIER_GAVIN', 'TRAINER_DUDLEY', 'TRAINER_TERRY',
    'TRAINER_KAYLEE', 'TRAINER_FRONTIER_JAXON', 'TRAINER_MIKE_1', 'TRAINER_FRONTIER_TODD',
    'TRAINER_FRONTIER_MALORY', 'TRAINER_FRONTIER_EMILEE', 'TRAINER_FRONTIER_ARMANDO',
    'TRAINER_FRONTIER_ELAINE', 'TRAINER_FRONTIER_CLARE',
}
JOHTO_GAUNTLET_IDS = {
    'TRAINER_FRONTIER_PEDRO', 'TRAINER_FRONTIER_JOSIE', 'TRAINER_FRONTIER_ERICK',
    'TRAINER_FRONTIER_JOYCE', 'TRAINER_FRONTIER_MELODY', 'TRAINER_FRONTIER_SKYLER',
    'TRAINER_FRONTIER_ESTHER', 'TRAINER_FRONTIER_WILSON',
}

# Special rebattleable utility trainers (shown as their own group, force-included even
# though their in-game class isn't "notable"). BRYON is the Mr. Mimic mirror-match slot.
SPECIAL_CAT = ('Special Trainers', 12)
SPECIAL_TRAINER_IDS = {'TRAINER_FRONTIER_BRYON', 'TRAINER_GRINDING_NURSE'}

# Explicit sidebar ordering of groups within a category (by display name).
GROUP_ORDER = {
    'Team Aqua':  ['Shelly', 'Matt', 'Archie'],
    'Team Magma': ['Courtney', 'Tabitha', 'Maxie'],
}

# Rival starter / location ordering (Brendan & May). This mod pairs each Hoenn
# starter with an Eeveelution, so the switcher heading shows both.
STARTER_RANK = {'TREECKO': 0, 'TORCHIC': 1, 'MUDKIP': 2}
STARTER_LABEL = {'TREECKO': 'Treecko / Eevee', 'TORCHIC': 'Torchic / Espeon', 'MUDKIP': 'Mudkip / Umbreon'}
RIVAL_LOC_RANK = {'ROUTE_103': 0, 'RUSTBORO': 1, 'ROUTE_110': 2,
                  'ROUTE_119': 3, 'LILYCOVE': 4, 'EVERGRANDE': 5}

# --- Display helpers ---

def _clean_text(raw):
    """Strip _("...") wrapper, quotes, and tidy whitespace."""
    s = raw.strip()
    s = re.sub(r'^_\(\s*"?', '', s)
    s = re.sub(r'"?\s*\)$', '', s)
    s = s.replace('{PKMN}', 'Pokémon')
    s = s.strip().strip('"')
    return s

def title_const(const, prefix):
    """ITEM_SILK_SCARF -> 'Silk Scarf' (fallback when no name table entry)."""
    name = const.replace(prefix, '')
    return ' '.join(p.capitalize() for p in name.split('_'))

def order_variants(name, variants):
    """Sort a group's variants in place and assign each a 'label'. Strips the
    common leading ID-tokens, then orders/labels by group flavour:
      - Rivals (Brendan/May): by starter (Treecko, Torchic, Mudkip) then location.
      - Wally: Mauville, Petalburg, then Victory Road N.
      - Numbered teams (gym leaders): Team 1, Team 1.2, Team 1.3, Team 2, …
    """
    ids = [v['id'] for v in variants]
    toks = [i.split('_') for i in ids]
    n = min(len(t) for t in toks)
    cp = 0
    for k in range(n):
        if len({t[k] for t in toks}) == 1:
            cp += 1
        else:
            break
    rests = [t[cp:] for t in toks]
    is_rival = any(tok in STARTER_RANK for r in rests for tok in r)
    is_wally = (name == 'Wally')

    for v, rest in zip(variants, rests):
        v['group'] = None
        if is_rival:
            starter = next((tok for tok in rest if tok in STARTER_RANK), None)
            loc_toks = [tok for tok in rest if tok not in STARTER_RANK]
            loc = '_'.join(loc_toks)
            loc_label = ' '.join(w.capitalize() for w in loc_toks) if loc_toks else ''
            v['_sort'] = (STARTER_RANK.get(starter, 99), RIVAL_LOC_RANK.get(loc, 99))
            v['group'] = STARTER_LABEL.get(starter, starter.capitalize() if starter else 'Other')
            v['label'] = loc_label or 'Battle'
        elif is_wally:
            r = '_'.join(rest)
            if r.startswith('VR'):
                num = int(rest[-1]) if rest and rest[-1].isdigit() else 0
                v['_sort'] = (2, num)
                v['label'] = f'Victory Road {num}'
            else:
                v['_sort'] = ({'MAUVILLE': 0, 'PETALBURG': 1}.get(r, 9), 0)
                v['label'] = ' '.join(w.capitalize() for w in rest) if rest else 'Battle'
        else:
            nums = [int(x) for x in rest if x.isdigit()]
            nonnum = [x for x in rest if not x.isdigit()]
            if nums:
                tail = ' ' + ' '.join(w.capitalize() for w in nonnum) if nonnum else ''
                v['_sort'] = (0, tuple(nums), nonnum)
                v['label'] = 'Team ' + '.'.join(str(x) for x in nums) + tail
            elif not rest:
                v['_sort'] = (0, (1,), [])
                v['label'] = 'Team 1'
            else:
                v['_sort'] = (1, (), rest)
                v['label'] = ' '.join(w.capitalize() for w in rest)

    variants.sort(key=lambda v: v['_sort'])
    for v in variants:
        v.pop('_sort', None)

# --- Parse trainer class names ---

def parse_class_names(path):
    content = open(path).read()
    result = {}
    for m in re.finditer(r'\[TRAINER_CLASS_(\w+)\]\s*=\s*(_\("[^"]*"\))', content):
        result[m.group(1)] = _clean_text(m.group(2))
    return result

# --- Parse item names ---

def parse_item_names(path):
    content = open(path).read()
    result = {}
    for m in re.finditer(r'\[ITEM_(\w+)\]\s*=\s*\{.*?\.name\s*=\s*_\("([^"]*)"\)',
                         content, re.DOTALL):
        result[m.group(1)] = _clean_text('"' + m.group(2) + '"').title()
    return result

def item_display(const, item_names):
    if const in ('ITEM_NONE', 'NONE', '', None):
        return None
    key = const.replace('ITEM_', '')
    return item_names.get(key) or title_const(const, 'ITEM_')

# --- Parse trainer front pics: TRAINER_PIC_X -> snake_case png basename ---

def parse_trainer_pics(tables_path, gfx_path):
    # TRAINER_SPRITE(HIKER, gTrainerFrontPic_Hiker, ...) -> PIC_HIKER : gTrainerFrontPic_Hiker
    pic_to_sym = {}
    for m in re.finditer(r'TRAINER_SPRITE\(\s*(\w+)\s*,\s*(gTrainerFrontPic_\w+)', open(tables_path).read()):
        pic_to_sym[m.group(1)] = m.group(2)
    # gTrainerFrontPic_Hiker[] = INCBIN_U32("graphics/trainers/front_pics/hiker.4bpp.lz")
    sym_to_file = {}
    for m in re.finditer(r'(gTrainerFrontPic_\w+)\[\]\s*=\s*INCBIN_U32\("graphics/trainers/front_pics/([\w/]+)\.4bpp',
                         open(gfx_path).read()):
        sym_to_file[m.group(1)] = m.group(2)
    result = {}
    for pic, sym in pic_to_sym.items():
        if sym in sym_to_file:
            result[pic] = sym_to_file[sym]
    return result

def load_trainer_pic_b64(basename):
    from PIL import Image
    path = os.path.join(BASE, 'graphics', 'trainers', 'front_pics', basename + '.png')
    if not os.path.exists(path):
        return ''
    src = Image.open(path)
    # GBA trainer front pics are OBJ sprites: palette index 0 is the transparent
    # backdrop (the FRLG green box etc.). Honor that so the web dex matches in-game.
    if src.mode == 'P':
        src.info['transparency'] = 0
    img = src.convert('RGBA')
    return pdx._img_to_b64(img)

# --- Parse trainer parties ---

# A mon block: a { } group that may hold one level of nested braces (evs/ivs/moves)
MON_BLOCK = re.compile(r'\{((?:[^{}]|\{[^{}]*\})*)\}')

def _parse_evs(raw):
    nums = [int(x) for x in re.findall(r'\d+', raw)]
    if len(nums) != 6 or not any(nums):
        return []
    labels = ['HP', 'Atk', 'Def', 'Spe', 'SpA', 'SpD']
    return [{'stat': labels[i], 'val': nums[i]} for i in range(6) if nums[i]]

def _parse_iv(body):
    m = re.search(r'\.ivs\s*=\s*([^,\n]+)', body)
    if m:
        v = m.group(1).strip()
        if v.startswith('{'):
            nums = re.findall(r'\d+', v)
            return 'IVs ' + '/'.join(nums)
        # macro like BEST_IV_SPREAD
        return v.replace('_', ' ').title()
    m = re.search(r'\.iv\s*=\s*(\d+)', body)
    if m:
        return 'IV ' + m.group(1)
    return ''

def parse_parties(path):
    content = open(path).read()
    parties = {}
    # split into named party arrays
    pat = re.compile(r'static const struct TrainerMon sParty_(\w+)\[\]\s*=\s*\{(.*?)\};', re.DOTALL)
    for m in pat.finditer(content):
        name = m.group(1)
        body = m.group(2)
        mons = []
        for mb in MON_BLOCK.finditer(body):
            b = mb.group(1)
            sp = re.search(r'\.species\s*=\s*SPECIES_(\w+)', b)
            if not sp:
                continue
            lvl = re.search(r'\.lvl\s*=\s*(\d+)', b)
            held = re.search(r'\.heldItem\s*=\s*(ITEM_\w+)', b)
            ability = re.search(r'\.ability\s*=\s*ABILITY_(\w+)', b)
            nature = re.search(r'\.nature\s*=\s*NATURE_(\w+)', b)
            nick = re.search(r'\.nickname\s*=\s*_\("([^"]*)"\)', b)
            shiny = bool(re.search(r'\.shiny\s*=\s*TRUE', b))
            evs = re.search(r'\.evs\s*=\s*\{([^}]*)\}', b)
            moves = [mv for mv in re.findall(r'MOVE_(\w+)', b) if mv != 'NONE']
            mons.append({
                'speciesKey': sp.group(1),
                'level': int(lvl.group(1)) if lvl else 0,
                'heldItem': held.group(1) if held else None,
                'abilitySlot': ability.group(1) if ability else None,
                'nature': nature.group(1).title() if nature else None,
                'nickname': nick.group(1) if nick else None,
                'shiny': shiny,
                'evs': _parse_evs(evs.group(1)) if evs else [],
                'iv': _parse_iv(b),
                'moves': ['MOVE_' + mv for mv in moves],
            })
        parties[name] = mons
    return parties

# --- Parse trainers ---

def parse_trainers(path):
    content = open(path).read()
    # isolate the gTrainers array body
    chunks = re.split(r'\[(TRAINER_\w+)\]\s*=\s*', content)
    trainers = []
    i = 1
    while i < len(chunks) - 1:
        tid = chunks[i]
        body = chunks[i + 1]
        i += 2
        if tid == 'TRAINER_NONE' or tid.endswith('_PLACEHOLDER') or tid.endswith('_SINGLE'):
            continue
        cls = re.search(r'\.trainerClass\s*=\s*TRAINER_CLASS_(\w+)', body)
        if not cls:
            continue
        is_br = tid.startswith('TRAINER_FRONTIER_')
        if cls.group(1) not in NOTABLE_CLASSES and not is_br and tid not in SPECIAL_TRAINER_IDS:
            continue
        name = re.search(r'\.trainerName\s*=\s*_\("([^"]*)"\)', body)
        pic = re.search(r'\.trainerPic\s*=\s*TRAINER_PIC_(\w+)', body)
        party = re.search(r'\.party\s*=\s*TRAINER_MON\((\w+)\)', body)
        double = bool(re.search(r'\.doubleBattle\s*=\s*TRUE', body))
        items = re.findall(r'\.items\s*=\s*\{([^}]*)\}', body)
        item_consts = []
        if items:
            item_consts = [x.strip() for x in items[0].split(',') if 'ITEM_' in x]
        trainers.append({
            'id': tid,
            'classKey': cls.group(1),
            'nameRaw': name.group(1) if name else '',
            'picKey': pic.group(1) if pic else None,
            'partySym': party.group(1).replace('sParty_', '') if party else None,
            'double': double,
            'itemConsts': item_consts,
        })
    return trainers

# --- Parse where each trainer is encountered (map folder of its battle script) ---

def prettify_map(folder):
    s = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', folder)   # CamelCase -> spaced
    s = s.replace('_', ' ')
    s = re.sub(r'(?<=[A-Za-z])(?=\d)', ' ', s)         # Route103 -> Route 103
    return re.sub(r'\s+', ' ', s).strip()

def parse_trainer_locations(maps_dir):
    import glob
    idx = {}
    for f in glob.glob(os.path.join(maps_dir, '*', 'scripts.inc')):
        pretty = prettify_map(os.path.basename(os.path.dirname(f)))
        for m in re.finditer(r'trainerbattle\w*\s+(TRAINER_\w+)', open(f).read()):
            idx.setdefault(m.group(1), [])
            if pretty not in idx[m.group(1)]:
                idx[m.group(1)].append(pretty)
    return idx

# --- Build combined data ---

def species_display(key):
    return pdx.species_display_name(key)

def species_sprite_folder(key):
    return pdx.FORM_FOLDER.get(key) or pdx.species_folder(key)

def build_data():
    print('Parsing class names...')
    class_names = parse_class_names(os.path.join(BASE, 'src/data/text/trainer_class_names.h'))
    print(f'  {len(class_names)} classes')

    print('Parsing item names...')
    item_names = parse_item_names(os.path.join(BASE, 'src/data/items.h'))
    print(f'  {len(item_names)} items')

    print('Parsing trainer pics...')
    pics = parse_trainer_pics(
        os.path.join(BASE, 'src/data/trainer_graphics/front_pic_tables.h'),
        os.path.join(BASE, 'src/data/graphics/trainers.h'),
    )
    print(f'  {len(pics)} pics')

    print('Parsing parties...')
    parties = parse_parties(os.path.join(BASE, 'src/data/trainer_parties.h'))
    print(f'  {len(parties)} parties')

    print('Parsing trainers...')
    raw_trainers = parse_trainers(os.path.join(BASE, 'src/data/trainers.h'))
    print(f'  {len(raw_trainers)} notable trainers')

    print('Parsing trainer locations...')
    locations = parse_trainer_locations(os.path.join(BASE, 'data/maps'))
    print(f'  {len(locations)} trainers placed in maps')

    print('Parsing base stats (for abilities)...')
    base_stats = pdx.parse_base_stats(os.path.join(BASE, 'src/data/pokemon/species_info.h'))

    print('Building move/ability tooltip data...')
    move_info = pdx.build_move_info(
        os.path.join(BASE, 'src/data/battle_moves.h'),
        os.path.join(BASE, 'src/data/text/move_descriptions.h'),
    )
    ability_info = pdx.parse_ability_info(os.path.join(BASE, 'src/data/text/abilities.h'))

    species_sprites = {}   # species key -> {normal, shiny}
    trainer_pics = {}      # pic key -> b64

    def get_species_sprite(key, shiny):
        if key not in species_sprites:
            folder = species_sprite_folder(key)
            species_sprites[key] = {
                'normal': pdx.load_sprite_b64(folder),
                'shiny': pdx.load_sprite_b64(folder, shiny=True),
            }
        return species_sprites[key]

    def resolve_ability(species_key, slot):
        if not slot:
            return None
        abilities = base_stats.get(species_key, {}).get('abilities', [])
        if slot == 'SLOT_1' and len(abilities) >= 1:
            akey = abilities[0]
        elif slot == 'SLOT_2' and len(abilities) >= 2:
            akey = abilities[1]
        elif slot == 'HIDDEN':
            return {'key': None, 'name': 'Hidden Ability'}
        else:
            akey = abilities[0] if abilities else None
        if not akey:
            return None
        return {'key': akey, 'name': ability_info.get(akey, {}).get('name', akey.replace('_', ' ').title())}

    from collections import OrderedDict
    groups = OrderedDict()   # (category, name) -> group dict
    missing_pics = set()
    for t in raw_trainers:
        if t['id'] in SPECIAL_TRAINER_IDS:
            cat, order = SPECIAL_CAT
        elif t['id'] in KANTO_GAUNTLET_IDS:
            cat, order = KANTO_GAUNTLET_CAT
        elif t['id'] in JOHTO_GAUNTLET_IDS:
            cat, order = JOHTO_GAUNTLET_CAT
        elif t['classKey'] in CATEGORY:
            cat, order = CATEGORY[t['classKey']]
        else:
            cat, order = BATTLE_ROYALE
        # trainer pic
        if t['picKey'] and t['picKey'] in pics:
            if t['picKey'] not in trainer_pics:
                trainer_pics[t['picKey']] = load_trainer_pic_b64(pics[t['picKey']])
        elif t['picKey']:
            missing_pics.add(t['picKey'])

        mons = parties.get(t['partySym'], []) if t['partySym'] else []
        # Mr. Mimic mirrors the player's current team, so his stored party is meaningless.
        # Show the single circled "?" (the Gen-3 "unseen Pokemon" sprite) instead.
        if t['id'] == 'TRAINER_FRONTIER_BRYON':
            if 'MR_MIMIC' not in species_sprites:
                _qm = pdx.load_sprite_b64('question_mark/circled')
                species_sprites['MR_MIMIC'] = {'normal': _qm, 'shiny': _qm}
            mons = [{'speciesKey': 'MR_MIMIC', 'shiny': False, 'nickname': None, 'level': '',
                     'heldItem': 'ITEM_NONE', 'abilitySlot': None, 'nature': None,
                     'iv': None, 'evs': [], 'moves': []}]
        party = []
        for mon in mons:
            skey = mon['speciesKey']
            get_species_sprite(skey, mon['shiny'])
            party.append({
                'speciesKey': skey,
                'name': '?' if skey == 'MR_MIMIC' else species_display(skey),
                'nickname': mon['nickname'],
                'shiny': mon['shiny'],
                'level': mon['level'],
                'heldItem': item_display(mon['heldItem'], item_names),
                'ability': resolve_ability(skey, mon['abilitySlot']),
                'nature': mon['nature'],
                'iv': mon['iv'],
                'evs': mon['evs'],
                'moves': [pdx.fmt_move(mv) for mv in mon['moves']],
            })

        bag = [item_display(c, item_names) for c in t['itemConsts']]
        bag = [x for x in bag if x]

        name = t['nameRaw'] or class_names.get(t['classKey'], t['classKey'].title())
        name = name.title() if name.isupper() else name
        className = class_names.get(t['classKey'], t['classKey'].replace('_', ' ').title())

        key = (cat, name)
        if key not in groups:
            groups[key] = {
                'name': name,
                'className': className,
                'category': cat,
                'categoryOrder': order,
                'appear': len(groups),
                'picKey': t['picKey'] if (t['picKey'] in trainer_pics) else None,
                'variants': [],
            }
        groups[key]['variants'].append({
            'id': t['id'].replace('TRAINER_', ''),
            'picKey': t['picKey'] if (t['picKey'] in trainer_pics) else None,
            'double': t['double'],
            'bag': bag,
            'location': locations.get(t['id'], []),
            'party': party,
        })

    if missing_pics:
        print(f'  WARNING: missing pics for {sorted(missing_pics)}')

    trainers = list(groups.values())
    # order + label variants within each group
    total_variants = 0
    for g in trainers:
        order_variants(g['name'], g['variants'])
        total_variants += len(g['variants'])

    def group_rank(g):
        order = GROUP_ORDER.get(g['category'])
        if order and g['name'] in order:
            return (0, order.index(g['name']))
        return (1, g['appear'])

    # sort: category order, then explicit/first-appearance order within category
    trainers.sort(key=lambda g: (g['categoryOrder'], group_rank(g)))
    for g in trainers:
        g.pop('appear', None)
    print(f'  Total: {len(trainers)} trainers ({total_variants} team variants), '
          f'{len(species_sprites)} species sprites, {len(trainer_pics)} trainer pics')
    return trainers, species_sprites, trainer_pics, move_info, ability_info


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trainer Dex — Emerald Legacy</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght,SOFT,WONK@0,9..144,300..900,0..100,0..1;1,9..144,300..900,0..100,0..1&family=Instrument+Sans:ital,wght@0,400..700;1,400..700&family=IBM+Plex+Mono:ital,wght@0,400;0,500;0,700;1,400&display=swap" rel="stylesheet">
<style>
  :root {
    --paper-0: #0a140e; --paper-1: #0e1b14; --paper-2: #13221a;
    --paper-3: #1a2c22; --paper-4: #233829;
    --ink: #ece3d0; --ink-dim: #b5a98f; --ink-mut: #7b705c; --ink-fnt: #534a3b;
    --rule: #2d3d33; --rule-2: #1e2a23;
    --jade: #1a8d5a; --jade-bright: #2eb070; --jade-deep: #0d6b40; --jade-soft: rgba(46,176,112,0.13);
    --ruby: #b3272b; --dusk: #e8a530; --dusk-soft: rgba(232,165,48,0.13);
    --f-serif: 'Fraunces', 'Iowan Old Style', Georgia, serif;
    --f-sans: 'Instrument Sans', system-ui, -apple-system, sans-serif;
    --f-mono: 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
    --grain: url("data:image/svg+xml;utf8,<svg viewBox='0 0 240 240' xmlns='http://www.w3.org/2000/svg'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.1  0 0 0 0 0.1  0 0 0 0 0.1  0 0 0 0.55 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/></svg>");
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--f-sans); background: var(--paper-1); color: var(--ink);
    display: flex; height: 100vh; overflow: hidden;
    -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
    font-size: 14px; letter-spacing: 0.005em;
  }
  body::before {
    content: ""; position: fixed; inset: 0; background-image: var(--grain);
    background-size: 240px 240px; opacity: 0.3; pointer-events: none;
    mix-blend-mode: overlay; z-index: 9999;
  }

  /* Sidebar */
  #sidebar {
    width: 300px; min-width: 260px; background: var(--paper-0);
    border-right: 1px solid var(--rule); display: flex; flex-direction: column;
    height: 100vh; min-height: 0;
  }
  #sidebar-header { padding: 22px 20px 14px; border-bottom: 1px solid var(--rule); }
  #sidebar-header h1 {
    font-family: var(--f-serif); font-variation-settings: "opsz" 48, "SOFT" 40, "WONK" 1;
    font-style: italic; font-weight: 400; font-size: 22px; color: var(--ink);
    letter-spacing: -0.01em; line-height: 1; margin-bottom: 4px;
  }
  #sidebar-header .volume {
    display: block; font-family: var(--f-mono); font-size: 9px; color: var(--jade-bright);
    letter-spacing: 0.3em; text-transform: uppercase; margin-bottom: 14px;
  }
  #search {
    width: 100%; padding: 8px 2px 8px 20px; border: 0; border-bottom: 1px solid var(--rule);
    background: transparent url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%237b705c' stroke-width='2' stroke-linecap='round'><circle cx='11' cy='11' r='7'/><line x1='21' y1='21' x2='16.65' y2='16.65'/></svg>") no-repeat left center;
    color: var(--ink); font-family: var(--f-serif); font-style: italic; font-size: 15px;
    outline: none; transition: border-color 0.2s;
  }
  #search::placeholder { color: var(--ink-mut); font-style: italic; }
  #search:focus { border-color: var(--jade-bright); }
  #trainer-count {
    font-family: var(--f-mono); font-size: 9px; color: var(--ink-mut); padding: 10px 20px;
    letter-spacing: 0.24em; text-transform: uppercase; border-bottom: 1px solid var(--rule);
    display: flex; justify-content: space-between; align-items: center;
  }
  #trainer-count::before { content: "Roster"; color: var(--jade-bright); }
  #trainer-list { overflow-y: auto; flex: 1; padding: 8px 8px 24px; display: flex; flex-direction: column; }
  #trainer-list::-webkit-scrollbar { width: 10px; }
  #trainer-list::-webkit-scrollbar-track { background: transparent; }
  #trainer-list::-webkit-scrollbar-thumb { background: var(--paper-3); border: 3px solid var(--paper-0); border-radius: 10px; }

  .cat-header {
    font-family: var(--f-mono); font-size: 9px; color: var(--jade-bright);
    letter-spacing: 0.28em; text-transform: uppercase; padding: 16px 12px 8px;
    display: flex; align-items: center; gap: 10px;
  }
  .cat-header::after { content: ""; flex: 1; height: 1px; background: var(--rule); }

  .tr-item {
    display: grid; grid-template-columns: 40px 1fr; align-items: center; gap: 10px;
    padding: 6px 12px; cursor: pointer; border-left: 2px solid transparent;
    transition: background 0.15s, border-color 0.15s;
  }
  .tr-item:hover { background: var(--paper-1); }
  .tr-item.active { background: var(--jade-soft); border-left-color: var(--jade-bright); }
  .tr-item img { width: 40px; height: 40px; image-rendering: pixelated; justify-self: center; }
  .tr-item .tr-name {
    font-family: var(--f-serif); font-style: italic; font-size: 15px; color: var(--ink-dim);
    line-height: 1.15; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0;
  }
  .tr-item .tr-class {
    font-family: var(--f-mono); font-size: 8px; color: var(--ink-mut);
    letter-spacing: 0.16em; text-transform: uppercase;
  }
  .tr-item:hover .tr-name { color: var(--ink); }
  .tr-item.active .tr-name { color: var(--ink); font-style: normal; font-weight: 500; }

  /* Main */
  #main {
    flex: 1; min-height: 0; overflow-y: auto;
    background: radial-gradient(1000px 500px at 100% -100px, rgba(46,176,112,0.05), transparent 55%), var(--paper-1);
    padding: 48px 56px 64px;
  }
  #main::-webkit-scrollbar { width: 12px; }
  #main::-webkit-scrollbar-track { background: transparent; }
  #main::-webkit-scrollbar-thumb { background: var(--paper-3); border: 3px solid var(--paper-1); border-radius: 12px; }

  #welcome {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    height: 100%; text-align: center; gap: 12px; max-width: 480px; margin: 0 auto;
  }
  #welcome h2 {
    font-family: var(--f-serif); font-variation-settings: "opsz" 144, "SOFT" 50, "WONK" 1;
    font-weight: 400; font-style: italic; font-size: 54px; color: var(--ink);
    letter-spacing: -0.03em; line-height: 0.95;
  }
  #welcome h2 em { font-style: normal; color: var(--jade-bright); }
  #welcome p {
    font-family: var(--f-mono); font-size: 10px; color: var(--ink-mut); letter-spacing: 0.3em;
    text-transform: uppercase; padding-top: 8px; border-top: 1px solid var(--rule); margin-top: 8px;
  }

  #trainer-detail { display: none; max-width: 920px; margin: 0 auto; }

  .spread { display: grid; grid-template-columns: 220px 1fr; gap: 40px; align-items: start; margin-bottom: 8px; }
  .sprite-col { display: flex; flex-direction: column; align-items: center; gap: 12px; }
  .plate {
    position: relative; padding: 18px;
    background: radial-gradient(circle at 30% 25%, rgba(46,176,112,0.10), transparent 60%), var(--paper-2);
    border: 1px solid var(--rule);
  }
  .plate::before {
    content: ""; position: absolute; inset: 0;
    background-image: radial-gradient(rgba(236,227,208,0.08) 1px, transparent 1.4px);
    background-size: 6px 6px; pointer-events: none; mix-blend-mode: overlay;
  }
  .trainer-sprite { image-rendering: pixelated; width: 168px; height: 168px; display: block; }
  .plate-tag {
    font-family: var(--f-mono); font-size: 9px; color: var(--jade-bright);
    border: 1px solid var(--jade-bright); padding: 4px 10px; letter-spacing: 0.24em;
    text-transform: uppercase; background: var(--paper-1); margin-top: -8px; position: relative; z-index: 2;
  }

  .detail-info { min-width: 0; padding-top: 4px; }
  .tr-class-line {
    font-family: var(--f-mono); font-size: 10px; color: var(--jade-bright);
    letter-spacing: 0.26em; text-transform: uppercase; margin-bottom: 10px;
    display: flex; align-items: center; gap: 10px;
  }
  .tr-class-line::after { content: ""; flex: 1; height: 1px; background: var(--rule); }
  .detail-info h2 {
    font-family: var(--f-serif); font-variation-settings: "opsz" 144, "SOFT" 60, "WONK" 1;
    font-weight: 400; font-style: italic; font-size: 60px; line-height: 0.92; color: var(--ink);
    letter-spacing: -0.03em; margin-bottom: 12px;
  }
  .badges { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
  .badge {
    font-family: var(--f-mono); font-size: 9px; padding: 4px 10px; letter-spacing: 0.18em;
    text-transform: uppercase; border: 1px solid var(--rule); color: var(--ink-dim);
  }
  .badge.double { border-color: var(--dusk); color: var(--dusk); }
  .badge.bag { border-color: var(--jade-bright); color: var(--jade-bright); }

  .bag-row { margin-top: 12px; }
  .variant-groups { margin: 14px 0 4px; }
  .variant-group-label {
    font-family: var(--f-mono); font-size: 9px; color: var(--ink-mut); letter-spacing: 0.22em;
    text-transform: uppercase; margin: 12px 0 6px;
  }
  .variant-group-label:first-child { margin-top: 0; }
  .variant-switcher { display: flex; flex-wrap: wrap; gap: 6px; margin: 14px 0 4px; }
  .variant-groups .variant-switcher { margin: 0 0 4px; }

  .location-list { display: flex; flex-wrap: wrap; gap: 8px; }
  .location-tag {
    font-family: var(--f-sans); font-size: 12px; color: var(--ink-dim); padding: 6px 12px;
    border: 1px solid var(--rule); background: var(--paper-2); letter-spacing: 0.01em;
  }
  .variant-btn {
    font-family: var(--f-mono); font-size: 9px; padding: 5px 11px; letter-spacing: 0.14em;
    text-transform: uppercase; border: 1px solid var(--rule); background: transparent;
    color: var(--ink-dim); cursor: pointer; transition: all 0.2s;
  }
  .variant-btn:hover { border-color: var(--jade-bright); color: var(--ink); }
  .variant-btn.active { background: var(--jade-soft); border-color: var(--jade-bright); color: var(--jade-bright); }

  .section-title {
    font-family: var(--f-mono); font-size: 10px; color: var(--jade-bright); letter-spacing: 0.3em;
    text-transform: uppercase; margin-bottom: 14px; margin-top: 36px; display: flex;
    align-items: center; gap: 12px; font-weight: 500;
  }
  .section-title::before { content: "§"; color: var(--ink-mut); font-weight: 400; font-size: 13px; }
  .section-title::after { content: ""; flex: 1; height: 1px; background: var(--rule); }

  /* Party grid */
  .party-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(248px, 1fr)); gap: 14px; }
  .mon-card { border: 1px solid var(--rule); background: var(--paper-2); padding: 14px; position: relative; }
  .mon-head { display: grid; grid-template-columns: 56px 1fr; gap: 10px; align-items: center; margin-bottom: 10px; }
  .mon-head img { width: 56px; height: 56px; image-rendering: pixelated; justify-self: center; }
  .mon-name { font-family: var(--f-serif); font-style: italic; font-size: 18px; color: var(--ink); line-height: 1.05; }
  .mon-nick { font-family: var(--f-mono); font-size: 9px; color: var(--ink-mut); letter-spacing: 0.1em; }
  .mon-lvl { font-family: var(--f-mono); font-size: 10px; color: var(--jade-bright); letter-spacing: 0.12em; }
  .mon-lvl .star { color: var(--dusk); margin-left: 4px; }
  .mon-meta { font-family: var(--f-mono); font-size: 10px; color: var(--ink-dim); display: flex; flex-direction: column; gap: 4px; margin-bottom: 10px; }
  .mon-meta .k { color: var(--ink-mut); letter-spacing: 0.12em; text-transform: uppercase; font-size: 8px; }
  .mon-meta .ability { color: var(--ink); border-bottom: 1px dotted var(--ink-mut); cursor: help; }
  .mon-moves { display: flex; flex-wrap: wrap; gap: 5px; }
  .pill {
    font-family: var(--f-mono); font-size: 10px; padding: 3px 8px; border: 1px solid var(--rule);
    color: var(--ink-dim); background: var(--paper-1); cursor: help;
  }
  .pill:hover { border-color: var(--jade-bright); color: var(--ink); }
  .evs { font-family: var(--f-mono); font-size: 9px; color: var(--ink-mut); margin-top: 8px; letter-spacing: 0.08em; }
  .empty-msg { font-family: var(--f-serif); font-style: italic; color: var(--ink-mut); }

  /* Tooltips */
  #move-tooltip, #ability-tooltip {
    position: fixed; display: none; z-index: 10000; max-width: 300px; pointer-events: none;
    background: var(--paper-0); border: 1px solid var(--jade-bright); padding: 12px 14px;
    box-shadow: 0 12px 30px -10px rgba(0,0,0,0.8);
  }
  .tt-name, .at-name { font-family: var(--f-serif); font-style: italic; font-size: 18px; color: var(--ink); margin-bottom: 6px; }
  .tt-type { display: inline-block; font-family: var(--f-mono); font-size: 9px; color: #fff; padding: 2px 8px; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 8px; }
  .tt-stats { display: flex; gap: 14px; margin-bottom: 8px; }
  .tt-stat { display: flex; flex-direction: column; }
  .tt-stat-label { font-family: var(--f-mono); font-size: 8px; color: var(--ink-mut); letter-spacing: 0.16em; text-transform: uppercase; }
  .tt-stat-val { font-family: var(--f-mono); font-size: 13px; color: var(--ink); }
  .tt-desc, .at-desc { font-family: var(--f-serif); font-size: 13px; color: var(--ink-dim); line-height: 1.5; font-style: italic; }

  #btn-back {
    display: none; align-items: center; gap: 8px; margin-bottom: 20px; padding: 7px 14px;
    border: 1px solid var(--rule); background: transparent; color: var(--jade-bright);
    font-family: var(--f-mono); font-size: 10px; font-weight: 500; cursor: pointer;
    letter-spacing: 0.22em; text-transform: uppercase;
  }

  @media (max-width: 700px) {
    body { flex-direction: column; overflow: auto; height: auto; min-height: 100dvh; }
    #sidebar { width: 100%; min-width: unset; height: auto; max-height: 100dvh; border-right: none; border-bottom: 1px solid var(--rule); }
    #sidebar.hidden { display: none; }
    #main { width: 100%; overflow-y: visible; padding: 24px 18px 40px; }
    #main.hidden { display: none; }
    #btn-back { display: inline-flex; }
    .spread { grid-template-columns: 1fr; gap: 24px; text-align: center; }
    .sprite-col { justify-self: center; }
    .detail-info h2 { font-size: 42px; }
  }
</style>
</head>
<body>

<div id="sidebar">
  <div id="sidebar-header">
    <h1>Trainer Dex</h1>
    <span class="volume">Vol. II · Notable Trainers</span>
    <input type="text" id="search" placeholder="Search by name, class, Pokémon…" oninput="filterList(this.value)">
  </div>
  <div id="trainer-count"></div>
  <div id="trainer-list"></div>
</div>

<div id="move-tooltip"></div>
<div id="ability-tooltip"></div>

<div id="main">
  <div id="welcome">
    <h2>The <em>Trainer</em><br>Dex</h2>
    <p>Select a trainer from the roster</p>
  </div>
  <div id="trainer-detail"></div>
</div>

<script>
const DATA = TRAINER_DATA_PLACEHOLDER;
const SPRITES = SPECIES_SPRITES_PLACEHOLDER;
const PICS = TRAINER_PICS_PLACEHOLDER;
const MOVES = MOVE_INFO_PLACEHOLDER;
const ABILITIES = ABILITY_INFO_PLACEHOLDER;

const TYPE_COLORS = {
  NORMAL:'#9099A1',FIRE:'#E8554E',WATER:'#5598D8',ELECTRIC:'#F0C13A',
  GRASS:'#5DBE62',ICE:'#76C6D0',FIGHTING:'#CE4068',POISON:'#A55FA5',
  GROUND:'#D97845',FLYING:'#8FA8D8',PSYCHIC:'#E8547A',BUG:'#90B820',
  ROCK:'#C0AA48',GHOST:'#5060A8',DRAGON:'#6048E8',DARK:'#5060A8',
  STEEL:'#9898B8',MYSTERY:'#68A090',
};

function spriteFor(key, shiny) {
  const s = SPRITES[key];
  if (!s) return '';
  return shiny ? (s.shiny || s.normal) : s.normal;
}

const tt = document.getElementById('move-tooltip');
const abilityTt = document.getElementById('ability-tooltip');
let ttTimeout, abilityTtTimeout;

function positionTip(el, cx, cy) {
  const margin = 14, w = el.offsetWidth || 300, h = el.offsetHeight || 160;
  const vw = window.innerWidth, vh = window.innerHeight;
  let x = cx + margin, y = cy + margin;
  if (x + w > vw - margin) x = cx - w - margin;
  if (x < margin) x = margin;
  if (y + h > vh - margin) y = cy - h - margin;
  if (y < margin) y = margin;
  el.style.left = x + 'px'; el.style.top = y + 'px';
}
function showTooltip(e, moveName) {
  const info = MOVES[moveName];
  if (!info) return;
  const color = TYPE_COLORS[info.type] || '#888';
  const pwStr = info.power > 0 ? info.power : '—';
  const accStr = info.accuracy > 0 ? info.accuracy + '%' : '—';
  tt.innerHTML = `<div class="tt-name">${moveName}</div>
    <div class="tt-type" style="background:${color}">${info.type}</div>
    <div class="tt-stats">
      <div class="tt-stat"><span class="tt-stat-label">Power</span><span class="tt-stat-val">${pwStr}</span></div>
      <div class="tt-stat"><span class="tt-stat-label">Acc.</span><span class="tt-stat-val">${accStr}</span></div>
      <div class="tt-stat"><span class="tt-stat-label">PP</span><span class="tt-stat-val">${info.pp}</span></div>
    </div>${info.desc ? `<div class="tt-desc">${info.desc}</div>` : ''}`;
  tt.style.display = 'block';
  positionTip(tt, e.clientX, e.clientY);
}
function showAbilityTooltip(e, key) {
  const info = ABILITIES[key];
  if (!info) return;
  abilityTt.innerHTML = `<div class="at-name">${info.name}</div>${info.desc ? `<div class="at-desc">${info.desc}</div>` : ''}`;
  abilityTt.style.display = 'block';
  positionTip(abilityTt, e.clientX, e.clientY);
}
document.addEventListener('mousemove', e => {
  if (tt.style.display === 'block') positionTip(tt, e.clientX, e.clientY);
  if (abilityTt.style.display === 'block') positionTip(abilityTt, e.clientX, e.clientY);
});
document.addEventListener('mouseover', e => {
  const el = e.target.closest('[data-move]');
  if (el) { clearTimeout(ttTimeout); showTooltip(e, el.dataset.move); }
  const ael = e.target.closest('[data-ability]');
  if (ael && ael.dataset.ability) { clearTimeout(abilityTtTimeout); showAbilityTooltip(e, ael.dataset.ability); }
});
document.addEventListener('mouseout', e => {
  if (e.target.closest('[data-move]')) ttTimeout = setTimeout(() => { tt.style.display = 'none'; }, 80);
  if (e.target.closest('[data-ability]')) abilityTtTimeout = setTimeout(() => { abilityTt.style.display = 'none'; }, 80);
});

let currentId = null;
const isMobile = () => window.innerWidth <= 700;
function goBack() {
  document.getElementById('sidebar').classList.remove('hidden');
  document.getElementById('main').classList.add('hidden');
}

function renderList(items) {
  const list = document.getElementById('trainer-list');
  const count = document.getElementById('trainer-count');
  list.innerHTML = '';
  count.innerHTML = `<span>${items.length} entries</span>`;
  if (items.length === 0) { list.innerHTML = '<div class="empty-msg" style="padding:16px 12px">No trainers match.</div>'; return; }
  let lastCat = null;
  items.forEach((t) => {
    if (t.category !== lastCat) {
      lastCat = t.category;
      const h = document.createElement('div');
      h.className = 'cat-header';
      h.textContent = t.category;
      list.appendChild(h);
    }
    const div = document.createElement('div');
    div.className = 'tr-item' + (t._idx === currentId ? ' active' : '');
    div.dataset.idx = t._idx;
    const pic = t.picKey ? PICS[t.picKey] : '';
    div.innerHTML = `${pic ? `<img src="${pic}" alt="${t.name}">` : '<div style="width:40px;height:40px"></div>'}
      <span><span class="tr-name">${t.name}</span><br><span class="tr-class">${t.className}</span></span>`;
    div.onclick = () => selectTrainer(t._idx);
    list.appendChild(div);
  });
}

function filterList(query) {
  const q = query.toLowerCase().trim();
  const filtered = indexed.filter(t => {
    if (!q) return true;
    if (t.name.toLowerCase().includes(q)) return true;
    if (t.className.toLowerCase().includes(q)) return true;
    return t.variants.some(v => v.party.some(m => m.name.toLowerCase().includes(q)));
  });
  renderList(filtered);
}

let currentVariant = 0;

function selectTrainer(idx) {
  currentId = idx;
  currentVariant = 0;
  document.querySelectorAll('.tr-item').forEach(el => el.classList.toggle('active', parseInt(el.dataset.idx) === idx));
  document.getElementById('welcome').style.display = 'none';
  document.getElementById('trainer-detail').style.display = 'block';
  if (isMobile()) {
    document.getElementById('sidebar').classList.add('hidden');
    document.getElementById('main').classList.remove('hidden');
  }
  renderDetail(DATA[idx], 0);
  document.getElementById('main').scrollTop = 0;
}

function switchVariant(vIdx) {
  currentVariant = vIdx;
  renderDetail(DATA[currentId], vIdx);
}

function renderDetail(t, vIdx) {
  vIdx = vIdx || 0;
  const v = t.variants[vIdx] || t.variants[0];
  const pic = (v.picKey || t.picKey) ? PICS[v.picKey || t.picKey] : '';
  const badges = [];
  if (v.double) badges.push('<span class="badge double">Double Battle</span>');
  const bagRow = v.bag.length
    ? `<div class="badges bag-row">${v.bag.map(it => `<span class="badge bag">${it}</span>`).join('')}</div>`
    : '';

  const btn = (vv, i) => `<button class="variant-btn${i === vIdx ? ' active' : ''}" onclick="switchVariant(${i})">${vv.label}</button>`;
  let variantSwitcher = '';
  if (t.variants.length > 1) {
    if (t.variants.some(vv => vv.group)) {
      // grouped by starter: heading + its own row of location buttons
      let html = '', lastGroup = null;
      t.variants.forEach((vv, i) => {
        if (vv.group !== lastGroup) {
          if (lastGroup !== null) html += '</div>';
          lastGroup = vv.group;
          html += `<div class="variant-group-label">${vv.group}</div><div class="variant-switcher">`;
        }
        html += btn(vv, i);
      });
      if (lastGroup !== null) html += '</div>';
      variantSwitcher = `<div class="variant-groups">${html}</div>`;
    } else {
      variantSwitcher = `<div class="variant-switcher">${t.variants.map(btn).join('')}</div>`;
    }
  }

  const locRow = v.location && v.location.length
    ? `<div class="section-title">Encountered</div>
       <div class="location-list">${v.location.map(l => `<span class="location-tag">${l}</span>`).join('')}</div>`
    : '';

  const cards = v.party.length === 0
    ? '<span class="empty-msg">No party data.</span>'
    : v.party.map(m => {
        const sprite = spriteFor(m.speciesKey, m.shiny);
        const meta = [];
        if (m.ability) meta.push(`<div><span class="k">Ability</span> <span class="ability"${m.ability.key ? ` data-ability="${m.ability.key}"` : ''}>${m.ability.name}</span></div>`);
        if (m.nature) meta.push(`<div><span class="k">Nature</span> ${m.nature}</div>`);
        if (m.heldItem) meta.push(`<div><span class="k">Held</span> ${m.heldItem}</div>`);
        const moves = m.moves.length
          ? `<div class="mon-moves">${m.moves.map(mv => `<span class="pill" data-move="${mv}">${mv}</span>`).join('')}</div>`
          : '<span class="empty-msg">No set moves</span>';
        const evs = m.evs.length ? `<div class="evs">EVs ${m.evs.map(e => e.val + ' ' + e.stat).join(' · ')}</div>` : '';
        return `<div class="mon-card">
          <div class="mon-head">
            ${sprite ? `<img src="${sprite}" alt="${m.name}">` : '<div style="width:56px;height:56px"></div>'}
            <div>
              <div class="mon-name">${m.name}</div>
              ${m.nickname ? `<div class="mon-nick">"${m.nickname}"</div>` : ''}
              <div class="mon-lvl">Lv ${m.level}${m.shiny ? '<span class="star">★</span>' : ''}</div>
            </div>
          </div>
          <div class="mon-meta">${meta.join('')}</div>
          ${moves}${evs}
        </div>`;
      }).join('');

  document.getElementById('trainer-detail').innerHTML = `
    <button id="btn-back" onclick="goBack()">← Return to Roster</button>
    <div class="spread">
      <div class="sprite-col">
        <div class="plate">
          ${pic ? `<img class="trainer-sprite" src="${pic}" alt="${t.name}">` : '<div class="trainer-sprite"></div>'}
        </div>
        <span class="plate-tag">${t.category}</span>
      </div>
      <div class="detail-info">
        <div class="tr-class-line">${t.className}</div>
        <h2>${t.name}</h2>
        <div class="badges">${badges.join('')}</div>
        ${variantSwitcher}
        ${bagRow}
      </div>
    </div>
    ${locRow}
    <div class="section-title">Team · ${v.party.length} Pokémon</div>
    <div class="party-grid">${cards}</div>
  `;
}

const indexed = DATA.map((t, i) => { t._idx = i; return t; });
renderList(indexed);
</script>
</body>
</html>
'''

def generate():
    trainers, species_sprites, trainer_pics, move_info, ability_info = build_data()

    def dump(o):
        return json.dumps(o, ensure_ascii=False, separators=(',', ':'))

    html = HTML_TEMPLATE
    html = html.replace('TRAINER_DATA_PLACEHOLDER', dump(trainers))
    html = html.replace('SPECIES_SPRITES_PLACEHOLDER', dump(species_sprites))
    html = html.replace('TRAINER_PICS_PLACEHOLDER', dump(trainer_pics))
    html = html.replace('MOVE_INFO_PLACEHOLDER', dump(move_info))
    html = html.replace('ABILITY_INFO_PLACEHOLDER', dump(ability_info))

    docs_dir = os.path.join(BASE, 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    out_path = os.path.join(docs_dir, 'trainerdex.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f'\nGenerated: {out_path} ({size_mb:.1f} MB)')

if __name__ == '__main__':
    generate()
