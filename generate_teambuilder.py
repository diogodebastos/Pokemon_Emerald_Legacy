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
import json
import contextlib

import coverage_data as cov
import generate_pokedex as pdx
import site_shared
from site_shared import BASE

# Moves whose damage ignores the type chart (or whose type varies): they never count as
# a super-effective hit.
NO_TYPE_DAMAGE = {'EFFECT_HIDDEN_POWER', 'EFFECT_LEVEL_DAMAGE', 'EFFECT_DRAGON_RAGE', 'EFFECT_SONICBOOM',
                  'EFFECT_SUPER_FANG', 'EFFECT_PSYWAVE', 'EFFECT_COUNTER', 'EFFECT_MIRROR_COAT',
                  'EFFECT_ENDEAVOR', 'EFFECT_BIDE', 'EFFECT_OHKO'}


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
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { background: var(--paper-1); }
  body {
    font-family: var(--f-sans); color: var(--ink); font-size: 14px; letter-spacing: 0.005em;
    -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; min-height: 100vh;
    background: radial-gradient(1000px 500px at 100% -100px, rgba(46,176,112,0.05), transparent 55%), var(--paper-1);
  }
  #page { max-width: 1100px; margin: 0 auto; padding: 48px 56px 64px; }
  .kicker {
    font-family: var(--f-mono); font-size: 10px; color: var(--jade-bright);
    letter-spacing: 0.26em; text-transform: uppercase; margin-bottom: 10px;
    display: flex; align-items: center; gap: 10px;
  }
  .kicker::after { content: ""; flex: 1; height: 1px; background: var(--rule); }
  h2 {
    font-family: var(--f-serif); font-variation-settings: "opsz" 144, "SOFT" 60, "WONK" 1;
    font-weight: 400; font-style: italic; font-size: 56px; line-height: 0.95; color: var(--ink);
    letter-spacing: -0.03em; margin-bottom: 20px;
  }
  .p { font-size: 15px; line-height: 1.7; color: var(--ink-dim); margin: 0 0 16px; max-width: 76ch; }
  .p b { color: var(--ink); font-weight: 600; }
  .section-title {
    font-family: var(--f-mono); font-size: 10px; color: var(--jade-bright); letter-spacing: 0.3em;
    text-transform: uppercase; margin-bottom: 14px; margin-top: 36px; display: flex;
    align-items: center; gap: 12px; font-weight: 500;
  }
  .section-title::before { content: "§"; color: var(--ink-mut); font-weight: 400; font-size: 13px; }
  .section-title::after { content: ""; flex: 1; height: 1px; background: var(--rule); }
  .dim { font-family: var(--f-mono); font-size: 10px; color: var(--ink-mut); }

  .toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 4px 0 8px; }
  .btn { font-family: var(--f-mono); font-size: 9px; padding: 6px 12px; letter-spacing: 0.14em; text-transform: uppercase;
         border: 1px solid var(--rule); background: transparent; color: var(--ink-dim); cursor: pointer; }
  .btn:hover { border-color: var(--jade-bright); color: var(--ink); }
  .btn.done { border-color: var(--jade-bright); color: var(--jade-bright); }
  .btn-ai { border-color: var(--jade-deep); color: var(--jade-bright); }
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
  .duo-moves { display: flex; flex-direction: column; gap: 6px; }
  .duo-move { display: grid; grid-template-columns: 40px 1fr auto; column-gap: 8px; align-items: center; }
  .duo-move .tyicon { width: 40px; height: 20px; }
  .duo-move .ty-blank { width: 40px; height: 20px; border: 1px dashed var(--rule); }
  select.mv { width: 100%; min-width: 0; padding: 4px 6px; }
  select.mv.unset { color: var(--ink-mut); font-style: italic; }
  .mv-pow { font-family: var(--f-mono); font-size: 12px; color: var(--ink-dim); text-align: right; white-space: nowrap; min-width: 84px; }
  .mv-how { grid-column: 2 / 4; font-family: var(--f-mono); font-size: 9px; color: var(--ink-mut); letter-spacing: 0.06em; margin-top: 2px; }
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

  #tip { position: fixed; z-index: 10000; display: none; pointer-events: none; max-width: 280px; padding: 6px 10px;
         background: var(--paper-0); border: 1px solid var(--rule); color: var(--ink-dim); font-size: 12px; line-height: 1.45; }
  #tip b { color: var(--ink); }

  @media (max-width: 700px) {
    #page { padding: 28px 16px 48px; }
    h2 { font-size: 40px; }
    .team { grid-template-columns: 1fr; }
    .meter { grid-template-columns: 64px 1fr 64px; }
    .mv-pow { min-width: 0; }
  }
