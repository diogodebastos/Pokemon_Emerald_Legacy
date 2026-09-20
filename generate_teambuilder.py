#!/usr/bin/env python3
"""Team Builder app → docs/teambuilder.html.

Pick six Pokémon and four moves each; the page shows the same matchup grids as the Guide's
Defensive Duos (what hits the team, what the team's moves hit) and every species the team
can't hit super effectively.

Data comes from coverage_data.py so the numbers match the Guide's Team Building pages:
learnsets include pre-evolution level-up and egg moves, and "super effective" respects the
defender's abilities (Levitate, Flash Fire, Volt/Water Absorb, Thick Fat).
"""

import io
import os
import re
import json
import contextlib

import coverage_data as cov
import generate_guide as gdx
import generate_pokedex as pdx
import guide_pages
import site_shared
from site_shared import BASE

# Moves whose damage ignores the type chart (or whose type varies): they never count as
# a super-effective hit.
NO_TYPE_DAMAGE = {'EFFECT_HIDDEN_POWER', 'EFFECT_LEVEL_DAMAGE', 'EFFECT_DRAGON_RAGE', 'EFFECT_SONICBOOM',
                  'EFFECT_SUPER_FANG', 'EFFECT_PSYWAVE', 'EFFECT_COUNTER', 'EFFECT_MIRROR_COAT',
                  'EFFECT_ENDEAVOR', 'EFFECT_BIDE', 'EFFECT_OHKO'}


def hold_items():
    """Items with a battle hold effect (src/data/items.h) that the Bag app can source in-game,
    as [{k, n, icon}] sorted by name."""
    import generate_items as idx
    with open(os.path.join(BASE, 'src/data/items.h')) as f:
        body = f.read()
    holds = {k for k, b in re.findall(r'\[(ITEM_\w+)\]\s*=\s*\{(.*?)\n    \},', body, re.S)
             if re.search(r'\.holdEffect = HOLD_EFFECT_(?!NONE)\w+', b)}
    with contextlib.redirect_stdout(io.StringIO()):
        obtainable = idx.build_data()[0]
    items = [dict(k=it['key'], n=it['name'], icon=site_shared.load_item_icon_b64(it['key']))
             for it in obtainable if it['key'] in holds]
    return sorted(items, key=lambda x: x['n'])


