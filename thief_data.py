"""Held items on every reachable trainer team — shared by the Guide (Where to use Thief)
and the Bag app (Steal from trainers). Scans src/data/trainers.h + trainer_parties.h."""

import os
import re

import generate_trainerdex as tdx
from site_shared import BASE, parse_rematch_tables as _rematch_tables


_LEAGUE_REPEAT = {'SIDNEY_2', 'PHOEBE_2', 'GLACIA_2', 'DRAKE_2', 'WALLACE_2'}


def _all_trainers():
    content = open(os.path.join(BASE, 'src/data/trainers.h')).read()
    chunks = re.split(r'\[(TRAINER_\w+)\]\s*=\s*', content)
    out = []
    for i in range(1, len(chunks) - 1, 2):
        tid, body = chunks[i], chunks[i + 1]
        if tid.endswith(('_SINGLE', '_PLACEHOLDER')) or tid in ('TRAINER_NONE', 'TRAINER_BATTLE_ROYALE_MR_MIMIC'):
            continue
        cls = re.search(r'\.trainerClass\s*=\s*TRAINER_CLASS_(\w+)', body)
        party = re.search(r'\.party\s*=\s*TRAINER_MON\((\w+)\)', body)
        if not cls or not party:
            continue
        name = re.search(r'\.trainerName\s*=\s*_\("([^"]*)"\)', body)
        pic = re.search(r'\.trainerPic\s*=\s*TRAINER_PIC_(\w+)', body)
        out.append(dict(id=tid, cls=cls.group(1), name=name.group(1) if name else '',
                        pic=pic.group(1) if pic else None, party=party.group(1).replace('sParty_', '')))
    return out


# Rough story order of trainer maps (prefix match, longest wins) for the chronological sort.
MAP_PROGRESSION = [
    'Littleroot Town', 'Route 101', 'Oldale Town', 'Route 103', 'Route 102', 'Petalburg City', 'Route 104',
    'Petalburg Woods', 'Rustboro City', 'Rustboro City Gym', 'Route 116', 'Rusturf Tunnel', 'Dewford Town',
    'Dewford Town Gym', 'Granite Cave', 'Route 109', 'Slateport City', 'Slateport City Oceanic Museum',
    'Route 110', 'Route 110 Trick House', 'Mauville City', 'Mauville City Gym', 'Route 117', 'Verdanturf Town',
    'Route 111', 'Route 112', 'Route 113', 'Fallarbor Town', 'Route 114', 'Meteor Falls 1F', 'Mt Chimney',
    'Jagged Pass', 'Lavaridge Town', 'Lavaridge Town Gym', 'Petalburg City Gym', 'Route 105', 'Route 106',
    'Route 107', 'Route 108', 'Abandoned Ship', 'Route 118', 'Route 119', 'Route 119 Weather Institute',
    'Route 120', 'Fortree City', 'Fortree City Gym', 'Route 121', 'Route 122', 'Mt Pyre', 'Route 123',
    'Lilycove City', 'Magma Hideout', 'Aqua Hideout', 'Route 124', 'Mossdeep City', 'Mossdeep City Gym',
    'Route 125', 'Mossdeep City Space Center', 'Route 126', 'Route 127', 'Route 128', 'Seafloor Cavern',
    'Sootopolis City', 'Sootopolis City Gym', 'Route 129', 'Route 130', 'Route 131', 'Pacifidlog Town',
    'Route 132', 'Route 133', 'Route 134', 'Sealed Chamber', 'Victory Road', 'Ever Grande City',
    # post-game areas
    'SSTidal', 'Battle Frontier', 'Meteor Falls Stevens Cave', 'Sky Pillar Top', 'Marine Cave', 'Terra Cave',
    'Cave Of Origin',
]
POSTGAME_MAPS = ('SSTidal', 'Battle Frontier', 'Meteor Falls Stevens Cave', 'Sky Pillar Top', 'Marine Cave',
                 'Terra Cave', 'Cave Of Origin', 'Route 110 Trick House Puzzle 8')
POSTGAME_IDS = {'SIDNEY_2', 'PHOEBE_2', 'GLACIA_2', 'DRAKE_2', 'WALLACE_2', 'STEVEN_2', 'ZINNIA'}


def map_rank(loc):
    best, rank = -1, len(MAP_PROGRESSION)
    for i, pre in enumerate(MAP_PROGRESSION):
        if loc.startswith(pre) and len(pre) > best:
            best, rank = len(pre), i
    return rank


