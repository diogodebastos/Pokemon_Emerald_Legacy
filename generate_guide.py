#!/usr/bin/env python3
"""Generates guide.html — hand-written player guide (trades, gift Pokémon, rematches).

Sibling of generate_pokedex.py / generate_trainerdex.py: bakes one self-contained
HTML file (content + sprites inlined as base64). Content is hand-written below but
every fact was checked against the decomp source; file refs sit next to each block.
"""

import os
import io
import json
import contextlib

import generate_pokedex as pdx
import generate_trainerdex as tdx

BASE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# In-game trades — src/data/trade.h (sIngameTrades). IVs listed HP/Atk/Def/SpA/SpD/Spe.
# Nature = personality % 25; gender = female if genderRatio > personality & 0xFF.
# ---------------------------------------------------------------------------
NPC_TRADES = [
    dict(get='NUMEL', nick='MEL', want='SHROOMISH', where='Rustboro City — house near the Gym',
         item='Chesto Berry', ot='MARLI · 38727', ability='Oblivious', nature='Relaxed', gender='♂',
         ivs='15 / 16 / 13 / 17 / 15 / 13'),
    dict(get='SNORUNT', nick='NIPPY', want='WHISMUR', where='Mauville City — Pokémon Center',
         item='—', ot='DANIELLA · 12345', ability='Inner Focus', nature='Hasty', gender='♀',
         ivs='14 / 14 / 14 / 15 / 14 / 15'),
    dict(get='LOUDRED', nick='ECHO', want='KECLEON', where='Fortree City — treehouse',
         item='Wood Mail', ot='ANTON · 08461', ability='Soundproof', nature='Naive', gender='♂',
         ivs='16 / 17 / 13 / 13 / 13 / 13'),
    dict(get='BAGON', nick='SEASOR', want='RELICANTH', where='Pacifidlog Town — house',
         item='Wave Mail', ot='SKYLAR · 46285', ability='Rock Head', nature='Brave', gender='♂',
         ivs='13 / 15 / 14 / 15 / 14 / 15'),
    dict(get='MEOWTH', nick='MEOWOW', want='SKITTY', where='Battle Frontier — house left of the Battle Tower',
         item='Retro Mail', ot='ISIS · 25945', ability='Pickup', nature='Naive', gender='♂',
         ivs='23 / 26 / 22 / 24 / 24 / 27'),
    dict(get='SEEDOT', nick='DOTS', want='RALTS', where='Battle Frontier — Pokémon Center',
         item='Chesto Berry', ot='KOBE · 38726', ability='Early Bird', nature='Relaxed', gender='♂',
         ivs='5 / 4 / 5 / 4 / 4 / 4'),
    dict(get='PLUSLE', nick='PLUSES', want='VOLBEAT', where='Battle Frontier — house right of the Pokémon Center',
         item='Wood Mail', ot='ROMAN · 08460', ability='Plus', nature='Hasty', gender='♀',
         ivs='4 / 4 / 4 / 5 / 4 / 5'),
]

# LittlerootTown_ProfessorBirchsLab/scripts.inc — RivalPostGame, keyed by VAR_STARTER_MON.
RIVAL_TRADES = [
    # (your starter, species the rival asks for, first gift, second gift)
    ('EEVEE',   'TREECKO', 'TORCHIC', 'MUDKIP'),
    ('ESPEON',  'TORCHIC', 'MUDKIP',  'TREECKO'),
    ('UMBREON', 'MUDKIP',  'TREECKO', 'TORCHIC'),
]

