#!/usr/bin/env python3
"""Generates items.html — the Bag: every item and everywhere to get it.

Sources (all parsed from the decomp):
  found   data/scripts/item_ball_scripts.inc (finditem) joined to data/maps/*/map.json object_events
  hidden  data/maps/*/map.json bg_events type hidden_item
  gift    giveitem / additem / setvar VAR_*, ITEM_X in data/maps/*/scripts.inc + data/scripts/*.inc
  shop    pokemart lists (.2byte ITEM_X ... ITEM_NONE), condition from the list label
  prize   Game Corner, Battle Frontier exchange, Trainer Hill, Battle Arena / Pyramid, Lottery
  wild    src/data/pokemon/species_info.h itemCommon (50%) / itemRare (5%)
  steal   thief_data.collect_entries (trainer held items)
  berry   data/scripts/new_game.inc setberrytree + map.json berry tree ids
  pickup  src/battle_script_commands.c sPickupItems / sRarePickupItems
"""

import os
import re
from functools import lru_cache
import io
import json
import glob
import contextlib

import generate_pokedex as pdx
import generate_trainerdex as tdx
import site_shared
from site_shared import BASE, load_item_icon_b64

POCKETS = {
    'POCKET_ITEMS': 'Items', 'POCKET_POKE_BALLS': 'Poké Balls', 'POCKET_TM_HM': 'TMs & HMs',
    'POCKET_BERRIES': 'Berries', 'POCKET_KEY_ITEMS': 'Key Items',
}


def read(path):
    return open(os.path.join(BASE, path), encoding='utf-8').read()


def map_name(folder):
    return tdx.prettify_map(folder)


def humanize_label(label):
    """DewfordTown_Gym_EventScript_GiveRematchReward -> 'Give rematch reward'"""
    tail = label.split('EventScript_')[-1]
    tail = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', tail)
    words = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', tail).replace('_', ' ').split()
    return ' '.join(words).capitalize() if words else ''


def parse_items():
    text = read('src/data/items.h')
    descs = {m.group(1): m.group(2) for m in re.finditer(
        r'static const u8 (s\w+Desc)\[\]\s*=\s*_\(\s*((?:"[^"]*"\s*)+)\)', read('src/data/text/item_descriptions.h'))}
    names = tdx.parse_item_names(os.path.join(BASE, 'src/data/items.h'))
    items = {}
    for m in re.finditer(r'\[(ITEM_\w+)\]\s*=\s*\{(.*?)\n    \},', text, re.S):
        key, body = m.group(1), m.group(2)
        name = names.get(key[5:])
        if key == 'ITEM_NONE' or not name or '?' in name:
            continue
        price = re.search(r'\.price\s*=\s*(\d+)', body)
        pocket = re.search(r'\.pocket\s*=\s*(POCKET_\w+)', body)
        dsym = re.search(r'\.description\s*=\s*(s\w+Desc)', body)
        desc = ''
        if dsym and dsym.group(1) in descs:
            desc = ' '.join(re.findall(r'"([^"]*)"', descs[dsym.group(1)]))
            desc = desc.replace('\\n', ' ').replace('{PKMN}', 'Pokémon').replace('POKéMON', 'Pokémon')
            desc = re.sub(r'\s+', ' ', desc).strip()
        items[key] = dict(key=key, name=name, price=int(price.group(1)) if price else 0,
                          pocket=POCKETS.get(pocket.group(1) if pocket else '', 'Items'), desc=desc,
                          src={})
    return items


def add(items, key, kind, entry):
    if key not in items:
        return
    lst = items[key]['src'].setdefault(kind, [])
    if entry not in lst:
        lst.append(entry)


def maps():
    for f in sorted(glob.glob(os.path.join(BASE, 'data/maps/*/map.json'))):
        yield os.path.basename(os.path.dirname(f)), json.load(open(f))


