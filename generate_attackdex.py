#!/usr/bin/env python3
"""Generates attackdex.html — a field guide to every move and who learns it.

Mirrors generate_trainerdex.py: parses the decomp source and bakes a single
self-contained HTML file (move data + species sprites inlined as base64). Reuses
the pokedex generator's learnset/move/sprite helpers via import.
"""

import re
import os
import json

import generate_pokedex as pdx

BASE = os.path.dirname(os.path.abspath(__file__))

# IS_TYPE_PHYSICAL from include/battle.h (this hack swaps Ghost to special and Dark to physical).
from coverage_data import PHYSICAL as PHYSICAL_TYPES

TARGET_DISPLAY = {
    'SELECTED':        'Single target',
    'DEPENDS':         'Varies',
    'USER':            'Self',
    'RANDOM':          'Random foe',
    'BOTH':            'Both foes',
    'FOES_AND_ALLY':   'All other Pokémon',
    'OPPONENTS_FIELD': "Foes' field",
}

FLAG_DISPLAY = [
    ('FLAG_MAKES_CONTACT',        'Contact'),
    ('FLAG_PROTECT_AFFECTED',     'Blocked by Protect'),
    ('FLAG_MAGIC_COAT_AFFECTED',  'Reflected by Magic Coat'),
    ('FLAG_SNATCH_AFFECTED',      'Stolen by Snatch'),
    ('FLAG_MIRROR_MOVE_AFFECTED', 'Copied by Mirror Move'),
    ('FLAG_KINGS_ROCK_AFFECTED',  "King's Rock"),
]

# --- Parse battle move details (fields the pokedex parser doesn't keep) ---

def parse_move_details(path):
    with open(path) as f:
        content = f.read()
    result = {}
    blocks = re.split(r'\[MOVE_(\w+)\]', content)
    for i in range(1, len(blocks) - 1, 2):
        key, body = blocks[i], blocks[i + 1]
        if key == 'NONE':
            continue

        def field(name, default='0'):
            m = re.search(rf'\.{name}\s*=\s*([^,\n]+)', body)
            return m.group(1).strip() if m else default

        flags = field('flags')
        result[key] = {
            'chance': int(field('secondaryEffectChance')),
            'priority': int(field('priority')),
            'target': field('target', 'MOVE_TARGET_SELECTED').replace('MOVE_TARGET_', ''),
            'flags': [label for const, label in FLAG_DISPLAY if const in flags],
        }
    return result

# --- Build combined data ---

def build_data():
    print('Parsing moves...')
    moves_path = os.path.join(BASE, 'src/data/battle_moves.h')
    battle = pdx.parse_battle_moves(moves_path)
    details = parse_move_details(moves_path)
    descs = pdx.parse_move_descriptions(os.path.join(BASE, 'src/data/text/move_descriptions.h'))
    print(f'  {len(battle)} moves')

    print('Parsing learnsets...')
    level_up = pdx.parse_level_up(os.path.join(BASE, 'src/data/pokemon/level_up_learnsets.h'))
    tutor = pdx.parse_tutor(os.path.join(BASE, 'src/data/pokemon/tutor_learnsets.h'))
    tmhm = pdx.parse_tmhm(os.path.join(BASE, 'src/data/pokemon/tmhm_learnsets.h'))
    egg = pdx.parse_egg_moves(os.path.join(BASE, 'src/data/pokemon/egg_moves.h'))
    dex_order = pdx.parse_national_dex_order(os.path.join(BASE, 'include/constants/pokedex.h'))

    # Species that count: everything with a dex number, plus alternate forms (Deoxys)
    print('Loading species sprites...')
    species = {}
    for key in level_up:
        if key in pdx.FORM_OF:
            base_key, form_name = pdx.FORM_OF[key]
            if base_key not in dex_order:
                continue
            name = f'{pdx.species_display_name(base_key)} ({form_name})'
            dex_num = dex_order[base_key]
        elif key in dex_order:
            name = pdx.species_display_name(key)
            dex_num = dex_order[key]
        else:
            continue
        folder = pdx.FORM_FOLDER.get(key) or pdx.species_folder(key)
        species[key] = {'name': name, 'dexNum': dex_num, 'sprite': pdx.load_sprite_b64(folder)}
    print(f'  {len(species)} species')

    # move display name -> learners, in national dex order
    learners = {}
    def add(move_name, kind, entry):
        learners.setdefault(move_name, {'level': [], 'tm': [], 'tutor': [], 'egg': []})[kind].append(entry)

    for key in sorted(species, key=lambda k: (species[k]['dexNum'], k)):
        levels = {}
        for lm in level_up.get(key, []):
            levels.setdefault(lm['move'], []).append(lm['level'])
        for move_name, lvls in levels.items():
            add(move_name, 'level', [key, sorted(set(lvls))])
        for label in tmhm.get(key, []):
            add(re.sub(r'^(?:TM|HM)\d+\s+', '', label), 'tm', key)
        for move_name in tutor.get(key, []):
            add(move_name, 'tutor', key)
        for move_name in egg.get(key, []):
            add(move_name, 'egg', key)

    moves = []
    for key, stats in battle.items():
        if key == 'NONE':
            continue
        name = pdx.fmt_move('MOVE_' + key)
        det = details.get(key, {})
        tm = None
        if key in pdx.TM_SET:
            tm = f'TM{pdx.TM_LIST.index(key) + 1:02d}'
        elif key in pdx.HM_SET:
            tm = f'HM{pdx.HM_LIST.index(key) + 1:02d}'
        category = 'Status' if stats['power'] == 0 else ('Physical' if stats['type'] in PHYSICAL_TYPES else 'Special')
        moves.append({
            'name': name,
            'type': stats['type'],
            'category': category,
            'power': stats['power'],
            'accuracy': stats['accuracy'],
            'pp': stats['pp'],
            'priority': det.get('priority', 0),
            'chance': det.get('chance', 0),
            'target': TARGET_DISPLAY.get(det.get('target'), det.get('target', '').replace('_', ' ').title()),
            'flags': det.get('flags', []),
            'desc': descs.get(key) or descs.get(re.sub(r'_(\d)', r'\1', key), ''),  # CONVERSION_2 -> CONVERSION2
            'tm': tm,
            'learners': learners.get(name, {'level': [], 'tm': [], 'tutor': [], 'egg': []}),
        })
    moves.sort(key=lambda m: m['name'])

    unmatched = set(learners) - {m['name'] for m in moves}
    if unmatched:
        print(f'  WARNING: learnset moves with no move data: {sorted(unmatched)}')
    print(f'  Total: {len(moves)} moves')
    return moves, species