# ---------------------------------------------------------------------------
# Gift / prize Pokémon — every givemon / giveegg in data/maps.
# ---------------------------------------------------------------------------
STORY_GIFTS = [
    dict(sp='EEVEE', lvl='5', where='Route 101 — starter pick',
         req='Your partner Pokémon, received with your starter: pick Eevee → a second Eevee; '
             'pick Espeon → Umbreon; pick Umbreon → Espeon.'),
    dict(sp='CASTFORM', lvl='25', where='Weather Institute 2F (Route 119)',
         req='Defeat Team Aqua at the Weather Institute. Holds Mystic Water. If you miss it, a scientist there gives it to you later.'),
    dict(sp='EGG', lvl='Egg', name='Wynaut Egg', where='Lavaridge Town',
         req='Talk to the old woman by the hot springs with a free party slot.'),
    dict(sp='LILEEP', lvl='30', where='Devon Corp. 2F (Rustboro City)',
         req='Bring the Root Fossil from the Route 111 desert to the fossil researcher.'),
    dict(sp='ANORITH', lvl='30', where='Devon Corp. 2F (Rustboro City)',
         req='Bring the Claw Fossil from the Route 111 desert to the fossil researcher.'),
    dict(sp='SLAKING', lvl='50', where='Lilycove Contest Hall',
         req='Win a <b>Master Rank Cool</b> contest with a score of <b>800+</b> and let the artist hang the painting in the museum.'),
    dict(sp='MILOTIC', lvl='50', where='Lilycove Contest Hall',
         req='Win a <b>Master Rank Beauty</b> contest with a score of <b>800+</b> and let the artist hang the painting in the museum.'),
    dict(sp='DELCATTY', lvl='50', where='Lilycove Contest Hall',
         req='Win a <b>Master Rank Cute</b> contest with a score of <b>800+</b> and let the artist hang the painting in the museum.'),
    dict(sp='GARDEVOIR', lvl='50', where='Lilycove Contest Hall',
         req='Win a <b>Master Rank Smart</b> contest with a score of <b>800+</b> and let the artist hang the painting in the museum.'),
    dict(sp='AGGRON', lvl='50', where='Lilycove Contest Hall',
         req='Win a <b>Master Rank Tough</b> contest with a score of <b>800+</b> and let the artist hang the painting in the museum.'),
]
_KECLEON = 'Fortree City ×1, Route 120 ×7 (including the bridge), Route 119 ×2'
_HEART_SCALES = ('Routes 104, 105, 106, 115, 118, 109 ×3, 128 ×3, Lilycove City, '
                 'and underwater on Routes 124 ×2, 126 and 127')
POST_GIFTS = [
    dict(sp='BELDUM', lvl='5', where="Steven's House (Mossdeep City)",
         req='On the table after you enter the Hall of Fame.'),
    dict(sp='CHIKORITA', lvl='5', where="Birch's Lab (Littleroot Town)", also=['CYNDAQUIL', 'TOTODILE'],
         name='Chikorita · Cyndaquil · Totodile',
         req='After the National Dex upgrade, return with the <b>Hoenn Pokédex fully caught</b> (Jirachi and Deoxys not needed). '
             'Pick one; each new Hall of Fame entry lets you pick another until you have all three.'),
    dict(sp='BULBASAUR', lvl='5', where="Birch's Lab — your rival",
         req=f'After both rival starter trades, find all <b>10 hidden Kecleon</b> (use the Devon Scope): {_KECLEON}.'),
    dict(sp='CHARMANDER', lvl='5', where="Birch's Lab — your rival",
         req='After Bulbasaur, carry the <b>Red, Blue and Yellow Flutes</b> in your bag (crafted by the glass workshop on Route 113). They are not taken.'),
    dict(sp='SQUIRTLE', lvl='5', where="Birch's Lab — your rival",
         req=f'After Charmander, pick up all <b>16 hidden Heart Scales</b>: {_HEART_SCALES}.'),
    dict(sp='SNORLAX', lvl='25', where='Trainer Hill (Route 111)',
         req='Clear <b>Expert</b> mode. Snorlax is handed over on the clear <i>after</i> your first Expert clear, '
             'so a second Expert run always gets it.'),
    dict(sp='EEVEE', lvl='25', where='Trick House (Route 110)',
         req='Finish the final Trick House puzzle (needs the Hall of Fame). If your party and PC are full, collect it at the entrance later.'),
    dict(sp='PORYGON', lvl='25', where='Mauville Game Corner',
         req='Prize for <b>9999 coins</b>. Appears after the Jirachi wish event in Mossdeep.'),
    dict(sp='OMANYTE', lvl='30', where='Devon Corp. 2F (Rustboro City)', also=['KABUTO'],
         name='Omanyte · Kabuto',
         req='The Helix Fossil (Route 124) and Dome Fossil (Route 127) appear after the Jirachi wish event. Revive them at Devon.'),
    dict(sp='AERODACTYL', lvl='30', where='Devon Corp. 2F (Rustboro City)',
         req="Revive the Old Amber, Roxanne's reward for beating her Team 3 rematch."),
    dict(sp='EGG', lvl='Egg', name='Togepi Egg', where='Fortree City Gym',
         req="Winona's reward for beating her Team 3 rematch."),
    dict(sp='BELDUM', lvl='5', where="Scott's House (Battle Frontier)", shiny=True, name='Beldum ★',
         req='Collect all seven <b>Gold Symbols</b> and report to Scott (after claiming his Silver Symbol reward). This Beldum is <b>shiny</b>.'),
]

