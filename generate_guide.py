#!/usr/bin/env python3
"""Generates guide.html — hand-written player guide (trades, gift Pokémon, rematches).

Sibling of generate_pokedex.py / generate_trainerdex.py: bakes one self-contained
HTML file (content + sprites inlined as base64). Content is hand-written below but
every fact was checked against the decomp source; file refs sit next to each block.
"""

import os
import io
import re
import json
import contextlib
from functools import lru_cache

import generate_pokedex as pdx
import generate_trainerdex as tdx
import coverage_data as cov
import guide_pages
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


# ---------------------------------------------------------------------------
# Safari Zone — src/safari_zone.c (30 balls, 500 steps, Pokéblock feeders),
# src/battle_util.c (catch / escape factors), src/battle_script_commands.c
# (Cmd_handleballthrow), src/wild_encounter.c (PickWildMonNature),
# data/scripts/safari_zone.inc and data/maps/SafariZone_*/map.json.
# Which areas need which bike was checked by flood-filling the six 40×40
# layouts in data/layouts/SafariZone_* against their collision bits.
# ---------------------------------------------------------------------------
SAFARI_AREAS = ['South', 'Southwest', 'Northwest', 'North', 'Northeast', 'Southeast']
SAFARI_METHODS = [('land_mons', 'Grass'), ('water_mons', 'Surfing'),
                  ('rock_smash_mons', 'Rock Smash'), ('fishing_mons', None)]
ROD_LABELS = {'old_rod': 'Old Rod', 'good_rod': 'Good Rod', 'super_rod': 'Super Rod'}
# Pokémon the Legacy tables put in the Safari Zone that vanilla Emerald never did.
SAFARI_NEW = {'BULBASAUR', 'CHARMANDER', 'SQUIRTLE', 'CHIKORITA', 'CYNDAQUIL', 'TOTODILE', 'MURKROW'}
# Pokéblock feeder tiles (MB_POKEBLOCK_FEEDER) counted per layout.
SAFARI_FEEDERS = {'South': 1, 'Southwest': 1, 'Northwest': 3, 'North': 2, 'Northeast': 1, 'Southeast': 3}
# Item Balls and Itemfinder spots from data/maps/SafariZone_*/map.json.
SAFARI_ITEMS = {
    'South': ([], []),
    'Southwest': (['ITEM_MAX_REVIVE'], []),
    'Northwest': (['ITEM_TM_SOLAR_BEAM'], []),
    'North': (['ITEM_CALCIUM'], []),
    'Northeast': (['ITEM_NUGGET'], ['ITEM_RARE_CANDY', 'ITEM_ZINC']),
    'Southeast': (['ITEM_BIG_PEARL'], ['ITEM_PP_UP', 'ITEM_FULL_RESTORE']),
}
SAFARI_ACCESS = {
    'South': ('Walk in', 'The entrance area, and the only way out. Acro Bike rails run along its north edge; '
                         'the east gate is walled off by two construction workers until the Hall of Fame.'),
    'Southwest': ('Walk west from South', 'Holds the <b>Rest House</b> and the first water. A muddy slope climbs '
                                          'out of its north-west corner.'),
    'Northwest': ('<b>Mach Bike</b> up the muddy slope in Southwest', 'The only area you cannot reach on foot '
                  'or with the Acro Bike — the slope is the single way in.'),
    'North': ('<b>Acro Bike</b> over the rails at the top of South', 'Rock Smash rocks and a bumpy slope inside '
              'that also needs the Acro Bike.'),
    'Northeast': ('Walk north from Southeast, or east from North', 'Part of the expansion. No bike needed if you '
                  'come up through Southeast.'),
    'Southeast': ('Walk east from South once the expansion opens', 'Part of the expansion. No bike needed.'),
}
SAFARI_POSTGAME = {'Northeast', 'Southeast'}


def parse_catch_rates(path):
    """SPECIES_X -> catchRate, from src/data/pokemon/species_info.h."""
    import re
    with open(path) as f:
        content = f.read()
    out = {}
    blocks = re.split(r'\[SPECIES_(\w+)\]\s*=\s*\{', content)
    i = 1
    while i < len(blocks) - 1:
        m = re.search(r'\.catchRate\s*=\s*(\d+)', blocks[i + 1])
        if m:
            out[blocks[i].strip()] = int(m.group(1))
        i += 2
    return out


def safari_encounters():
    """{area: [(method label, [(species, chance %, min lvl, max lvl), …]), …]}."""
    with open(os.path.join(BASE, 'src/data/wild_encounters.json')) as f:
        group = json.load(f)['wild_encounter_groups'][0]
    rates = {f['type']: f['encounter_rates'] for f in group['fields']}
    rods = next(f for f in group['fields'] if f['type'] == 'fishing_mons')['groups']

    def agg(mons, kind, idxs):
        total = sum(rates[kind][i] for i in idxs)
        acc = {}
        for i in idxs:
            m = mons[i]
            sp = m['species'].replace('SPECIES_', '')
            n, lo, hi = acc.get(sp, (0, 999, 0))
            acc[sp] = (n + rates[kind][i], min(lo, m['min_level']), max(hi, m['max_level']))
        rows = [(sp, 100.0 * n / total, lo, hi) for sp, (n, lo, hi) in acc.items()]
        return sorted(rows, key=lambda r: (-r[1], r[0]))

    out = {}
    for enc in group['encounters']:
        if not enc['map'].startswith('MAP_SAFARI_ZONE_'):
            continue
        area = enc['map'].replace('MAP_SAFARI_ZONE_', '').title()
        if area not in SAFARI_AREAS:
            continue
        tables = []
        for kind, label in SAFARI_METHODS:
            if kind not in enc:
                continue
            mons = enc[kind]['mons']
            if label:
                tables.append((label, agg(mons, kind, range(len(mons)))))
            else:
                for rod, idxs in rods.items():
                    tables.append((ROD_LABELS[rod], agg(mons, kind, idxs)))
        out[area] = tables
    return out


