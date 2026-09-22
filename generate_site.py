#!/usr/bin/env python3
"""Regenerates the whole website (docs/):
  pokedex.html, trainerdex.html, attackdex.html, items.html, guide.html, teambuilder.html
  manifest.json      counts per app + build id (cache-busting for the dock shell)
  search-index.json  the Spotlight search index used by docs/index.html
"""

import io
import os
import json
import time
import contextlib

import generate_pokedex as pdx
import generate_trainerdex as tdx
import generate_attackdex as adx
import generate_items as idx
import generate_guide as gdx
import generate_teambuilder as tbx
from site_shared import BASE


def quiet(fn, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a)


def main():
    t0 = time.time()
    for name, mod in [('Pokédex', pdx), ('Trainers', tdx), ('Moves', adx), ('Bag', idx), ('Guide', gdx), ('Team', tbx)]:
        print(f'== {name}')
        quiet(mod.generate)

    print('== Search index + manifest')
    mons = quiet(pdx.build_data)[0]
    trainers = quiet(tdx.build_data)[0]
    moves = quiet(adx.build_data)[0]
    items = quiet(idx.build_data)[0]
    pages = quiet(gdx.build_data)[0]

    index = []
    for p in mons:
        index.append(dict(t='mon', k=p['key'], n=p['name'],
                          s=f"#{p['dexNum']:03d} · " + ' / '.join(x.title() for x in p['types'])))
    for g in trainers:
        v = g['variants'][0]
        locs = sorted({l for vv in g['variants'] for l in vv['location']})
        index.append(dict(t='trainer', k=v['id'], n=g['name'], s=f"{g['category']} · {', '.join(locs[:2])}"))
    for m in moves:
        index.append(dict(t='move', k=m['name'], n=m['name'], s=f"{m['type'].title()} · {m['category']}"))
    for it in items:
        index.append(dict(t='item', k=it['key'], n=it['name'], s=it['pocket']))
    for pg in pages:
        team = pg['section'] in gdx.TEAM_SECTIONS
        index.append(dict(t='guide', k=pg['id'], n=pg['title'], s=pg['section'],
                          **(dict(a='teambuilder') if team else {})))
    index.append(dict(t='guide', k='', n='Team Builder', s='Six Pokémon · type charts and coverage', a='teambuilder'))
    for ab in quiet(gdx.ability_index):
        index.append(dict(t='ability', k=ab['key'], n=ab['name'], s=ab['sub']))

    docs = os.path.join(BASE, 'docs')
    with open(os.path.join(docs, 'search-index.json'), 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, separators=(',', ':'))
    manifest = dict(
        build=time.strftime('%Y%m%d%H%M%S'),
        counts=dict(pokedex=len(mons), trainers=len(trainers), moves=len(moves), bag=len(items), guide=sum(1 for p in pages if p['section'] not in gdx.TEAM_SECTIONS),
                    teambuilder=sum(1 for p in pages if p['section'] in gdx.TEAM_SECTIONS)),
    )
    with open(os.path.join(docs, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=1)
    print(f"  {len(index)} search entries; counts {manifest['counts']}")
    print(f'Done in {time.time() - t0:.1f}s')


if __name__ == '__main__':
    main()