# ---------------------------------------------------------------------------
# Rematches — src/gym_leader_rematch.c, data/scripts/hall_of_fame.inc, gym scripts.
# ---------------------------------------------------------------------------
LEADER_PICS = {
    'ROXANNE': 'leader_roxanne', 'BRAWLY': 'leader_brawly', 'WATTSON': 'leader_wattson',
    'FLANNERY': 'leader_flannery', 'NORMAN': 'leader_norman', 'WINONA': 'leader_winona',
    'TATE_AND_LIZA': 'leader_tate_and_liza', 'JUAN': 'leader_juan',
}
LEADER_NAMES = {'TATE_AND_LIZA': 'Tate & Liza'}

BR_CATEGORIES = ['Supertrainers', 'Myth Trainers', 'Kanto Gauntlet', 'Johto Gauntlet',
                 'Kanto Elite Four', 'Frontier Brains', 'Special Trainers']


def build_pages(br_groups):
    def mon_title(k):
        return pdx.species_display_name(k)

    pages = []

    # --- Trades ---
    pages.append(dict(id='trades-npc', section='In-Game Trades', title='NPC Trades',
        kicker='Seven trades across Hoenn', blocks=[
        dict(type='p', html='Every NPC trade offers something more useful than the Pokémon it asks for. '
                            'The Pokémon you get arrives at the <b>same level</b> as the one you hand over, '
                            'holding the listed item. IVs are listed as HP / Atk / Def / SpA / SpD / Spe.'),
        dict(type='cards', items=[dict(
            sprite='mon:' + t['get'], title=mon_title(t['get']), sub=f'“{t["nick"]}” {t["gender"]}',
            place=t['where'], wantSprite='mon:' + t['want'], want=mon_title(t['want']),
            rows=[['Held', t['item']], ['OT · ID', t['ot']], ['Ability', t['ability']],
                  ['Nature', t['nature']], ['IVs', t['ivs']]],
        ) for t in NPC_TRADES]),
    ]))
    pages.append(dict(id='trades-rival', section='In-Game Trades', title='Rival Starter Trades',
        kicker="Birch's Lab · post-game", blocks=[
        dict(type='p', html="After you become Champion, talk to your rival (May or Brendan) in Professor Birch's lab. "
                            'They trade you the two Hoenn starters you don’t already have, one after the other. '
                            'Both ask for the <b>same</b> Hoenn starter, and which one depends on the starter you picked.'),
        dict(type='callout', html='You started with an Eeveelution, so you need to <b>catch</b> the Hoenn starter they ask for: '
                                  'Treecko on Route 101, Torchic on Route 102, Mudkip on Route 103.'),
        dict(type='table', head=['Your starter', 'They ask for (twice)', '1st trade', '2nd trade'], rows=[
            [dict(sprite='mon:' + a, text=mon_title(a)), dict(sprite='mon:' + b, text=mon_title(b)),
             dict(sprite='mon:' + c, text=mon_title(c)), dict(sprite='mon:' + d, text=mon_title(d))]
            for a, b, c, d in RIVAL_TRADES]),
        dict(type='p', html='Traded starters: OT MAY/BRENDAN · ID 42424, Brave nature, no held item. '
                            'Finishing both trades starts the rival’s <b>Kanto starter quest</b> (see Post-Game Gifts).'),
    ]))

    # --- Gifts ---
    def gift_cards(lst):
        items = []
        for g in lst:
            items.append(dict(sprite='mon:' + g['sp'], extra=['mon:' + a for a in g.get('also', [])],
                              shiny=g.get('shiny', False),
                              title=g.get('name') or mon_title(g['sp']),
                              sub=('Lv ' + g['lvl']) if g['lvl'] != 'Egg' else 'Egg',
                              place=g['where'], note=g['req']))
        return items
    pages.append(dict(id='gifts-story', section='Prize & Gift Pokémon', title='Story Gifts',
        kicker='Before the Hall of Fame', blocks=[
        dict(type='p', html='Pokémon you can be given during the main story. The contest prizes are available as soon as '
                            'you reach Master Rank, one per contest category.'),
        dict(type='cards', items=gift_cards(STORY_GIFTS)),
    ]))
    pages.append(dict(id='gifts-post', section='Prize & Gift Pokémon', title='Post-Game Gifts',
        kicker='After the Hall of Fame', blocks=[
        dict(type='p', html='Rewards for side content after you become Champion. The Kanto starters come from a quest '
                            'your rival starts after the <a onclick="selectPage(\'trades-rival\')">Rival Starter Trades</a>, and must be done in order.'),
        dict(type='cards', items=gift_cards(POST_GIFTS)),
    ]))

    # --- Rematches ---
    leader_rows = []
    for lid, (t2, reward) in tdx._GYM_LEADERS.items():
        leader_rows.append([
            dict(sprite='tr:' + LEADER_PICS[lid], text=LEADER_NAMES.get(lid, lid.title())),
            dict(text=t2 or 'Skipped. Juan only returns after the Hall of Fame, so his next fight is Team 3.'),
            dict(text=reward),
        ])
    pages.append(dict(id='rematch-gym', section='Rematches', title='Gym Leaders',
        kicker='Teams 2 – 5', blocks=[
        dict(type='p', html='Every Hoenn Gym Leader has four rematch teams. When a rematch is ready, just talk to the leader in their gym.'),
        dict(type='list', items=[
            'Rematches are <b>double battles</b>, so bring at least two healthy Pokémon.',
            'No PokéNav registration is needed. The game checks for new rematches as you walk around towns and routes, '
            "so if a leader isn't ready right after you meet a requirement, take a few steps outside and come back.",
            'Each team unlocks one at a time: you must beat a leader’s previous team first.',
        ]),
        dict(type='h', text='Unlock Tiers'),
        dict(type='table', head=['Team', 'Unlocks when'], rows=[
            [dict(text='Team 2'), dict(html='A story milestone, different per leader (below).')],
            [dict(text='Team 3'), dict(html=tdx._GYM_TIERS[3])],
            [dict(text='Team 4'), dict(html=tdx._GYM_TIERS[4])],
            [dict(text='Team 5'), dict(html=tdx._GYM_TIERS[5])],
        ]),
        dict(type='callout', html='<b>Fight Team 2 before entering the Hall of Fame.</b> Becoming Champion marks every '
                                  'unfought Team 2 as beaten, so you skip straight to Team 3 and can never battle those teams.'),
        dict(type='h', text='Per Leader'),
        dict(type='table', head=['Leader', 'Team 2 unlocks after', 'Reward for beating Team 3'], rows=leader_rows),
        dict(type='callout', html='Beating <b>all eight</b> leaders’ Team 3 releases <b>Articuno</b> (Shoal Cave), '
                                  '<b>Zapdos</b> (New Mauville) and <b>Moltres</b> (Magma Hideout).'),
    ]))
    pages.append(dict(id='rematch-league', section='Rematches', title='Elite Four & Champion',
        kicker='Pokémon League', blocks=[
        dict(type='p', html='After your first Hall of Fame entry, the Elite Four bring their rematch teams to every later League run, '
                            'and <b>Wallace</b> replaces Steven as the Champion. The League resets each time you enter the '
                            'Hall of Fame, so you can challenge it again and again.'),
        dict(type='table', head=['Trainer', 'Rematch'], rows=[
            [dict(sprite='tr:elite_four_sidney', text='Sidney'), dict(html='Double battle (a single battle if you have only one usable Pokémon).')],
            [dict(sprite='tr:elite_four_phoebe', text='Phoebe'), dict(html='Double battle (a single battle if you have only one usable Pokémon).')],
            [dict(sprite='tr:elite_four_glacia', text='Glacia'), dict(html='Double battle.')],
            [dict(sprite='tr:elite_four_drake', text='Drake'), dict(html='Double battle.')],
            [dict(sprite='tr:champion_wallace', text='Wallace'), dict(html='Champion on every run after your first.')],
        ]),
        dict(type='p', html='Every Hall of Fame entry also brings back any legendaries you knocked out instead of catching '
                            '(Mew, Latias/Latios, Deoxys, Lugia, Ho-Oh, Mewtwo, the legendary beasts and birds).'),
    ]))
    pages.append(dict(id='rematch-others', section='Rematches', title='Wally, Steven & Zinnia',
        kicker='Post-game rivals', blocks=[
        dict(type='table', head=['Trainer', 'Where', 'How to battle'], rows=[
            [dict(sprite='tr:wally', text='Wally'), dict(text='Victory Road exit'),
             dict(html=tdx.TRAINER_NOTES['WALLY_VR_2'] + ' ' + tdx.TRAINER_NOTES['WALLY_VR_3'])],
            [dict(sprite='tr:steven', text='Steven'), dict(text="Meteor Falls — Steven's Cave"),
             dict(html=tdx.TRAINER_NOTES['STEVEN_2'])],
            [dict(sprite='tr:zinnia', text='Zinnia'), dict(text='Sky Pillar'),
             dict(html=tdx.TRAINER_NOTES['ZINNIA'])],
            [dict(text='Craig, Weebra & Smith'), dict(text='Cave of Origin B1F'),
             dict(html='A trio of developers. Clearing Trainer Hill on <b>Expert</b> opens the Cave of Origin. '
                       'Beat Craig to reveal Weebra, then Weebra to reveal Smith. Each gives you a Regi doll. One battle each.')],
        ]),
    ]))

    br_blocks = [
        dict(type='p', html='Battle Royale mode fills the overworld with strong one-off trainers: Supertrainers, Myth Trainers, '
                            'the Kanto and Johto Gym Leaders, the Kanto Elite Four, and more. Turn it on by saying yes when Mom offers it '
                            '(when she gives you the Running Shoes, or later whenever she heals you at home). Mom can turn it off again too. '
                            'Each trainer battles you once.'),
    ]
    for cat in BR_CATEGORIES:
        rows = []
        for g in br_groups:
            if g['category'] != cat:
                continue
            locs = sorted({l for v in g['variants'] for l in v['location']})
            rows.append([dict(sprite=('trpic:' + g['picKey']) if g['picKey'] else None, text=g['name']),
                         dict(text=', '.join(locs) or '—')])
        if not rows:
            continue
        if cat == 'Frontier Brains':
            rows = [r for r in rows if r[0]['text'] != 'Zinnia']
            title = 'Frontier Brains (overworld)'
        elif cat == 'Special Trainers':
            title = 'Special Trainers (rebattle any time)'
        else:
            title = cat
        br_blocks.append(dict(type='h', text=title))
        br_blocks.append(dict(type='table', head=['Trainer', 'Location'], rows=rows))
    br_blocks.insert(1, dict(type='p', html='Red and Leaf are Battle Royale trainers too: Red is in the Sealed Chamber, Leaf on Route 130.'))
    pages.append(dict(id='rematch-br', section='Rematches', title='Battle Royale Trainers',
        kicker='Optional mode', blocks=br_blocks))
    return pages