def collect(items):
    # --- item balls + hidden items + berry trees ---
    ball = dict(re.findall(r'^(\w+)::\s*\n\s*finditem\s+(ITEM_\w+)', read('data/scripts/item_ball_scripts.inc'), re.M))
    trees = {}
    for m in re.finditer(r'setberrytree\s+(BERRY_TREE_\w+),\s*ITEM_TO_BERRY\((ITEM_\w+)\)', read('data/scripts/new_game.inc')):
        trees[m.group(1)] = m.group(2)
    for folder, mj in maps():
        where = map_name(folder)
        for ev in mj.get('object_events', []):
            scr = ev.get('script', '')
            if scr in ball:
                add(items, ball[scr], 'found', where)
            if scr == 'BerryTreeScript' and ev.get('trainer_sight_or_berry_tree_id') in trees:
                add(items, trees[ev['trainer_sight_or_berry_tree_id']], 'berry', where)
        for bg in mj.get('bg_events', []):
            if bg.get('type') == 'hidden_item':
                add(items, bg.get('item'), 'hidden', where)

    # --- script gifts + marts ---
    files = [(os.path.basename(os.path.dirname(f)), f) for f in glob.glob(os.path.join(BASE, 'data/maps/*/scripts.inc'))]
    files += [(os.path.splitext(os.path.basename(f))[0], f) for f in glob.glob(os.path.join(BASE, 'data/scripts/*.inc'))
              if not f.endswith('item_ball_scripts.inc')]
    skip_setvar = ('BattleFrontier_ExchangeServiceCorner', 'MauvilleCity_GameCorner')
    for folder, f in sorted(files):
        text = open(f, encoding='utf-8').read()
        where = map_name(folder) if '/maps/' in f else humanize_label(folder.replace('_', ' ').title().replace(' ', ''))
        label = ''
        mart = None
        for line in text.splitlines():
            lm = re.match(r'^(\w+)::?\s*$', line)
            if lm:
                label = lm.group(1)
                mart = label if re.search(r'(Pokemart|Mart|Shop)\w*$', label) or 'Pokemart' in label else None
                continue
            gm = re.match(r'^\s*(giveitem|additem)\s+(ITEM_\w+)(?:\s*,\s*(\d+))?', line)
            if gm:
                what = humanize_label(label)
                add(items, gm.group(2), 'gift', dict(where=where, what=what, qty=int(gm.group(3) or 1)))
                continue
            sm = re.match(r'^\s*setvar\s+VAR_\w+,\s*(ITEM_\w+)', line)
            if sm and folder not in skip_setvar:
                add(items, sm.group(1), 'gift', dict(where=where, what=humanize_label(label), qty=1))
                continue
            im = re.match(r'^\s*\.2byte\s+(ITEM_\w+)', line)
            if im and mart and im.group(1) != 'ITEM_NONE':
                add(items, im.group(1), 'shop', dict(where=where, cond=mart_condition(mart)))

    # --- prizes ---
    gc = read('data/maps/MauvilleCity_GameCorner/scripts.inc')
    for m in re.finditer(r'\.set\s+(TM_\w+)_COINS,\s*(\d+)', gc):
        add(items, 'ITEM_' + m.group(1), 'prize', dict(where='Mauville Game Corner', cost=f'{int(m.group(2)):,} coins'))
    add(items, 'ITEM_UP_GRADE', 'prize', dict(where='Mauville Game Corner', cost='9,999 coins (after Porygon and Wattson’s Team 3)'))
    ex = read('data/maps/BattleFrontier_ExchangeServiceCorner/scripts.inc')
    for m in re.finditer(r'setvar\s+VAR_0x8008,\s*(\d+)\s*\n\s*setvar\s+VAR_0x8009,\s*(ITEM_\w+)', ex):
        add(items, m.group(2), 'prize', dict(where='Battle Frontier Exchange Service Corner', cost=f'{m.group(1)} BP'))
    import generate_guide as gg
    for mode, lst in gg.HILL_PRIZES.items():
        for ti, key in enumerate(lst):
            add(items, key, 'prize', dict(where=f'Trainer Hill ({mode})', cost=f'clear time {gg.HILL_TIMES[ti].lower()}'))
    def c_array(path, name):
        m = re.search(name + r'\[\]\s*=\s*\{([^}]*)\}', read(path))
        return re.findall(r'ITEM_\w+', m.group(1)) if m else []
    for key in c_array('src/battle_arena.c', 'sShortStreakPrizeItems'):
        add(items, key, 'prize', dict(where='Battle Arena', cost='random prize for a short win streak'))
    for key in c_array('src/battle_arena.c', 'sLongStreakPrizeItems'):
        add(items, key, 'prize', dict(where='Battle Arena', cost='random prize for a long win streak'))
    for key in c_array('src/battle_pyramid.c', 'sShortStreakRewardItems'):
        add(items, key, 'prize', dict(where='Battle Pyramid', cost='random prize for a short win streak'))
    for key in c_array('src/battle_pyramid.c', 'sLongStreakRewardItems'):
        add(items, key, 'prize', dict(where='Battle Pyramid', cost='random prize for a long win streak'))
    for i, key in enumerate(c_array('src/lottery_corner.c', 'sLotteryPrizes')):
        add(items, key, 'prize', dict(where='Lilycove Dept. Store lottery', cost=f'{2 + i} matching ID digits' if i < 3 else 'all 5 ID digits match'))
    for key, cost in [('ITEM_LANSAT_BERRY', 'all 7 Silver Symbols'), ('ITEM_STARF_BERRY', 'all 7 Gold Symbols')]:
        add(items, key, 'prize', dict(where="Scott's House (Battle Frontier)", cost=cost))

    # --- wild held items ---
    si = read('src/data/pokemon/species_info.h')
    for m in re.finditer(r'\[SPECIES_(\w+)\]\s*=\s*\{(.*?)\n    \},', si, re.S):
        sp, body = m.group(1), m.group(2)
        common = re.search(r'\.itemCommon\s*=\s*(ITEM_\w+)', body)
        rare = re.search(r'\.itemRare\s*=\s*(ITEM_\w+)', body)
        common = common.group(1) if common else 'ITEM_NONE'
        rare = rare.group(1) if rare else 'ITEM_NONE'
        if common != 'ITEM_NONE' and common == rare:
            add(items, common, 'wild', dict(sp=sp, name=pdx.species_display_name(sp), pct='100%'))
            continue
        if common != 'ITEM_NONE':
            add(items, common, 'wild', dict(sp=sp, name=pdx.species_display_name(sp), pct='50%'))
        if rare != 'ITEM_NONE':
            add(items, rare, 'wild', dict(sp=sp, name=pdx.species_display_name(sp), pct='5%'))

    # --- pickup ---
    bsc = read('src/battle_script_commands.c')
    common = re.findall(r'ITEM_\w+', re.search(r'sPickupItems\[\]\s*=\s*\{([^}]*)\}', bsc).group(1))
    rare = re.findall(r'ITEM_\w+', re.search(r'sRarePickupItems\[\]\s*=\s*\{([^}]*)\}', bsc).group(1))
    probs = [int(x) for x in re.findall(r'\d+', re.search(r'sPickupProbabilities\[\]\s*=\s*\{([^}]*)\}', bsc).group(1))]
    chances = [probs[0]] + [probs[i] - probs[i - 1] for i in range(1, len(probs))]
    for band in range(10):
        lv = f'Lv {band * 10 + 1}–{band * 10 + 10}'
        for j, pct in enumerate(chances):
            add(items, common[band + j], 'pickup', dict(lv=lv, pct=pct))
        add(items, rare[band], 'pickup', dict(lv=lv, pct=1))
        add(items, rare[band + 1], 'pickup', dict(lv=lv, pct=1))

    # --- steal from trainers ---
    import thief_data
    with contextlib.redirect_stdout(io.StringIO()):
        tdex = tdx.build_data()[0]
    entries, item_const = thief_data.collect_entries(tdex)
    for e in entries:
        for name, n in e['counts'].items():
            add(items, item_const[name], 'steal', dict(label=e['label'], tv=e['tv'], locs=', '.join(e['locs']), n=n,
                                                       repeat=bool(e['repeat']), br=e['br']))