# --- Generate HTML ---

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Attack Dex — Emerald Legacy</title>
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
  .filters { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; margin-top: 12px; }
  .filters select {
    appearance: none; -webkit-appearance: none; width: 100%; min-width: 0;
    font-family: var(--f-mono); font-size: 9px; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--ink-dim); background: var(--paper-1); border: 1px solid var(--rule);
    padding: 5px 6px; cursor: pointer; outline: none;
  }
  .filters select:focus, .filters select:hover { border-color: var(--jade-bright); color: var(--ink); }
  #move-count {
    font-family: var(--f-mono); font-size: 9px; color: var(--ink-mut); padding: 10px 20px;
    letter-spacing: 0.24em; text-transform: uppercase; border-bottom: 1px solid var(--rule);
    display: flex; justify-content: space-between; align-items: center;
  }
  #move-count::before { content: "Index"; color: var(--jade-bright); }
  #move-list { overflow-y: auto; flex: 1; padding: 8px 8px 24px; display: flex; flex-direction: column; }
  #move-list::-webkit-scrollbar { width: 10px; }
  #move-list::-webkit-scrollbar-track { background: transparent; }
  #move-list::-webkit-scrollbar-thumb { background: var(--paper-3); border: 3px solid var(--paper-0); border-radius: 10px; }

  .mv-item {
    display: grid; grid-template-columns: 4px 1fr auto; align-items: center; gap: 12px;
    padding: 7px 12px 7px 8px; cursor: pointer; border-left: 2px solid transparent;
    transition: background 0.15s, border-color 0.15s;
  }
  .mv-item:hover { background: var(--paper-1); }
  .mv-item.active { background: var(--jade-soft); border-left-color: var(--jade-bright); }
  .mv-item .swatch { width: 4px; height: 26px; }
  .mv-item .mv-name {
    font-family: var(--f-serif); font-style: italic; font-size: 15px; color: var(--ink-dim);
    line-height: 1.15; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; display: block;
  }
  .mv-item .mv-sub {
    font-family: var(--f-mono); font-size: 8px; color: var(--ink-mut);
    letter-spacing: 0.16em; text-transform: uppercase;
  }
  .mv-item .mv-pow { font-family: var(--f-mono); font-size: 11px; color: var(--ink-mut); }
  .mv-item:hover .mv-name { color: var(--ink); }
  .mv-item.active .mv-name { color: var(--ink); font-style: normal; font-weight: 500; }
  .mv-item.active .mv-pow { color: var(--jade-bright); }

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

  #move-detail { display: none; max-width: 920px; margin: 0 auto; }

  .kicker {
    font-family: var(--f-mono); font-size: 10px; color: var(--jade-bright);
    letter-spacing: 0.26em; text-transform: uppercase; margin-bottom: 10px;
    display: flex; align-items: center; gap: 10px;
  }
  .kicker::after { content: ""; flex: 1; height: 1px; background: var(--rule); }
  #move-detail h2 {
    font-family: var(--f-serif); font-variation-settings: "opsz" 144, "SOFT" 60, "WONK" 1;
    font-weight: 400; font-style: italic; font-size: 60px; line-height: 0.95; color: var(--ink);
    letter-spacing: -0.03em; margin-bottom: 14px; overflow-wrap: anywhere;
  }
  .badges { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 18px; }
  .badge {
    font-family: var(--f-mono); font-size: 9px; padding: 4px 10px; letter-spacing: 0.18em;
    text-transform: uppercase; border: 1px solid var(--rule); color: var(--ink-dim);
  }
  .badge.type { color: #fff; border-color: transparent; }
  .badge.tm { border-color: var(--dusk); color: var(--dusk); }
  .badge.tutor { border-color: var(--jade-bright); color: var(--jade-bright); }

  .desc {
    font-family: var(--f-serif); font-style: italic; font-size: 19px; color: var(--ink-dim);
    line-height: 1.45; max-width: 620px; margin-bottom: 26px;
  }

  .stat-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); border: 1px solid var(--rule); background: var(--paper-2); }
  .stat { padding: 14px 16px; border-right: 1px solid var(--rule); }
  .stat:last-child { border-right: 0; }
  .stat .k { display: block; font-family: var(--f-mono); font-size: 8px; color: var(--ink-mut); letter-spacing: 0.2em; text-transform: uppercase; margin-bottom: 6px; }
  .stat .v { font-family: var(--f-serif); font-size: 26px; color: var(--ink); line-height: 1; }
  .stat .v.small { font-size: 15px; font-style: italic; line-height: 1.3; }

  .flag-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 14px; }
  .flag { font-family: var(--f-mono); font-size: 9px; color: var(--ink-mut); letter-spacing: 0.1em; padding: 3px 8px; border: 1px dashed var(--rule); }

  .section-title {
    font-family: var(--f-mono); font-size: 10px; color: var(--jade-bright); letter-spacing: 0.3em;
    text-transform: uppercase; margin-bottom: 14px; margin-top: 36px; display: flex;
    align-items: center; gap: 12px; font-weight: 500;
  }
  .section-title::before { content: "§"; color: var(--ink-mut); font-weight: 400; font-size: 13px; }
  .section-title::after { content: ""; flex: 1; height: 1px; background: var(--rule); }
  .section-title .n { color: var(--ink-mut); font-weight: 400; }

  .learner-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 6px; }
  .learner {
    display: grid; grid-template-columns: 40px 1fr; align-items: center; gap: 8px;
    padding: 4px 10px 4px 4px; border: 1px solid var(--rule-2); background: var(--paper-2); min-width: 0;
  }
  .learner img { width: 40px; height: 40px; image-rendering: pixelated; }
  .learner .ln-name { font-family: var(--f-serif); font-style: italic; font-size: 14px; color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; }
  .learner .ln-meta { font-family: var(--f-mono); font-size: 9px; color: var(--ink-mut); letter-spacing: 0.06em; }
  .learner .ln-meta b { color: var(--jade-bright); font-weight: 500; }
  .empty-msg { font-family: var(--f-serif); font-style: italic; color: var(--ink-mut); }

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
    #move-detail h2 { font-size: 42px; }
    .stat-row { grid-template-columns: repeat(3, 1fr); }
    .stat { border-bottom: 1px solid var(--rule); }
  }