def build_data():
    D = cov.load()
    with contextlib.redirect_stdout(io.StringIO()):
        dex = pdx.parse_national_dex_order(os.path.join(BASE, 'include/constants/pokedex.h'))
        abil = pdx.parse_ability_info(os.path.join(BASE, 'src/data/text/abilities.h'))
        base_stats = pdx.parse_base_stats(os.path.join(BASE, 'src/data/pokemon/species_info.h'))
    se = cov.coverage()
    final = set(cov.final_forms(legendary=True)) | {'SHEDINJA', 'SMEARGLE', 'UNOWN'}

    move_keys = sorted(D['moves'], key=lambda k: pdx.fmt_move('MOVE_' + k))
    move_keys = [k for k in move_keys if k not in ('NONE', 'STRUGGLE')]
    move_idx = {k: i for i, k in enumerate(move_keys)}
    moves = []
    for k in move_keys:
        m = D['moves'][k]
        moves.append(dict(k=k, n=pdx.fmt_move('MOVE_' + k), t=m['type'], p=m['power'], a=m['accuracy'],
                          atk=m['power'] > 0 and m['effect'] not in NO_TYPE_DAMAGE, ally=m['spread']))

    species = []
    order = sorted(D['species'], key=lambda s: (dex.get(pdx.FORM_OF.get(s, (s,))[0], 999), s))
    for s in order:
        d = D['species'][s]
        learn = sorted(((move_idx[mv], ' · '.join(how)) for mv, how in D['learn'][s].items() if mv in move_idx),
                       key=lambda x: moves[x[0]]['n'])
        species.append(dict(
            k=s, n=pdx.species_display_name(s), d=dex.get(pdx.FORM_OF.get(s, (s,))[0], 0),
            dex=pdx.FORM_OF.get(s, (s,))[0],
            t=list(d['types']),
            ab=[[a, abil.get(a, {}).get('name', a.replace('_', ' ').title())] for a in base_stats.get(s, {}).get('abilities') or sorted(d['abilities'])],
            f=s in final,
            se=sum(1 << i for i, t in enumerate(cov.TYPES) if s in se[t]),
            # b: base HP + Def + Sp. Def, so suggestions can tell a wall from a Magikarp.
            # at: attacking types this species can learn a real damaging move of — the
            # offensive counterpart to `se`, used to suggest answers for uncovered types.
            b=d['bulk'], o=max(d['atk'], d['spa']), lg=s in cov.LEGENDARY,
            at=sum(1 << i for i, t in enumerate(cov.TYPES)
                   if any(moves[j]['atk'] and moves[j]['t'] == t for j, _ in learn)),
            m=learn,
        ))
    return species, moves


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Emerald Legacy — Team Builder</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght,SOFT,WONK@0,9..144,300..900,0..100,0..1;1,9..144,300..900,0..100,0..1&family=Instrument+Sans:ital,wght@0,400..700;1,400..700&family=IBM+Plex+Mono:ital,wght@0,400;0,500;0,700;1,400&display=swap" rel="stylesheet">
<style>
GUIDE_PAGES_CSS
  /* Team app: a tab bar over two views — the builder, and the battling pages */
  body { display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
  #tabbar { flex: none; display: flex; align-items: center; gap: 6px; padding: 10px 16px; border-bottom: 1px solid var(--rule); background: var(--paper-0); }
  #tabbar .brand { font-family: var(--f-serif); font-style: italic; font-size: 17px; color: var(--ink); margin-right: 10px; }
  #tabbar .tb { font-family: var(--f-mono); font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase;
                padding: 7px 14px; border: 1px solid transparent; background: none; color: var(--ink-mut); cursor: pointer; }
  #tabbar .tb:hover { color: var(--ink); }
  #tabbar .tb.active { color: var(--jade-bright); border-color: var(--jade-bright); background: var(--jade-soft); }
  /* min-width: 0 everywhere, or these flex items refuse to shrink below their content width */
  #views { flex: 1; min-height: 0; min-width: 0; display: flex; }
  #views > div, #view-pages > #main { min-width: 0; }
  #views.builder #view-pages, #views.pages #view-builder { display: none; }
  #view-builder { flex: 1; min-height: 0; overflow-y: auto;
                  background: radial-gradient(1000px 500px at 100% -100px, rgba(46,176,112,0.05), transparent 55%), var(--paper-1); }
  #view-pages { flex: 1; min-height: 0; display: flex; }
  #builder { max-width: 1100px; margin: 0 auto; padding: 40px 56px 64px; }
  #builder h2 {
    font-family: var(--f-serif); font-variation-settings: "opsz" 144, "SOFT" 60, "WONK" 1;
    font-weight: 400; font-style: italic; font-size: 56px; line-height: 0.95; color: var(--ink);
    letter-spacing: -0.03em; margin-bottom: 20px;
  }
  .dim { font-family: var(--f-mono); font-size: 10px; color: var(--ink-mut); }
  .open-builder { display: flex; justify-content: flex-end; margin: 0 0 6px; }

  .toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 4px 0 8px; }
  .btn { font-family: var(--f-mono); font-size: 9px; padding: 6px 12px; letter-spacing: 0.14em; text-transform: uppercase;
         border: 1px solid var(--rule); background: transparent; color: var(--ink-dim); cursor: pointer; }
  .btn:hover { border-color: var(--jade-bright); color: var(--ink); }
  .btn.done { border-color: var(--jade-bright); color: var(--jade-bright); }
  .btn-ai { border-color: var(--jade-deep); color: var(--jade-bright); }
  .sugs { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin: 2px 0 14px; }
  .sug-lbl { width: 100%; font-family: var(--f-mono); font-size: 9px; letter-spacing: 0.18em; text-transform: uppercase;
             color: var(--ink-mut); margin-bottom: 2px; }
  .sugchip { display: inline-flex; align-items: center; gap: 5px; padding: 3px 10px 3px 3px; border: 1px solid var(--rule);
             border-radius: 999px; background: var(--paper-2); cursor: pointer; transition: border-color 0.15s, background 0.15s; }
  .sugchip:hover { border-color: var(--jade-bright); background: var(--jade-soft); }
  .sugchip img { width: 28px; height: 28px; image-rendering: pixelated; }
  .sugchip .sn { font-family: var(--f-serif); font-style: italic; font-size: 14px; color: var(--ink); }
  .sugchip .sa { font-family: var(--f-mono); font-size: 8px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink-mut); }
  #ai-out { width: 100%; height: 220px; margin: 6px 0 8px; font-family: var(--f-mono); font-size: 11px; color: var(--ink-dim);
            background: var(--paper-0); border: 1px solid var(--rule); padding: 10px; resize: vertical; }

  /* Slots — same card language as the Guide's duo / team cards */
  .team { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; margin: 8px 0 8px; }
  .slot { border: 1px solid var(--rule); background: var(--paper-2); padding: 14px; display: flex; flex-direction: column; gap: 10px; min-height: 236px; position: relative; }
  .slot.empty { border-style: dashed; background: transparent; justify-content: center; align-items: center; }
  .slot-n { font-family: var(--f-mono); font-size: 9px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--ink-mut); margin-bottom: 8px; text-align: center; }
  .slot.empty input { width: 100%; max-width: 240px; }
  input.pick, select.abil, select.mv {
    font-family: var(--f-sans); font-size: 13px; color: var(--ink); background: var(--paper-1);
    border: 1px solid var(--rule); padding: 6px 8px; outline: none; border-radius: 0;
  }
  input.pick:focus, select:focus { border-color: var(--jade-bright); }
  input.pick::placeholder { color: var(--ink-mut); font-style: italic; }
  .slot-x { position: absolute; top: 8px; right: 8px; width: 24px; height: 24px; border: 1px solid transparent; background: none;
            color: var(--ink-mut); cursor: pointer; font-size: 15px; line-height: 1; }
  .slot-x:hover { color: var(--ink); border-color: var(--rule); }
  .duo-mon { display: flex; gap: 10px; align-items: center; }
  .duo-mon > img { width: 64px; height: 64px; image-rendering: pixelated; flex: none; }
  .card-title { font-family: var(--f-serif); font-style: italic; font-size: 20px; color: var(--ink); line-height: 1.05; }
  .duo-types { display: flex; gap: 2px; margin: 4px 0 4px; }
  .tyicon { width: 48px; height: 24px; image-rendering: pixelated; vertical-align: middle; flex: none; }
  .duo-types .tyicon { width: 40px; height: 20px; }
  select.abil { font-family: var(--f-mono); font-size: 10px; color: var(--ink-dim); padding: 2px 4px; background: transparent; }
  .slot-item { display: flex; align-items: center; gap: 6px; }
  .slot-item img { width: 24px; height: 24px; image-rendering: pixelated; flex: none; }
  .slot-item .item-blank { width: 24px; height: 24px; border: 1px dashed var(--rule); flex: none; }
  select.item { flex: 1; min-width: 0; font-family: var(--f-sans); font-size: 12px; color: var(--ink);
                background: var(--paper-1); border: 1px solid var(--rule); padding: 4px 6px; outline: none; }
  select.item.unset { color: var(--ink-mut); font-style: italic; }
  .duo-moves { display: flex; flex-direction: column; gap: 6px; }
  .duo-move { display: grid; grid-template-columns: 40px 1fr auto; column-gap: 8px; align-items: center; }
  .duo-move .tyicon { width: 40px; height: 20px; }
  .duo-move .ty-blank { width: 40px; height: 20px; border: 1px dashed var(--rule); }
  select.mv { width: 100%; min-width: 0; padding: 4px 6px; }
  select.mv.unset { color: var(--ink-mut); font-style: italic; }
  .mv-pow { font-family: var(--f-mono); font-size: 12px; color: var(--ink-dim); text-align: right; white-space: nowrap; min-width: 84px; }
  .mv-how { grid-column: 2 / 4; font-family: var(--f-mono); font-size: 9px; color: var(--ink-mut); letter-spacing: 0.06em; margin-top: 2px; }
  /* Hidden Power — the move's type icon is a button that opens a 16-type picker */
  .hp-pick { position: relative; }
  .hp-btn { display: block; padding: 0; line-height: 0; cursor: pointer; background: none;
            border: 1px dashed var(--rule); }
  .hp-btn.set { border-style: solid; border-color: var(--jade-deep); }
  .hp-btn:hover { border-color: var(--jade-bright); }
  .hp-btn .tyicon { width: 38px; height: 19px; display: block; }
  .hp-menu { position: absolute; z-index: 60; top: calc(100% + 4px); left: 0; width: 240px; padding: 8px;
             background: var(--paper-0); border: 1px solid var(--rule); box-shadow: 0 12px 28px rgba(0,0,0,0.35); }
  .hp-menu .hp-lbl { font-family: var(--f-mono); font-size: 8px; letter-spacing: 0.16em; text-transform: uppercase;
                     color: var(--ink-mut); margin-bottom: 6px; }
  .hp-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 3px; }
  .hp-grid button { padding: 0; line-height: 0; cursor: pointer; background: none; border: 1px solid transparent; }
  .hp-grid button:hover { border-color: var(--jade-bright); }
  .hp-grid button.on { border-color: var(--jade-bright); background: var(--jade-soft); }
  .hp-grid .tyicon { width: 100%; height: auto; display: block; }
  .hp-foot { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: 8px;
             font-family: var(--f-mono); font-size: 9px; color: var(--ink-mut); white-space: nowrap; }
  .hp-clear { font-family: var(--f-mono); font-size: 9px; letter-spacing: 0.1em; text-transform: uppercase;
              padding: 2px 6px; background: none; border: 1px solid var(--rule); color: var(--ink-dim); cursor: pointer; }
  .hp-clear:hover { border-color: var(--jade-bright); color: var(--ink); }
  .stab { font-family: var(--f-mono); font-size: 8px; letter-spacing: 0.12em; color: var(--dusk); border: 1px solid var(--dusk); padding: 0 3px; margin-left: 5px; vertical-align: middle; }

  /* Matchup grids — the Guide's Defensive Duos table */
  .mu-wrap { overflow-x: auto; max-width: 100%; padding-bottom: 4px; }
  table.mu { width: auto; border-collapse: separate; border-spacing: 2px; font-family: var(--f-mono); font-size: 11px; }
  table.mu th { padding: 0; background: none; border: 0; }
  table.mu th .tyicon { width: 32px; height: 16px; display: block; }
  table.mu .mu-name { font-family: var(--f-serif); font-style: italic; font-size: 13px; color: var(--ink); text-transform: none; letter-spacing: 0; text-align: right; padding-right: 8px; white-space: nowrap; font-weight: 400; }
  table.mu .mu-sum { font-family: var(--f-mono); font-style: normal; font-size: 9px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--ink-mut); }
  table.mu tr.sum-first td, table.mu tr.sum-first th { padding-top: 6px; }
  table.mu td { width: 32px; height: 22px; padding: 0; text-align: center; border: 0; border-radius: 3px; background: var(--paper-2); color: var(--ink-mut); cursor: default; }
  table.mu td.weak { background: rgba(232,165,48,0.28); color: var(--ink); }
  table.mu td.res { background: rgba(46,176,112,0.22); color: var(--ink); }
  table.mu td.imm { background: rgba(46,176,112,0.5); color: var(--ink); font-weight: 700; }
  table.mu td.bad { background: rgba(232,165,48,0.5); color: var(--ink); font-weight: 700; }
  table.mu td.none { background: transparent; }
  .flags { display: flex; flex-direction: column; gap: 6px; margin: 12px 0 0; font-size: 13px; color: var(--ink-dim); }
  .flag { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 6px; }
  .flag .lbl { font-family: var(--f-mono); font-size: 9px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--ink-mut); margin-right: 6px; }
  .flag .tyicon { width: 32px; height: 16px; }
  .ok { color: var(--jade-bright); }

  /* Coverage meter + misses — the Guide's duo card footer */
  .meter { display: grid; grid-template-columns: 80px 1fr 72px; gap: 10px; align-items: center; margin: 4px 0 12px; max-width: 760px; }
  .lbl { font-family: var(--f-mono); font-size: 9px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--ink-mut); }
  .bar-track { display: block; height: 12px; background: var(--paper-0); border-radius: 0 4px 4px 0; overflow: hidden; }
  .bar-fill { display: block; height: 100%; background: var(--jade-bright); border-radius: 0 4px 4px 0; transition: width 0.25s; }
  .bar-n { font-family: var(--f-mono); font-size: 12px; color: var(--ink-dim); text-align: right; }
  .opts { display: flex; gap: 16px; align-items: center; margin: 0 0 10px; }
  .opts label { font-family: var(--f-mono); font-size: 10px; color: var(--ink-dim); letter-spacing: 0.08em; display: flex; gap: 6px; align-items: center; cursor: pointer; }
  .opts input { accent-color: var(--jade-bright); }
  .misses { display: flex; flex-wrap: wrap; gap: 0 2px; align-items: center; }
  .monchip { display: inline-flex; align-items: center; font-size: 12px; margin-right: 8px; white-space: nowrap; }
  .monchip img { width: 36px; height: 36px; image-rendering: pixelated; }
  .empty-msg { font-size: 13px; color: var(--ink-mut); font-style: italic; }


  @media (max-width: 700px) {
    /* The shared mobile layout hands scrolling to <body>, but this app keeps body fixed
       (height: 100vh, overflow: hidden) so the tab bar stays put — which left Team Pages
       clipped with no scroller at all. Give the pages view its own, the way #view-builder
       already has one. */
    #view-pages { min-height: 0; }
    #sidebar { max-height: none; min-height: 0; }
    #main { overflow-y: auto; min-height: 0; }
    #page { padding: 28px 16px 48px; }
    h2 { font-size: 40px; }
    .team { grid-template-columns: 1fr; }
    .meter { grid-template-columns: 64px 1fr 64px; }
    .mv-pow { min-width: 0; }
  }
