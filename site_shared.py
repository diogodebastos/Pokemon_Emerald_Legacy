"""Shared bits for the website generators (generate_*.py → docs/*.html).

- APP_FILES / SHARED_CSS / SHARED_JS: the cross-app link protocol. Every page registers
  `window.APP = {select(key)}` and reads `location.hash`; links are
  `<a class="xl" data-app="pokedex" data-key="MARILL">`. Inside the dock shell
  (docs/index.html) a click calls `parent.openApp(app, key)`, standalone it navigates to
  `<file>#key`.
- load_item_icon_b64: bag icon for an ITEM_* constant (palette applied).
- parse_rematch_tables: gRematchTable (src/battle_setup.c) → base team per rematch id.
"""

import os
import re
import html

BASE = os.path.dirname(os.path.abspath(__file__))

APP_FILES = {
    'pokedex': 'pokedex.html',
    'trainers': 'trainerdex.html',
    'moves': 'attackdex.html',
    'bag': 'items.html',
    'guide': 'guide.html',
}


def xl(app, key, label):
    """HTML link to another app's entry."""
    return (f'<a class="xl" data-app="{app}" data-key="{html.escape(str(key), quote=True)}">'
            f'{label}</a>')


SHARED_CSS = '''
  .xl { color: inherit; cursor: pointer; text-decoration: underline; text-decoration-style: dotted;
        text-decoration-color: var(--jade-bright); text-underline-offset: 3px; }
  .xl:hover { color: var(--jade-bright); }
  a.xl b, .xl b { color: inherit; }
'''

SHARED_JS = '''
// ---- cross-app links (site_shared.py) ----
const APP_FILES = APP_FILES_PLACEHOLDER;
const EMBEDDED = (() => { try { return window.parent !== window && typeof window.parent.openApp === 'function'; } catch (e) { return false; } })();
function openLink(app, key) {
  if (EMBEDDED) { window.parent.openApp(app, key); return; }
  if (window.APP && window.APP.id === app) { window.APP.select(key); history.replaceState(null, '', '#' + encodeURIComponent(key)); return; }
  location.href = APP_FILES[app] + '#' + encodeURIComponent(key);
}
document.addEventListener('click', e => {
  const a = e.target.closest('.xl[data-app]');
  if (a) { e.preventDefault(); e.stopPropagation(); openLink(a.dataset.app, a.dataset.key); return; }
  const mv = e.target.closest('[data-move]');
  if (mv && (!window.APP || window.APP.id !== 'moves')) {
    openLink('moves', mv.dataset.move.replace(/^(?:TM|HM)\\d+\\s+/, ''));
  }
});
document.addEventListener('keydown', e => {
  if (!EMBEDDED || typeof window.parent.openPalette !== 'function') return;
  const typing = /INPUT|TEXTAREA|SELECT/.test(e.target.tagName || '');
  if (((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') || (e.key === '/' && !typing)) {
    e.preventDefault(); window.parent.openPalette();
  }
});
function registerApp(id, select) {
  window.APP = { id, key: null, select: key => { window.APP.key = key; try { return select(key); } catch (e) { console.warn('select failed', key, e); } } };
  // Keep list/detail in sync when the frame crosses the phone breakpoint (e.g. split view in the dock shell)
  let wasMobile = window.innerWidth <= 700;
  window.addEventListener('resize', () => {
    const mobile = window.innerWidth <= 700;
    if (mobile === wasMobile) return;
    wasMobile = mobile;
    const sb = document.getElementById('sidebar'), mn = document.getElementById('main');
    if (!mobile) { sb && sb.classList.remove('hidden'); mn && mn.classList.remove('hidden'); }
    else {
      const w = document.getElementById('welcome');
      const shown = w ? w.style.display === 'none' : (typeof currentPage !== 'undefined' && !!currentPage);
      if (shown) { sb && sb.classList.add('hidden'); mn && mn.classList.remove('hidden'); }
      else if (typeof goBack === 'function') goBack();
    }
  });
  const fromHash = () => { const k = decodeURIComponent(location.hash.slice(1)); if (k) window.APP.select(k); };
  window.addEventListener('hashchange', fromHash);
  if (location.hash.length > 1) fromHash();
  else if (window.innerWidth <= 700 && typeof goBack === 'function') goBack();
}
'''.replace('APP_FILES_PLACEHOLDER', repr(APP_FILES).replace("'", '"'))


def load_item_icon_b64(const):
    """ITEM_LEFTOVERS -> base64 PNG of its bag icon, palette applied, index 0 transparent."""
    from PIL import Image
    import generate_pokedex as pdx
    global _ICON_FILES
    if '_ICON_FILES' not in globals():
        gfx = open(os.path.join(BASE, 'src/data/graphics/items.h')).read()
        sym_file = dict(re.findall(r'(gItemIcon(?:Palette)?_\w+)\[\]\s*=\s*INCBIN_U32\("([^"]+)"\)', gfx))
        table = open(os.path.join(BASE, 'src/data/item_icon_table.h')).read()
        _ICON_FILES = {}
        # The icon table keys TMs/HMs as ITEM_TM01 / ITEM_HM01; items.h uses ITEM_TM_FOCUS_PUNCH (tms_hms.h order)
        tmhm = open(os.path.join(BASE, 'include/constants/tms_hms.h')).read()
        alias = {}
        for kind in ('TM', 'HM'):
            body = re.search(r'#define FOREACH_%s\(F\)(.*?)(?:\n\s*\n|#define|$)' % kind, tmhm, re.S).group(1)
            for i, move in enumerate(re.findall(r'F\((\w+)\)', body)):
                alias[f'ITEM_{kind}{i + 1:02d}'] = f'ITEM_{kind}_{move}'
        for item, icon, pal in re.findall(r'\[(ITEM_\w+)\]\s*=\s*\{(\w+),\s*(\w+)\}', table):
            if icon in sym_file and pal in sym_file:
                _ICON_FILES[alias.get(item, item)] = (sym_file[icon].split('.')[0] + '.png', sym_file[pal].split('.')[0] + '.pal')
    if const not in _ICON_FILES:
        return ''
    png, pal = (os.path.join(BASE, f) for f in _ICON_FILES[const])
    if not os.path.exists(png):
        return ''
    img = Image.open(png)
    if img.mode == 'P' and os.path.exists(pal):
        colors = [tuple(int(x) for x in l.split()) for l in open(pal).read().splitlines()[3:] if len(l.split()) == 3]
        flat = img.getpalette()
        for i, c in enumerate(colors[:16]):
            flat[i * 3:i * 3 + 3] = list(c)
        img.putpalette(flat)
        img.info['transparency'] = 0
    return pdx._img_to_b64(img.convert('RGBA'))


def parse_rematch_tables():
    """-> (base_of: rematch trainer id -> first-battle id, last: set of final rematch ids)."""
    src = open(os.path.join(BASE, 'src/battle_setup.c')).read()
    base_of, last = {}, set()
    for m in re.finditer(r'\[REMATCH_\w+\]\s*=\s*REMATCH\(([^)]*)\)', src):
        ids = [x.strip() for x in m.group(1).split(',')][:-1]
        for x in ids:
            base_of.setdefault(x, ids[0])
        last.add(ids[-1])
    return base_of, last


def inject(template):
    """Add SHARED_CSS before </style> and SHARED_JS right after the first <script> tag."""
    template = template.replace('</style>', SHARED_CSS + '</style>', 1)
    return template.replace('<script>', '<script>' + SHARED_JS, 1)