def mart_condition(label):
    rules = [('PostGame', 'after the Hall of Fame'), ('MainGame', 'before the Hall of Fame'),
             ('Expanded', 'expanded stock'), ('Basic', 'starting stock'), ('Incense', 'after becoming Champion'),
             ('PrettyPetalFlowerShop_Pokemart_Berries2', 'after beating Norman'),
             ('PrettyPetalFlowerShop_Pokemart_Berries1', 'before beating Norman')]
    for suffix, text in rules:
        if suffix in label:
            return text
    return ''


def dedupe_shops(items):
    """A shop listed both with and without a condition is simply always available."""
    for it in items.values():
        rows = it['src'].get('shop')
        if rows:
            always = {r['where'] for r in rows if not r['cond']}
            it['src']['shop'] = [r for r in rows if not r['cond'] or r['where'] not in always]


def merge_pickup(items):
    """Collapse per-band pickup rows into '<chance>% at Lv a–b' ranges per item."""
    for it in items.values():
        rows = it['src'].get('pickup')
        if not rows:
            continue
        by_pct = {}
        for r in rows:
            by_pct[r['lv']] = by_pct.get(r['lv'], 0) + r['pct']
        it['src']['pickup'] = [dict(lv=lv, pct=pct) for lv, pct in by_pct.items()]