</style>
</head>
<body>
<div id="tabbar">
  <span class="brand">Teams</span>
  <button class="tb active" id="tb-builder" onclick="showView('builder')">Builder</button>
  <button class="tb" id="tb-pages" onclick="showView('pages')">Team Pages</button>
</div>
<div id="views" class="builder">
  <div id="view-builder"><div id="builder">
  <div class="kicker">Team Building · Six Pokémon · Twenty-four moves</div>
  <h2>Team Builder</h2>
  <p class="p">Pick six Pokémon and up to four moves each. Every move a Pokémon can learn is listed: level-up (including its pre-evolutions),
    TM/HM, tutor and egg moves. The grids use the game’s own type chart, and a species only counts as hit
    <b>super effectively</b> if the hit gets through all of its abilities (Levitate, Flash Fire, Volt Absorb, Water Absorb, Thick Fat).</p>
  <div class="toolbar">
    <button class="btn" id="btn-share">Copy share link</button>
    <button class="btn" id="btn-clear">Clear team</button>
    <button class="btn btn-ai" id="btn-ai" data-tip="Copies a short prompt with your team and its weak spots. Paste it into any AI chat for a quick review.">Copy AI review prompt</button>
  </div>
  <textarea id="ai-out" readonly hidden></textarea>
  <datalist id="mon-list"></datalist>
  <div class="team" id="team"></div>
  <div id="analysis"></div>
  </div></div>
  <div id="view-pages">
    <div id="sidebar">
      <div id="sidebar-header">
        <h1>Team Pages</h1>
        <span class="volume">Vol. VI · Coverage · Doubles · Specialists</span>
      </div>
      <div id="page-list"></div>
    </div>
    <div id="main">
      <button id="btn-back" onclick="goBack()">← Return to Contents</button>
      <div id="page"></div>
    </div>
  </div>
</div>

<script>
const PAGES = TEAM_PAGES_PLACEHOLDER;
const SPRITES = TEAM_SPRITES_PLACEHOLDER;
GUIDE_PAGES_JS
const SPECIES = SPECIES_PLACEHOLDER;
const ITEMS = ITEMS_PLACEHOLDER;
const MOVES = MOVES_PLACEHOLDER;
const TYPES = TYPES_PLACEHOLDER;
// Gen 3 has no per-move category: physical vs special follows the move's TYPE.
// This hack swaps two of them — Dark is physical, Ghost is special.
const PHYSICAL = new Set(PHYSICAL_PLACEHOLDER);
// Hidden Power: the 16 types it can roll (never Normal), and per type the highest IVs that
// roll it at 70 power — the Guide's "Hidden Power by IVs" table, from Cmd_hiddenpowercalc.
const HP_TYPES = HP_TYPES_PLACEHOLDER;
const HP_IVS = HP_IVS_PLACEHOLDER;
const HP_STATS = HP_STATS_PLACEHOLDER;
const TYPE_CHART = TYPE_CHART_PLACEHOLDER;
const SPR = SPRITES_PLACEHOLDER;   // species front sprites, by species index

