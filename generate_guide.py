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
import coverage_data as cov
import doubles_teams as dt

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
         req='Clear <b>Expert</b> mode. The owner hands Snorlax over the <i>next</i> time you claim a prize on the roof '
             '(any mode), not on the Expert clear itself.'),
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
            dict(sprite='tr:' + LEADER_PICS[lid], text=LEADER_NAMES.get(lid, lid.title()), link=['trainers', lid + '_2' if t2 else lid + '_3']),
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
            [dict(sprite='tr:elite_four_sidney', text='Sidney', link=['trainers', 'SIDNEY_2']), dict(html='Double battle (a single battle if you have only one usable Pokémon).')],
            [dict(sprite='tr:elite_four_phoebe', text='Phoebe', link=['trainers', 'PHOEBE_2']), dict(html='Double battle (a single battle if you have only one usable Pokémon).')],
            [dict(sprite='tr:elite_four_glacia', text='Glacia', link=['trainers', 'GLACIA_2']), dict(html='Double battle.')],
            [dict(sprite='tr:elite_four_drake', text='Drake', link=['trainers', 'DRAKE_2']), dict(html='Double battle.')],
            [dict(sprite='tr:champion_wallace', text='Wallace', link=['trainers', 'WALLACE_2']), dict(html='Champion on every run after your first.')],
        ]),
        dict(type='p', html='Every Hall of Fame entry also brings back any legendaries you knocked out instead of catching '
                            '(Mew, Latias/Latios, Deoxys, Lugia, Ho-Oh, Mewtwo, the legendary beasts and birds).'),
    ]))
    pages.append(dict(id='rematch-others', section='Rematches', title='Wally, Steven & Zinnia',
        kicker='Post-game rivals', blocks=[
        dict(type='table', head=['Trainer', 'Where', 'How to battle'], rows=[
            [dict(sprite='tr:wally', text='Wally', link=['trainers', 'WALLY_VR_2']), dict(text='Victory Road exit'),
             dict(html=tdx.TRAINER_NOTES['WALLY_VR_2'] + ' ' + tdx.TRAINER_NOTES['WALLY_VR_3'])],
            [dict(sprite='tr:steven', text='Steven', link=['trainers', 'STEVEN_2']), dict(text="Meteor Falls — Steven's Cave"),
             dict(html=tdx.TRAINER_NOTES['STEVEN_2'])],
            [dict(sprite='tr:zinnia', text='Zinnia', link=['trainers', 'ZINNIA']), dict(text='Sky Pillar'),
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



from thief_data import (collect_entries, ITEM_IMPORTANCE, MAP_PROGRESSION, map_rank)
from site_shared import load_item_icon_b64, xl


def build_thief_pages(tdex_groups):
    entries, item_const = collect_entries(tdex_groups)

    how = dict(id='thief-how', section='Where to Use Thief', title='How Thief Works',
        kicker='Steal held items from trainers', blocks=[
        dict(type='p', html='<b>Thief</b> (and <b>Covet</b>, which has the same effect) takes the target’s held item, and '
                            '<b>you keep it after the battle</b>. Many trainers hold competitive items such as Leftovers, '
                            'Choice Band and King’s Rock that are hard to find anywhere else.'),
        dict(type='h', text='Getting TM46 Thief'),
        dict(type='list', items=[
            'Free from the Team Aqua grunt in the <b>Slateport Oceanic Museum</b> (1F).',
            'Buy more at the <b>Lilycove Department Store</b> (4F) or the <b>Sootopolis City Poké Mart</b>.',
        ]),
        dict(type='h', text='Rules'),
        dict(type='list', items=[
            'The Pokémon using Thief must be holding <b>nothing</b>. Once it steals, it holds the item, so bring several empty-handed Thief users to take more than one item per battle.',
            'Thief has to hit and do damage. It fails against Pokémon with <b>Sticky Hold</b>, and <b>Mail</b> and the <b>Enigma Berry</b> can’t be stolen.',
            'Works in every normal trainer battle, including rematches and Battle Royale trainers. It does <b>not</b> work in <b>Trainer Hill</b>.',
            'A <b>Nugget</b> sells for ₽5,000, so trainers holding Nuggets are easy money.',
        ]),
        dict(type='callout', html='Tip: many trainers repeat forever. See <a onclick="selectPage(\'thief-farms\')">Repeatable Farms</a> '
                                  'to steal the same item again and again, or the <a onclick="selectPage(\'thief-items\')">Item Finder</a> '
                                  'to see who holds a specific item.'),
    ])

    farm = [e for e in entries if e['repeat']]
    rank = {'Gym Team 5: rebattle any time': 0, 'Every League run after becoming Champion': 1,
            'Rebattle any time': 2, 'Match Call rematch: their final team repeats': 3}
    farm.sort(key=lambda e: (rank[e['repeat']], e['label']))
    farms = dict(id='thief-farms', section='Where to Use Thief', title='Repeatable Farms',
        kicker='Steal the same items again and again', blocks=[
        dict(type='p', html='These trainers can be fought again and again, so their items can be stolen every time. '
                            'Gym Team 5 and the League unlock after the Hall of Fame (see '
                            '<a onclick="selectPage(\'rematch-gym\')">Gym Leaders</a>). Match Call trainers offer '
                            'rematches at random as you walk around; once you have beaten their last team, it repeats on every later rematch. '
                            'Your PokéNav shows who is ready.'),
        dict(type='table', head=['Trainer', 'Where', 'How it repeats', 'Held items'], rows=[
            [dict(sprite=('tr:' + e['pic']) if e['pic'] else None, text=e['label'],
                  link=['trainers', e['tv']] if e['tv'] else None),
             dict(text=', '.join(e['locs'])), dict(text=e['repeat']),
             dict(items=[dict(name=k, n=v, icon='item:' + item_const[k]) for k, v in sorted(e['counts'].items())])]
            for e in farm]),
    ])

    by_item = {}
    for e in entries:
        for it, n in e['counts'].items():
            by_item.setdefault(it, []).append((e, n))
    items = []
    for it, holders in by_item.items():
        tier, imp = ITEM_IMPORTANCE.get(it, ('C', 999))
        items.append(dict(name=it, icon='item:' + item_const[it], tier=tier, imp=imp,
                          count=sum(n for _, n in holders),
                          key=item_const[it],
                          holders=[dict(label=e['label'], n=n, tv=e['tv'], locs=', '.join(e['locs']), repeat=bool(e['repeat']),
                                        chrono=e['chrono'], post=e['phase'] == 2, br=e['br']) for e, n in holders]))
    finder = dict(id='thief-items', section='Where to Use Thief', title='Item Finder',
        kicker='Who holds what', blocks=[
        dict(type='p', html=f'Every held item on a reachable trainer’s team ({len(entries)} teams in total). '
                            '<b>↻</b> marks a repeatable fight, <b>Post</b> a post-game fight and <b>BR</b> a Battle Royale mode trainer. '
                            'Importance tiers (S → C) rank how useful an item is in Gen 3 battles. '
                            'Chronological order is by the earliest trainer you can steal each item from, following the story.'),
        dict(type='itemfinder', items=items),
    ])
    return [how, farms, finder]



# ---------------------------------------------------------------------------
# Battle Frontier & Trainer Hill — src/frontier_util.c, src/trainer_hill.c,
# data/maps/BattleFrontier_*/scripts.inc, src/data/battle_frontier/trainer_hill.h
# ---------------------------------------------------------------------------
NATURES = ['Hardy', 'Lonely', 'Brave', 'Adamant', 'Naughty', 'Bold', 'Docile', 'Relaxed', 'Impish', 'Lax',
           'Timid', 'Hasty', 'Serious', 'Jolly', 'Naive', 'Modest', 'Mild', 'Quiet', 'Bashful', 'Rash',
           'Calm', 'Gentle', 'Sassy', 'Careful', 'Quirky']
HILL_MODES = ['Normal', 'Variety', 'Unique', 'Expert']
# Prize per clear time (trainer_hill.c GetPrizeItemId; list chosen per mode from the fixed trainer data)
HILL_PRIZES = {
    'Normal':  ['ITEM_RARE_CANDY', 'ITEM_SAFARI_BALL', 'ITEM_PP_UP', 'ITEM_ELIXIR', 'ITEM_ETHER', 'ITEM_RED_SHARD'],
    'Variety': ['ITEM_PP_MAX', 'ITEM_SAFARI_BALL', 'ITEM_PP_UP', 'ITEM_ELIXIR', 'ITEM_ETHER', 'ITEM_BLUE_SHARD'],
    'Unique':  ['ITEM_SACRED_ASH', 'ITEM_SAFARI_BALL', 'ITEM_PP_UP', 'ITEM_ELIXIR', 'ITEM_ETHER', 'ITEM_GREEN_SHARD'],
    'Expert':  ['ITEM_MASTER_BALL', 'ITEM_SAFARI_BALL', 'ITEM_PP_UP', 'ITEM_ELIXIR', 'ITEM_ETHER', 'ITEM_YELLOW_SHARD'],
}
HILL_TIMES = ['Under 12:00', '12:00–12:59', '13:00–13:59', '14:00–15:59', '16:00–17:59', '18:00 or more']


def parse_trainer_hill():
    """-> {mode: [floor: [trainer: {name, cls, mons:[{sp, item, moves, nature}]}]]}.
    Trainer 1 on a floor uses mons[0..2], trainer 2 uses mons[3..5] (trainer_hill.c sTrainerPartySlots)."""
    import re
    text = open(os.path.join(BASE, 'src/data/battle_frontier/trainer_hill.h')).read()
    out = {}
    for mode in HILL_MODES:
        start = text.index(f'sFloors_{mode}[]')
        nxt = [text.find(f'sChallenge_{m}', start) for m in HILL_MODES]
        end = min([n for n in nxt if n > start] + [len(text)])
        block = text[start:end]
        floors = []
        for fchunk in re.split(r'\n    \[\d+\] =', block)[1:]:
            trainers = []
            names = list(re.finditer(r'\.name = _\("([^"]*)"\),\s*\.facilityClass = FACILITY_CLASS_(\w+)', fchunk))
            for ti, nm in enumerate(names):
                tend = names[ti + 1].start() if ti + 1 < len(names) else len(fchunk)
                tchunk = fchunk[nm.end():tend]
                slots = {}
                for m in re.finditer(r'\[(\d)\]\s*=\s*\{\s*\.species = SPECIES_(\w+),\s*\.heldItem = (ITEM_\w+),'
                                     r'\s*\.moves = \{([^}]*)\}(.*?)\.personality = (0x[0-9A-Fa-f]+|\d+)', tchunk, re.S):
                    slots[int(m.group(1))] = dict(
                        sp=m.group(2), item=m.group(3),
                        moves=[pdx.fmt_move(x.strip()) for x in m.group(4).split(',') if x.strip() and x.strip() != 'MOVE_NONE'],
                        nature=NATURES[int(m.group(6), 0) % 25])
                wanted = range(0, 3) if ti == 0 else range(3, 6)
                cls = ' '.join(w.capitalize() for w in nm.group(2).split('_') if w not in ('M', 'F'))
                trainers.append(dict(name=nm.group(1).title(), cls=cls, mons=[slots[i] for i in wanted if i in slots]))
            if trainers:
                floors.append(trainers)
        out[mode] = floors
    return out


def build_frontier_pages(item_names):
    def item(c):
        return dict(name=tdx.item_display(c, item_names), n=1, icon='item:' + c)

    S = 'Battle Frontier & Trainer Hill'
    pages = []
    pages.append(dict(id='frontier-start', section=S, title='Getting to the Frontier', kicker='Post-game', blocks=[
        dict(type='list', items=[
            'After the Hall of Fame, your Dad gives you the <b>S.S. Ticket</b>. Take the S.S. Tidal from Slateport or Lilycove.',
            'Meet <b>Scott</b> on the ship. After that, the Battle Frontier is a destination; you get the <b>Frontier Pass</b> at the reception gate.',
            '<b>Level modes:</b> in Lv.50 mode opponents are level 50; in Open Level they match your highest party level (minimum 60).',
            'Every facility awards <b>Battle Points (BP)</b> for each completed challenge, plus <b>+10 BP</b> for beating a Frontier Brain (capped at 9,999).',
        ]),
        dict(type='h', text='Banned Pokémon'),
        dict(type='p', html='Mewtwo, Ho-Oh, Lugia, Kyogre, Groudon, Rayquaza, Deoxys (Normal) and Deoxys (Attack) can’t enter. '
                            'Unlike vanilla Emerald, <b>Mew, Celebi, Jirachi, Deoxys (Defense) and Deoxys (Speed) are allowed</b>, '
                            'so the mythicals you find have somewhere to battle.'),
        dict(type='h', text='Symbols'),
        dict(type='p', html='Beat a facility’s Frontier Brain once for its <b>Silver Symbol</b> and again for the <b>Gold Symbol</b>. '
                            'Brains can show up in singles and doubles in this version (vanilla: singles only). '
                            'After you own both symbols, the Brain keeps coming back at the same streak intervals.'),
        dict(type='callout', html='Collect all seven <b>Silver Symbols</b> and <b>talk to Scott</b>: that unlocks the gym leaders’ '
                                  '<a onclick="selectPage(\'rematch-gym\')">Team 4 rematches</a> and <b>Mewtwo</b> in Altering Cave.'),
    ]))
    pages.append(dict(id='frontier-facilities', section=S, title='Facilities', kicker='7 challenges', blocks=[
        dict(type='table', head=['Facility', 'Rules', 'Brain', 'Modes', 'Brain appears at', 'BP per challenge'], rows=[
            [dict(html='<b>Battle Tower</b>'), dict(text='Rounds of 7 battles with 3 Pokémon (4 in doubles).'),
             dict(text='Anabel'), dict(text='Single, Double, Multi, Link Multi'),
             dict(text='Battle 35 (Silver), 70 (Gold), then every 35'), dict(text='Singles 1 → 15, Doubles 2 → 15, Multi 3 → 15')],
            [dict(html='<b>Battle Dome</b>'), dict(text='4-round tournaments; pick 2 of your 3 Pokémon for each match.'),
             dict(text='Tucker'), dict(text='Single, Double'),
             dict(text='5th tournament (Silver), 10th (Gold), then every 5'), dict(text='1, 1, 2, 2, 3, 3 … → 15')],
            [dict(html='<b>Battle Palace</b>'), dict(text='7 battles; your Pokémon pick their own moves based on their nature.'),
             dict(text='Spenser'), dict(text='Single, Double'),
             dict(text='Battle 21 (Silver), 42 (Gold), then every 21'), dict(text='Singles 4 → 15, Doubles 5 → 15')],
            [dict(html='<b>Battle Arena</b>'), dict(text='7 battles, 1-on-1; judged on Mind, Skill and Body after 3 turns.'),
             dict(text='Greta'), dict(text='Single'),
             dict(text='Battle 28 (Silver), 56 (Gold), then every 28'), dict(text='1, 1, 1, 2, 2, 2, 3 … → 15')],
            [dict(html='<b>Battle Factory</b>'), dict(text='7 battles with rental Pokémon; swap one after each win.'),
             dict(text='Noland'), dict(text='Single, Double'),
             dict(text='Battle 21 (Silver), 42 (Gold), then every 21'), dict(text='Singles 3 → 15, Doubles 4 → 15')],
            [dict(html='<b>Battle Pike</b>'), dict(text='14 rooms per challenge; choose 1 of 3 doors each time.'),
             dict(text='Lucy'), dict(text='Single'),
             dict(text='Room 28 (Silver), 140 (Gold), then every 56'), dict(text='1, 1, 2, 2, 2, 4, 4, 4, 8 … → 12')],
            [dict(html='<b>Battle Pyramid</b>'), dict(text='7 floors to explore with a separate bag; no outside items.'),
             dict(text='Brandon'), dict(text='Single'),
             dict(text='After floor 21 (Silver), 70 (Gold), then every 35'), dict(text='5, 5, 6, 6, 7 … → 15')],
        ]),
        dict(type='p', html='“Brain appears at” counts your current win streak in that facility and mode. '
                            'The overworld Anabel, Tucker, Spenser, Greta, Noland, Lucy and Brandon on Hoenn’s routes are '
                            '<a onclick="selectPage(\'rematch-br\')">Battle Royale trainers</a> with different teams.'),
    ]))
    bp_rows = [
        ['Vitamins', [('ITEM_PROTEIN', 1), ('ITEM_CALCIUM', 1), ('ITEM_IRON', 1), ('ITEM_ZINC', 1), ('ITEM_CARBOS', 1), ('ITEM_HP_UP', 1), ('ITEM_RARE_CANDY', 24)]],
        ['Held items', [('ITEM_LEFTOVERS', 48), ('ITEM_WHITE_HERB', 48), ('ITEM_QUICK_CLAW', 48), ('ITEM_MENTAL_HERB', 48),
                        ('ITEM_BRIGHT_POWDER', 64), ('ITEM_CHOICE_BAND', 64), ('ITEM_KINGS_ROCK', 64), ('ITEM_FOCUS_BAND', 64),
                        ('ITEM_SCOPE_LENS', 64), ('ITEM_METAL_COAT', 64)]],
        ['Berries', [('ITEM_LIECHI_BERRY', 48), ('ITEM_GANLON_BERRY', 48), ('ITEM_SALAC_BERRY', 48), ('ITEM_PETAYA_BERRY', 48),
                     ('ITEM_APICOT_BERRY', 48), ('ITEM_POMEG_BERRY', 3), ('ITEM_KELPSY_BERRY', 3), ('ITEM_QUALOT_BERRY', 3),
                     ('ITEM_HONDEW_BERRY', 3), ('ITEM_GREPA_BERRY', 3), ('ITEM_TAMATO_BERRY', 3)]],
    ]
    pages.append(dict(id='frontier-rewards', section=S, title='Rewards & Battle Points', kicker='Scott · Exchange · Tutors', blocks=[
        dict(type='h', text="Scott's House"),
        dict(type='table', head=['When', 'Reward'], rows=[
            [dict(text='First visit'), dict(text='1–4 BP, depending on how often you met Scott during the story')],
            [dict(text='All 7 Silver Symbols'), dict(items=[item('ITEM_LANSAT_BERRY')] + [dict(name=tdx.item_display(c, item_names), n=5, icon='item:' + c) for c in
                ('ITEM_HP_UP', 'ITEM_PROTEIN', 'ITEM_IRON', 'ITEM_CALCIUM', 'ITEM_ZINC', 'ITEM_CARBOS', 'ITEM_PP_UP')])],
            [dict(text='All 7 Gold Symbols'), dict(html='<b>Starf Berry</b> and a <b>shiny Beldum</b> (Lv.5)')],
            [dict(text='Battle Tower singles streak 50 / 100'), dict(text='Silver Shield / Gold Shield decorations')],
        ]),
        dict(type='h', text='Exchange Service Corner (BP)'),
        dict(type='table', head=['Clerk', 'Prizes'], rows=[
            [dict(text=name), dict(items=[dict(name=f'{tdx.item_display(c, item_names)} · {bp} BP', n=1, icon='item:' + c) for c, bp in lst])]
            for name, lst in bp_rows] + [[dict(text='Decorations'), dict(text='Dolls, cushions and posters (16–100 BP)')]]),
        dict(type='callout', html='<b>Move tutors in Lounge 7 are free</b> in this version (vanilla charged 16–48 BP). '
                                  'They teach Softboiled, Seismic Toss, Dream Eater, Mega Punch, Mega Kick, Body Slam, '
                                  'Rock Slide, Counter, Thunder Wave, Swords Dance, Defense Curl, Snore, Mud-Slap, Swift, Icy Wind, Endure, '
                                  'Psych Up, Ice Punch, ThunderPunch and Fire Punch.'),
        dict(type='h', text='Around the Frontier'),
        dict(type='list', items=[
            '<b>Frontier Mart</b> (money): Ultra Balls, healing items, all six vitamins and 20 TMs, including Psychic, Flamethrower, Ice Beam, Thunderbolt, Earthquake, Calm Mind, Bulk Up and Dragon Claw.',
            '<b>Lounge 1</b>: a Breeder rates your Pokémon’s best IV. <b>Lounge 5</b> explains how natures behave in the Battle Palace.',
            '<b>Lounge 3</b>: bet 5, 10 or 15 BP on another trainer’s challenge.',
            'In-game trades for Meowth, Seedot and Plusle (see <a onclick="selectPage(\'trades-npc\')">NPC Trades</a>).',
            'A strange tree on the east side is a <a class="xl" data-app="pokedex" data-key="SUDOWOODO">Sudowoodo</a> (Lv.40). Water it with the Wailmer Pail.',
        ]),
    ]))
    prize_rows = []
    for ti, t in enumerate(HILL_TIMES):
        prize_rows.append([dict(text=t)] + [dict(items=[item(HILL_PRIZES[m][ti])]) for m in HILL_MODES])
    pages.append(dict(id='trainer-hill', section=S, title='Trainer Hill', kicker='Route 111', blocks=[
        dict(type='list', items=[
            'Opens after the Hall of Fame. Four modes: <b>Normal, Variety, Unique and Expert</b>. Each has 4 floors with 2 trainers per floor.',
            'Opponents match your <b>highest party level</b>. You earn no EXP inside, and <b>Thief, Covet and Trick can’t take items</b> here.',
            'At the roof, the owner gives <b>one prize per run</b>, based on your clear time. Your best time per mode is recorded.',
        ]),
        dict(type='h', text='Prize by clear time'),
        dict(type='table', head=['Time'] + HILL_MODES, rows=prize_rows),
        dict(type='callout', html='A sub-12-minute <b>Expert</b> clear gives a <b>Master Ball</b> every time.'),
        dict(type='h', text='Expert rewards'),
        dict(type='list', items=[
            '<b><a class="xl" data-app="pokedex" data-key="SNORLAX">Snorlax</a></b> (Lv.25): clearing Expert readies it, and the owner hands it over the <b>next time</b> you claim a prize on the roof (any mode).',
            'Clearing Expert also opens the <b>Cave of Origin</b> developer trio (below).',
        ]),
        dict(type='h', text='Cave of Origin: Craig, Weebra & Smith'),
        dict(type='table', head=['Order', 'Trainer', 'Team (Lv.70, double battle)', 'Reward'], rows=[
            [dict(text='1'), dict(text='Craig'), dict(text='Meganium, Aerodactyl, Milotic, Rayquaza, Jolteon, Arcanine'), dict(text='Registeel Doll · reveals Weebra')],
            [dict(text='2'), dict(text='Weebra'), dict(text='Jirachi, Ludicolo, Gengar, Metagross, Latios, Hitmontop'), dict(text='Regice Doll · reveals Smith')],
            [dict(text='3'), dict(text='Smith'), dict(text='Kyogre, Zapdos, Starmie, Raikou, Suicune, Gengar'), dict(text='Regirock Doll')],
        ]),
    ]))
    hill = parse_trainer_hill()
    team_blocks = [dict(type='p', html='The fixed teams for every Trainer Hill mode. Levels scale to your highest party level. '
                                       'Hover over a Pokémon to see its moves.')]
    for mode in HILL_MODES:
        team_blocks.append(dict(type='h', text=mode))
        rows = []
        for fi, floor in enumerate(hill[mode]):
            for t in floor:
                rows.append([dict(text=f'Floor {fi + 1}'), dict(html=f'<b>{t["name"]}</b><br><span class="dim">{t["cls"]}</span>'),
                             dict(mons=[dict(sp=m['sp'], sprite='mon:' + m['sp'], name=pdx.species_display_name(m['sp']),
                                             item=tdx.item_display(m['item'], item_names), icon='item:' + m['item'] if m['item'] != 'ITEM_NONE' else None,
                                             moves=m['moves'], nature=m['nature']) for m in t['mons']])])
        team_blocks.append(dict(type='table', head=['Floor', 'Trainer', 'Team'], rows=rows))
    pages.append(dict(id='trainer-hill-teams', section=S, title='Trainer Hill Teams', kicker='All 4 modes', blocks=team_blocks))
    return pages


# ---------------------------------------------------------------------------
# Team Building — type coverage (coverage_data.py does the maths from the decomp).
# ---------------------------------------------------------------------------
# Hand-picked duos; the movesets themselves are computed, so they follow the learnsets.
# (a, a's attacking types, b, b's attacking types, doubles-safe?)
COVERAGE_DUOS = [
    ('BLAZIKEN', ['FIGHTING', 'FLYING', 'ROCK', 'FIRE'], 'FLYGON', ['GROUND', 'GRASS', 'DRAGON', 'DARK'], False),
    ('SCEPTILE', ['GRASS', 'DRAGON', 'DARK', 'FLYING'], 'BLAZIKEN', ['FIGHTING', 'GROUND', 'ROCK', 'FIRE'], False),
    ('TYRANITAR', ['FIGHTING', 'FLYING', 'ROCK', 'DARK'], 'FLYGON', ['GROUND', 'FIRE', 'GRASS', 'DRAGON'], False),
    ('SALAMENCE', ['FLYING', 'GROUND', 'ROCK', 'FIRE'], 'SCEPTILE', ['FIGHTING', 'GRASS', 'DRAGON', 'DARK'], False),
]
COVERAGE_SAFE_DUOS = [
    ('TYRANITAR', ['FIGHTING', 'FLYING', 'GROUND', 'ROCK'], 'FLYGON', ['FIRE', 'GRASS', 'DRAGON', 'DARK'], True),
    ('SCEPTILE', ['FIGHTING', 'GROUND', 'GRASS', 'DARK'], 'SALAMENCE', ['FLYING', 'ROCK', 'FIRE', 'DRAGON'], True),
]
TYPE_LABEL = {t: t.title() for t in cov.TYPES}
SPECIAL_LABELS = [TYPE_LABEL[t] for t in cov.TYPES if t not in cov.PHYSICAL]


def build_coverage_pages():
    D = cov.load()
    name = pdx.species_display_name
    hittable = cov.hittable()
    total_species = len(D['species'])
    k, min_sets = cov.minimum_covers()
    best8 = cov.best_sets(8, 1)[0]
    best8_hit = len(cov.covered_by(best8) & hittable)
    untouchable = cov.uncoverable()

    def mon(sp):
        return dict(sprite='mon:' + sp, sp=sp, name=name(sp))

    # Per attacking type: how many species it hits super effectively.
    bars = sorted(({'type': t, 'label': TYPE_LABEL[t], 'n': len(cov.coverage()[t])} for t in cov.TYPES),
                  key=lambda r: (-r['n'], r['label']))

    # Species with exactly one super-effective answer force that type into any full cover.
    only = {}
    for sp in sorted(hittable, key=lambda s: pdx.species_display_name(s)):
        ts = [t for t in cov.TYPES if sp in cov.coverage()[t]]
        if len(ts) == 1:
            only.setdefault(ts[0], []).append(sp)
    bottlenecks = [dict(types=[t], mons=[mon(s) for s in only[t]])
                   for t in sorted(only, key=lambda t: -len(only[t]))]
    # Pairs of answers that still pin the choice down (e.g. Koffing: Psychic only, because of Levitate).
    two = {}
    for sp in hittable:
        ts = tuple(t for t in cov.TYPES if sp in cov.coverage()[t])
        if len(ts) == 2 and not any(t in only for t in ts):
            two.setdefault(ts, []).append(sp)

    def ability_note(sp):
        ab = D['species'][sp]['abilities']
        return next((f'{a.replace("_", " ").title()}' for a in ab if a in cov.ABILITY_BLOCKS or a == 'THICK_FAT'), '')

    def duo_block(spec):
        a, at, b, bt, safe = spec
        return duo_view(cov.duo(a, at, b, bt, partner_safe=safe))

    def duo_view(d, matchups=None):
        a, b = d['a'], d['b']
        def moves(ms):
            return [dict(type=m['type'], name=pdx.fmt_move('MOVE_' + m['move']), power=m['power'], stab=m['stab'],
                         how=m['how'], spread=m['spread']) for m in ms]
        def side(sp, ms):
            return dict(mon=mon(sp), types=list(D['species'][sp]['types']), ability=' / '.join(
                x.replace('_', ' ').title() for x in sorted(D['species'][sp]['abilities'])), moves=moves(ms))
        if d['ally_hits']:
            user, mv, ally = d['ally_hits'][0]
            doubles = dict(ok=False, html=f'<b>Doubles:</b> {name(user)}’s {pdx.fmt_move("MOVE_" + mv)} also hits {name(ally)}.')
        else:
            spread = [(x, m) for x, ms in ((a, d['a_moves']), (b, d['b_moves'])) for m in ms if m['spread']]
            if spread:
                user, m = spread[0]
                ally = b if user == a else a
                why = 'Flying type' if 'FLYING' in D['species'][ally]['types'] else 'Levitate'
                doubles = dict(ok=True, html=f'<b>Doubles-safe:</b> {name(user)} carries {pdx.fmt_move("MOVE_" + m["move"])}, '
                                             f'and {name(ally)} is immune ({why}).')
            else:
                doubles = dict(ok=True, html='<b>Doubles-safe:</b> no move here hits the partner.')
        out = dict(a=side(a, d['a_moves']), b=side(b, d['b_moves']), hit=d['hit'], total=d['total'],
                   missed=[mon(s) for s in d['missed']], doubles=doubles)
        if matchups:
            out['matchups'] = dict(types=cov.TYPES, rows=[matchups[a], matchups[b]], names=[name(a), name(b)])
        return out

    def move_cell(ms):
        return ' '.join(f'<span class="mvchip" data-move="{pdx.fmt_move("MOVE_" + m["move"])}">'
                        f'<img class="tyicon" src="TYPEICON:{m["type"]}" alt="{TYPE_LABEL[m["type"]]}">'
                        f'{pdx.fmt_move("MOVE_" + m["move"])}</span>' for m in ms)

    with contextlib.redirect_stdout(io.StringIO()):
        legend_duos = cov.rank_duos(True, 8, legendary=True)
        def_plain = cov.rank_defensive_duos(10, legendary=False)
        def_legend = cov.rank_defensive_duos(8, legendary=True)
    legend_rows = [[dict(sprite='mon:' + d['a'], text=name(d['a'])), dict(html=move_cell(d['a_moves'])),
                    dict(sprite='mon:' + d['b'], text=name(d['b'])), dict(html=move_cell(d['b_moves']))] for d in legend_duos[2:]]

    def def_cards(lst):
        return [duo_view(cov.best_split(x['a'], x['b']), x['matchups']) for x in lst]

    def split_featured(lst, n):
        # Featured cards shouldn't repeat a Pokémon; everything else goes to the table.
        cards, used = [], set()
        for x in lst:
            if len(cards) < n and not ({x['a'], x['b']} & used):
                cards.append(x)
                used |= {x['a'], x['b']}
        return cards, [x for x in lst if x not in cards]
    def_plain_cards, def_plain_rest = split_featured(def_plain, 4)
    def_legend_cards, def_legend_rest = split_featured(def_legend, 2)

    def def_rows(lst):
        rows = []
        for x in lst:
            imm = [TYPE_LABEL[t] for i, t in enumerate(cov.TYPES) if min(x['matchups'][x['a']][i], x['matchups'][x['b']][i]) == 0]
            rows.append([dict(sprite='mon:' + x['a'], text=name(x['a'])), dict(sprite='mon:' + x['b'], text=name(x['b'])),
                         dict(html=f'<b>{x["resist"]}</b>/17'), dict(text=', '.join(imm) or '—'), dict(text=str(x['bulk']))])
        return rows

    with contextlib.redirect_stdout(io.StringIO()):
        more_safe = cov.rank_duos(True, 12)
    featured = {(x[0], x[2]) for x in COVERAGE_DUOS + COVERAGE_SAFE_DUOS}
    more_rows = []
    for d in more_safe:
        if (d['a'], d['b']) in featured or len(more_rows) >= 8:
            continue
        more_rows.append([dict(sprite='mon:' + d['a'], text=name(d['a'])), dict(html=move_cell(d['a_moves'])),
                          dict(sprite='mon:' + d['b'], text=name(d['b'])), dict(html=move_cell(d['b_moves']))])

    missed8 = sorted(hittable - cov.covered_by(best8))
    pages = []
    pages.append(dict(id='coverage-types', section='Team Building', title='Type Coverage',
        kicker='Can you hit everything?', blocks=[
        dict(type='p', html='Which attacking types hit every Pokémon in the game for <b>super-effective</b> damage? '
                            'This page is computed from the game’s own type chart, species data and abilities. '
                            'An ability that cancels the hit counts as a miss: <b>Levitate</b> (Ground), <b>Flash Fire</b> (Fire), '
                            '<b>Volt Absorb</b> (Electric), <b>Water Absorb</b> (Water), and <b>Thick Fat</b>, which turns a 2× Fire or Ice hit neutral. '
                            'This is Gen 3, so there is no Fairy type.'),
        dict(type='stats', items=[
            dict(value=str(total_species), label='Species, counting Deoxys forms'),
            dict(value=str(len(untouchable)), label='Nothing hits super effectively', mons=[mon(s) for s in untouchable]),
            dict(value=str(k), label='Fewest attacking types to hit the rest'),
            dict(value=f'{best8_hit}/{len(hittable)}', label='Best you can do with 8 moves'),
        ]),
        dict(type='callout', html=f'<b>Two Pokémon are not enough for full coverage.</b> Two Pokémon have 8 move slots, but hitting all {len(hittable)} '
                                  f'hittable species needs {k} attacking types. The best 8 types reach {best8_hit}. '
                                  '<b>Sableye</b> (Dark/Ghost) has no weaknesses at all in Gen 3.'),
        dict(type='h', text='Species hit super effectively, per attacking type'),
        dict(type='bars', total=total_species, rows=bars),
        dict(type='p', html='Covering the most species isn’t what matters. What matters is the Pokémon that <b>only one type</b> can hit. '
                            'Each group below forces its type into any complete set.'),
        dict(type='h', text='Pokémon with a single weakness'),
        dict(type='bottlenecks', items=bottlenecks),
        dict(type='h', text='Pokémon with exactly two weaknesses'),
        dict(type='p', html='These don’t force a single type, but each one needs one of its two answers in the set.'),
        dict(type='bottlenecks', items=[dict(types=list(ts), mons=[mon(x) for x in sorted(sps, key=name)])
                                        for ts, sps in sorted(two.items(), key=lambda kv: (-len(kv[1]), kv[0]))]),
        dict(type='h', text=f'Every {k}-type set that hits all {len(hittable)}'),
        dict(type='typesets', sets=[list(s) for s in min_sets]),
        dict(type='h', text='The best 8-type set'),
        dict(type='typesets', sets=[list(best8)], note=f'{best8_hit}/{len(hittable)} species. Misses:', mons=[mon(s) for s in missed8]),
        dict(type='p', html='For duos that carry this set, see <a onclick="selectPage(\'coverage-duos\')">Coverage Duos</a>.'),
    ]))

    pages.append(dict(id='coverage-duos', section='Team Building', title='Coverage Duos',
        kicker='Two Pokémon · eight moves', blocks=[
        dict(type='p', html=f'Each pair below splits the best 8 attacking types, four each, so together they hit '
                            f'<b>{best8_hit} of {len(hittable)}</b> Pokémon super effectively. Moves are the strongest reliable ones each Pokémon '
                            'can learn by level-up, TM/HM, tutor or egg move. That rules out moves with a charge turn or recharge, '
                            'self-KO moves, fixed-damage moves and Hidden Power. Every move shown has at least '
                            f'{cov.MIN_POWER} power, and <span class="stab">STAB</span> marks a same-type bonus.'),
        dict(type='h', text='Singles picks'),
        dict(type='duos', items=[duo_block(s) for s in COVERAGE_DUOS]),
        dict(type='h', text='Doubles-safe picks'),
        dict(type='p', html='<b>Earthquake hits your partner too.</b> In a double battle it hits both foes <i>and</i> your ally, and '
                            'Hoenn rematches are doubles. Give Earthquake to the Pokémon whose partner is immune to Ground, '
                            'either a <b>Flying</b> type or one with <b>Levitate</b>. The two duos below are the same idea as above, '
                            'with the Ground slot moved to the other Pokémon: Tyranitar fires Earthquake over a levitating Flygon, '
                            'and Sceptile fires it under a flying Salamence.'),
        dict(type='duos', items=[duo_block(s) for s in COVERAGE_SAFE_DUOS]),
        dict(type='h', text='More doubles-safe duos'),
        dict(type='p', html=f'Also {best8_hit}/{len(hittable)}, ranked by damage (move power × STAB × the attacking stat). '
                            'Legendaries are left out.'),
        dict(type='table', head=['Pokémon', 'Moves', 'Partner', 'Moves'], rows=more_rows),
        dict(type='h', text='Legendary duos'),
        dict(type='p', html=f'The same search with post-game legendaries allowed (every pair includes at least one; each legendary appears at most twice). '
                            f'It still tops out at {best8_hit}/{len(hittable)}, because no Pokémon beats the type chart, but the moves hit much harder. Every pair is still doubles-safe.'),
        dict(type='duos', items=[duo_view(d) for d in legend_duos[:2]]),
        dict(type='table', head=['Pokémon', 'Moves', 'Partner', 'Moves'], rows=legend_rows),
        dict(type='h', text='Defensive duos'),
        dict(type='p', html='Pairs that are hard to hit together. In doubles, spread moves such as Rock Slide, Surf, Heat Wave and Earthquake strike both Pokémon at once, so a defensive pair should have '
                            '<b>no shared weakness</b>, and <b>every weakness of one should be resisted or blocked by the other</b>. That way, whatever threatens one has a safe switch-in. '
                            f'Pairs are ranked by how many of the 17 attacking types at least one of them resists (worth {cov.RESIST_WEIGHT} points each), plus their combined base HP, Defense and Sp. Def. '
                            'Abilities count: Levitate, Flash Fire, Volt Absorb and Water Absorb are immunities, and Thick Fat halves Fire and Ice. '
                            'Each card also gives the pair its best doubles-safe attacking split.'),
        dict(type='duos', items=def_cards(def_plain_cards)),
        dict(type='table', head=['Pokémon', 'Partner', 'Resisted', 'Immune to', 'Base bulk'], rows=def_rows(def_plain_rest)),
        dict(type='h', text='Legendary defensive duos'),
        dict(type='duos', items=def_cards(def_legend_cards)),
        dict(type='table', head=['Pokémon', 'Partner', 'Resisted', 'Immune to', 'Base bulk'], rows=def_rows(def_legend_rest)),
        dict(type='h', text='Full coverage'),
        dict(type='callout', html='Add a <b>third</b> Pokémon with <b>Psychic + Ice</b> (Gardevoir, Alakazam or Starmie, for example). '
                                  'Psychic handles Koffing and Weezing, and Ice handles Gligar and Kingdra. That covers everything except Sableye.'),
    ]))
    return pages


# ---------------------------------------------------------------------------
# Double Battles — archetype teams (doubles_teams.py validates every set).
# ---------------------------------------------------------------------------
SMOGON_SOURCES = ('<a href="https://www.smogon.com/articles/adv-doubles-intro" target="_blank" rel="noopener">Introduction to ADV Doubles</a> and the '
                  '<a href="https://www.smogon.com/forums/threads/adv-doubles-ou.3666831/" target="_blank" rel="noopener">ADV Doubles OU</a> thread on Smogon')


def build_doubles_pages():
    import generate_items as gi
    with contextlib.redirect_stdout(io.StringIO()):
        items = {o['key']: o for o in gi.build_data()[0]}
    D = cov.load()
    name = pdx.species_display_name
    title = lambda c: c.replace('_', ' ').title()

    def target_label(mv):
        t = D['moves'][mv]['target']
        if t == 'MOVE_TARGET_BOTH':
            return 'both foes · ½'
        if t == 'MOVE_TARGET_FOES_AND_ALLY':
            return 'all · hits ally'
        return ''

    def member(mem):
        moves = []
        for d in dt.validate(mem, set(items)):
            mv = d['move']
            how_parts = [h for h in d['how'] if h != 'Egg move']
            if 'Egg move' in d['how'] and not how_parts:
                how_parts = ['Egg move · Move Relearner']
                if d.get('chain'):
                    chain = d['chain']
                    how_parts.append('or breed ' + ' → '.join(
                        [xl('pokedex', chain[0], name(chain[0])) + ' ♂'] + [xl('pokedex', c, name(c)) for c in chain[1:]]))
            tip = ''
            if d.get('warn'):
                alt = d['alt']
                tip = (f'<b>{pdx.fmt_move("MOVE_" + mv)}</b> is an egg move. Teach it with the {dt.RELEARNER}. '
                       f'{d["warn"]}<br><br>If you’d rather not use the relearner, use <b>{pdx.fmt_move("MOVE_" + alt["move"])}</b> '
                       f'({" · ".join(alt["how"])}).')
            moves.append(dict(type=d['type'], name=pdx.fmt_move('MOVE_' + mv),
                              power=d['power'] if d['power'] > 1 else ('—' if d['power'] == 0 else 'varies'),
                              target=target_label(mv) if d['power'] else '', how=' · '.join(how_parts), tip=tip,
                              alt=pdx.fmt_move('MOVE_' + d['alt']['move']) if d.get('alt') else ''))
        it = items['ITEM_' + mem['item']]
        return dict(sprite='mon:' + mem['sp'], sp=mem['sp'], name=name(mem['sp']), types=list(D['species'][mem['sp']]['types']),
                    ability=title(mem['ability']), item=dict(icon='item:' + it['key'], key=it['key'], name=it['name']),
                    nature=mem['nature'], moves=moves, note=mem['note'])

    # --- Basics: verified mechanics + learner tables straight from the data ---
    evolves = set(D['prevo'].values())
    final = lambda s: s not in evolves and s not in cov.LEGENDARY
    def learners(mv):
        return [dict(sprite='mon:' + s, sp=s, name=name(s)) for s in sorted(D['species'], key=name)
                if final(s) and mv in D['learn'][s]]
    spread_both = sorted((mv for mv, x in D['moves'].items() if x['target'] == 'MOVE_TARGET_BOTH' and x['power'] > 0), key=pdx.fmt_move)
    spread_all = sorted((mv for mv, x in D['moves'].items() if x['target'] == 'MOVE_TARGET_FOES_AND_ALLY' and x['power'] > 0), key=pdx.fmt_move)
    move_chips = lambda mvs: ' '.join(f'<span class="mvchip" data-move="{pdx.fmt_move("MOVE_" + mv)}"><img class="tyicon" src="TYPEICON:{D["moves"][mv]["type"]}" alt="">'
                                      f'{pdx.fmt_move("MOVE_" + mv)}</span>' for mv in mvs)
    immune = sorted((s for s in D['species'] if final(s) and cov.immune_to('GROUND', s)), key=name)

    pages = [dict(id='doubles-basics', section='Double Battles', title='Doubles Basics',
        kicker='Gen 3 rules, checked in the code', blocks=[
        dict(type='p', html='On this version <b>every battle is a double battle</b>, trainers and wild encounters alike. '
                            'These are the Gen 3 rules that decide them. Each one was checked against the battle code, because several work '
                            'differently from newer games. The team ideas are adapted from ' + SMOGON_SOURCES + ', then checked move by move against this hack’s learnsets, '
                            'abilities, items and breeding.'),
        dict(type='table', head=['Mechanic', 'How it works in this game'], rows=[
            [dict(html='<b>Spread moves</b>'), dict(html='Moves that hit <b>both foes</b> (Surf, Rock Slide, Heat Wave, Blizzard…) deal <b>half damage</b> to each while both foes are standing. They never hit your partner.')],
            [dict(html='<b>Earthquake &amp; Explosion</b>'), dict(html='Hit <b>everyone else</b> at <b>full power</b>, including your partner. Pair Earthquake with a Flying type or Levitate. Explosion also halves the target’s Defense, and Ghost types are immune.')],
            [dict(html='<b>Physical / special</b>'), dict(html='Decided by type, not by move. ' + ', '.join(SPECIAL_LABELS[:-1]) + ' and ' + SPECIAL_LABELS[-1] + ' are special, so Dragon Claw and Shadow Ball use Sp. Atk. The other types are physical. This hack swaps Dark and Ghost: Crunch uses Attack.')],
            [dict(html='<b>Fake Out</b>'), dict(html='Priority, and the target flinches, but only on the user’s first turn out. Inner Focus blocks the flinch.')],
            [dict(html='<b>Follow Me</b>'), dict(html='Redirects every <b>single-target</b> move from the other side to the user for that turn. It doesn’t redirect spread moves.')],
            [dict(html='<b>Helping Hand</b>'), dict(html='Priority. The partner’s move this turn does ×1.5 damage.')],
            [dict(html='<b>Intimidate</b>'), dict(html='Lowers the Attack of both foes when the user enters. Clear Body, Hyper Cutter and White Smoke block it.')],
            [dict(html='<b>Weather</b>'), dict(html='Rain Dance, Sunny Day, Sandstorm and Hail last <b>5 turns</b>. Weather from Sand Stream, Drought or Drizzle never wears off; only another weather replaces it. '
                                                      'Rain: Water ×1.5, Fire ×0.5, Thunder never misses. Sun: Fire ×1.5, Water ×0.5, one-turn Solar Beam, Thunder 50% accuracy. Hail: Blizzard never misses.')],
            [dict(html='<b>Swift Swim / Chlorophyll</b>'), dict(html='Double Speed in rain / sun.')],
            [dict(html='<b>Lightning Rod</b>'), dict(html='Pulls the <b>opponents’</b> single-target Electric moves onto the holder. It gives <b>no immunity</b> in Gen 3, so pair it with a Ground type (Marowak, Rhydon).')],
            [dict(html='<b>Plus / Minus</b>'), dict(html='×1.5 Sp. Atk while a Pokémon with the other ability is on the field.')],
            [dict(html='<b>Wonder Guard</b>'), dict(html='Blocks every hit that isn’t super effective, <b>including your partner’s</b> Earthquake.')],
            [dict(html='<b>Reflect / Light Screen</b>'), dict(html='Reduce damage to <b>⅔</b> (not ½) while both Pokémon on the protected side are standing. They also reduce spread moves. Critical hits ignore them, and Brick Break removes them.')],
            [dict(html='<b>Protect</b>'), dict(html='Blocks everything, spread moves included. Each consecutive use is half as likely to work (100% → 50% → 25% → 12.5%).')],
        ]),
        dict(type='h', text='Hits both foes · ½ damage'),
        dict(type='p', html=move_chips(spread_both)),
        dict(type='h', text='Hits everyone, partner included · full damage'),
        dict(type='p', html=move_chips(spread_all)),
        dict(type='h', text='Earthquake-safe partners'),
        dict(type='p', html='Fully evolved Pokémon that take no damage from a partner’s Earthquake (Flying types and Levitate):'),
        dict(type='monlist', mons=[dict(sprite='mon:' + s, sp=s, name=name(s)) for s in immune]),
        dict(type='h', text='Who learns the support moves'),
        dict(type='p', html='Fully evolved, non-legendary Pokémon that can learn each move by any method (level-up, TM, tutor or egg move).'),
        dict(type='table', head=['Move', 'Learned by'], rows=[
            [dict(html=move_chips([mv])), dict(mons=[dict(sprite=x['sprite'], sp=x['sp'], name=x['name'], nature='', moves=[], item='') for x in learners(mv)])]
            for mv in ['FAKE_OUT', 'FOLLOW_ME', 'HELPING_HAND', 'ENCORE']]),
        dict(type='p', html='See also <a onclick="selectPage(\'coverage-duos\')">Coverage Duos</a>, which pairs movesets so Earthquake never hits the partner.'),
    ])]

    # Region-locked teams: prove every member really is from that region's dex range.
    dex_order = pdx.parse_national_dex_order(os.path.join(BASE, 'include/constants/pokedex.h'))
    for t in dt.TEAMS:
        for group in [t] + list(t.get('variants') or []):
            if not group.get('region'):
                continue
            label, lo, hi, *exempt = group['region']
            exempt = set(exempt[0]) if exempt else set()
            for x in group['members']:
                n = dex_order.get(x['sp'])
                if x['sp'] not in exempt and not (n and lo <= n <= hi):
                    raise ValueError(f"{t['id']}: {x['sp']} (#{n}) is not a {label} Pokémon ({lo}-{hi})")

    # "Before the Elite Four" teams: every member (or a pre-evolution) must be catchable before the
    # post-game, and every move needs a source other than the post-game Battle Frontier tutors.
    wild = pdx.parse_encounters(os.path.join(BASE, 'src/data/wild_encounters.json'))
    for t in dt.TEAMS:
        if not t.get('pre_e4'):
            continue
        for x in [x for g in [t] + list(t.get('variants') or []) for x in g['members']]:
            line = [x['sp']]
            while line[-1] in D['prevo']:
                line.append(D['prevo'][line[-1]])
            if not any(not l['postgame'] for s in line for l in wild.get(s, [])):
                raise ValueError(f"{t['id']}: {x['sp']} can't be caught before the Elite Four")
            for mv in x['moves']:
                mv = mv[0] if isinstance(mv, tuple) else mv
                if all('Battle Frontier' in h for h in D['learn'][x['sp']][mv]):
                    raise ValueError(f"{t['id']}: {x['sp']}'s {mv} only comes from a post-game Battle Frontier tutor")

    STAT_LABEL = dict(hp='HP', atk='Attack', def_='Defense', spa='Sp. Atk', spd='Sp. Def', spe='Speed')
    team_pages = []
    for t in dt.TEAMS:
        members = [member(x) for x in t['members']]
        for x, src in zip(members, t['members']):
            stat = src.get('stat') or t.get('stat')
            if stat:
                key = 'def_' if stat == 'def' else stat
                x['stat'] = f'Base {STAT_LABEL[key]} {D["species"][x["sp"]]["base"][key]}'
        team_pages.append(dict(id='team-' + t['id'], section=t.get('group', 'Double Battles'), title=t['name'], kicker=t['tag'], blocks=[
            dict(type='p', html=t['blurb']),
            dict(type='leads', leads=[[dict(sprite='mon:' + s, sp=s, name=name(s)) for s in pair] for pair in t['leads']]),
            dict(type='team', members=members),
        ] + [b for v in (t.get('variants') or []) for b in (
            dict(type='h', text=v['name']),
            dict(type='p', html=v['blurb']),
            dict(type='team', members=[member(x) for x in v['members']]),
        )] + [
            dict(type='p', html='<span class="dim">Every move, ability and item here was checked against this hack’s data. '
                                'Egg moves can be taught by the ' + dt.RELEARNER + ', and a working breeding father is listed when one exists. A ⚑ marks an egg move that breeding can’t deliver: hover it for the fallback. Tutors in this hack teach any number of times, and the Battle Frontier tutors are free.</span>'),
        ]))

    pages += [p for p in team_pages if p['section'] == 'Double Battles']
    specialist_pages = [p for p in team_pages if p['section'] != 'Double Battles']
    combo_blocks = [dict(type='p', html='Two-Pokémon combos that only work in doubles. Each relies on a mechanic confirmed in this game’s battle code.')]
    for c in dt.COMBOS:
        combo_blocks.append(dict(type='h', text=c['name']))
        combo_blocks.append(dict(type='p', html=c['html']))
        combo_blocks.append(dict(type='team', members=[member(x) for x in c['pair']]))
    pages.append(dict(id='doubles-combos', section='Double Battles', title='Partner Combos', kicker='Pairs that only work in doubles', blocks=combo_blocks))
    return pages + specialist_pages


def load_type_icon_b64(t):
    return pdx.load_type_icon_b64(t)


def build_data():
    with contextlib.redirect_stdout(io.StringIO()):
        trainers, _, trainer_pics, _, _ = tdx.build_data()
    item_names = tdx.parse_item_names(os.path.join(BASE, 'src/data/items.h'))
    pages = build_pages(trainers) + build_thief_pages(trainers) + build_frontier_pages(item_names) + build_coverage_pages() + build_doubles_pages()

    # Collect every sprite reference used by the pages and bake it once.
    refs = set()
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ('sprite', 'wantSprite', 'icon') and v:
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
        elif kind == 'item':
            sprites[ref] = load_item_icon_b64(key)
    for t in cov.TYPES:
        sprites['type:' + t] = load_type_icon_b64(t)
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
  .duo-doubles { display: flex; gap: 10px; align-items: baseline; font-size: 13px; line-height: 1.5; padding: 8px 12px; color: var(--ink-dim); }
  .duo-doubles.ok { border: 1px solid var(--jade-bright); background: var(--jade-soft); }
  .duo-doubles.warn { border: 1px solid var(--dusk); background: var(--dusk-soft); }
  .duo-doubles .glyph { font-weight: 700; }
  .duo-doubles.ok .glyph { color: var(--jade-bright); }
  .duo-doubles.warn .glyph { color: var(--dusk); }
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
</style>
</head>
<body>

<div id="sidebar">
  <div id="sidebar-header">
    <h1>Field Guide</h1>
    <span class="volume">Vol. IV · Trades · Gifts · Rematches · Thief · Coverage · Doubles</span>
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
    <div class="duo-doubles ${d.doubles.ok ? 'ok' : 'warn'}"><span class="glyph">${d.doubles.ok ? '✓' : '⚠'}</span><span>${d.doubles.html}</span></div>
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
      return `<div class="team">${b.members.map(renderMember).join('')}</div>`;
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

renderList();
registerApp('guide', key => selectPage(key));
if (!currentPage && !isMobile()) selectPage(PAGES[0].id);
</script>
</body>
</html>
'''


def generate():
    print('Building guide...')
    pages, sprites = build_data()

    def dump(o):
        return json.dumps(o, ensure_ascii=False, separators=(',', ':'))

    import site_shared
    html = site_shared.inject(HTML_TEMPLATE).replace('GUIDE_PAGES_PLACEHOLDER', dump(pages))
    html = html.replace('GUIDE_SPRITES_PLACEHOLDER', dump(sprites))

    out_path = os.path.join(BASE, 'docs', 'guide.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  {len(pages)} pages, {len(sprites)} sprites')
    print(f'\nGenerated: {out_path} ({os.path.getsize(out_path) / 1024:.0f} KB)')


if __name__ == '__main__':
    generate()