def build_data():
    with contextlib.redirect_stdout(io.StringIO()):
        trainers, _, trainer_pics, _, _ = tdx.build_data()
    pages = build_pages(trainers)

    # Collect every sprite reference used by the pages and bake it once.
    refs = set()
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ('sprite', 'wantSprite') and v:
                    refs.add(v)
                elif k == 'extra':
                    refs.update(v)
                else:
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(pages)

    sprites = {}
    for ref in sorted(refs):
        kind, key = ref.split(':', 1)
        if kind == 'mon':
            folder = 'egg' if key == 'EGG' else tdx.species_sprite_folder(key)
            sprites[ref] = pdx.load_sprite_b64(folder)
        elif kind == 'shiny':
            sprites[ref] = pdx.load_sprite_b64(tdx.species_sprite_folder(key), shiny=True)
        elif kind == 'tr':
            sprites[ref] = tdx.load_trainer_pic_b64(key)
        elif kind == 'trpic':
            sprites[ref] = trainer_pics.get(key, '')
    # Shiny variants for cards flagged shiny
    for p in pages:
        for b in p['blocks']:
            for it in b.get('items', []) if b['type'] == 'cards' else []:
                if it.get('shiny'):
                    ref = 'shiny:' + it['sprite'].split(':', 1)[1]
                    sprites[ref] = pdx.load_sprite_b64(tdx.species_sprite_folder(ref.split(':', 1)[1]), shiny=True)
                    it['sprite'] = ref
    missing = [r for r, v in sprites.items() if not v]
    if missing:
        print(f'  WARNING: missing sprites for {missing}')
    return pages, sprites


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Emerald Legacy — Guide</title>
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
  }