const byKey = {}; SPECIES.forEach((s, i) => byKey[s.k] = i);
const moveByKey = {}; MOVES.forEach((m, i) => moveByKey[m.k] = i);
const HP_IDX = moveByKey['HIDDEN_POWER'];
const itemByKey = {}; ITEMS.forEach((it, i) => itemByKey[it.k] = i);
const byName = {}; SPECIES.forEach((s, i) => byName[s.n.toLowerCase()] = i);
const esc = s => String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
// MYSTERY is the decomp's name for Gen 3's ??? type. Curse is the only move that has it.
const tc = t => t === 'MYSTERY' ? '???' : t[0] + t.slice(1).toLowerCase();
const eff = (atk, types) => types.reduce((n, d) => n * ((TYPE_CHART[atk] || {})[d] ?? 1), 1);
// Abilities that change what hits a Pokémon (Gen 3).
const ABILITY_DEFENSE = {
  LEVITATE:     (atk, m) => atk === 'GROUND' ? 0 : m,
  FLASH_FIRE:   (atk, m) => atk === 'FIRE' ? 0 : m,
  VOLT_ABSORB:  (atk, m) => atk === 'ELECTRIC' ? 0 : m,
  WATER_ABSORB: (atk, m) => atk === 'WATER' ? 0 : m,
  THICK_FAT:    (atk, m) => (atk === 'FIRE' || atk === 'ICE') ? m / 2 : m,
  WONDER_GUARD: (atk, m) => m > 1 ? m : 0,
};

document.getElementById('mon-list').innerHTML = SPECIES.map(s => `<option value="${esc(s.n)}">`).join('');

// team[i] = null | {s: species index, ab: ability index, mv: [move index | -1] x4,
//                    it: item index | -1, hp: Hidden Power's rolled type | ''}
let team = [null, null, null, null, null, null];
let finalOnly = true;   // default: judge coverage against fully evolved species
let hpOpen = null;      // slot whose Hidden Power type picker is open
const HP_SET = new Set(HP_TYPES);
const blankMon = (s, ab) => ({s, ab: ab || 0, mv: [-1, -1, -1, -1], it: -1, hp: ''});

/* ---------- Hidden Power ----------
   Its type is a property of the Pokémon's IVs, not of the move, so it is stored on the
   member and picked by hand. Until it is picked the move stays Normal and counts for
   nothing on the coverage grids, the same as any move that ignores the type chart. */
function mvType(m, x) { return x === HP_IDX && m.hp ? m.hp : MOVES[x].t; }
function mvAtk(m, x) { return x === HP_IDX ? !!m.hp : MOVES[x].atk; }
function mvName(m, x) { return x === HP_IDX && m.hp ? MOVES[x].n + ' ' + tc(m.hp) : MOVES[x].n; }
function hpTip(t) {
  const iv = HP_IVS[t] || [];
  return `<b>Hidden Power ${tc(t)}</b> · 70 power · ${PHYSICAL.has(t) ? 'Physical' : 'Special'}<br>`
       + `Highest IVs · ${HP_STATS.map((n, i) => `${n} <b>${iv[i]}</b>`).join(' · ')}<br>`
       + `<span class='dim'>Odd/even picks the type; the 30s and 31s are what hold the power at 70.</span>`;
}

/* ---------- save / load (localStorage + share hash) ---------- */
function encode() {
  // The Hidden Power field is only written when it is set, so codes without one read as they always did.
  return team.map(m => m ? [SPECIES[m.s].k, m.ab, m.mv.filter(x => x >= 0).map(x => MOVES[x].k).join(','),
                            m.it >= 0 ? ITEMS[m.it].k : ''].concat(m.hp ? [m.hp] : []).join(':') : '').join(';');
}
function decode(str) {
  const out = [null, null, null, null, null, null];
  String(str || '').split(';').slice(0, 6).forEach((part, i) => {
    const [k, ab, mv, item, hp] = part.split(':');   // item and hp are optional: older links are shorter
    if (!(k in byKey)) return;
    const s = byKey[k], learn = new Set(SPECIES[s].m.map(x => x[0]));
    const moves = (mv || '').split(',').map(x => moveByKey[x]).filter(x => x !== undefined && learn.has(x)).slice(0, 4);
    while (moves.length < 4) moves.push(-1);
    const it = itemByKey[item];
    out[i] = {s, ab: Math.min(+ab || 0, SPECIES[s].ab.length - 1), mv: moves, it: it === undefined ? -1 : it,
              hp: HP_SET.has(hp) ? hp : ''};
  });
  return out;
}
const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
                set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
function save() {
  const code = encode();
  store.set('el.team', code);
  try { if (!EMBEDDED) history.replaceState(null, '', team.some(Boolean) ? '#' + encodeURIComponent(code) : location.pathname); } catch (e) {}
}