</style>
</head>
<body>

<div id="sidebar">
  <div id="sidebar-header">
    <h1>Attack Dex</h1>
    <span class="volume">Vol. III · Moves &amp; Learners</span>
    <input type="text" id="search" placeholder="Search move or Pokémon…" oninput="applyFilters()">
    <div class="filters">
      <select id="f-type" onchange="applyFilters()" aria-label="Type"><option value="">All types</option></select>
      <select id="f-cat" onchange="applyFilters()" aria-label="Category">
        <option value="">All kinds</option><option>Physical</option><option>Special</option><option>Status</option>
      </select>
      <select id="f-sort" onchange="applyFilters()" aria-label="Sort">
        <option value="name">A–Z</option><option value="power">Power</option><option value="type">Type</option>
      </select>
    </div>
  </div>
  <div id="move-count"></div>
  <div id="move-list"></div>
</div>

<div id="main">
  <div id="welcome">
    <h2>The <em>Attack</em><br>Dex</h2>
    <p>Select a move from the index</p>
  </div>
  <div id="move-detail"></div>
</div>

<script>
const DATA = MOVE_DATA_PLACEHOLDER;
const SPECIES = SPECIES_PLACEHOLDER;

const TYPE_COLORS = {
  NORMAL:'#9099A1',FIRE:'#E8554E',WATER:'#5598D8',ELECTRIC:'#F0C13A',
  GRASS:'#5DBE62',ICE:'#76C6D0',FIGHTING:'#CE4068',POISON:'#A55FA5',
  GROUND:'#D97845',FLYING:'#8FA8D8',PSYCHIC:'#E8547A',BUG:'#90B820',
  ROCK:'#C0AA48',GHOST:'#5060A8',DRAGON:'#6048E8',DARK:'#5060A8',
  STEEL:'#9898B8',MYSTERY:'#68A090',
};
const typeLabel = t => t === 'MYSTERY' ? '???' : t;