</style>
</head>
<body>

<div id="sidebar">
  <div id="sidebar-header">
    <h1>Field Guide</h1>
    <span class="volume">Vol. IV · Trades · Gifts · Rematches</span>
  </div>
  <div id="page-list"></div>
</div>

<div id="main">
  <button id="btn-back" onclick="goBack()">← Return to Contents</button>
  <div id="page"></div>
</div>

<script>
const PAGES = GUIDE_PAGES_PLACEHOLDER;
const SPRITES = GUIDE_SPRITES_PLACEHOLDER;
const isMobile = () => window.innerWidth <= 700;
let currentPage = null;

function img(ref, alt) {
  const s = ref && SPRITES[ref];
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

function cell(c) {
  if ('sprite' in c) return `<span class="ent">${img(c.sprite, c.text)}${c.text}</span>`;
  return c.html !== undefined ? c.html : c.text;
}

function renderBlock(b) {
  switch (b.type) {
    case 'p': return `<p class="p">${b.html}</p>`;
    case 'h': return `<div class="section-title">${b.text}</div>`;
    case 'callout': return `<div class="callout">${b.html}</div>`;
    case 'list': return `<ul class="list">${b.items.map(i => `<li>${i}</li>`).join('')}</ul>`;
    case 'table':
      return `<div class="tbl-wrap"><table><thead><tr>${b.head.map(h => `<th>${h}</th>`).join('')}</tr></thead>
        <tbody>${b.rows.map(r => `<tr>${r.map(c => `<td>${cell(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
    case 'cards':
      return `<div class="cards">${b.items.map(it => `<div class="card">
        <div class="card-head">
          <div class="card-sprites">${img(it.sprite, it.title)}${(it.extra || []).map(e => img(e)).join('')}</div>
          <div><div class="card-title">${it.title}</div>${it.sub ? `<div class="card-sub">${it.sub}</div>` : ''}</div>
        </div>
        ${it.place ? `<div class="card-place">${it.place}</div>` : ''}
        ${it.want ? `<div class="card-want">Trade your ${img(it.wantSprite, it.want)}<span>${it.want}</span></div>` : ''}
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
    `<div class="kicker">${p.section} · ${p.kicker}</div><h2>${p.title}</h2>` + p.blocks.map(renderBlock).join('');
  if (isMobile()) {
    document.getElementById('sidebar').classList.add('hidden');
    document.getElementById('main').classList.remove('hidden');
  }
  document.getElementById('main').scrollTop = 0;
  window.scrollTo(0, 0);
}

renderList();
if (isMobile()) { goBack(); } else { selectPage(PAGES[0].id); }
</script>
</body>
</html>
'''


def generate():
    print('Building guide...')
    pages, sprites = build_data()

    def dump(o):
        return json.dumps(o, ensure_ascii=False, separators=(',', ':'))

    html = HTML_TEMPLATE.replace('GUIDE_PAGES_PLACEHOLDER', dump(pages))
    html = html.replace('GUIDE_SPRITES_PLACEHOLDER', dump(sprites))

    out_path = os.path.join(BASE, 'docs', 'guide.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  {len(pages)} pages, {len(sprites)} sprites')
    print(f'\nGenerated: {out_path} ({os.path.getsize(out_path) / 1024:.0f} KB)')


if __name__ == '__main__':
    generate()