/* ---------- slots ---------- */
function learnOf(s) { return SPECIES[s].m; }
function moveOptions(m, slot) {
  const learn = learnOf(m.s);
  const taken = new Set(m.mv.filter((x, j) => j !== slot && x >= 0));
  const opt = ([i]) => {
    const mv = MOVES[i];
    const pow = i === HP_IDX ? (m.hp ? ' 70' : ' —') : mv.p === 0 ? '' : ' ' + (mv.atk && mv.p > 1 ? mv.p : '—');
    return `<option value="${i}"${m.mv[slot] === i ? ' selected' : ''}${taken.has(i) ? ' disabled' : ''}>${esc(mv.n)} · ${tc(mvType(m, i))}${pow}</option>`;
  };
  const byName = (a, b) => MOVES[a[0]].n.localeCompare(MOVES[b[0]].n);
  // Official Gen 3 categories. Status is "deals no damage"; everything else splits on type,
  // so Seismic Toss is Physical (Fighting) and Night Shade is Special (Ghost, per the swap).
  // Hidden Power splits on the type it rolled, so it changes group once that is picked.
  const cat = i => MOVES[i].p === 0 ? 2 : PHYSICAL.has(mvType(m, i)) ? 0 : 1;
  const g = k => learn.filter(([i]) => cat(i) === k).sort(byName).map(opt).join('');
  const group = (label, k) => { const h = g(k); return h ? `<optgroup label="${label}">${h}</optgroup>` : ''; };
  return `<option value="-1">— move ${slot + 1} —</option>
    ${group('Physical', 0)}${group('Special', 1)}${group('Status', 2)}`;
}
function renderSlot(m, i) {
  if (!m) return `<div class="slot empty"><div><div class="slot-n">Slot ${i + 1}</div>
    <input class="pick" list="mon-list" placeholder="Add a Pokémon…" data-slot="${i}" autocomplete="off"></div></div>`;
  const s = SPECIES[m.s];
  const how = Object.fromEntries(s.m);
  const abil = s.ab.length > 1
    ? `<select class="abil" data-slot="${i}" title="Ability">${s.ab.map((a, j) => `<option value="${j}"${j === m.ab ? ' selected' : ''}>${esc(a[1])}</option>`).join('')}</select>`
    : `<span class="dim">${esc(s.ab[0] ? s.ab[0][1] : '')}</span>`;
  const item = m.it >= 0 ? ITEMS[m.it] : null;
  const itemPick = `<div class="slot-item">${item ? `<img src="${item.icon}" alt="">` : '<span class="item-blank"></span>'}
    <select class="item${item ? '' : ' unset'}" data-slot="${i}" title="Held item">
      <option value="-1">— no item —</option>
      ${ITEMS.map((it, j) => `<option value="${j}"${j === m.it ? ' selected' : ''}>${esc(it.n)}</option>`).join('')}
    </select></div>`;
  const rows = m.mv.map((x, j) => {
    const mv = x >= 0 ? MOVES[x] : null;
    const t = mv ? mvType(m, x) : null;
    const stab = mv && mvAtk(m, x) && s.t.includes(t);
    const pow = !mv ? '' : x === HP_IDX ? (m.hp ? 70 : 'varies') : mv.p > 0 ? (mv.p > 1 ? mv.p : 'varies') : '';
    return `<div class="duo-move">
      ${!mv ? '<span class="ty-blank"></span>' : x === HP_IDX ? hpPicker(m, i) : tyIcon(t)}
      <select class="mv${mv ? '' : ' unset'}" data-slot="${i}" data-j="${j}">${moveOptions(m, j)}</select>
      <span class="mv-pow">${pow}${stab ? '<span class="stab">STAB</span>' : ''}</span>
      ${mv ? `<span class="mv-how">${esc(how[x] || '')}</span>` : ''}
    </div>`;
  }).join('');
  return `<div class="slot">
    <button class="slot-x" data-remove="${i}" title="Remove">×</button>
    <div class="duo-mon"><img src="${SPR[m.s]}" alt="${esc(s.n)}"><div>
      <div class="card-title"><a class="xl" data-app="pokedex" data-key="${s.dex}">${esc(s.n)}</a></div>
      <div class="duo-types">${s.t.map(tyIcon).join('')}</div>${abil}</div></div>
    ${itemPick}
    <div class="duo-moves">${rows}</div>
  </div>`;
}

// The Hidden Power type icon doubles as its picker: click it for the 16 types, hover any of
// them for the IV spread that rolls it (the Guide's table, recomputed here).
function hpPicker(m, i) {
  const tip = m.hp ? hpTip(m.hp)
    : `<b>Hidden Power</b> reads its type off the Pokémon's IVs, so it shows as Normal until you say `
      + `which one you have.<br>Click to pick it — it then counts on the coverage grids.`;
  const menu = hpOpen !== i ? '' : `<div class="hp-menu">
      <div class="hp-lbl">Hidden Power type · hover for IVs</div>
      <div class="hp-grid">${HP_TYPES.map(t =>
        `<button class="${m.hp === t ? 'on' : ''}" data-hp-set="${i}" data-hp-t="${t}" data-tip="${hpTip(t)}">${tyIcon(t)}</button>`).join('')}</div>
      <div class="hp-foot"><a class="xl" data-app="guide" data-key="hp-ivs">The full IV table</a>
        ${m.hp ? `<button class="hp-clear" data-hp-set="${i}" data-hp-t="">Clear</button>` : '<span>Never Normal</span>'}</div>
    </div>`;
  return `<span class="hp-pick"><button class="hp-btn${m.hp ? ' set' : ''}" data-hp-open="${i}"
    data-tip="${tip}">${tyIcon(mvType(m, HP_IDX))}</button>${menu}</span>`;
}