def build_safari_pages(item_names):
    S = 'Safari Zone'
    catch_rates = parse_catch_rates(os.path.join(BASE, 'src/data/pokemon/species_info.h'))
    enc = safari_encounters()

    def item(c):
        return dict(name=tdx.item_display(c, item_names), n=1, icon='item:' + c)

    def mon_cell(sp):
        return dict(sprite='mon:' + sp, text=pdx.species_display_name(sp))

    def pct(p):
        return f'{p:g}%'

    def lvl(lo, hi):
        return f'Lv.{lo}' if lo == hi else f'Lv.{lo}–{hi}'

    def factor(sp):
        return catch_rates.get(sp, 0) * 100 // 1275

    pages = []

    # --- Basics ---
    pages.append(dict(id='safari-basics', section=S, title='How the Safari Game Works',
        kicker='Route 121 · ¥500', blocks=[
        dict(type='p', html='The Safari Zone sits on <b>Route 121</b>, between Lilycove and Mt. Pyre. '
                            'You cannot send out your own Pokémon inside: every encounter is a catching puzzle '
                            'solved with Safari Balls, Pokéblocks and patience.'),
        dict(type='h', text='Admission'),
        dict(type='list', items=[
            '<b>¥500</b> per game, and you must be carrying the <b>Pokéblock Case</b> — the attendant turns you away '
            'without one. It comes from the Lilycove Contest Hall.',
            'You are handed <b>30 Safari Balls</b>. The game ends when they run out, when you have walked '
            '<b>500 steps</b>, or when you retire at the entrance. Unused balls are taken back; the admission is not refunded.',
            'Steps only tick on the field, so battles, fishing and Pokéblock menus are free.',
            'Everything you catch is yours. A full party and a full PC stop you at the counter.',
        ]),
        dict(type='h', text='Your four options in a Safari encounter'),
        dict(type='table', head=['Option', 'What it does'], rows=[
            [dict(html='<b>Safari Ball</b>'),
             dict(html='Throws at the Pokémon’s <b>catch factor</b> — a 0–20 number the game builds from the species’ '
                       'catch rate as <b>rate × 100 ÷ 1275</b>, then converts back at 12.75 per point. '
                       'A catch rate of 255 gives 20, 190 gives 14, and anything from 39 to 50 gives 3 — which the ball then reads back as a catch rate of 38. '
                       'The Safari Ball itself is worth 1.5×, the same as a Great Ball.')],
            [dict(html='<b>Go near</b>'),
             dict(html='Adds <b>+4, then +3, +2, +1</b> to the catch factor on successive uses (it stops at 20) — '
                       'but <b>+4 to the escape factor every single time</b>. Two creeps make most Pokémon more likely '
                       'to bolt than to be caught.')],
            [dict(html='<b>Pokéblock</b>'),
             dict(html='Only ever <b>lowers the escape factor</b>; it never helps you catch. The drop depends on how '
                       'many blocks you have already thrown and on how the Pokémon reacts (see below).')],
            [dict(html='<b>Run</b>'), dict(html='Always works. Costs nothing but the steps you spent walking there.')],
        ]),
        dict(type='h', text='The escape factor'),
        dict(type='p', html='Every turn, the Pokémon rolls to flee at <b>escape factor × 5%</b>. A fresh encounter '
                            'starts at <b>3</b>, so 15% per turn — which is why a long fight usually ends with an empty patch of grass.'),
        dict(type='table', head=['Pokéblock throw', 'Enthralled', 'Curious', 'Ignored'], rows=[
            [dict(text='1st'), dict(text='−5'), dict(text='−3'), dict(text='no effect')],
            [dict(text='2nd'), dict(text='−3'), dict(text='−2'), dict(text='no effect')],
            [dict(text='3rd and later'), dict(text='−2'), dict(text='−1'), dict(text='no effect')],
        ]),
        dict(type='list', items=[
            '<b>Enthralled</b> — the block’s flavour is one the Pokémon’s nature likes.',
            '<b>Curious</b> — the nature is neutral about every flavour in the block.',
            '<b>Ignored</b> — the nature dislikes it. The throw is wasted.',
        ]),
        dict(type='callout', html='<b>The flee lock.</b> A throw that would take the escape factor below 1 clamps to 1, '
                                  'but a throw that lands on <b>exactly 0</b> is allowed — and 0 × 5% means the Pokémon '
                                  '<b>can never run away</b>. A fresh encounter sits at 3, and a <b>curious</b> first block is −3. '
                                  'So a block the Pokémon is <i>neutral</i> about locks it in place for good, while an '
                                  '<b>enthralled</b> −5 only clamps to 1 (5% a turn). Lock it down first, then throw balls '
                                  'until it gives in — never “go near” afterwards, since that adds 4 back.'),
        dict(type='h', text='Pokéblock feeders'),
        dict(type='p', html='The square boxes scattered through the zone take a Pokéblock and keep it for <b>100 steps</b>. '
                            'While it sits there, any wild Pokémon you meet within <b>5 tiles</b> of the feeder has an '
                            '<b>80% chance</b> to be rolled with a nature that <i>likes</i> that block’s flavour. '
                            'The game tracks up to 10 baited feeders at once; the zone has 11 of them.'),
        dict(type='list', items=[
            'That is the cleanest nature farm in the game: bait a feeder, then catch what walks up to it.',
            'It also works against you for the flee lock — a baited Pokémon is <i>enthralled</i> (−5), not curious (−3). '
            'Bait for natures, or throw for a lock, not both at once.',
            'If your lead Pokémon has <b>Synchronize</b> and no feeder is in range, wild natures match it half the time.',
        ]),
        dict(type='h', text='Overworld spawns'),
        dict(type='p', html='With the <b>Overworld Spawns</b> option on, the Pokémon wandering the grass can be walked into '
                            'on purpose, so you pick your target instead of burning steps on random encounters. '
                            'Those bumps start an <b>ordinary wild battle</b>, not a Safari one: your own Pokémon, your own '
                            'Poké Balls, and EXP. Only the grass itself follows Safari rules.'),
    ]))

    # --- Starters ---
    starter_cards = []
    for sp, area, method, needs, note in [
        ('BULBASAUR', 'South', 'grass', 'Nothing — it is the entrance area',
         'You can walk to it the first time you pay in. Your rival also gives one away in the post-game, '
         'after all ten hidden Kecleon (see <a onclick="selectPage(\'gifts-post\')">Post-Game Gifts</a>).'),
        ('CHARMANDER', 'North', 'grass', 'Acro Bike',
         'Behind the rails at the top of the entrance area. The rival’s Charmander wants all three Flutes; '
         'this one only wants a bike.'),
        ('SQUIRTLE', 'Southwest', 'surfing', 'Surf',
         'The pond west of the entrance. The rival’s Squirtle is gated behind all 16 hidden Heart Scales.'),
        ('CHIKORITA', 'Southeast', 'grass', 'Hall of Fame',
         'Expansion area, so post-game — but far cheaper than Birch’s lab, which wants the whole Hoenn Dex caught.'),
        ('CYNDAQUIL', 'Northeast', 'grass', 'Hall of Fame',
         'Expansion area. Walk up from Southeast; no bike needed.'),
        ('TOTODILE', 'Southeast', 'surfing', 'Hall of Fame · Surf',
         'Expansion area, on the water. Birch’s lab hands out one Johto starter per Hall of Fame entry; the Safari '
         'Zone hands out as many as you can catch.'),
    ]:
        chance = next(p for (label, rows) in enc[area] for (s, p, lo, hi) in rows
                      if s == sp and label.lower().startswith(method[:4]))
        starter_cards.append(dict(
            sprite='mon:' + sp, title=pdx.species_display_name(sp), sub=f'Lv.30 · {pct(chance)} of {method} encounters',
            place=f'Safari Zone — {area}' + (' (post-game)' if area in SAFARI_POSTGAME else ''),
            rows=[['Needs', needs], ['Catch factor', f'{factor(sp)} / 20']],
            note=note))
    pages.append(dict(id='safari-starters', section=S, title='The Six Starters',
        kicker='Kanto & Johto, in the grass', blocks=[
        dict(type='p', html='Emerald Legacy hides all six Kanto and Johto starters in the Safari Zone. They are ordinary '
                            'wild Pokémon: random IVs, random natures, and as many attempts as you can pay for — which makes '
                            'them a far shorter road than the gift versions in Littleroot.'),
        dict(type='callout', html='Every one of them is <b>Lv.30</b> with a catch factor of <b>3 / 20</b>, the worst tier in the zone. '
                                  'Lock the escape factor to 0 with a curious Pokéblock before you spend a single ball — '
                                  'see <a onclick="selectPage(\'safari-basics\')">How the Safari Game Works</a>.'),
        dict(type='cards', items=starter_cards),
        dict(type='p', html='Bulbasaur, Charmander and Squirtle are all reachable <b>before</b> the Hall of Fame — '
                            'Charmander wants the Acro Bike, Squirtle wants Surf. The Johto three live in the expansion '
                            'areas, which open once you are Champion.'),
    ]))

    # --- Areas ---
    area_rows = []
    for a in SAFARI_AREAS:
        balls, hidden = SAFARI_ITEMS[a]
        found = [item(c) for c in balls] + [dict(item(c), name=tdx.item_display(c, item_names) + ' (hidden)') for c in hidden]
        how, note = SAFARI_ACCESS[a]
        area_rows.append([
            dict(html=f'<b>{a}</b>' + ('<span class="pg">POST</span>' if a in SAFARI_POSTGAME else '')),
            dict(html=f'{how}<br><span class="dim">{note}</span>'),
            dict(html=f'{SAFARI_FEEDERS[a]}'),
            dict(items=found) if found else dict(text='—'),
        ])
    pages.append(dict(id='safari-areas', section=S, title='The Six Areas',
        kicker='Bikes · feeders · items', blocks=[
        dict(type='p', html='The zone is a 3 × 2 grid of 40 × 40 maps. You always start in <b>South</b>, and South is '
                            'the only way out — the attendant by the door retires your game.'),
        dict(type='table', head=['Area', 'How to get in', 'Feeders', 'Items'], rows=area_rows),
        dict(type='list', items=[
            '<b>Northwest is Mach Bike only.</b> Nothing else reaches it: the muddy slope out of Southwest is the single entrance.',
            '<b>North is Acro Bike only.</b> The rails along the top of South are the only way up, and a bumpy slope '
            'inside the area needs the Acro Bike too.',
            'The <b>expansion</b> — Southeast and Northeast — opens the moment you enter the Hall of Fame. '
            'Before that, two construction workers block the east gate of South. Neither area needs a bike.',
            'The hidden items need the <b>Itemfinder</b>. Surf reaches water in Southwest, Northwest and Southeast; '
            'Rock Smash rocks stand in North and Northeast.',
            'The <b>Rest House</b> in Southwest is just conversation — there is no healing inside the zone.',
        ]),
    ]))

    # --- Encounters ---
    blocks = [
        dict(type='p', html='Chance is the odds <i>within</i> that method. Land slots each hold one fixed level, so a '
                            'range there means the species sits in more than one slot; surfing and fishing roll a real range. '
                            '<b>Catch factor</b> is the 0–20 number your Safari Balls actually throw against — 20 is a '
                            'Magikarp, 3 is a starter.'),
    ]
    for a in SAFARI_AREAS:
        blocks.append(dict(type='h', text=a + (' — expansion, post-game' if a in SAFARI_POSTGAME else '')))
        rows = []
        for label, mons in enc[a]:
            for sp, p, lo, hi in mons:
                new = ' <span class="pg br">NEW</span>' if sp in SAFARI_NEW else ''
                rows.append([dict(text=label), mon_cell(sp), dict(text=pct(p)),
                             dict(html=lvl(lo, hi) + new), dict(text=f'{factor(sp)}')])
        blocks.append(dict(type='table', head=['Method', 'Pokémon', 'Chance', 'Level', 'Catch'], rows=rows))
    pages.append(dict(id='safari-encounters', section=S, title='Every Encounter',
        kicker='Grass · surf · fishing · rocks', blocks=blocks))
    return pages


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
# Hidden Power — src/battle_script_commands.c (Cmd_hiddenpowercalc) and
# src/pokemon_summary_screen.c (SetMoveTypeIcons). The IV table below is computed
# from that formula; it matches psypokes.com/dex/hp.php ("Highest IVs per Type").
# ---------------------------------------------------------------------------
# Bit order the game reads the IVs in — HP, Atk, Def, Speed, SpAtk, SpDef.
HP_STATS = ['HP', 'Atk', 'Def', 'Spd', 'Sp. Atk', 'Sp. Def']
# ((NUMBER_OF_MON_TYPES - 3) * typeBits) / 63 + 1, skipping Normal and Mystery.
HP_TYPE_ORDER = ['FIGHTING', 'FLYING', 'POISON', 'GROUND', 'ROCK', 'BUG', 'GHOST', 'STEEL',
                 'FIRE', 'WATER', 'GRASS', 'ELECTRIC', 'PSYCHIC', 'ICE', 'DRAGON', 'DARK']


