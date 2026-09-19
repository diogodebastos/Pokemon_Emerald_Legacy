#!/usr/bin/env python3
"""The page renderer shared by the Guide (generate_guide.py) and the Team app
(generate_teambuilder.py).

Both apps show the same kind of page: a sidebar list of pages grouped by section, and a
main column built from typed blocks (p, h, cards, table, team, duos, bars, …). CSS holds
the whole look, including the palette and the sidebar/main layout; JS holds the block
renderers. A page uses them by declaring `PAGES` and `SPRITES`, embedding JS, then calling
renderList() and selectPage().
"""

CSS = r'''  :root {
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
  a { color: var(--jade-bright); cursor: pointer; }

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
    letter-spacing: 0.3em; text-transform: uppercase;
  }
  #page-list { overflow-y: auto; flex: 1; padding: 8px 8px 24px; }
  .cat-header {
    font-family: var(--f-mono); font-size: 9px; color: var(--jade-bright);
    letter-spacing: 0.28em; text-transform: uppercase; padding: 16px 12px 8px;
    display: flex; align-items: center; gap: 10px;
  }
  .cat-header::after { content: ""; flex: 1; height: 1px; background: var(--rule); }
  .pg-item {
    padding: 9px 12px; cursor: pointer; border-left: 2px solid transparent;
    transition: background 0.15s, border-color 0.15s;
  }
  .pg-item:hover { background: var(--paper-1); }
  .pg-item.active { background: var(--jade-soft); border-left-color: var(--jade-bright); }
  .pg-item .pg-name { font-family: var(--f-serif); font-style: italic; font-size: 16px; color: var(--ink-dim); line-height: 1.15; }
  .pg-item .pg-kicker { font-family: var(--f-mono); font-size: 8px; color: var(--ink-mut); letter-spacing: 0.16em; text-transform: uppercase; }
  .pg-item:hover .pg-name { color: var(--ink); }
  .pg-item.active .pg-name { color: var(--ink); font-style: normal; font-weight: 500; }

  /* Main */
  #main {
    flex: 1; min-height: 0; overflow-y: auto;
    background: radial-gradient(1000px 500px at 100% -100px, rgba(46,176,112,0.05), transparent 55%), var(--paper-1);
    padding: 48px 56px 64px;
  }
  #main::-webkit-scrollbar { width: 12px; }
  #main::-webkit-scrollbar-thumb { background: var(--paper-3); border: 3px solid var(--paper-1); border-radius: 12px; }
  #page { max-width: 960px; margin: 0 auto; }

  .kicker {
    font-family: var(--f-mono); font-size: 10px; color: var(--jade-bright);
    letter-spacing: 0.26em; text-transform: uppercase; margin-bottom: 10px;
    display: flex; align-items: center; gap: 10px;
  }
  .kicker::after { content: ""; flex: 1; height: 1px; background: var(--rule); }
  #page h2 {
    font-family: var(--f-serif); font-variation-settings: "opsz" 144, "SOFT" 60, "WONK" 1;
    font-weight: 400; font-style: italic; font-size: 56px; line-height: 0.95; color: var(--ink);
    letter-spacing: -0.03em; margin-bottom: 20px;
  }
  .p { font-size: 15px; line-height: 1.7; color: var(--ink-dim); margin: 0 0 16px; max-width: 76ch; }
  .p b, .callout b, td b, .note b, li b { color: var(--ink); font-weight: 600; }
  ul.list { margin: 0 0 16px 18px; color: var(--ink-dim); line-height: 1.7; font-size: 14px; max-width: 76ch; }
  ul.list li { margin-bottom: 4px; }
  .callout {
    font-size: 14px; line-height: 1.65; color: var(--ink-dim); margin: 18px 0; padding: 12px 16px;
    border: 1px solid var(--dusk); background: var(--dusk-soft); max-width: 80ch;
  }
  .section-title {
    font-family: var(--f-mono); font-size: 10px; color: var(--jade-bright); letter-spacing: 0.3em;
    text-transform: uppercase; margin-bottom: 14px; margin-top: 36px; display: flex;
    align-items: center; gap: 12px; font-weight: 500;
  }
  .section-title::before { content: "§"; color: var(--ink-mut); font-weight: 400; font-size: 13px; }
  .section-title::after { content: ""; flex: 1; height: 1px; background: var(--rule); }

  /* Cards */
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; margin: 8px 0 16px; }
  .card { border: 1px solid var(--rule); background: var(--paper-2); padding: 14px; display: flex; flex-direction: column; gap: 10px; }
  .card-head { display: grid; grid-template-columns: auto 1fr; gap: 10px; align-items: center; }
  .card-sprites { display: flex; }
  .card-sprites img { width: 64px; height: 64px; image-rendering: pixelated; }
  .card-sprites img + img { margin-left: -18px; }
  .card-title { font-family: var(--f-serif); font-style: italic; font-size: 20px; color: var(--ink); line-height: 1.05; }
  .card-sub { font-family: var(--f-mono); font-size: 10px; color: var(--jade-bright); letter-spacing: 0.12em; margin-top: 3px; }
  .card-place { font-family: var(--f-sans); font-size: 12px; color: var(--ink-dim); padding: 6px 10px; border: 1px solid var(--rule); background: var(--paper-1); }
  .card-want { display: flex; align-items: center; gap: 6px; font-family: var(--f-mono); font-size: 10px; color: var(--ink-mut); letter-spacing: 0.12em; text-transform: uppercase; }
  .card-want img { width: 40px; height: 40px; image-rendering: pixelated; }
  .card-want span { color: var(--ink); font-family: var(--f-serif); font-style: italic; font-size: 15px; text-transform: none; letter-spacing: 0; }
  .card-rows { font-family: var(--f-mono); font-size: 11px; color: var(--ink-dim); display: grid; grid-template-columns: auto 1fr; gap: 4px 10px; }
  .card-rows .k { color: var(--ink-mut); letter-spacing: 0.12em; text-transform: uppercase; font-size: 8px; padding-top: 2px; }
  .note { font-size: 13px; line-height: 1.6; color: var(--ink-dim); border-left: 2px solid var(--jade-bright); padding-left: 12px; }

  /* Tables */
  .tbl-wrap { overflow-x: auto; margin: 8px 0 16px; border: 1px solid var(--rule); }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th {
    text-align: left; font-family: var(--f-mono); font-size: 9px; font-weight: 500; color: var(--jade-bright);
    letter-spacing: 0.2em; text-transform: uppercase; padding: 10px 12px; background: var(--paper-0);
    border-bottom: 1px solid var(--rule);
  }
  td { padding: 10px 12px; border-bottom: 1px solid var(--rule-2); color: var(--ink-dim); line-height: 1.55; vertical-align: middle; }
  tr:last-child td { border-bottom: 0; }
  td .ent { display: flex; align-items: center; gap: 8px; white-space: nowrap; font-family: var(--f-serif); font-style: italic; font-size: 15px; color: var(--ink); }
  td .ent img { width: 40px; height: 40px; image-rendering: pixelated; }
  td .dim { color: var(--ink-mut); font-size: 12px; }
  .mons { display: flex; flex-wrap: wrap; gap: 4px 14px; }
  .mon { display: inline-flex; align-items: center; gap: 4px; font-size: 13px; line-height: 1.25; }
  .mon > img { width: 40px; height: 40px; image-rendering: pixelated; }
  .mon .dim img { width: 18px; height: 18px; vertical-align: middle; image-rendering: pixelated; }
  .chip { display: inline-flex; align-items: center; gap: 2px; margin: 0 8px 2px 0; white-space: nowrap; }
  .chip img, .it-name img { width: 24px; height: 24px; image-rendering: pixelated; }
  .it-name { display: flex; align-items: center; gap: 6px; font-weight: 600; color: var(--ink); white-space: nowrap; }
  .tier { display: inline-block; min-width: 22px; text-align: center; font-family: var(--f-mono); font-size: 11px; padding: 2px 6px; border: 1px solid var(--rule); }
  .tier-S { color: var(--dusk); border-color: var(--dusk); background: var(--dusk-soft); }
  .tier-A { color: var(--jade-bright); border-color: var(--jade-bright); }
  .tier-B { color: var(--ink-dim); }
  .tier-C { color: var(--ink-mut); }
  .sortbar { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin: 4px 0 12px; }
  .sortbar .lbl { font-family: var(--f-mono); font-size: 9px; color: var(--ink-mut); letter-spacing: 0.22em; text-transform: uppercase; margin-right: 4px; }
  .sort-btn { font-family: var(--f-mono); font-size: 9px; padding: 5px 11px; letter-spacing: 0.14em; text-transform: uppercase; border: 1px solid var(--rule); background: transparent; color: var(--ink-dim); cursor: pointer; }
  .sort-btn:hover { border-color: var(--jade-bright); color: var(--ink); }
  .sort-btn.active { background: var(--jade-soft); border-color: var(--jade-bright); color: var(--jade-bright); }
  .pg.br { color: var(--jade-bright); border-color: var(--jade-bright); }
  .pg { font-family: var(--f-mono); font-size: 8px; letter-spacing: 0.14em; color: var(--dusk); border: 1px solid var(--dusk); padding: 0 4px; margin-left: 4px; vertical-align: middle; }

  /* Team Building — coverage */
  .tyicon { width: 48px; height: 24px; image-rendering: pixelated; vertical-align: middle; flex: none; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: 8px 0 16px; }
  .stat { border: 1px solid var(--rule); background: var(--paper-2); padding: 14px 16px; }
  .stat-v { font-family: var(--f-serif); font-size: 40px; line-height: 1; color: var(--ink); font-variation-settings: "opsz" 144; }
  .stat-l { font-family: var(--f-mono); font-size: 9px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--ink-mut); margin-top: 8px; line-height: 1.5; }
  .stat-mons { margin-top: 6px; }
  .bars { display: flex; flex-direction: column; gap: 2px; margin: 8px 0 20px; max-width: 720px; }
  .bar-row { display: grid; grid-template-columns: 56px 1fr 44px; align-items: center; gap: 10px; padding: 3px 6px; cursor: default; }
  .bar-row:hover { background: var(--paper-2); }
  .bar-track { display: block; height: 12px; background: var(--paper-0); border-radius: 0 4px 4px 0; overflow: hidden; }
  .bar-fill { display: block; height: 100%; background: var(--jade-bright); border-radius: 0 4px 4px 0; }
  .bar-row:hover .bar-fill { background: var(--ink); }
  .bar-n { font-family: var(--f-mono); font-size: 12px; color: var(--ink-dim); text-align: right; }
  .bneck { border: 1px solid var(--rule); margin: 8px 0 16px; }
  .bneck-row { display: grid; grid-template-columns: 150px 1fr; gap: 12px; padding: 10px 12px; border-bottom: 1px solid var(--rule-2); align-items: center; }
  .bneck-row:last-child { border-bottom: 0; }
  .bneck-type { display: flex; align-items: center; gap: 8px; font-family: var(--f-mono); font-size: 9px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--ink-mut); }
  .bneck-mons, .stat-mons, .typeset-note { display: flex; flex-wrap: wrap; gap: 0 2px; align-items: center; }
  .monchip { display: inline-flex; align-items: center; font-size: 12px; margin-right: 8px; white-space: nowrap; }
  .monchip img { width: 36px; height: 36px; image-rendering: pixelated; }
  .typesets { display: flex; flex-direction: column; gap: 6px; margin: 8px 0 16px; }
  .typeset { display: flex; flex-wrap: wrap; gap: 4px; padding: 8px 10px; border: 1px solid var(--rule); background: var(--paper-2); }
  .typeset-note { font-size: 13px; color: var(--ink-dim); gap: 4px 6px; }
  .duos { display: flex; flex-direction: column; gap: 16px; margin: 8px 0 20px; }
  .duo { border: 1px solid var(--rule); background: var(--paper-2); padding: 16px; display: flex; flex-direction: column; gap: 12px; }
  .duo-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .duo-side + .duo-side { border-left: 1px solid var(--rule); padding-left: 16px; }
  .duo-mon { display: flex; gap: 10px; align-items: center; margin-bottom: 8px; }
  .duo-mon > img { width: 64px; height: 64px; image-rendering: pixelated; }
  .duo-types { display: flex; gap: 2px; margin: 4px 0 2px; }
  .duo-types .tyicon { width: 40px; height: 20px; }
  .duo-mon .dim { font-family: var(--f-mono); font-size: 10px; color: var(--ink-mut); }
  .duo-moves { display: flex; flex-direction: column; gap: 4px; }
  .duo-move { display: grid; grid-template-columns: 48px 1fr auto; column-gap: 8px; align-items: center; }
  .mv-name { color: var(--ink); font-weight: 600; cursor: pointer; text-decoration: underline dotted var(--jade-bright); text-underline-offset: 3px; }
  .mv-name:hover { color: var(--jade-bright); }
  .mv-pow { font-family: var(--f-mono); font-size: 12px; color: var(--ink-dim); text-align: right; white-space: nowrap; }
  .mv-how { grid-column: 2 / 4; font-family: var(--f-mono); font-size: 9px; color: var(--ink-mut); letter-spacing: 0.06em; margin-top: -2px; }
  .stab { font-family: var(--f-mono); font-size: 8px; letter-spacing: 0.12em; color: var(--dusk); border: 1px solid var(--dusk); padding: 0 3px; margin-left: 5px; vertical-align: middle; }
  .duo-meter { display: grid; grid-template-columns: 80px 1fr 64px; gap: 10px; align-items: center; }
  .duo .lbl { font-family: var(--f-mono); font-size: 9px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--ink-mut); margin-right: 10px; }
  .duo-miss { display: flex; flex-wrap: wrap; align-items: center; }
  .mvchip { display: inline-flex; align-items: center; gap: 4px; margin: 0 10px 2px 0; white-space: nowrap; cursor: pointer; }
  .mvchip .tyicon { width: 32px; height: 16px; }
  #tip { position: fixed; z-index: 10000; display: none; pointer-events: none; max-width: 280px; padding: 6px 10px;
         background: var(--paper-0); border: 1px solid var(--rule); color: var(--ink-dim); font-size: 12px; line-height: 1.45; }
  #tip b { color: var(--ink); }

  .mu-wrap { overflow-x: auto; }
  table.mu { width: auto; border-collapse: separate; border-spacing: 2px; font-family: var(--f-mono); font-size: 11px; }
  table.mu th { padding: 0; background: none; border: 0; }
  table.mu th .tyicon { width: 32px; height: 16px; }
  table.mu .mu-name { font-family: var(--f-serif); font-style: italic; font-size: 13px; color: var(--ink); text-transform: none; letter-spacing: 0; text-align: right; padding-right: 8px; white-space: nowrap; font-weight: 400; }
  table.mu td { width: 32px; height: 22px; padding: 0; text-align: center; border: 0; border-radius: 3px; background: var(--paper-1); color: var(--ink-mut); cursor: default; }
  table.mu td.weak { background: rgba(232,165,48,0.28); color: var(--ink); }
  table.mu td.res { background: rgba(46,176,112,0.22); color: var(--ink); }
  table.mu td.imm { background: rgba(46,176,112,0.5); color: var(--ink); font-weight: 700; }

  /* Double Battles */
  .leads { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 18px; margin: 4px 0 16px; }
  .leads .lbl { font-family: var(--f-mono); font-size: 9px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--ink-mut); }
  .lead { display: inline-flex; align-items: center; border: 1px solid var(--rule); background: var(--paper-2); padding: 2px 10px 2px 4px; }
  .lead .plus { color: var(--ink-mut); margin: 0 6px 0 -2px; }
  .team { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 14px; margin: 8px 0 20px; }
  .tm { border: 1px solid var(--rule); background: var(--paper-2); padding: 14px; display: flex; flex-direction: column; gap: 10px; }
  .tm-meta { display: flex; flex-wrap: wrap; gap: 2px 12px; font-family: var(--f-mono); font-size: 10px; color: var(--ink-dim); margin-top: 3px; align-items: center; }
  .tm-meta .it-name { font-family: var(--f-mono); font-weight: 400; color: var(--ink-dim); font-size: 10px; gap: 2px; }
  .tm-meta .it-name img { width: 20px; height: 20px; }
  .tgt { font-family: var(--f-mono); font-size: 8px; font-weight: 400; letter-spacing: 0.1em; text-transform: uppercase; color: var(--jade-bright); border: 1px solid var(--rule); padding: 0 4px; margin-left: 6px; vertical-align: middle; text-decoration: none; display: inline-block; }
  .mv-how a.xl { font-family: var(--f-mono); }
  .monlist { margin: 4px 0 16px; }
  .stat-tag { color: var(--jade-bright); border: 1px solid var(--jade-bright); padding: 0 5px; }
  .alt-flag { font-family: var(--f-mono); font-size: 8px; font-weight: 400; letter-spacing: 0.08em; color: var(--dusk); border: 1px solid var(--dusk); padding: 0 4px; margin-left: 6px; vertical-align: middle; text-decoration: none; display: inline-block; }
  .mv-name.has-alt { text-decoration-color: var(--dusk); }

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
    #page h2 { font-size: 40px; }
    .cards { grid-template-columns: 1fr; }
    .duo-grid { grid-template-columns: 1fr; }
    .team { grid-template-columns: 1fr; }
    .duo-side + .duo-side { border-left: 0; padding-left: 0; border-top: 1px solid var(--rule); padding-top: 14px; }
    .bneck-row { grid-template-columns: 1fr; }
    .duo-meter { grid-template-columns: auto 1fr auto; }
  }
'''