/* ---------- analysis ---------- */
function defenseRow(m) {
  const s = SPECIES[m.s], ab = s.ab[m.ab] && ABILITY_DEFENSE[s.ab[m.ab][0]];
  return TYPES.map(t => { const x = eff(t, s.t); return ab ? ab(t, x) : x; });
}
function attackTypes(m) { return [...new Set(m.mv.filter(x => x >= 0 && mvAtk(m, x)).map(x => mvType(m, x)))]; }
function offenseRow(m) {
  const ts = attackTypes(m);
  return TYPES.map(d => ts.length ? Math.max(...ts.map(a => eff(a, [d]))) : null);
}
const lab = x => x === null ? '' : x === 0 ? '0' : x >= 4 ? '4×' : x >= 2 ? '2×' : x <= 0.25 ? '¼' : x <= 0.5 ? '½' : '';
function table(head, rows) {
  return `<div class="mu-wrap"><table class="mu"><thead><tr><th></th>${head.map(t => `<th>${tyIcon(t)}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`;
}

// Numbers shared by the page and the AI prompt.
function summarize(members, final) {
  const def = members.map(defenseRow);
  const weakN = TYPES.map((_, j) => def.filter(r => r[j] > 1).length);
  const resN = TYPES.map((_, j) => def.filter(r => r[j] < 1).length);
  const off = members.map(offenseRow);
  const teamOff = TYPES.map((_, j) => { const v = off.map(r => r[j]).filter(x => x !== null); return v.length ? Math.max(...v) : null; });
  const atkTypes = new Set(members.flatMap(attackTypes));
  const mask = TYPES.reduce((n, t, i) => atkTypes.has(t) ? n | (1 << i) : n, 0);
  const pool = SPECIES.filter(s => s.se && (!final || s.f));
  const missed = pool.filter(s => !(s.se & mask));
  return {
    def, weakN, resN, off, teamOff, pool, missed,
    unresisted: TYPES.filter((t, j) => weakN[j] > 0 && resN[j] === 0),
    stacked: TYPES.filter((t, j) => weakN[j] >= 3),
    noSE: TYPES.filter((t, j) => !(teamOff[j] > 1)),
    never: SPECIES.filter(s => !s.se && (!final || s.f)),
  };
}

/* ---------- suggestions: who plugs the gaps ----------
   Shown only once there are 2+ members (with one, every weakness is unresisted, so the
   list is noise) and a free slot to put them in. These rank on the type chart alone —
   they know nothing about Speed, movepool quality or role. */
const SUGGEST_MIN = 2, SUGGEST_MAX = 6;

// Same maths as defenseRow, but for a species + ability we are considering rather than a member.
function defRowFor(s, abIdx) {
  const ab = s.ab[abIdx] && ABILITY_DEFENSE[s.ab[abIdx][0]];
  return TYPES.map(t => { const x = eff(t, s.t); return ab ? ab(t, x) : x; });
}
function suggestPool(members) {
  // Legendaries are left out: they top both lists on raw stats and are not a real answer to
  // a type gap. They stay pickable in the builder itself, they are just not suggested.
  const onTeam = new Set(members.map(m => m.s));
  return SPECIES.map((s, si) => ({s, si})).filter(({s, si}) => !onTeam.has(si) && !s.lg && (!finalOnly || s.f));
}
function suggestDefense(S, members, n) {
  const gaps = S.unresisted.map(t => TYPES.indexOf(t));
  if (!gaps.length) return [];
  const out = [];
  for (const {s, si} of suggestPool(members)) {
    let best = null;
    s.ab.forEach((a, ai) => {
      // Wonder Guard "resists" almost everything on 1 HP. It would top every list and mean nothing.
      if (a[0] === 'WONDER_GUARD') return;
      const row = defRowFor(s, ai);
      const gain = gaps.reduce((t, j) => t + (row[j] === 0 ? 2 : row[j] < 1 ? 1 : 0), 0);
      if (!gain) return;
      // A weakness the team neither resists nor already has is a brand-new hole; charge for it.
      const cost = TYPES.reduce((t, _, j) => t + (row[j] > 1 && S.resN[j] === 0 && S.weakN[j] === 0 ? 1 : 0), 0);
      if (!best || gain - cost > best.score) best = {score: gain - cost, gain, cost, ai, row};
    });
    if (best && best.score > 0) out.push({s, si, ...best});
  }
  out.sort((a, b) => b.score - a.score || b.s.b - a.s.b || a.s.n.localeCompare(b.s.n));
  return out.slice(0, n);
}
function suggestOffense(S, members, n) {
  const gaps = S.noSE.map(t => TYPES.indexOf(t));
  // With no attacking move chosen anywhere, all 17 types read as gaps — that is the team being
  // blank, not a coverage hole, and ranking against it just lists the game's bulkiest species.
  if (!gaps.length || !members.some(m => attackTypes(m).length)) return [];
  const out = [];
  for (const {s, si} of suggestPool(members)) {
    const atk = TYPES.filter((t, i) => s.at >> i & 1);
    if (!atk.length) continue;
    const covers = gaps.filter(j => atk.some(a => eff(a, [TYPES[j]]) > 1));
    if (covers.length) out.push({s, si, gain: covers.length, covers});
  }
  out.sort((a, b) => b.gain - a.gain || b.s.o - a.s.o || a.s.n.localeCompare(b.s.n));
  return out.slice(0, n);
}
function firstEmptySlot() { return team.indexOf(null); }

function renderAnalysis() {
  const members = team.filter(Boolean);
  const el = document.getElementById('analysis');
  if (!members.length) {
    el.innerHTML = `<div class="section-title">Team Analysis</div><p class="empty-msg">Add a Pokémon to see the type charts and what your moves can hit.</p>`;
    return;
  }
  const name = m => esc(SPECIES[m.s].n);

  // Defense — what hits each member
  const S = summarize(members, finalOnly);
  const {def, weakN, resN, off, teamOff, pool, missed, unresisted, stacked, noSE, never} = S;
  const hit = pool.length - missed.length;
  const dCls = x => x === 0 ? 'imm' : x > 1 ? 'weak' : x < 1 ? 'res' : '';
  const dWord = x => x === 0 ? 'immune' : x > 1 ? `weak (${lab(x)})` : x < 1 ? `resists (${lab(x)})` : 'neutral';
  const defRows = members.map((m, i) => `<tr><th class="mu-name">${name(m)}</th>${def[i].map((x, j) =>
      `<td class="${dCls(x)}" data-tip="<b>${name(m)}</b> vs ${tc(TYPES[j])}: ${dWord(x)}">${lab(x)}</td>`).join('')}</tr>`).join('')
    + `<tr class="sum-first"><th class="mu-name mu-sum">Weak</th>${weakN.map((n, j) =>
      `<td class="${n ? (n > resN[j] ? 'bad' : 'weak') : 'none'}" data-tip="${n} weak to ${tc(TYPES[j])}, ${resN[j]} resist or immune">${n || ''}</td>`).join('')}</tr>`
    + `<tr><th class="mu-name mu-sum">Resist</th>${resN.map((n, j) =>
      `<td class="${n ? 'res' : 'none'}" data-tip="${n} resist or immune to ${tc(TYPES[j])}">${n || ''}</td>`).join('')}</tr>`;

  // Offense — what each member's attacks hit, per defending type
  const oCls = x => x === null ? 'none' : x === 0 ? 'bad' : x > 1 ? 'imm' : x < 1 ? 'weak' : '';
  const oWord = x => x === null ? 'no attacking moves' : x === 0 ? 'no effect' : x > 1 ? 'super effective' : x < 1 ? 'not very effective' : 'neutral';
  const offRows = members.map((m, i) => `<tr><th class="mu-name">${name(m)}</th>${off[i].map((x, j) =>
      `<td class="${oCls(x)}" data-tip="<b>${name(m)}</b>’s best hit on ${tc(TYPES[j])}: ${oWord(x)}">${lab(x)}</td>`).join('')}</tr>`).join('')
    + `<tr class="sum-first"><th class="mu-name mu-sum">Team</th>${teamOff.map((x, j) =>
      `<td class="${oCls(x)}" data-tip="Team’s best hit on ${tc(TYPES[j])}: ${oWord(x)}">${lab(x)}</td>`).join('')}</tr>`;

  // Suggestions — only with 2+ members (one member makes every weakness a "gap") and a free slot.
  const canSuggest = members.length >= SUGGEST_MIN && firstEmptySlot() >= 0;
  const sugChip = (x, tip, sub) => `<span class="sugchip" data-tip="${tip}" data-add="${x.si}" data-ab="${x.ai || 0}">
      <img src="${SPR[x.si]}" alt=""><span class="sn">${esc(x.s.n)}</span>${sub ? `<span class="sa">${esc(sub)}</span>` : ''}</span>`;
  const defSug = canSuggest ? suggestDefense(S, members, SUGGEST_MAX) : [];
  const offSug = canSuggest ? suggestOffense(S, members, SUGGEST_MAX) : [];
  const plugs = x => x.row.map((v, j) => unresisted.includes(TYPES[j]) && v < 1 ? tc(TYPES[j]) + (v === 0 ? ' (immune)' : '') : null).filter(Boolean);
  const defSugHtml = defSug.length ? `<div class="sugs">
      <div class="sug-lbl">Resists what your team doesn\u2019t \u00b7 click to add</div>
      ${defSug.map(x => sugChip(x, `<b>${esc(x.s.n)}</b> handles ${plugs(x).join(', ')}${x.cost ? `<br>Adds a new weakness nothing else resists` : ''}`,
                                ABILITY_DEFENSE[x.s.ab[x.ai][0]] ? x.s.ab[x.ai][1] : '')).join('')}</div>` : '';
  const offSugHtml = offSug.length ? `<div class="sugs">
      <div class="sug-lbl">Can learn moves for the gaps \u00b7 click to add</div>
      ${offSug.map(x => sugChip(x, `<b>${esc(x.s.n)}</b> can learn moves that hit ${x.covers.map(j => tc(TYPES[j])).join(', ')}`, '')).join('')}</div>` : '';

  // Species coverage
  const monChip = s => `<span class="monchip" data-tip="${esc(s.n)} · ${s.t.map(tc).join(' / ')}"><img src="${SPR[byKey[s.k]]}" alt=""><a class="xl" data-app="pokedex" data-key="${s.dex}">${esc(s.n)}</a></span>`;

  el.innerHTML = `
    <div class="section-title">Defensive Chart</div>
    <p class="p">Damage each team member takes from every attacking type, with the ability picked on its card.</p>
    ${table(TYPES, defRows)}
    <div class="flags">
      <div class="flag"><span class="lbl">No resist</span>${unresisted.length ? unresisted.map(tyIcon).join('') : '<span class="ok">Every weakness is covered by a teammate.</span>'}</div>
      ${stacked.length ? `<div class="flag"><span class="lbl">3+ weak</span>${stacked.map(tyIcon).join('')}</div>` : ''}
    </div>
    ${defSugHtml}

    <div class="section-title">Offensive Coverage</div>
    <p class="p">The best hit each member’s attacks land on every single type. Status moves and moves that ignore the type chart
      (Seismic Toss, Night Shade, fixed-damage moves) don’t count. <b>Hidden Power</b> counts as soon as you click its
      type icon and say what it rolled — hover the types there for the IVs that get you each one.</p>
    ${table(TYPES, offRows)}
    <div class="flags">
      <div class="flag"><span class="lbl">No 2× hit on</span>${noSE.length ? noSE.map(tyIcon).join('') : '<span class="ok">Every type is hit super effectively.</span>'}</div>
    </div>
    ${offSugHtml}

    <div class="section-title">Pokémon You Can’t Hit Super Effectively</div>
    <div class="opts"><label><input type="checkbox" id="final-only"${finalOnly ? ' checked' : ''}> Fully evolved only</label></div>
    <div class="meter" data-tip="${hit} of ${pool.length} species hit super effectively">
      <span class="lbl">Coverage</span><span class="bar-track"><span class="bar-fill" style="width:${(100 * hit / pool.length).toFixed(2)}%"></span></span>
      <span class="bar-n">${hit}/${pool.length}</span></div>
    <div class="misses">${missed.length ? `<span class="lbl" style="margin-right:10px">Misses · ${missed.length}</span>` + missed.map(monChip).join('')
      : '<span class="ok">Your moves hit every species super effectively.</span>'}</div>
    ${never.length ? `<p class="p" style="margin-top:14px;font-size:13px">Not counted, because no type hits ${never.length > 1 ? 'them' : 'it'} super effectively in Gen 3:</p>
      <div class="misses">${never.map(monChip).join('')}</div>` : ''}
  `;
}

function render() {
  document.getElementById('team').innerHTML = team.map(renderSlot).join('');
  renderAnalysis();
}

/* ---------- events ---------- */
function findSpecies(value) {
  const v = value.trim().toLowerCase();
  if (!v) return undefined;
  if (byName[v] !== undefined) return byName[v];
  const i = SPECIES.findIndex(s => s.n.toLowerCase().startsWith(v));
  return i >= 0 ? i : undefined;
}
function pickSpecies(i, value) {
  const s = findSpecies(value);
  if (s === undefined) return false;
  team[i] = blankMon(s);
  save(); render();
  return true;
}
document.addEventListener('change', e => {
  const t = e.target;
  hpOpen = null;
  if (t.matches('input.pick')) pickSpecies(+t.dataset.slot, t.value);
  else if (t.matches('select.abil')) { team[+t.dataset.slot].ab = +t.value; save(); render(); }
  else if (t.matches('select.mv')) { team[+t.dataset.slot].mv[+t.dataset.j] = +t.value; save(); render(); }
  else if (t.matches('select.item')) { team[+t.dataset.slot].it = +t.value; save(); render(); }
  else if (t.id === 'final-only') { finalOnly = t.checked; store.set('el.team.final', finalOnly ? '1' : '0'); renderAnalysis(); }
});
// Datalist picks fire 'input' before 'change' in some browsers — accept an exact name right away.
document.addEventListener('input', e => {
  if (e.target.matches('input.pick') && byName[e.target.value.trim().toLowerCase()] !== undefined) pickSpecies(+e.target.dataset.slot, e.target.value);
});
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && e.target.matches('input.pick')) pickSpecies(+e.target.dataset.slot, e.target.value);
  else if (e.key === 'Escape' && hpOpen !== null) { hpOpen = null; render(); }
});
document.addEventListener('click', e => {
  const x = e.target.closest('[data-remove]');
  if (x) { team[+x.dataset.remove] = null; hpOpen = null; save(); render(); return; }
  const hset = e.target.closest('[data-hp-set]');
  if (hset) { team[+hset.dataset.hpSet].hp = hset.dataset.hpT; hpOpen = null; save(); render(); return; }
  const hopen = e.target.closest('[data-hp-open]');
  if (hopen) { hpOpen = hpOpen === +hopen.dataset.hpOpen ? null : +hopen.dataset.hpOpen; render(); return; }
  if (hpOpen !== null && !e.target.closest('.hp-menu')) { hpOpen = null; render(); }
  const add = e.target.closest('[data-add]');
  if (add) {
    const slot = firstEmptySlot();
    if (slot < 0) return;
    team[slot] = blankMon(+add.dataset.add, +add.dataset.ab || 0);
    save(); render();
  }
});
document.getElementById('btn-clear').onclick = () => { team = [null, null, null, null, null, null]; save(); render(); };
document.getElementById('btn-share').onclick = async e => {
  const code = encodeURIComponent(encode());
  let url;
  try { url = EMBEDDED ? parent.location.href.split('#')[0] + '#teambuilder/' + code : location.href.split('#')[0] + '#' + code; }
  catch (err) { url = location.href.split('#')[0] + '#' + code; }
  const btn = e.currentTarget;
  try { await navigator.clipboard.writeText(url); btn.textContent = 'Link copied'; }
  catch (err) { window.prompt('Copy this link:', url); }
  btn.classList.add('done');
  setTimeout(() => { btn.textContent = 'Copy share link'; btn.classList.remove('done'); }, 1600);
};

/* ---------- AI review prompt (kept short: it costs tokens both ways) ---------- */
function buildPrompt() {
  const members = team.filter(Boolean);
  const S = summarize(members, true);
  const list = (ts, none) => ts.length ? ts.map(tc).join(', ') : none;
  const lines = members.map((m, i) => {
    const s = SPECIES[m.s];
    const mv = m.mv.filter(x => x >= 0).map(x => mvName(m, x));
    const item = m.it >= 0 ? ITEMS[m.it].n : 'no item';
    return `${i + 1}. ${s.n} | ${s.t.map(tc).join('/')} | ${s.ab[m.ab] ? s.ab[m.ab][1] : '-'} | ${item} | ${mv.length ? mv.join(', ') : 'no moves set'}`;
  });
  // Spread moves that also hit the partner (Earthquake, Explosion…) and who is safe from them.
  const allyHits = members.flatMap((m, i) => m.mv.filter(x => x >= 0 && MOVES[x].ally && MOVES[x].atk).map(x => {
    const safe = members.filter((o, j) => j !== i && S.def[j][TYPES.indexOf(MOVES[x].t)] === 0).map(o => SPECIES[o.s].n);
    return `${SPECIES[m.s].n}'s ${MOVES[x].n} (immune partners: ${safe.join(', ') || 'none'})`;
  }));
  const CAP = 40;
  const miss = S.missed.map(s => s.n);
  const out = [
    'Review my Pokémon team. Be concise.',
    'Game: a modded Pokémon Emerald, Gen 3 mechanics: physical/special is decided by move type, and this mod swaps two of them — Dark is physical, Ghost is special. No Fairy type. Gen 3 abilities. Rosters and learnsets differ from vanilla. Main format: double battles.',
    '',
    'Team (Pokémon | type | ability | held item | moves):',
    ...lines,
    members.length < 6 ? `Empty slots: ${6 - members.length}` : null,
    '',
    'Computed from the game type chart (ability-aware):',
    `- Weak with no teammate resisting: ${list(S.unresisted, 'none')}`,
    S.stacked.length ? `- 3+ members weak to: ${list(S.stacked)}` : null,
    `- No super-effective attack vs: ${list(S.noSE, 'none')}`,
    `- Fully evolved species not hit super effectively (${S.missed.length}/${S.pool.length}): ${miss.slice(0, CAP).join(', ') || 'none'}${miss.length > CAP ? `, +${miss.length - CAP} more` : ''}`,
    allyHits.length ? `- Moves that also hit my partner: ${allyHits.join('; ')}` : null,
    '',
    'Reply in under 300 words, no preamble, bullets only:',
    '1) Top 3 problems, one line each.',
    '2) Up to 3 concrete fixes (Move → Move, or Pokémon → Pokémon), one-line reason each. Gen 3 only; mark any move you are unsure the Pokémon can learn with (?).',
    '3) One doubles tip for this team.',
  ];
  return out.filter(l => l !== null).join('\\n');
}
document.getElementById('btn-ai').onclick = async e => {
  const btn = e.currentTarget, box = document.getElementById('ai-out');
  if (!team.some(Boolean)) { btn.textContent = 'Add a Pokémon first'; setTimeout(() => btn.textContent = 'Copy AI review prompt', 1600); return; }
  const text = buildPrompt();
  box.value = text;
  try { await navigator.clipboard.writeText(text); box.hidden = true; btn.textContent = 'Prompt copied'; btn.classList.add('done'); }
  catch (err) { box.hidden = false; box.focus(); box.select(); btn.textContent = 'Copy the text below'; }
  setTimeout(() => { btn.textContent = 'Copy AI review prompt'; btn.classList.remove('done'); }, 1800);
};