@lru_cache(maxsize=1)
def build_data():
    items = parse_items()
    collect(items)
    merge_pickup(items)
    dedupe_shops(items)
    out = []
    icons = {}
    for it in sorted(items.values(), key=lambda x: (list(POCKETS.values()).index(x['pocket']), x['name'])):
        it['n'] = sum(len(v) for v in it['src'].values())
        if it['n']:  # leftover FRLG / unused items have no source in Emerald
            out.append(it)
    for it in out:
        icons[it['key']] = load_item_icon_b64(it['key'])
    sprites = {}
    for it in out:
        for w in it['src'].get('wild', []):
            if w['sp'] not in sprites:
                sprites[w['sp']] = pdx.load_sprite_b64(tdx.species_sprite_folder(w['sp']))
    return out, icons, sprites


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bag — Emerald Legacy</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght,SOFT,WONK@0,9..144,300..900,0..100,0..1;1,9..144,300..900,0..100,0..1&family=Instrument+Sans:ital,wght@0,400..700;1,400..700&family=IBM+Plex+Mono:ital,wght@0,400;0,500;0,700;1,400&display=swap" rel="stylesheet">
<style>
  :root {
    --paper-0: #0a140e; --paper-1: #0e1b14; --paper-2: #13221a; --paper-3: #1a2c22;
    --ink: #ece3d0; --ink-dim: #b5a98f; --ink-mut: #7b705c;
    --rule: #2d3d33; --rule-2: #1e2a23;
    --jade-bright: #2eb070; --jade-soft: rgba(46,176,112,0.13); --dusk: #e8a530; --dusk-soft: rgba(232,165,48,0.13);
    --f-serif: 'Fraunces', 'Iowan Old Style', Georgia, serif;
    --f-sans: 'Instrument Sans', system-ui, -apple-system, sans-serif;
    --f-mono: 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: var(--f-sans); background: var(--paper-1); color: var(--ink); display: flex; height: 100vh; overflow: hidden; font-size: 14px; -webkit-font-smoothing: antialiased; }
  #sidebar { width: 310px; min-width: 260px; background: var(--paper-0); border-right: 1px solid var(--rule); display: flex; flex-direction: column; height: 100vh; }
  #sidebar-header { padding: 22px 20px 12px; border-bottom: 1px solid var(--rule); }
  #sidebar-header h1 { font-family: var(--f-serif); font-style: italic; font-weight: 400; font-size: 22px; line-height: 1; margin-bottom: 4px; }
  .volume { display: block; font-family: var(--f-mono); font-size: 9px; color: var(--jade-bright); letter-spacing: 0.3em; text-transform: uppercase; margin-bottom: 12px; }
  #search { width: 100%; padding: 8px 2px; border: 0; border-bottom: 1px solid var(--rule); background: transparent; color: var(--ink); font-family: var(--f-serif); font-style: italic; font-size: 15px; outline: none; }
  #search:focus { border-color: var(--jade-bright); }
  .filters { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }
  .fbtn { font-family: var(--f-mono); font-size: 9px; padding: 4px 8px; letter-spacing: 0.1em; text-transform: uppercase; border: 1px solid var(--rule); background: transparent; color: var(--ink-dim); cursor: pointer; }
  .fbtn.active { background: var(--jade-soft); border-color: var(--jade-bright); color: var(--jade-bright); }
  #count { font-family: var(--f-mono); font-size: 9px; color: var(--ink-mut); padding: 8px 20px; letter-spacing: 0.24em; text-transform: uppercase; border-bottom: 1px solid var(--rule); }
  #list { overflow-y: auto; flex: 1; padding: 6px 8px 24px; }
  .cat-header { font-family: var(--f-mono); font-size: 9px; color: var(--jade-bright); letter-spacing: 0.28em; text-transform: uppercase; padding: 14px 12px 6px; }
  .it { display: grid; grid-template-columns: 28px 1fr auto; align-items: center; gap: 8px; padding: 5px 12px; cursor: pointer; border-left: 2px solid transparent; }
  .it:hover { background: var(--paper-1); }
  .it.active { background: var(--jade-soft); border-left-color: var(--jade-bright); }
  .it img { width: 24px; height: 24px; image-rendering: pixelated; }
  .it .nm { font-family: var(--f-serif); font-style: italic; font-size: 15px; color: var(--ink-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .it.active .nm, .it:hover .nm { color: var(--ink); }
  .it .ct { font-family: var(--f-mono); font-size: 9px; color: var(--ink-mut); }
  .it.none .nm { opacity: 0.5; }
  #main { flex: 1; overflow-y: auto; padding: 44px 52px 64px; }
  #detail { max-width: 900px; margin: 0 auto; }
  #welcome { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; gap: 12px; }
  #welcome h2 { font-family: var(--f-serif); font-style: italic; font-weight: 400; font-size: 54px; line-height: 0.95; }
  #welcome h2 em { font-style: normal; color: var(--jade-bright); }
  #welcome p { font-family: var(--f-mono); font-size: 10px; color: var(--ink-mut); letter-spacing: 0.3em; text-transform: uppercase; }
  .head { display: grid; grid-template-columns: 96px 1fr; gap: 24px; align-items: center; margin-bottom: 8px; }
  .plate { width: 96px; height: 96px; display: grid; place-items: center; background: var(--paper-2); border: 1px solid var(--rule); }
  .plate img { width: 72px; height: 72px; image-rendering: pixelated; }
  .kicker { font-family: var(--f-mono); font-size: 10px; color: var(--jade-bright); letter-spacing: 0.26em; text-transform: uppercase; margin-bottom: 6px; }
  h2.title { font-family: var(--f-serif); font-style: italic; font-weight: 400; font-size: 48px; line-height: 0.95; letter-spacing: -0.02em; }
  .desc { font-family: var(--f-serif); font-size: 17px; line-height: 1.55; margin: 18px 0; padding-left: 16px; border-left: 2px solid var(--jade-bright); }
  .price { font-family: var(--f-mono); font-size: 11px; color: var(--ink-dim); }
  .section-title { font-family: var(--f-mono); font-size: 10px; color: var(--jade-bright); letter-spacing: 0.3em; text-transform: uppercase; margin: 30px 0 12px; display: flex; align-items: center; gap: 12px; }
  .section-title::before { content: "§"; color: var(--ink-mut); }
  .section-title::after { content: ""; flex: 1; height: 1px; background: var(--rule); }
  .section-title .n { color: var(--ink-mut); letter-spacing: 0.1em; }
  .tags { display: flex; flex-wrap: wrap; gap: 8px; }
  .tag { font-size: 12px; color: var(--ink-dim); padding: 6px 12px; border: 1px solid var(--rule); background: var(--paper-2); }
  .tag b { color: var(--ink); font-weight: 600; }
  .tag .dim, .dim { color: var(--ink-mut); }
  .tag img { width: 32px; height: 32px; image-rendering: pixelated; vertical-align: middle; margin: -8px 2px -8px -6px; }
  .pg { font-family: var(--f-mono); font-size: 8px; letter-spacing: 0.14em; color: var(--dusk); border: 1px solid var(--dusk); padding: 0 4px; margin-left: 4px; }
  .pg.br { color: var(--jade-bright); border-color: var(--jade-bright); }
  .empty { font-family: var(--f-serif); font-style: italic; color: var(--ink-mut); }
  #btn-back { display: none; margin-bottom: 18px; padding: 7px 14px; border: 1px solid var(--rule); background: transparent; color: var(--jade-bright); font-family: var(--f-mono); font-size: 10px; letter-spacing: 0.22em; text-transform: uppercase; cursor: pointer; }
  @media (max-width: 700px) {
    body { flex-direction: column; overflow: auto; height: auto; min-height: 100dvh; }
    #sidebar { width: 100%; min-width: unset; height: auto; max-height: 100dvh; border-right: none; }
    #sidebar.hidden, #main.hidden { display: none; }
    #main { padding: 22px 18px 40px; overflow: visible; }
    #btn-back { display: inline-block; }
    h2.title { font-size: 36px; }
  }
</style>
</head>
<body>
<div id="sidebar">
  <div id="sidebar-header">
    <h1>Bag</h1>
    <span class="volume">Vol. V · Where to find every item</span>
    <input type="text" id="search" placeholder="Search item or place…" oninput="render()">
    <div class="filters" id="filters"></div>
  </div>
  <div id="count"></div>
  <div id="list"></div>
</div>
<div id="main">
  <div id="welcome"><h2>The <em>Bag</em></h2><p>Select an item</p></div>
  <div id="detail" hidden>
    <button id="btn-back" onclick="goBack()">← Return to Bag</button>
    <div id="detail-body"></div>
  </div>
</div>
<script>
const ITEMS = ITEMS_PLACEHOLDER;
const ICONS = ICONS_PLACEHOLDER;
const SPRITES = SPRITES_PLACEHOLDER;
const POCKETS = [...new Set(ITEMS.map(i => i.pocket))];
let pocket = '', current = null;
const isMobile = () => window.innerWidth <= 700;
const norm = s => s.toLowerCase().normalize('NFD').replace(/[^a-z0-9]+/g, ' ').trim();
const xl = (app, key, label) => key ? `<a class="xl" data-app="${app}" data-key="${key}">${label}</a>` : label;

function goBack() {
  document.getElementById('sidebar').classList.remove('hidden');
  document.getElementById('main').classList.add('hidden');
}

function haystack(it) {
  if (!it._h) it._h = norm([it.name, ...Object.values(it.src).flat().map(s => typeof s === 'string' ? s : (s.where || s.locs || ''))].join(' '));
  return it._h;
}

function render() {
  document.getElementById('filters').innerHTML = ['', ...POCKETS].map(p =>
    `<button class="fbtn${p === pocket ? ' active' : ''}" onclick="pocket='${p}';render()">${p || 'All'}</button>`).join('');
  const q = norm(document.getElementById('search').value);
  const items = ITEMS.filter(it => (!pocket || it.pocket === pocket) && (!q || haystack(it).includes(q)));
  document.getElementById('count').textContent = `${items.length} items`;
  let last = null, html = '';
  items.forEach(it => {
    if (it.pocket !== last) { last = it.pocket; html += `<div class="cat-header">${it.pocket}</div>`; }
    html += `<div class="it${it.key === current ? ' active' : ''}${it.n ? '' : ' none'}" onclick="selectItem('${it.key}')">
      ${ICONS[it.key] ? `<img src="${ICONS[it.key]}" alt="">` : '<span></span>'}<span class="nm">${it.name}</span><span class="ct">${it.n || ''}</span></div>`;
  });
  document.getElementById('list').innerHTML = html || '<div class="empty" style="padding:16px">No items match.</div>';
}

const SECTIONS = [
  ['found', 'Found on the ground', s => `<span class="tag">${s}</span>`],
  ['hidden', 'Hidden (use the Itemfinder)', s => `<span class="tag">${s}</span>`],
  ['gift', 'Given by NPCs', s => `<span class="tag"><b>${s.where}</b>${s.what ? ` <span class="dim">· ${s.what}</span>` : ''}${s.qty > 1 ? ` ×${s.qty}` : ''}</span>`],
  ['shop', 'Buy in shops', (s, it) => `<span class="tag"><b>${s.where}</b>${s.cond ? ` <span class="dim">· ${s.cond}</span>` : ''}</span>`],
  ['prize', 'Prizes & exchanges', s => `<span class="tag"><b>${s.where}</b> <span class="dim">· ${s.cost}</span></span>`],
  ['berry', 'Berry trees (at the start of the game)', s => `<span class="tag">${s}</span>`],
  ['wild', 'Held by wild Pokémon', s => `<span class="tag">${SPRITES[s.sp] ? `<img src="${SPRITES[s.sp]}" alt="">` : ''}${xl('pokedex', s.sp, `<b>${s.name}</b>`)} <span class="dim">· ${s.pct}</span></span>`],
  ['steal', 'Steal from trainers (Thief / Covet)', s => `<span class="tag">${s.repeat ? '↻ ' : ''}${xl('trainers', s.tv, `<b>${s.label}</b>`)}${s.n > 1 ? ' ×' + s.n : ''}${s.br ? '<span class="pg br">BR</span>' : ''} <span class="dim">· ${s.locs}</span></span>`],
  ['pickup', 'Pickup ability', s => `<span class="tag"><b>${s.lv}</b> <span class="dim">· ${s.pct}% of pickups</span></span>`],
];

function selectItem(key) {
  const it = ITEMS.find(i => i.key === key);
  if (!it) return;
  current = key;
  document.querySelectorAll('.it').forEach(el => el.classList.toggle('active', el.getAttribute('onclick').includes(`'${key}'`)));
  document.getElementById('welcome').style.display = 'none';
  document.getElementById('detail').hidden = false;
  if (isMobile()) { document.getElementById('sidebar').classList.add('hidden'); document.getElementById('main').classList.remove('hidden'); }
  const price = it.price ? `Buy ₽${it.price.toLocaleString()} · Sell ₽${Math.floor(it.price / 2).toLocaleString()}` : 'Can’t be sold';
  let body = `<div class="head"><div class="plate">${ICONS[it.key] ? `<img src="${ICONS[it.key]}" alt="">` : ''}</div>
    <div><div class="kicker">${it.pocket}</div><h2 class="title">${it.name}</h2><div class="price">${price}</div></div></div>
    ${it.desc ? `<div class="desc">${it.desc}</div>` : ''}`;
  let any = false;
  SECTIONS.forEach(([k, title, fmt]) => {
    const rows = it.src[k];
    if (!rows || !rows.length) return;
    any = true;
    let extra = '';
    if (k === 'wild') extra = '<p class="dim" style="margin:-4px 0 10px;font-size:12px">A Pokémon with Compound Eyes in the lead raises the odds to 60% (common) and 20% (rare).</p>';
    if (k === 'pickup') extra = '<p class="dim" style="margin:-4px 0 10px;font-size:12px">After each battle, every Pokémon with Pickup that isn’t holding an item has a 10% chance to find something. What it finds depends on its level.</p>';
    body += `<div class="section-title">${title} <span class="n">${rows.length}</span></div>${extra}<div class="tags">${rows.map(r => fmt(r, it)).join('')}</div>`;
  });
  if (!any) body += '<p class="empty" style="margin-top:24px">No known source in this version.</p>';
  document.getElementById('detail-body').innerHTML = body;
  document.getElementById('main').scrollTop = 0;
}

render();
registerApp('bag', key => {
  let k = String(key).toUpperCase();
  if (!k.startsWith('ITEM_')) { const hit = ITEMS.find(i => norm(i.name) === norm(key)); k = hit ? hit.key : 'ITEM_' + k; }
  if (!document.querySelector(`.it[onclick*="'${k}'"]`)) { pocket = ''; document.getElementById('search').value = ''; render(); }
  selectItem(k);
  const el = document.querySelector(`.it[onclick*="'${k}'"]`); if (el) el.scrollIntoView({block: 'nearest'});
});
</script>
</body>
</html>
'''


def generate():
    print('Building Bag...')
    items, icons, sprites = build_data()

    def dump(o):
        return json.dumps(o, ensure_ascii=False, separators=(',', ':'))

    html = site_shared.inject(HTML_TEMPLATE)
    html = html.replace('ITEMS_PLACEHOLDER', dump(items)).replace('ICONS_PLACEHOLDER', dump(icons))
    html = html.replace('SPRITES_PLACEHOLDER', dump(sprites))
    out = os.path.join(BASE, 'docs', 'items.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  {len(items)} items, {len(sprites)} Pokémon sprites')
    print(f'\nGenerated: {out} ({os.path.getsize(out) / 1024:.0f} KB)')
    return len(items)


if __name__ == '__main__':
    generate()