const norm = s => s.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
const indexed = DATA.map((m, i) => {
  m._idx = i;
  const L = m.learners;
  const keys = new Set([...L.level.map(e => e[0]), ...L.tm, ...L.tutor, ...L.egg]);
  m._learnerNames = [...keys].map(k => norm(SPECIES[k].name));
  return m;
});

const typeSel = document.getElementById('f-type');
[...new Set(DATA.map(m => m.type))].sort().forEach(t => {
  const o = document.createElement('option');
  o.value = t; o.textContent = typeLabel(t);
  typeSel.appendChild(o);
});

let currentIdx = null;
const isMobile = () => window.innerWidth <= 700;
function goBack() {
  document.getElementById('sidebar').classList.remove('hidden');
  document.getElementById('main').classList.add('hidden');
}

function renderList(items) {
  const list = document.getElementById('move-list');
  document.getElementById('move-count').innerHTML = `<span>${items.length} entries</span>`;
  list.innerHTML = '';
  if (items.length === 0) { list.innerHTML = '<div class="empty-msg" style="padding:16px 12px">No moves match.</div>'; return; }
  const frag = document.createDocumentFragment();
  items.forEach(m => {
    const div = document.createElement('div');
    div.className = 'mv-item' + (m._idx === currentIdx ? ' active' : '');
    div.dataset.idx = m._idx;
    const sub = m._via
      ? `Learned by ${m._via}`
      : `${typeLabel(m.type)} · ${m.category}${m.tm ? ' · ' + m.tm : ''}`;
    div.innerHTML = `<span class="swatch" style="background:${TYPE_COLORS[m.type] || '#888'}"></span>
      <span style="min-width:0"><span class="mv-name">${m.name}</span><span class="mv-sub">${sub}</span></span>
      <span class="mv-pow">${m.power > 1 ? m.power : '—'}</span>`;
    div.onclick = () => selectMove(m._idx);
    frag.appendChild(div);
  });
  list.appendChild(frag);
}

function applyFilters() {
  const q = norm(document.getElementById('search').value);
  const type = typeSel.value;
  const cat = document.getElementById('f-cat').value;
  const sort = document.getElementById('f-sort').value;
  let items = [];
  indexed.forEach(m => {
    if (type && m.type !== type) return;
    if (cat && m.category !== cat) return;
    m._via = null;
    if (q && !norm(m.name).includes(q)) {
      // Pokémon search: "pikachu" lists every move Pikachu can learn
      const hit = m._learnerNames.find(n => n.includes(q));
      if (!hit && !norm(typeLabel(m.type)).includes(q)) return;
      if (hit) m._via = Object.values(SPECIES).find(s => norm(s.name) === hit).name;
    }
    items.push(m);
  });
  if (sort === 'power') items.sort((a, b) => b.power - a.power || a.name.localeCompare(b.name));
  else if (sort === 'type') items.sort((a, b) => a.type.localeCompare(b.type) || a.name.localeCompare(b.name));
  renderList(items);
}

function selectMove(idx) {
  currentIdx = idx;
  document.querySelectorAll('.mv-item').forEach(el => el.classList.toggle('active', parseInt(el.dataset.idx) === idx));
  document.getElementById('welcome').style.display = 'none';
  document.getElementById('move-detail').style.display = 'block';
  if (isMobile()) {
    document.getElementById('sidebar').classList.add('hidden');
    document.getElementById('main').classList.remove('hidden');
  }
  renderDetail(DATA[idx]);
  document.getElementById('main').scrollTop = 0;
}