// The tooltip (#tip) and its mousemove handler come from the shared page renderer.

// Ticked unless this viewer turned it off before ('' is the old off value).
const savedFinal = store.get('el.team.final');
finalOnly = savedFinal === null ? true : savedFinal === '1';
team = decode(store.get('el.team'));
render();
function showView(v) {
  document.getElementById('views').className = v;
  document.getElementById('tb-builder').classList.toggle('active', v === 'builder');
  document.getElementById('tb-pages').classList.toggle('active', v === 'pages');
}
// Species sprites already live in the builder's own list, so the pages reuse them
// instead of baking a second copy into this file.
function spriteFallback(ref) {
  const m = /^mon:(\w+)$/.exec(ref || '');
  return m && byKey[m[1]] !== undefined ? SPR[byKey[m[1]]] : '';
}
// "Open in Builder" on every hand-picked team: encode its members as a builder team code.
function teamCode(members) {
  return members.slice(0, 6).map(x => {
    const s = SPECIES[byKey[x.sp]];
    const ab = s ? Math.max(0, s.ab.findIndex(a => a[0] === x.abil)) : 0;
    return `${x.sp}:${ab}:${(x.mvkeys || []).join(',')}:${(x.item && x.item.key) || ''}`;
  }).join(';');
}
function teamBlockExtra(b) {
  if (!b.members || !b.members.length || !b.members[0].mvkeys) return '';
  return `<div class="open-builder"><button class="btn" onclick="openInBuilder('${teamCode(b.members)}')">Open in Builder →</button></div>`;
}
function openInBuilder(code) {
  team = decode(code);
  save();
  render();
  showView('builder');
  document.getElementById('view-builder').scrollTop = 0;
}