</style>
</head>
<body>
<div id="page">
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
</div>
<div id="tip"></div>

<script>
const SPECIES = SPECIES_PLACEHOLDER;
const MOVES = MOVES_PLACEHOLDER;
const TYPES = TYPES_PLACEHOLDER;
const TYPE_CHART = TYPE_CHART_PLACEHOLDER;
const TYPE_ICONS = TYPE_ICONS_PLACEHOLDER;
const SPRITES = SPRITES_PLACEHOLDER;

const byKey = {}; SPECIES.forEach((s, i) => byKey[s.k] = i);
const moveByKey = {}; MOVES.forEach((m, i) => moveByKey[m.k] = i);
const byName = {}; SPECIES.forEach((s, i) => byName[s.n.toLowerCase()] = i);
const esc = s => String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
const tc = t => t[0] + t.slice(1).toLowerCase();
const tyIcon = t => `<img class="tyicon" src="${TYPE_ICONS[t]}" alt="${t}" title="${tc(t)}">`;
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

// team[i] = null | {s: species index, ab: ability index, mv: [move index | -1] x4}
let team = [null, null, null, null, null, null];
let finalOnly = false;

/* ---------- save / load (localStorage + share hash) ---------- */
function encode() {
  return team.map(m => m ? [SPECIES[m.s].k, m.ab, m.mv.filter(x => x >= 0).map(x => MOVES[x].k).join(',')].join(':') : '').join(';');
}
function decode(str) {
  const out = [null, null, null, null, null, null];
  String(str || '').split(';').slice(0, 6).forEach((part, i) => {
    const [k, ab, mv] = part.split(':');
    if (!(k in byKey)) return;
    const s = byKey[k], learn = new Set(SPECIES[s].m.map(x => x[0]));
    const moves = (mv || '').split(',').map(x => moveByKey[x]).filter(x => x !== undefined && learn.has(x)).slice(0, 4);
    while (moves.length < 4) moves.push(-1);
    out[i] = {s, ab: Math.min(+ab || 0, SPECIES[s].ab.length - 1), mv: moves};
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
    return `<option value="${i}"${m.mv[slot] === i ? ' selected' : ''}${taken.has(i) ? ' disabled' : ''}>${esc(mv.n)}${mv.atk ? ' · ' + tc(mv.t) + ' ' + (mv.p > 1 ? mv.p : '—') : ''}</option>`;
  };
  const atk = learn.filter(([i]) => MOVES[i].atk).sort((a, b) => MOVES[b[0]].p - MOVES[a[0]].p || MOVES[a[0]].n.localeCompare(MOVES[b[0]].n));
  const other = learn.filter(([i]) => !MOVES[i].atk);
  return `<option value="-1">— move ${slot + 1} —</option>
    <optgroup label="Attacks (by power)">${atk.map(opt).join('')}</optgroup>
    <optgroup label="Other moves">${other.map(opt).join('')}</optgroup>`;
}
function renderSlot(m, i) {
  if (!m) return `<div class="slot empty"><div><div class="slot-n">Slot ${i + 1}</div>
    <input class="pick" list="mon-list" placeholder="Add a Pokémon…" data-slot="${i}" autocomplete="off"></div></div>`;
  const s = SPECIES[m.s];
  const how = Object.fromEntries(s.m);
  const abil = s.ab.length > 1
    ? `<select class="abil" data-slot="${i}" title="Ability">${s.ab.map((a, j) => `<option value="${j}"${j === m.ab ? ' selected' : ''}>${esc(a[1])}</option>`).join('')}</select>`
    : `<span class="dim">${esc(s.ab[0] ? s.ab[0][1] : '')}</span>`;
  const rows = m.mv.map((x, j) => {
    const mv = x >= 0 ? MOVES[x] : null;
    const stab = mv && mv.atk && s.t.includes(mv.t);
    return `<div class="duo-move">
      ${mv ? tyIcon(mv.t) : '<span class="ty-blank"></span>'}
      <select class="mv${mv ? '' : ' unset'}" data-slot="${i}" data-j="${j}">${moveOptions(m, j)}</select>
      <span class="mv-pow">${mv && mv.p > 0 ? (mv.p > 1 ? mv.p : 'varies') : ''}${stab ? '<span class="stab">STAB</span>' : ''}</span>
      ${mv ? `<span class="mv-how">${esc(how[x] || '')}</span>` : ''}
    </div>`;
  }).join('');
  return `<div class="slot">
    <button class="slot-x" data-remove="${i}" title="Remove">×</button>
    <div class="duo-mon"><img src="${SPRITES[m.s]}" alt="${esc(s.n)}"><div>
      <div class="card-title"><a class="xl" data-app="pokedex" data-key="${s.dex}">${esc(s.n)}</a></div>
      <div class="duo-types">${s.t.map(tyIcon).join('')}</div>${abil}</div></div>
    <div class="duo-moves">${rows}</div>
  </div>`;
}

/* ---------- analysis ---------- */
function defenseRow(m) {
  const s = SPECIES[m.s], ab = s.ab[m.ab] && ABILITY_DEFENSE[s.ab[m.ab][0]];
  return TYPES.map(t => { const x = eff(t, s.t); return ab ? ab(t, x) : x; });
}
function attackTypes(m) { return [...new Set(m.mv.filter(x => x >= 0 && MOVES[x].atk).map(x => MOVES[x].t))]; }
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

function renderAnalysis() {
  const members = team.filter(Boolean);
  const el = document.getElementById('analysis');
  if (!members.length) {
    el.innerHTML = `<div class="section-title">Team Analysis</div><p class="empty-msg">Add a Pokémon to see the type charts and what your moves can hit.</p>`;
    return;
  }
  const name = m => esc(SPECIES[m.s].n);

  // Defense — what hits each member
  const {def, weakN, resN, off, teamOff, pool, missed, unresisted, stacked, noSE, never} = summarize(members, finalOnly);
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

  // Species coverage
  const monChip = s => `<span class="monchip" data-tip="${esc(s.n)} · ${s.t.map(tc).join(' / ')}"><img src="${SPRITES[byKey[s.k]]}" alt=""><a class="xl" data-app="pokedex" data-key="${s.dex}">${esc(s.n)}</a></span>`;

  el.innerHTML = `
    <div class="section-title">Defensive Chart</div>
    <p class="p">Damage each team member takes from every attacking type, with the ability picked on its card.</p>
    ${table(TYPES, defRows)}
    <div class="flags">
      <div class="flag"><span class="lbl">No resist</span>${unresisted.length ? unresisted.map(tyIcon).join('') : '<span class="ok">Every weakness is covered by a teammate.</span>'}</div>
      ${stacked.length ? `<div class="flag"><span class="lbl">3+ weak</span>${stacked.map(tyIcon).join('')}</div>` : ''}
    </div>

    <div class="section-title">Offensive Coverage</div>
    <p class="p">The best hit each member’s attacks land on every single type. Status moves and moves that ignore the type chart
      (Seismic Toss, Night Shade, Hidden Power, fixed-damage moves) don’t count.</p>
    ${table(TYPES, offRows)}
    <div class="flags">
      <div class="flag"><span class="lbl">No 2× hit on</span>${noSE.length ? noSE.map(tyIcon).join('') : '<span class="ok">Every type is hit super effectively.</span>'}</div>
    </div>

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
  team[i] = {s, ab: 0, mv: [-1, -1, -1, -1]};
  save(); render();
  return true;
}
document.addEventListener('change', e => {
  const t = e.target;
  if (t.matches('input.pick')) pickSpecies(+t.dataset.slot, t.value);
  else if (t.matches('select.abil')) { team[+t.dataset.slot].ab = +t.value; save(); render(); }
  else if (t.matches('select.mv')) { team[+t.dataset.slot].mv[+t.dataset.j] = +t.value; save(); render(); }
  else if (t.id === 'final-only') { finalOnly = t.checked; store.set('el.team.final', finalOnly ? '1' : ''); renderAnalysis(); }
});
// Datalist picks fire 'input' before 'change' in some browsers — accept an exact name right away.
document.addEventListener('input', e => {
  if (e.target.matches('input.pick') && byName[e.target.value.trim().toLowerCase()] !== undefined) pickSpecies(+e.target.dataset.slot, e.target.value);
});
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && e.target.matches('input.pick')) pickSpecies(+e.target.dataset.slot, e.target.value);
});
document.addEventListener('click', e => {
  const x = e.target.closest('[data-remove]');
  if (x) { team[+x.dataset.remove] = null; save(); render(); }
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
    const mv = m.mv.filter(x => x >= 0).map(x => MOVES[x].n);
    return `${i + 1}. ${s.n} | ${s.t.map(tc).join('/')} | ${s.ab[m.ab] ? s.ab[m.ab][1] : '-'} | ${mv.length ? mv.join(', ') : 'no moves set'}`;
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
    'Game: Pokémon Emerald, Gen 3 mechanics: no Fairy, physical/special decided by move type, Gen 3 abilities. Main format: double battles.',
    '',
    'Team (Pokémon | type | ability | moves):',
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
    'Reply in under 150 words, no preamble, bullets only:',
    '1) Top 3 problems, one line each.',
    '2) Up to 3 concrete fixes (Move → Move, or Pokémon → Pokémon), one-line reason each. Gen 3 only; learnsets may differ from vanilla, so mark any move you are unsure the Pokémon can learn with (?).',
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

const tip = document.getElementById('tip');
document.addEventListener('mousemove', e => {
  const t = e.target.closest('[data-tip]');
  if (!t) { tip.style.display = 'none'; return; }
  tip.innerHTML = t.dataset.tip;
  tip.style.display = 'block';
  const r = tip.getBoundingClientRect();
  tip.style.left = Math.min(e.clientX + 14, window.innerWidth - r.width - 8) + 'px';
  tip.style.top = Math.min(e.clientY + 14, window.innerHeight - r.height - 8) + 'px';
});

finalOnly = !!store.get('el.team.final');
team = decode(store.get('el.team'));
render();
registerApp('teambuilder', key => { team = decode(key); save(); render(); });
</script>
</body>
</html>
'''


def generate():
    species, moves = build_data()
    sprites = [pdx.load_sprite_b64(pdx.FORM_FOLDER.get(s['k']) or pdx.species_folder(s['k'])) for s in species]
    chart = {}
    for (a, d), m in cov.load()['chart'].items():
        chart.setdefault(a, {})[d] = m
    dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    html = site_shared.inject(HTML_TEMPLATE)
    for ph, val in [('SPECIES_PLACEHOLDER', species), ('MOVES_PLACEHOLDER', moves), ('TYPES_PLACEHOLDER', cov.TYPES),
                    ('TYPE_CHART_PLACEHOLDER', chart), ('SPRITES_PLACEHOLDER', sprites),
                    ('TYPE_ICONS_PLACEHOLDER', {t: pdx.load_type_icon_b64(t) for t in cov.TYPES})]:
        html = html.replace(ph, dump(val), 1)
    out = os.path.join(BASE, 'docs', 'teambuilder.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    missing = [s['k'] for s, sp in zip(species, sprites) if not sp]
    if missing:
        print(f'  WARNING: missing sprites for {missing}')
    print(f'Generated: {out} ({os.path.getsize(out) / 1024:.0f} KB, {len(species)} species, {len(moves)} moves)')


if __name__ == '__main__':
    generate()