function learnerCard(key, meta) {
  const s = SPECIES[key];
  return `<div class="learner">
    ${s.sprite ? `<img src="${s.sprite}" alt="${s.name}" loading="lazy">` : '<div style="width:40px;height:40px"></div>'}
    <span style="min-width:0"><a class="ln-name xl" data-app="pokedex" data-key="${key}">${s.name}</a><span class="ln-meta">#${String(s.dexNum).padStart(3, '0')}${meta ? ' · ' + meta : ''}</span></span>
  </div>`;
}

function learnerSection(title, entries, render) {
  if (!entries.length) return '';
  return `<div class="section-title">${title} <span class="n">${entries.length}</span></div>
    <div class="learner-grid">${entries.map(render).join('')}</div>`;
}

function renderDetail(m) {
  const color = TYPE_COLORS[m.type] || '#888';
  const badges = [`<span class="badge type" style="background:${color}">${typeLabel(m.type)}</span>`,
                  `<span class="badge">${m.category}</span>`];
  if (m.tm) badges.push(`<span class="badge tm">${m.tm}</span>`);
  if (m.learners.tutor.length) badges.push('<span class="badge tutor">Move Tutor</span>');

  const stats = [
    ['Power', m.power > 1 ? m.power : '—'],
    ['Accuracy', m.accuracy > 0 ? m.accuracy + '%' : '—'],
    ['PP', m.pp],
    ['Priority', m.priority > 0 ? '+' + m.priority : m.priority],
  ];
  if (m.chance) stats.push(['Effect %', m.chance + '%']);
  const statHtml = stats.map(([k, v]) => `<div class="stat"><span class="k">${k}</span><span class="v">${v}</span></div>`).join('')
    + `<div class="stat"><span class="k">Target</span><span class="v small">${m.target}</span></div>`;

  const L = m.learners;
  const total = new Set([...L.level.map(e => e[0]), ...L.tm, ...L.tutor, ...L.egg]).size;
  const sections =
    learnerSection('Level Up', L.level, ([k, lvls]) => learnerCard(k, `Lv <b>${lvls.join(', ')}</b>`)) +
    learnerSection(m.tm ? `${m.tm}` : 'TM / HM', L.tm, k => learnerCard(k, '')) +
    learnerSection('Move Tutor', L.tutor, k => learnerCard(k, '')) +
    learnerSection('Egg Move', L.egg, k => learnerCard(k, ''));

  document.getElementById('move-detail').innerHTML = `
    <button id="btn-back" onclick="goBack()">← Return to Index</button>
    <div class="kicker">${typeLabel(m.type)} · ${m.category}</div>
    <h2>${m.name}</h2>
    <div class="badges">${badges.join('')}</div>
    ${m.desc ? `<p class="desc">${m.desc}</p>` : ''}
    <div class="stat-row">${statHtml}</div>
    ${m.flags.length ? `<div class="flag-list">${m.flags.map(f => `<span class="flag">${f}</span>`).join('')}</div>` : ''}
    ${total ? sections : '<div class="section-title">Learned By</div><span class="empty-msg">No Pokémon learns this move.</span>'}
  `;
}

applyFilters();
registerApp('moves', key => {
  const k = String(key).toUpperCase().replace(/[^A-Z0-9]/g, '');
  let i = DATA.findIndex(m => m.name.toUpperCase().replace(/[^A-Z0-9]/g, '') === k);
  if (i < 0) return;
  if (!document.querySelector(`.mv-item[data-idx="${i}"]`)) {  // clear filters hiding it
    document.getElementById('search').value = ''; typeSel.value = ''; document.getElementById('f-cat').value = ''; applyFilters();
  }
  selectMove(i);
  const el = document.querySelector(`.mv-item[data-idx="${i}"]`); if (el) el.scrollIntoView({block: 'nearest'});
});
</script>
</body>
</html>
'''

def generate():
    moves, species = build_data()

    def dump(o):
        return json.dumps(o, ensure_ascii=False, separators=(',', ':'))

    import site_shared
    html = site_shared.inject(HTML_TEMPLATE)
    html = html.replace('MOVE_DATA_PLACEHOLDER', dump(moves))
    html = html.replace('SPECIES_PLACEHOLDER', dump(species))

    docs_dir = os.path.join(BASE, 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    out_path = os.path.join(docs_dir, 'attackdex.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f'\nGenerated: {out_path} ({size_mb:.1f} MB)')

if __name__ == '__main__':
    generate()