renderList();
registerApp('teambuilder', key => {
  if (PAGES.some(p => p.id === key)) { showView('pages'); selectPage(key); return; }
  showView('builder'); team = decode(key); save(); render();
});
</script>
</body>
</html>
'''


def team_pages():
    """The battling pages (Team Building, Double Battles, Stat Specialists), split off the Guide.
    Species sprites are dropped: the builder's own sprite list already holds them (spriteFallback)."""
    with contextlib.redirect_stdout(io.StringIO()):
        _, (pages, sprites) = gdx.split_pages(*gdx.build_data())
    keys = {s['k'] for s in build_data()[0]}
    sprites = {k: v for k, v in sprites.items() if not (k.startswith('mon:') and k.split(':', 1)[1] in keys)}
    return pages, sprites


def generate():
    species, moves = build_data()
    items = hold_items()
    sprites = [pdx.load_sprite_b64(pdx.FORM_FOLDER.get(s['k']) or pdx.species_folder(s['k'])) for s in species]
    chart = {}
    for (a, d), m in cov.load()['chart'].items():
        chart.setdefault(a, {})[d] = m
    dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    pages, page_sprites = team_pages()
    tpl = HTML_TEMPLATE.replace('GUIDE_PAGES_CSS\n', guide_pages.CSS).replace('GUIDE_PAGES_JS', guide_pages.JS)
    html = site_shared.inject(tpl)
    for ph, val in [('TEAM_PAGES_PLACEHOLDER', pages), ('TEAM_SPRITES_PLACEHOLDER', page_sprites),
                    ('ITEMS_PLACEHOLDER', items), ('SPECIES_PLACEHOLDER', species), ('MOVES_PLACEHOLDER', moves), ('TYPES_PLACEHOLDER', cov.TYPES),
                    ('TYPE_CHART_PLACEHOLDER', chart), ('SPRITES_PLACEHOLDER', sprites),
                    ('PHYSICAL_PLACEHOLDER', sorted(cov.PHYSICAL)),
                    ('HP_TYPES_PLACEHOLDER', gdx.HP_TYPE_ORDER),
                    ('HP_IVS_PLACEHOLDER', gdx.hidden_power_rows()),
                    ('HP_STATS_PLACEHOLDER', gdx.HP_STATS),
                    ]:
        html = html.replace(ph, dump(val), 1)
    out = os.path.join(BASE, 'docs', 'teambuilder.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    missing = [s['k'] for s, sp in zip(species, sprites) if not sp]
    if missing:
        print(f'  WARNING: missing sprites for {missing}')
    print(f'Generated: {out} ({os.path.getsize(out) / 1024:.0f} KB, {len(species)} species, '
          f'{len(moves)} moves, {len(items)} items, {len(pages)} team pages)')


if __name__ == '__main__':
    generate()