def hidden_power_rows():
    """Highest IVs that still give each type at the full 70 base power.

    An IV of 31 sets both read bits, 30 sets only the power bit, so a spread of
    31s and 30s always lands on 70 power and the 31/30 pattern picks the type.
    Four or five patterns hit each type; the one with the most 31s wins, and a tie
    goes to the pattern that keeps the 31s furthest to the right (highest typeBits),
    which is the spread psypokes.com lists.
    """
    best = {}
    for bits in range(64):
        ty = HP_TYPE_ORDER[(15 * bits) // 63]
        ivs = [31 if (bits >> i) & 1 else 30 for i in range(6)]
        key = (bin(bits).count('1'), bits)
        if ty not in best or key > best[ty][0]:
            best[ty] = (key, ivs)
    return {t: v[1] for t, v in best.items()}


def build_hidden_power_pages():
    S = 'Hidden Power'
    best = hidden_power_rows()
    ty_icon = lambda t: (f'<span class="ent"><img class="tyicon" src="TYPEICON:{t}" '
                         f'alt="{TYPE_LABEL[t]}">{TYPE_LABEL[t]}</span>')
    rows = []
    for t in sorted(HP_TYPE_ORDER, key=lambda x: TYPE_LABEL[x]):
        rows.append([dict(html=ty_icon(t))]
                    + [dict(html=('<b>31</b>' if v == 31 else '30')) for v in best[t]])

    pages = [dict(id='hp-ivs', section=S, title='Hidden Power by IVs',
        kicker='Type & power table', blocks=[
        dict(type='p', html='<b>Hidden Power</b> (TM10) has no fixed type or power: both are read off the '
                            'Pokémon’s <b>IVs</b>, which are set the moment it is generated and never change. '
                            'The same Pokémon therefore has the same Hidden Power forever — the only way to change it '
                            'is to breed or catch another one.'),
        dict(type='callout', html='Catch <b>all 28 Unown</b> and the summary screen starts showing Hidden Power’s '
                                  'real type on the move list, so you can read a Pokémon’s type straight off the '
                                  'party menu instead of working it out.'),
        dict(type='h', text='Where to get TM10'),
        dict(type='list', items=[
            'Free from the man in a <b>Fortree City treehouse</b> — guess which hand three times in a row.',
            'Sold by the <b>TM clerk in Slateport City</b> (the stall by the market) for ₽3,000.',
            'Sold at the <b>Lilycove Department Store</b> (4F).',
        ]),
        dict(type='h', text='How the game works it out'),
        dict(type='p', html='Each stat carries a weight, and the game adds those weights up twice — once for the type, '
                            'once for the power. A stat only pays into a total if its IV passes that total’s test.'),
        dict(type='table', cls='stat-grid', head=['Stat'] + HP_STATS, rows=[
            [dict(html='<b>Weight</b>')] + [dict(text=str(1 << i)) for i in range(6)],
        ]),
        dict(type='list', items=[
            '<b>Type total</b> adds the weight of every stat whose IV is <b>odd</b>. '
            'Type = <code>15 × total ÷ 63</code>, rounded down → a number from 0 to 15, read as '
            'Fighting, Flying, Poison, Ground, Rock, Bug, Ghost, Steel, Fire, Water, Grass, Electric, '
            'Psychic, Ice, Dragon, Dark. Normal is not possible.',
            '<b>Power total</b> adds the weight of every stat whose IV falls in <b>2–3, 6–7, 10–11, … 30–31</b> '
            '(the IVs whose second bit is set). '
            'Power = <code>40 × total ÷ 63</code>, rounded down, <b>+ 30</b> → from <b>30</b> when no stat qualifies '
            'to <b>70</b> when all six do.',
        ]),
        dict(type='h', text='Highest IVs per type'),
        dict(type='p', html='Every row below is a <b>70 base power</b> Hidden Power of that type, using the highest '
                            'IVs that can produce it. A <b>31</b> is odd and a <b>30</b> is even, so the 31/30 pattern '
                            'is what picks the type; both keep the power bit, so the power stays at 70.'),
        dict(type='table', cls='stat-grid', head=['Type'] + HP_STATS, rows=rows),
        dict(type='p', html='Breeding for one of these means chasing a specific <b>odd/even pattern</b>, not specific '
                            'numbers: swap any 31 for another odd IV and any 30 for another even IV and the type holds. '
                            'The power is what suffers — drop an IV out of the 2–3, 6–7, … 30–31 groups and it falls below 70.'),
        dict(type='h', text='In battle'),
        dict(type='list', items=[
            'Hidden Power is <b>physical or special according to the type it rolls</b>, like every other move in Gen 3. '
            'This hack swaps Dark and Ghost, so <b>Hidden Power Dark is physical</b> and <b>Hidden Power Ghost is special</b> here.',
            'It still counts as a <b>Normal</b> move for Counter and Mirror Coat, so it only ever triggers <b>Counter</b> — '
            'whatever type it rolled.',
            'For the same reason, Hidden Power Fire <b>cannot thaw</b> a frozen target.',
            'Its rolled type does get <b>STAB</b>, type matchups and the matching type-boosting item (Charcoal, Mystic Water…).',
        ]),
        dict(type='p', html='<span class="dim">Table checked against psypokes.com’s Hidden Power calculator and '
                            'recomputed from this ROM’s <code>Cmd_hiddenpowercalc</code>.</span>'),
    ])]
    return pages



# ---------------------------------------------------------------------------
# Abilities — one page listing every ability, its holders and what it really does.
# Every note below was checked against this ROM's code, not against the Gen 3 canon:
# src/battle_util.c (AbilityBattleEffects), src/battle_script_commands.c (accuracy, stat
# drops, secondary effects), src/pokemon.c (CalculateBaseDamage), data/battle_scripts_1.s,
# src/wild_encounter.c, src/egg_hatch.c, src/field_player_avatar.c, src/fldeff_cut.c,
# src/match_call.c and src/overworld.c.
# ---------------------------------------------------------------------------

# Abilities this hack changed from stock Emerald (git log -S on the lines involved).
LEGACY_CHANGED = {'STENCH', 'ILLUMINATE', 'MAGMA_ARMOR', 'SAND_VEIL'}

ABILITY_NOTES = {
    'STENCH': 'Out in the field it <b>halves the wild encounter rate</b> while it leads the party '
              '(only a quarter off inside the Battle Pyramid). In battle it borrows the hold-effect '
              'number of whatever item the Pokémon is carrying and takes that many percent off the '
              'attacker’s accuracy — so with no item, that number is 0 and the ability does nothing.',
    'DRIZZLE': 'Rain starts the moment it comes in and <b>never runs out</b>: Gen 3 ability weather has '
               'no five-turn clock. Only another weather ability or a weather move replaces it.',
    'SPEED_BOOST': '+1 Speed at the end of every turn, starting with the turn <i>after</i> it switched in, '
                   'up to +6.',
    'BATTLE_ARMOR': 'Critical hits can never land on it. Same effect as Shell Armor.',
    'STURDY': 'Only blocks the one-hit KO moves — Fissure, Horn Drill and Guillotine. It does nothing '
              'against ordinary damage, so it will not survive a hit at full HP the way it does in later games.',
    'DAMP': 'Explosion and Self-Destruct fail while <b>any</b> Pokémon on the field has it — including '
            'your own, which means a Damp partner shuts off your own Explosion in a double battle.',
    'LIMBER': 'Paralysis can’t stick, and an existing paralysis is cured the moment the ability applies.',
    'SAND_VEIL': 'In a sandstorm, attacks aimed at it are multiplied by <b>0.8 accuracy</b> and its '
                 '<b>Sp. Def is raised by 50%</b> — the same bonus Rock types get. Leading the party, it '
                 'halves the wild encounter rate while the overworld weather is a sandstorm.',
    'STATIC': 'A contact move has a <b>1 in 3</b> chance of paralysing the attacker. Leading the party, it '
              'has a 50% chance of pulling an <b>Electric type</b> out of the encounter table.',
    'VOLT_ABSORB': 'A damaging Electric move heals <b>¼ of max HP</b> instead of hitting. At full HP the move '
                   'still does nothing, it simply heals nothing. Status Electric moves (Thunder Wave) are not absorbed.',
    'WATER_ABSORB': 'A damaging Water move heals <b>¼ of max HP</b> instead of hitting. At full HP it still '
                    'blocks the move.',
    'OBLIVIOUS': 'Attraction can’t stick, and it also stops the foe’s <b>Cute Charm</b> from infatuating it.',
    'CLOUD_NINE': 'While it is on the field, <b>nobody’s weather does anything</b> — no chip damage, no '
                  'Solar Beam shortcut, no Swift Swim, no Synthesis boost. The weather itself stays up, so '
                  'it comes straight back when this Pokémon leaves. Same effect as Air Lock.',
    'COMPOUND_EYES': 'Multiplies its own accuracy by <b>1.3</b>. Leading the party it also improves wild '
                     'held items: the odds of a wild Pokémon carrying nothing drop from 45% to 20%, and its '
                     'rare item shows up 20% of the time instead of 5%.',
    'INSOMNIA': 'Sleep can’t stick, and an existing sleep is cured. Rest fails outright. Same effect as Vital Spirit.',
    'COLOR_CHANGE': 'After it takes a damaging move it becomes that move’s type, which usually leaves it weak '
                    'to whatever comes next. It doesn’t trigger on status moves or on a move it is immune to.',
    'IMMUNITY': 'Poison — regular or Toxic — can’t stick, and an existing poison is cured.',
    'FLASH_FIRE': 'Fire moves miss it entirely and its own Fire moves get stronger for the rest of the battle. '
                  'It does <b>not</b> work while the Pokémon is frozen, and the boost is lost on switching out.',
    'SHIELD_DUST': 'Blocks the <i>added</i> effect of a move (Flamethrower’s burn, Rock Slide’s flinch), '
                   'never the damage, and never a move whose only job is the status (Thunder Wave still works).',
    'OWN_TEMPO': 'Confusion can’t stick, and existing confusion is cured — including self-confusion from '
                 'Outrage or Petal Dance.',
    'SUCTION_CUPS': 'Roar and Whirlwind can’t drag it out. Leading the party it also makes fishing bite '
                    '<b>85% of the time</b> instead of the usual roll, the same as Sticky Hold.',
    'INTIMIDATE': 'On switch-in it drops the Attack of <b>every</b> opponent by one stage — both of them in a '
                  'double battle. A Substitute, Clear Body, Hyper Cutter or White Smoke blocks it. Leading the '
                  'party it also skips half of the wild encounters that are 5 or more levels below it, same as Keen Eye.',
    'SHADOW_TAG': 'No opponent can switch out or run — there is no Flying or Levitate exemption, unlike Arena Trap.',
    'ROUGH_SKIN': 'A contact move costs the attacker <b>1/16 of its max HP</b>, every time.',
    'WONDER_GUARD': 'Only <b>super-effective damaging moves</b> land. Status moves, weather, poison, Leech Seed '
                    'and Spikes all still work, and a move that is super effective against one of its types but '
                    'not very effective against the other is blocked too.',
    'LEVITATE': 'Ground moves miss it, Spikes don’t hurt it, and it can walk away from <b>Arena Trap</b>. '
                'Magnet Pull still traps it if it is a Steel type.',
    'EFFECT_SPORE': 'A contact move has a <b>1 in 10</b> chance of leaving the attacker asleep, poisoned or '
                    'paralysed, split evenly between the three.',
    'SYNCHRONIZE': 'When something poisons, burns or paralyses it, the same status is passed straight back. '
                   'Toxic comes back as <b>ordinary poison</b>. Leading the party, wild Pokémon have a 50% '
                   'chance of sharing its <b>nature</b> — the cheapest nature breeding trick in the game.',
    'CLEAR_BODY': 'No opponent can lower any of its stats: Intimidate, Growl, String Shot, Sand-Attack, '
                  'all refused. Its own Overheat or Belly Drum still works. Same effect as White Smoke.',
    'NATURAL_CURE': 'Switching out cures poison, burn, paralysis, sleep and freeze. Resting and switching is '
                    'a full heal for two turns of work.',
    'LIGHTNING_ROD': 'Draws in the <b>opponents’</b> single-target Electric moves — and takes the damage: this '
                     'is Gen 3, so there is no immunity and no Sp. Atk boost. It does not redirect an ally’s '
                     'move. Leading the party it doubles the chance a trainer rings you on the <b>Match Call</b>, '
                     'from 30% to 60%.',
    'SERENE_GRACE': 'Doubles the chance of a move’s added effect — a 10% flinch becomes 20%, a 30% freeze becomes 60%.',
    'SWIFT_SWIM': 'Doubles Speed in rain. Cloud Nine or Air Lock turns it off.',
    'CHLOROPHYLL': 'Doubles Speed in harsh sunlight. Cloud Nine or Air Lock turns it off.',
    'ILLUMINATE': 'In this hack it is a real battle ability: its moves <b>ignore the target’s evasion</b> '
                  '(Double Team, Sand Veil, BrightPowder) and nothing can lower its accuracy. Leading the party '
                  'it also <b>doubles the wild encounter rate</b>.',
    'TRACE': 'On switch-in it copies an opponent’s ability — a random one of the two in a double battle, unless '
             'only one of them has anything to copy. Wonder Guard is fair game. The copy lasts until it switches out.',
    'HUGE_POWER': 'Doubles Attack, before any other boost. Same effect as Pure Power.',
    'POISON_POINT': 'A contact move has a <b>1 in 3</b> chance of poisoning the attacker.',
    'INNER_FOCUS': 'It can never be made to flinch. Intimidate still works on it.',
    'MAGMA_ARMOR': 'Freeze can’t stick. In this hack it is also a serious defensive ability: <b>Water moves do '
                   'an eighth of their damage</b> to it. In the party it halves the steps an Egg needs to hatch, '
                   'the same as Flame Body.',
    'WATER_VEIL': 'Burn can’t stick, and an existing burn is cured.',
    'MAGNET_PULL': 'Steel types can’t switch out or run. It checks the <b>whole field</b>, so it pins your own '
                   'Steel partner in a double battle as well. Leading the party, it has a 50% chance of pulling '
                   'a <b>Steel type</b> out of the encounter table.',
    'SOUNDPROOF': 'Blocks exactly ten moves: Growl, Roar, Sing, Supersonic, Screech, Snore, Uproar, Metal Sound, '
                  'Grass Whistle and Hyper Voice. Perish Song is not in the list in Gen 3 — this is the one '
                  'ability that stops Roar <i>and</i> shrugs off Hyper Voice.',
    'RAIN_DISH': 'Heals <b>1/16 of max HP</b> at the end of each turn while it is raining.',
    'SAND_STREAM': 'A sandstorm starts on switch-in and <b>never runs out</b>. It chips every Pokémon that isn’t '
                   'Rock, Ground or Steel, and raises the Sp. Def of Rock types (and Sand Veil holders) by 50%.',
    'PRESSURE': 'Every move aimed at it costs the attacker <b>one extra PP</b>; a spread move pays once per '
                'Pressure Pokémon it hits. Leading the party it also gives wild Pokémon a 50% chance of rolling '
                'the <b>top of their level range</b>.',
    'THICK_FAT': 'Halves the damage of every Fire and Ice move. Both types are special in Gen 3, so nothing '
                 'slips past it.',
    'EARLY_BIRD': 'Sleep runs out twice as fast — it wakes after half as many turns, Rest included.',
    'FLAME_BODY': 'A contact move has a <b>1 in 3</b> chance of burning the attacker. In the party it halves '
                  'the steps an Egg needs to hatch, the same as Magma Armor.',
    'RUN_AWAY': 'Running from a wild battle <b>always works</b>, whatever the Speed difference and whatever is '
                'trapping you. The Battle Pyramid is the exception: there it only improves the odds.',
    'KEEN_EYE': 'No opponent can lower its accuracy. Leading the party it also skips half of the wild encounters '
                'that are 5 or more levels below it, same as Intimidate.',
    'HYPER_CUTTER': 'No opponent can lower its Attack — Intimidate included. Out in the field, using <b>Cut</b> '
                    'with this Pokémon clears a <b>5×5 patch</b> of grass instead of 3×3.',
    'PICKUP': 'After each battle, a Pokémon holding nothing has a <b>1 in 10</b> chance of turning up with an '
              'item. It works from anywhere in the party, and the table gets better as the game goes on.',
    'TRUANT': 'It moves the turn it comes in, then loafs every other turn. A switch resets the counter, so '
              'switching out and back in buys another free turn.',
    'HUSTLE': 'Attack is raised by 50%, and its <b>physical</b> moves are multiplied by 0.8 accuracy. Special '
              'moves keep full accuracy. Leading the party it gives wild Pokémon a 50% chance of rolling the '
              'top of their level range.',
    'CUTE_CHARM': 'A contact move has a <b>1 in 3</b> chance of infatuating an attacker of the opposite gender; '
                  'Oblivious blocks it. Leading the party, two thirds of wild Pokémon come out the <b>opposite '
                  'gender</b> to it.',
    'PLUS': 'Sp. Atk is raised by 50% while a <b>Minus</b> Pokémon is anywhere on the field — including on the '
            'opposing side, which is a rare way to get a boost handed to you.',
    'MINUS': 'Sp. Atk is raised by 50% while a <b>Plus</b> Pokémon is anywhere on the field, the opposing side '
             'included.',
    'FORECAST': 'Castform re-types with the weather: Fire in sun, Water in rain, Ice in hail, Normal otherwise. '
                'Its sprite changes with it, and Cloud Nine or Air Lock puts it back to Normal.',
    'STICKY_HOLD': 'Thief, Covet and Knock Off all fail against its item. Leading the party it also makes '
                   'fishing bite <b>85% of the time</b>, the same as Suction Cups.',
    'SHED_SKIN': 'At the end of each turn there is a <b>1 in 3</b> chance it shakes off poison, burn, paralysis, '
                 'sleep or freeze.',
    'GUTS': 'Attack is raised by 50% while it has any status — and a burn no longer halves its Attack, so a '
            'burned Guts attacker hits <i>harder</i> than a healthy one.',
    'MARVEL_SCALE': 'Defense is raised by 50% while it has any status. A self-inflicted Toxic or a Rest works fine.',
    'LIQUID_OOZE': 'Absorb, Mega Drain, Giga Drain, Leech Life and Leech Seed all <b>damage</b> the drainer '
                   'instead of healing them. <b>Dream Eater</b> is the exception — its script never checks '
                   'the ability, so it heals as normal.',
    'OVERGROW': 'Grass moves are 50% stronger once its HP is at or below a third of its maximum.',
    'BLAZE': 'Fire moves are 50% stronger once its HP is at or below a third of its maximum.',
    'TORRENT': 'Water moves are 50% stronger once its HP is at or below a third of its maximum.',
    'SWARM': 'Bug moves are 50% stronger once its HP is at or below a third of its maximum. With one in the '
             'party the overworld’s ambient Pokémon cries come twice as often.',
    'ROCK_HEAD': 'No recoil from Double-Edge, Take Down, Submission or Volt Tackle. <b>Struggle still hurts</b> — '
                 'the game checks for it before it checks the ability.',
    'DROUGHT': 'Harsh sunlight starts on switch-in and <b>never runs out</b>: Fire moves +50%, Water moves −50%, '
               'Solar Beam in one turn, Thunder and Blizzard down to 50% accuracy.',
    'ARENA_TRAP': 'No opponent can switch out or run — <b>except</b> Flying types and anything with Levitate. '
                  'Leading the party it doubles the wild encounter rate.',
    'VITAL_SPIRIT': 'Sleep can’t stick, and an existing sleep is cured. Leading the party it gives wild Pokémon '
                    'a 50% chance of rolling the top of their level range.',
    'WHITE_SMOKE': 'No opponent can lower any of its stats, Intimidate included. Leading the party it halves the '
                   'wild encounter rate.',
    'PURE_POWER': 'Doubles Attack, before any other boost. Same effect as Huge Power.',
    'SHELL_ARMOR': 'Critical hits can never land on it. Same effect as Battle Armor.',
    'CACOPHONY': 'A leftover slot in the ability table. Nothing in the game has it and nothing in the code reads it.',
    'AIR_LOCK': 'While it is on the field, <b>nobody’s weather does anything</b>, though the weather itself stays '
                'up and returns when this Pokémon leaves. Same effect as Cloud Nine.',
}

# Lead-slot effects, for the table at the top of the page. (species → wild_encounter.c,
# egg_hatch.c, field_player_avatar.c, fldeff_cut.c, match_call.c, overworld.c, pokemon.c)
LEAD_EFFECTS = [
    ('Illuminate, Arena Trap', 'Twice as many wild encounters.'),
    ('Stench, White Smoke', 'Half as many wild encounters (Stench only takes a quarter off in the Battle Pyramid).'),
    ('Sand Veil', 'Half as many wild encounters while the overworld weather is a sandstorm.'),
    ('Keen Eye, Intimidate', 'Skips half of the encounters 5 or more levels below the lead.'),
    ('Hustle, Vital Spirit, Pressure', '50% chance the wild Pokémon rolls the top of its level range.'),
    ('Static', '50% chance the encounter is pulled from the <b>Electric</b> types in the table.'),
    ('Magnet Pull', '50% chance the encounter is pulled from the <b>Steel</b> types in the table.'),
    ('Synchronize', '50% chance the wild Pokémon has the <b>lead’s nature</b>.'),
    ('Cute Charm', 'Two thirds of wild Pokémon come out the opposite gender to the lead.'),
    ('Compound Eyes', 'Wild held items: 20% chance of nothing instead of 45%, and the rare item at 20% instead of 5%.'),
    ('Suction Cups, Sticky Hold', 'Fishing bites 85% of the time.'),
    ('Lightning Rod', 'Match Call rings twice as often (60% instead of 30%).'),
    ('Magma Armor, Flame Body', 'Eggs need half as many steps to hatch — from anywhere in the party.'),
    ('Hyper Cutter', 'Cut clears a 5×5 patch of grass instead of 3×3 (the Pokémon you pick to use Cut).'),
    ('Pickup', '1 in 10 chance of an item after each battle — from anywhere in the party.'),
    ('Swarm', 'Ambient overworld cries come twice as often.'),
]


def pretty_ability_desc(desc):
    """In-game description → prose: 'Not hit by GROUND attacks.' -> 'Not hit by Ground attacks.'"""
    def fix(m):
        w = m.group(0)
        return 'Pokémon' if w.upper().startswith('POK') else w.title()
    return re.sub(r'\b[A-Zé]{3,}\b', fix, desc).replace('“Super effective” hits.', 'Only “super effective” hits land.')


def build_ability_pages():
    S = 'Abilities'
    info = pdx.parse_ability_info(os.path.join(BASE, 'src/data/text/abilities.h'))
    stats = pdx.parse_base_stats(os.path.join(BASE, 'src/data/pokemon/species_info.h'))
    dex = pdx.parse_national_dex_order(os.path.join(BASE, 'include/constants/pokedex.h'))

    holders = {k: [] for k in info}
    for sp, d in stats.items():
        base = pdx.FORM_OF.get(sp, (sp,))[0]
        # Alternate forms only earn their own chip when their abilities differ from the base form's.
        if base != sp and stats.get(base, {}).get('abilities') == d.get('abilities'):
            continue
        abilities = d.get('abilities', [])
        for slot, a in enumerate(abilities):
            # Four species (Granbull, Vibrava, Flygon, Snorunt) list the same ability in both
            # slots, so there is nothing to choose and nothing to badge.
            if slot and a == abilities[0]:
                continue
            if a in holders:
                holders[a].append(dict(sp=sp, name=pdx.species_display_name(sp), sprite='mon:' + sp,
                                       slot=slot, dex=dex.get(base, 999)))
    for v in holders.values():
        v.sort(key=lambda m: (m['dex'], m['name']))

    items = []
    for key in sorted(info, key=lambda k: info[k]['name']):
        note = ABILITY_NOTES.get(key, '')
        items.append(dict(
            key=key, name=info[key]['name'], desc=pretty_ability_desc(info[key]['desc']),
            note=note, plain=re.sub(r'<[^>]+>', '', note),
            tag='Changed in Legacy' if key in LEGACY_CHANGED else '',
            mons=[{k: v for k, v in m.items() if k != 'dex'} for m in holders[key]],
        ))

    two_slots = sum(1 for it in items for m in it['mons'] if m['slot'])
    return [dict(id='abilities', section=S, title='Abilities', kicker=f'{len(items)} · who has what', blocks=[
        dict(type='p', html=f'Every Pokémon carries one of the game’s <b>{len(items)} abilities</b>, and '
                            f'<b>{two_slots}</b> species have a second one they might get instead. '
                            'Which one a Pokémon gets is decided the instant it is generated — caught, hatched '
                            'or handed over — and <b>nothing in the game can change it afterwards</b>: there is '
                            'no ability capsule here, and breeding does not pass an ability down. If you want '
                            'the other one, you catch or hatch another.'),
        dict(type='callout', html='The slot travels through evolution. A Ralts that rolled the second slot is a '
                                  'Gardevoir with the second slot, so a species whose two abilities are worth '
                                  'different amounts is worth checking <i>before</i> you invest levels in it.'),
        dict(type='h', text='What the lead Pokémon changes'),
        dict(type='p', html='Some abilities do their best work outside battle, from the <b>first slot in the '
                            'party</b> — an egg in slot one switches all of this off. The two hatching '
                            'abilities and Pickup are the exceptions: they work from anywhere in the party.'),
        dict(type='table', rows=[[dict(html=f'<b>{a}</b>'), dict(html=w)] for a, w in LEAD_EFFECTS],
             head=['Ability', 'What it does in the field']),
        dict(type='h', text='Every ability'),
        dict(type='p', html='Search by ability, by what it does, or by a Pokémon’s name — searching a Pokémon '
                            'leaves only the abilities it can have, with its own chip picked out. A <span '
                            'class="slot2">2</span> marks the species’ second slot.'),
        dict(type='abilities', items=items),
    ])]

# ---------------------------------------------------------------------------
# Team Building — type coverage (coverage_data.py does the maths from the decomp).
# ---------------------------------------------------------------------------
# Nothing here is hand-picked: coverage_data.py ranks every fully-evolved pair over the best
# 8-type sets and picks each Pokémon's strongest legal move per slot. Doubles-safety is a
# constraint on that search, not a theme — a spread move (Earthquake…) is only allowed when the
# partner is immune to it, otherwise the search takes a different move, or a different type.
FEATURED_DUOS = 4        # offensive cards shown before the table
FEATURED_LEGEND_DUOS = 2
DUO_POOL = 12            # how deep the ranking goes; what the cards don't take fills the table

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

    def duo_view(d, matchups=None):
        a, b = d['a'], d['b']
        def moves(ms):
            return [dict(type=m['type'], name=pdx.fmt_move('MOVE_' + m['move']), power=m['power'], stab=m['stab'],
                         how=m['how'], spread=m['spread']) for m in ms]
        def side(sp, ms):
            return dict(mon=mon(sp), types=list(D['species'][sp]['types']), ability=' / '.join(
                x.replace('_', ' ').title() for x in sorted(D['species'][sp]['abilities'])), moves=moves(ms))
        # Doubles-safety is guaranteed by the search (partner_safe), so the cards don't say so.
        assert not d['ally_hits'], f"{a}/{b}: {d['ally_hits']}"
        out = dict(a=side(a, d['a_moves']), b=side(b, d['b_moves']), hit=d['hit'], total=d['total'],
                   missed=[mon(s) for s in d['missed']])
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
        # Straight damage ranking, no per-species cap: if one Pokémon really is the best partner
        # over and over, the page should say so. The cards only avoid repeating a Pokémon.
        top_duos = cov.rank_duos(True, DUO_POOL, per_species=None)
    top_cards, top_rest = split_featured(top_duos, FEATURED_DUOS)

    def duo_rows(lst):
        return [[dict(sprite='mon:' + d['a'], text=name(d['a'])), dict(html=move_cell(d['a_moves'])),
                 dict(sprite='mon:' + d['b'], text=name(d['b'])), dict(html=move_cell(d['b_moves']))] for d in lst]
    more_rows = duo_rows(top_rest)
    legend_cards, legend_rest = split_featured(legend_duos, FEATURED_LEGEND_DUOS)
    legend_rows = duo_rows(legend_rest)

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
        dict(type='p', html=f'The strongest two-Pokémon cores in the game. Each pair below splits the best 8 attacking types, '
                            f'four moves each, so together they hit <b>{best8_hit} of {len(hittable)}</b> Pokémon super effectively — '
                            'the most any two Pokémon can reach. Nothing is hand-picked: every fully-evolved pair was scored, and '
                            'the ones here hit the hardest, ranked by move power × same-type bonus × the attacking stat.'),
        dict(type='p', html='Moves are the strongest reliable ones each Pokémon can learn by level-up, TM/HM, tutor or egg move. '
                            'That rules out moves with a charge turn or recharge, self-KO moves, fixed-damage moves and Hidden Power. '
                            f'Every move shown has at least {cov.MIN_POWER} power, and <span class="stab">STAB</span> marks a same-type bonus. '
                            'Every pair also works in a double battle: no move on one side can hit its own partner, which in practice means '
                            '<b>Earthquake</b> only ever sits on a Pokémon whose partner is immune to Ground.'),
        dict(type='h', text='Strongest duos'),
        dict(type='duos', items=[duo_view(d) for d in top_cards]),
        dict(type='h', text='More duos'),
        dict(type='p', html=f'Also {best8_hit}/{len(hittable)}, ranked the same way. Legendaries are left out. '
                            '<b>Flygon</b> turns up a lot, and that is the honest answer: <b>Levitate</b> makes it the one strong attacker that can stand next to an Earthquake, so it partners with almost anything.'),
        dict(type='table', head=['Pokémon', 'Moves', 'Partner', 'Moves'], rows=more_rows),
        dict(type='h', text='Legendary duos'),
        dict(type='p', html=f'The same search with post-game legendaries allowed (every pair includes at least one; each legendary appears at most twice). '
                            f'It still tops out at {best8_hit}/{len(hittable)}, because no Pokémon beats the type chart, but the moves hit much harder.'),
        dict(type='duos', items=[duo_view(d) for d in legend_cards]),
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
        moves, keys = [], []
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
            keys.append(mv)
            moves.append(dict(type=d['type'], name=pdx.fmt_move('MOVE_' + mv),
                              power=d['power'] if d['power'] > 1 else ('—' if d['power'] == 0 else 'varies'),
                              target=target_label(mv) if d['power'] else '', how=' · '.join(how_parts), tip=tip,
                              alt=pdx.fmt_move('MOVE_' + d['alt']['move']) if d.get('alt') else ''))
        it = items['ITEM_' + mem['item']]
        return dict(sprite='mon:' + mem['sp'], sp=mem['sp'], name=name(mem['sp']), types=list(D['species'][mem['sp']]['types']),
                    ability=title(mem['ability']), item=dict(icon='item:' + it['key'], key=it['key'], name=it['name']),
                    nature=mem['nature'], moves=moves, note=mem['note'],
                    abil=mem['ability'], mvkeys=keys)

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
        dict(type='p', html='See also <a onclick="selectPage(\'coverage-duos\')">Coverage Duos</a>, the strongest two-Pokémon cores, all of them safe to fire on any turn.'),
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


# The battling sections live in the Team app (generate_teambuilder.py); the Guide keeps the
# walkthrough reference pages. Nothing links across the two groups.
TEAM_SECTIONS = ('Team Building', 'Double Battles', 'Stat Specialists')


def ability_index():
    """Spotlight entries for every ability: [{key: 'abilities/LEVITATE', name, sub}].

    The key is a page id plus an anchor, which selectPage() (guide_pages.py) splits.
    """
    pages, _ = build_data()
    for p in pages:
        for b in p['blocks']:
            if b['type'] == 'abilities':
                return [dict(key=f"{p['id']}/{it['key']}", name=it['name'],
                             sub=f"{it['desc']} · {len(it['mons'])} Pokémon" if it['mons'] else it['desc'])
                        for it in b['items']]
    return []



def page_refs(pages):
    """Every sprite reference ('mon:MARILL', 'item:ITEM_LEFTOVERS', …) used by these pages."""
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
    return refs


def split_pages(pages, sprites):
    """-> (guide pages, guide sprites), (team pages, team sprites)."""
    def part(keep):
        ps = [p for p in pages if (p['section'] in TEAM_SECTIONS) == keep]
        refs = page_refs(ps)
        return ps, {k: v for k, v in sprites.items() if k in refs or k.startswith('type:')}
    return part(False), part(True)


@lru_cache(maxsize=1)
def build_data():
    with contextlib.redirect_stdout(io.StringIO()):
        trainers, _, trainer_pics, _, _ = tdx.build_data()
    item_names = tdx.parse_item_names(os.path.join(BASE, 'src/data/items.h'))
    pages = (build_pages(trainers) + build_thief_pages(trainers) + build_safari_pages(item_names)
             + build_frontier_pages(item_names) + build_hidden_power_pages()
             + build_ability_pages()
             + build_coverage_pages() + build_doubles_pages())

    refs = page_refs(pages)

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
GUIDE_PAGES_CSS
</style>
</head>
<body>

<div id="sidebar">
  <div id="sidebar-header">
    <h1>Field Guide</h1>
    <span class="volume">Vol. V · Trades · Gifts · Rematches · Thief · Safari · Frontier · Hidden Power · Abilities</span>
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
GUIDE_PAGES_JS
renderList();
registerApp('guide', key => selectPage(key));
if (!currentPage && !isMobile()) selectPage(PAGES[0].id);
</script>
</body>
</html>
'''


def generate():
    print('Building guide...')
    (pages, sprites), _ = split_pages(*build_data())

    def dump(o):
        return json.dumps(o, ensure_ascii=False, separators=(',', ':'))

    import site_shared
    tpl = HTML_TEMPLATE.replace('GUIDE_PAGES_CSS\n', guide_pages.CSS).replace('GUIDE_PAGES_JS', guide_pages.JS)
    html = site_shared.inject(tpl).replace('GUIDE_PAGES_PLACEHOLDER', dump(pages))
    html = html.replace('GUIDE_SPRITES_PLACEHOLDER', dump(sprites))

    out_path = os.path.join(BASE, 'docs', 'guide.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  {len(pages)} pages, {len(sprites)} sprites')
    print(f'\nGenerated: {out_path} ({os.path.getsize(out_path) / 1024:.0f} KB)')


if __name__ == '__main__':
    generate()