# Importance tiers for held items (opinionated: competitive value in Gen 3 first).
ITEM_TIERS = [
    ('S', ['Leftovers', 'Choice Band', 'Lum Berry']),
    ('A', ['Salac Berry', 'Liechi Berry', 'Petaya Berry', 'Starf Berry', 'Apicot Berry', 'Ganlon Berry',
           'Light Ball', 'Thick Club', 'Soul Dew', 'Deepseatooth', 'Deepseascale', 'Shell Bell', "King's Rock",
           'Scope Lens', 'Focus Band', 'Brightpowder', 'White Herb', 'Quick Claw', 'Sitrus Berry']),
    ('B', ['Nugget', 'Charcoal', 'Mystic Water', 'Magnet', 'Miracle Seed', 'Nevermeltice', 'Black Belt',
           'Soft Sand', 'Sharp Beak', 'Twistedspoon', 'Silverpowder', 'Hard Stone', 'Spell Tag', 'Blackglasses',
           'Silk Scarf', 'Lax Incense', 'Sun Stone']),
    ('C', ['Chesto Berry', 'Wiki Berry', 'Aguav Berry', 'Figy Berry', 'Persim Berry', 'Leppa Berry', 'Oran Berry']),
]
ITEM_IMPORTANCE = {}
for _tier, _names in ITEM_TIERS:
    for _n in _names:
        ITEM_IMPORTANCE[_n] = (_tier, len(ITEM_IMPORTANCE))


def collect_entries(tdex_groups):
    """-> (entries, item_const). entries: one per trainer team with held items;
    item_const: display name -> ITEM_* constant."""
    parties = tdx.parse_parties(os.path.join(BASE, 'src/data/trainer_parties.h'))
    class_names = tdx.parse_class_names(os.path.join(BASE, 'src/data/text/trainer_class_names.h'))
    item_names = tdx.parse_item_names(os.path.join(BASE, 'src/data/items.h'))
    pics = tdx.parse_trainer_pics(os.path.join(BASE, 'src/data/trainer_graphics/front_pic_tables.h'),
                                  os.path.join(BASE, 'src/data/graphics/trainers.h'))
    locations = tdx.parse_trainer_locations(os.path.join(BASE, 'data/maps'))
    base_of, last_rematch = _rematch_tables()
    leader_team5 = {f'TRAINER_{l}_5' for l in tdx._GYM_LEADERS}

    tdex_vids = {v['id'] for g in tdex_groups for v in g['variants']}
    br_ids = {'TRAINER_' + v['id'] for g in tdex_groups for v in g['variants']
              if tdx.trainer_note(v['id'], g['category']) == tdx.BATTLE_ROYALE_NOTE}
    entries = []
    item_const = {}
    for t in _all_trainers():
        consts = [m['heldItem'] for m in parties.get(t['party'], [])
                  if tdx.item_display(m['heldItem'], item_names)]
        items = [tdx.item_display(c, item_names) for c in consts]
        for c, n in zip(consts, items):
            item_const[n] = c
        if not items:
            continue
        locs = locations.get(t['id']) or locations.get(base_of.get(t['id'], ''), [])
        if not locs:
            continue  # unused / unreachable team
        short = t['id'].replace('TRAINER_', '')
        if t['id'] in leader_team5:
            repeat = 'Gym Team 5: rebattle any time'
        elif short in _LEAGUE_REPEAT:
            repeat = 'Every League run after becoming Champion'
        elif t['id'] == 'TRAINER_GRINDING_NURSE':
            repeat = 'Rebattle any time'
        elif t['id'] in last_rematch and t['id'] not in base_of.values() or t['id'] == 'TRAINER_WALLY_VR_5':
            repeat = 'Match Call rematch: their final team repeats'
        else:
            repeat = ''
        cls = class_names.get(t['cls'], t['cls'].replace('_', ' '))
        cls = ' '.join(w[:1].upper() + w[1:].lower() for w in cls.split())
        nm = t['name'].title() if t['name'].isupper() else t['name']
        plain = ('pkmn trainer', 'pokémon trainer', 'leader', 'elite four', 'champion')
        label = nm if (not nm or cls.lower() in plain) else f'{cls} {nm}'
        # Tell apart the several teams of the same trainer
        team = re.search(r'_(\d+)$', short)
        if short in _LEAGUE_REPEAT:
            label += ' (Champion)' if short == 'WALLACE_2' else ' (Rematch)'
        elif team and (t['id'] in base_of or short.startswith('BRAWLY_1_')):
            label += ' (Team ' + '.'.join(re.findall(r'_(\d+)', short)) + ')'
        counts = {}
        for it in items:
            counts[it] = counts.get(it, 0) + 1
        # Chronology: story fights, then in-story Match Call rematches, then post-game fights.
        team_n = int(team.group(1)) if team else 1
        if (short in POSTGAME_IDS or short.startswith(('WALLY_VR_', 'JUAN_')) and short != 'WALLY_VR_1'
                or any(l.startswith(POSTGAME_MAPS) for l in locs)
                or (t['id'] in base_of and short.split('_')[0] in {k.split('_')[0] for k in tdx._GYM_LEADERS} and team_n >= 3)):
            phase = 2
        elif t['id'] in base_of and t['id'] not in base_of.values():
            phase = 1
        else:
            phase = 0
        chrono = phase * 10000 + min(map_rank(l) for l in locs) * 10 + min(team_n, 9)
        entries.append(dict(id=short, label=label or cls, cls=cls, locs=locs, repeat=repeat, counts=counts,
                            pic=pics.get(t['pic']), chrono=chrono, phase=phase, br=t['id'] in br_ids,
                            tv=short if short in tdex_vids else None))

    return entries, item_const