JS = r'''const isMobile = () => window.innerWidth <= 700;
let currentPage = null;

function img(ref, alt) {
  // A page can supply spriteFallback() when it already holds the sprite elsewhere (the Team app does).
  const s = (ref && SPRITES[ref]) || (typeof spriteFallback === 'function' ? spriteFallback(ref) : '');
  return s ? `<img src="${s}" alt="${alt || ''}">` : '';
}

function goBack() {
  document.getElementById('sidebar').classList.remove('hidden');
  document.getElementById('main').classList.add('hidden');
}

function renderList() {
  const list = document.getElementById('page-list');
  let lastSec = null, html = '';
  PAGES.forEach(p => {
    if (p.section !== lastSec) { lastSec = p.section; html += `<div class="cat-header">${p.section}</div>`; }
    html += `<div class="pg-item${p.id === currentPage ? ' active' : ''}" onclick="selectPage('${p.id}')">
      <div class="pg-name">${p.title}</div><div class="pg-kicker">${p.kicker}</div></div>`;
  });
  list.innerHTML = html;
}

function xlink(app, key, label) {
  return key ? `<a class="xl" data-app="${app}" data-key="${key}">${label}</a>` : label;
}
function monKey(sprite) { return sprite && /^(mon|shiny):/.test(sprite) && !/:EGG$/.test(sprite) ? sprite.split(':')[1] : null; }
function chip(it) {
  return `<span class="chip">${img(it.icon, it.name)}${xlink('bag', it.icon && it.icon.slice(5), it.name)}${it.n > 1 ? ' ×' + it.n : ''}</span>`;
}

let finderSort = 'importance';
let finderBR = true;
const FINDER_SORTS = {
  importance: (a, b) => a.imp - b.imp || a.name.localeCompare(b.name),
  chrono:     (a, b) => a.first - b.first || a.imp - b.imp,
  common:     (a, b) => b.count - a.count || a.imp - b.imp,
};
function setFinderBR(on) { finderBR = on; setFinderSort(finderSort); }
function setFinderSort(mode) {
  finderSort = mode;
  const p = PAGES.find(x => x.id === currentPage);
  const b = p.blocks.find(x => x.type === 'itemfinder');
  document.getElementById('itemfinder').outerHTML = renderFinder(b);
}
function renderFinder(b) {
  const items = b.items.map(it => {
    const holders = it.holders.filter(h => finderBR || !h.br);
    return {...it, holders, count: holders.reduce((s, h) => s + h.n, 0), first: Math.min(...holders.map(h => h.chrono))};
  }).filter(it => it.holders.length).sort(FINDER_SORTS[finderSort]);
  const holderSort = finderSort === 'chrono'
    ? (x, y) => x.chrono - y.chrono
    : (x, y) => (y.repeat - x.repeat) || x.chrono - y.chrono;
  const btn = (m, label) => `<button class="sort-btn${finderSort === m ? ' active' : ''}" onclick="setFinderSort('${m}')">${label}</button>`;
  return `<div id="itemfinder">
    <div class="sortbar"><span class="lbl">Order by</span>${btn('importance', 'Importance')}${btn('chrono', 'Chronological')}${btn('common', 'Most common')}
      <button class="sort-btn${finderBR ? ' active' : ''}" style="margin-left:auto" onclick="setFinderBR(${!finderBR})">${finderBR ? '☑' : '☐'} Battle Royale trainers</button></div>
    <div class="tbl-wrap"><table><thead><tr><th>Item</th><th>Tier</th><th>Copies</th><th>Steal from</th></tr></thead><tbody>
    ${items.map(it => `<tr>
      <td><span class="it-name">${img(it.icon, it.name)}${xlink('bag', it.key, it.name)}</span></td>
      <td><span class="tier tier-${it.tier}">${it.tier}</span></td>
      <td>${it.count}</td>
      <td>${[...it.holders].sort(holderSort).map(h =>
        `${h.repeat ? '↻ ' : ''}${xlink('trainers', h.tv, h.label)}${h.n > 1 ? ' ×' + h.n : ''}${h.post ? '<span class="pg">Post</span>' : ''}${h.br ? '<span class="pg br">BR</span>' : ''} <span class="dim">· ${h.locs}</span>`).join('<br>')}</td>
    </tr>`).join('')}
    </tbody></table></div></div>`;
}

function cell(c) {
  if ('sprite' in c) {
    const link = c.link || (monKey(c.sprite) ? ['pokedex', monKey(c.sprite)] : null);
    return `<span class="ent">${img(c.sprite, c.text)}${link ? xlink(link[0], link[1], c.text) : c.text}</span>`;
  }
  if (c.items) return c.items.map(chip).join('');
  if (c.mons) return `<div class="mons">${c.mons.map(m => `<span class="mon" title="${m.nature}${m.moves.length ? ' · ' + m.moves.join(', ') : ''}">${img(m.sprite, m.name)}<span>${xlink('pokedex', m.sp, m.name)}${m.item ? `<br><span class="dim">${img(m.icon, m.item)}${xlink('bag', m.icon && m.icon.slice(5), m.item)}</span>` : ''}</span></span>`).join('')}</div>`;
  return c.html !== undefined ? c.html : c.text;
}

function tyIcon(t) { return `<img class="tyicon" src="${SPRITES['type:' + t] || ''}" alt="${t}" title="${t[0] + t.slice(1).toLowerCase()}">`; }
function monChip(m) { return `<span class="monchip" data-tip="${m.name}">${img(m.sprite, m.name)}${xlink('pokedex', m.sp, m.name)}</span>`; }
function renderMember(x) {
  return `<div class="tm">
    <div class="duo-mon">${img(x.sprite, x.name)}<div><div class="card-title">${xlink('pokedex', x.sp, x.name)}</div>
      <div class="duo-types">${x.types.map(tyIcon).join('')}</div>
      <div class="tm-meta"><span>${x.ability}</span><span class="it-name">${img(x.item.icon, x.item.name)}${xlink('bag', x.item.key, x.item.name)}</span><span>${x.nature}</span>${x.stat ? `<span class="stat-tag">${x.stat}</span>` : ''}</div></div></div>
    <div class="duo-moves">${x.moves.map(m => `<div class="duo-move">
      ${tyIcon(m.type)}<span class="mv-name${m.tip ? ' has-alt' : ''}" data-move="${m.name}"${m.tip ? ` data-tip="${m.tip.replace(/"/g, '&quot;')}"` : ''}>${m.name}${m.tip ? `<span class="alt-flag">⚑ ${m.alt}</span>` : ''}${m.target ? `<span class="tgt">${m.target}</span>` : ''}</span>
      <span class="mv-pow">${m.power}</span>
      <span class="mv-how">${m.how}</span></div>`).join('')}</div>
    ${x.note ? `<div class="note">${x.note}</div>` : ''}
  </div>`;
}
function renderMatchups(mu) {
  const lab = x => x === 0 ? '0' : x >= 4 ? '4×' : x >= 2 ? '2×' : x <= 0.25 ? '¼' : x <= 0.5 ? '½' : '';
  const cls = x => x === 0 ? 'imm' : x > 1 ? 'weak' : x < 1 ? 'res' : '';
  const word = x => x === 0 ? 'immune' : x > 1 ? `weak (${lab(x)})` : x < 1 ? `resists (${lab(x)})` : 'neutral';
  return `<div class="mu-wrap"><table class="mu"><thead><tr><th></th>${mu.types.map(t => `<th>${tyIcon(t)}</th>`).join('')}</tr></thead><tbody>
    ${mu.rows.map((row, i) => `<tr><th class="mu-name">${mu.names[i]}</th>${row.map((x, j) =>
      `<td class="${cls(x)}" data-tip="<b>${mu.names[i]}</b> vs ${mu.types[j][0] + mu.types[j].slice(1).toLowerCase()}: ${word(x)}">${lab(x)}</td>`).join('')}</tr>`).join('')}
  </tbody></table></div>`;
}
function renderDuo(d) {
  const side = s => `<div class="duo-side">
    <div class="duo-mon">${img(s.mon.sprite, s.mon.name)}<div><div class="card-title">${xlink('pokedex', s.mon.sp, s.mon.name)}</div>
      <div class="duo-types">${s.types.map(tyIcon).join('')}</div><div class="dim">${s.ability}</div></div></div>
    <div class="duo-moves">${s.moves.map(m => `<div class="duo-move">
      ${tyIcon(m.type)}<span class="mv-name" data-move="${m.name}">${m.name}</span>
      <span class="mv-pow">${m.power}${m.stab ? '<span class="stab">STAB</span>' : ''}</span>
      <span class="mv-how">${m.how}</span></div>`).join('')}</div></div>`;
  const pct = 100 * d.hit / d.total;
  return `<div class="duo">
    <div class="duo-grid">${side(d.a)}${side(d.b)}</div>
    ${d.matchups ? renderMatchups(d.matchups) : ''}
    <div class="duo-meter" data-tip="${d.hit} of ${d.total} hittable species">
      <span class="lbl">Coverage</span><span class="bar-track"><span class="bar-fill" style="width:${pct.toFixed(2)}%"></span></span>
      <span class="bar-n">${d.hit}/${d.total}</span></div>
    <div class="duo-miss"><span class="lbl">Misses</span>${d.missed.slice(0, 14).map(monChip).join('')}${d.missed.length > 14 ? `<span class="dim" data-tip="${d.missed.slice(14).map(m => m.name).join(', ')}">+${d.missed.length - 14} more</span>` : ''}</div>
  </div>`;
}
const tip = document.createElement('div');
tip.id = 'tip';
document.body.appendChild(tip);
document.addEventListener('mousemove', e => {
  const t = e.target.closest('[data-tip]');
  if (!t) { tip.style.display = 'none'; return; }
  tip.innerHTML = t.dataset.tip;
  tip.style.display = 'block';
  const r = tip.getBoundingClientRect();
  tip.style.left = Math.min(e.clientX + 14, window.innerWidth - r.width - 8) + 'px';
  tip.style.top = (e.clientY + 18 + r.height > window.innerHeight ? e.clientY - r.height - 10 : e.clientY + 18) + 'px';
});

function renderBlock(b) {
  switch (b.type) {
    case 'p': return `<p class="p">${b.html}</p>`;
    case 'h': return `<div class="section-title">${b.text}</div>`;
    case 'callout': return `<div class="callout">${b.html}</div>`;
    case 'list': return `<ul class="list">${b.items.map(i => `<li>${i}</li>`).join('')}</ul>`;
    case 'table':
      return `<div class="tbl-wrap"><table><thead><tr>${b.head.map(h => `<th>${h}</th>`).join('')}</tr></thead>
        <tbody>${b.rows.map(r => `<tr>${r.map(c => `<td>${cell(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
    case 'itemfinder': return renderFinder(b);
    case 'stats':
      return `<div class="stats">${b.items.map(it => `<div class="stat">
        <div class="stat-v">${it.value}</div><div class="stat-l">${it.label}</div>
        ${it.mons ? `<div class="stat-mons">${it.mons.map(monChip).join('')}</div>` : ''}</div>`).join('')}</div>`;
    case 'bars': {
      const max = Math.max(...b.rows.map(r => r.n));
      return `<div class="bars" role="table" aria-label="Species hit super effectively per attacking type">${b.rows.map(r => {
        const pct = (100 * r.n / b.total).toFixed(1);
        return `<div class="bar-row" role="row" data-tip="<b>${r.label}</b> hits ${r.n} of ${b.total} species super effectively (${pct}%)">
          <span class="bar-type" role="rowheader">${tyIcon(r.type)}</span>
          <span class="bar-track"><span class="bar-fill" style="width:${(100 * r.n / max).toFixed(2)}%"></span></span>
          <span class="bar-n" role="cell">${r.n}</span></div>`;
      }).join('')}</div>`;
    }
    case 'bottlenecks':
      return `<div class="bneck">${b.items.map(g => `<div class="bneck-row">
        <div class="bneck-type">${g.types.map(tyIcon).join('<span>or</span>')}</div>
        <div class="bneck-mons">${g.mons.map(monChip).join('')}</div></div>`).join('')}</div>`;
    case 'typesets':
      return `<div class="typesets">${b.sets.map(set => `<div class="typeset">${set.map(tyIcon).join('')}</div>`).join('')}
        ${b.note ? `<div class="typeset-note">${b.note} ${b.mons.map(monChip).join('')}</div>` : ''}</div>`;
    case 'monlist': return `<div class="bneck-mons monlist">${b.mons.map(monChip).join('')}</div>`;
    case 'leads':
      return `<div class="leads"><span class="lbl">Suggested leads</span>${b.leads.map(pair => `<span class="lead">${pair.map(monChip).join('<span class="plus">+</span>')}</span>`).join('')}</div>`;
    case 'team':
      // The Team app adds an "open in the builder" button here; the Guide defines no hook.
      return (typeof teamBlockExtra === 'function' ? teamBlockExtra(b) : '')
        + `<div class="team">${b.members.map(renderMember).join('')}</div>`;
    case 'duos':
      return `<div class="duos">${b.items.map(renderDuo).join('')}</div>`;
    case 'cards':
      return `<div class="cards">${b.items.map(it => `<div class="card">
        <div class="card-head">
          <div class="card-sprites">${img(it.sprite, it.title)}${(it.extra || []).map(e => img(e)).join('')}</div>
          <div><div class="card-title">${(it.extra || []).length || !monKey(it.sprite) ? it.title : xlink('pokedex', monKey(it.sprite), it.title)}</div>${it.sub ? `<div class="card-sub">${it.sub}</div>` : ''}</div>
        </div>
        ${it.place ? `<div class="card-place">${it.place}</div>` : ''}
        ${it.want ? `<div class="card-want">Trade your ${img(it.wantSprite, it.want)}<span>${xlink('pokedex', monKey(it.wantSprite), it.want)}</span></div>` : ''}
        ${it.rows ? `<div class="card-rows">${it.rows.map(([k, v]) => `<span class="k">${k}</span><span>${v}</span>`).join('')}</div>` : ''}
        ${it.note ? `<div class="note">${it.note}</div>` : ''}
      </div>`).join('')}</div>`;
  }
  return '';
}

function selectPage(id) {
  const p = PAGES.find(x => x.id === id);
  if (!p) return;
  currentPage = id;
  renderList();
  document.getElementById('page').innerHTML =
    (`<div class="kicker">${p.section} · ${p.kicker}</div><h2>${p.title}</h2>` + p.blocks.map(renderBlock).join(''))
      .replace(/src="TYPEICON:(\w+)"/g, (_, t) => `src="${SPRITES['type:' + t]}"`);
  if (isMobile()) {
    document.getElementById('sidebar').classList.add('hidden');
    document.getElementById('main').classList.remove('hidden');
  }
  document.getElementById('main').scrollTop = 0;
  window.scrollTo(0, 0);
}
'''
