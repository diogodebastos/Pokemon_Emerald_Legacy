#!/usr/bin/env python3
"""Suggested 4-move sets for the Pokédex ("Suggested Moveset" section, generate_pokedex.py).

Every move comes from coverage_data.load(), i.e. what the species can really learn in this
hack (level-up incl. pre-evolutions, TM/HM, tutor, egg moves — the Move Relearner teaches
those). Built for double battles:

1. Species used by a Guide team (doubles_teams.TEAMS, validated at Guide build time) reuse
   that hand-picked set.
2. Everyone else gets an automatic set:
   - its attacking side is whichever of Attack / Sp. Atk is higher (Gen 3 splits by type,
     so a type is only worth using if its category matches);
   - the strongest reliable attack (power × accuracy × STAB × the matching stat, spread
     moves slightly preferred, moves that also hit the partner slightly penalised),
   - then attacks that add the most super-effective coverage,
   - and one doubles slot: Spore, a setup move for strong attackers, Fake Out, Follow Me /
     Helping Hand / Wish for frail supports, otherwise Protect.
"""

import re
from functools import lru_cache

import coverage_data as cov

# Damaging effects that can't be relied on as a regular attack.
SKIP_EFFECTS = cov.UNRELIABLE | {
    'EFFECT_TRAP', 'EFFECT_COUNTER', 'EFFECT_MIRROR_COAT', 'EFFECT_SONICBOOM', 'EFFECT_DRAGON_RAGE',
    'EFFECT_PSYWAVE', 'EFFECT_SUPER_FANG', 'EFFECT_ENDEAVOR', 'EFFECT_PRESENT', 'EFFECT_RAGE',
    'EFFECT_FURY_CUTTER', 'EFFECT_SMELLINGSALT', 'EFFECT_WEATHER_BALL', 'EFFECT_FRUSTRATION',
    'EFFECT_TRIPLE_KICK', 'EFFECT_BEAT_UP', 'EFFECT_RAPID_SPIN', 'EFFECT_FAKE_OUT', 'EFFECT_PAY_DAY',
    'EFFECT_THIEF', 'EFFECT_SNORE', 'EFFECT_LEVEL_DAMAGE',
}
HITS = {'EFFECT_MULTI_HIT': 3, 'EFFECT_DOUBLE_HIT': 2, 'EFFECT_TWINEEDLE': 2}
FIXED_POWER = {'RETURN': 102}          # max friendship

TAG_STAB, TAG_COVER, TAG_SPREAD, TAG_ALLY = 'STAB', 'Coverage', 'Hits both foes', 'Hits ally too'


@lru_cache(maxsize=1)
def natures():
    """{('atk', 'spa'): 'Adamant', …} — the raised/lowered stat pair, from gNatureStatTable."""
    order = ['atk', 'def_', 'spe', 'spa', 'spd']
    table, body = {}, cov._read('src/pokemon.c').split('gNatureStatTable')[1]
    for name, nums in re.findall(r'\[NATURE_(\w+)\]\s*=\s*\{([^}]*)\}', body):
        vals = [int(x) for x in re.findall(r'[+-]?\d+', nums)]
        plus = next((order[i] for i, v in enumerate(vals) if v > 0), None)
        minus = next((order[i] for i, v in enumerate(vals) if v < 0), None)
        if plus and minus:
            table[(plus, minus)] = name.title()
    return table


STAT_NAME = dict(hp='HP', atk='Attack', def_='Defense', spa='Sp. Atk', spd='Sp. Def', spe='Speed')


def _nature_entry(name):
    for (plus, minus), n in natures().items():
        if n == name:
            return dict(name=n, plus=STAT_NAME[plus], minus=STAT_NAME[minus])
    return dict(name=name, plus='', minus='')


def pick_nature(sp, moves, support=False):
    """Raise what the set actually uses; lower the offensive stat it needs least."""
    D = cov.load()
    b = D['species'][sp]['base']
    damage = {'phys': 0.0, 'spec': 0.0}
    for mv in moves:
        if D['moves'][mv]['power'] > 0:
            damage['phys' if D['moves'][mv]['type'] in cov.PHYSICAL else 'spec'] += attack_score(sp, mv)
    # A move doing under 15% of the set's damage isn't worth protecting its stat.
    if max(damage.values() or [0]) > 0:
        for k in damage:
            if damage[k] / max(damage.values()) < 0.15:
                damage[k] = 0.0
    fast = b['spe'] >= 100
    lean = 'atk' if damage['phys'] >= damage['spec'] else 'spa'
    spare = 'spa' if lean == 'atk' else 'atk'
    if not any(damage.values()):                   # no attacks at all
        spare = 'spa' if b['atk'] <= b['spa'] else 'atk'
        lean = None
    if support or lean is None:                    # frail: bulk (or speed) matters more than power
        plus = 'spe' if fast else ('def_' if b['def_'] >= b['spd'] else 'spd')
        minus = spare
    elif damage['phys'] and damage['spec']:        # mixed: no offensive stat is really spare
        plus = 'spe' if fast else lean
        minus = 'spd' if plus == 'spe' and b['spd'] <= b['def_'] else 'def_'
    else:
        plus = 'spe' if fast else lean
        minus = spare
    return _nature_entry(natures()[(plus, minus)])


def _attack_stat(sp, mtype):
    s = cov.load()['species'][sp]
    stat = s['atk'] if mtype in cov.PHYSICAL else s['spa']
    if mtype in cov.PHYSICAL and s['abilities'] & {'HUGE_POWER', 'PURE_POWER'}:
        stat *= 2
    return stat


def _power(mv):
    m = cov.load()['moves'][mv]
    return FIXED_POWER.get(mv, m['power']) * HITS.get(m['effect'], 1)


def attack_score(sp, mv):
    D = cov.load()
    m = D['moves'][mv]
    if m['power'] <= 0 or m['effect'] in SKIP_EFFECTS:
        return 0
    s = D['species'][sp]
    acc = (m['accuracy'] or 100) / 100
    score = _power(mv) * acc * (1.5 if m['type'] in s['types'] else 1) * _attack_stat(sp, m['type'])
    if m['target'] == 'MOVE_TARGET_BOTH':
        score *= 1.1
    if m['target'] == 'MOVE_TARGET_FOES_AND_ALLY':
        score *= 0.9
    return score


def _first(learn, moves):
    return next((mv for mv in moves if mv in learn), None)


def _curated():
    import doubles_teams as dt
    out = {}
    for t in dt.TEAMS:
        for x in t['members']:
            out.setdefault(x['sp'], (t, x))
    return out


@lru_cache(maxsize=None)
def suggest(sp):
    D = cov.load()
    if sp not in D['species']:
        return None
    learn = D['learn'][sp]
    cur = _curated().get(sp)
    if cur:
        t, x = cur
        moves = [mv[0] if isinstance(mv, tuple) else mv for mv in x['moves']]
        return _pack(sp, moves, source=dict(team=t['name'], id='team-' + t['id']),
                     role=x['ability'].replace('_', ' ').title(), nature=_nature_entry(x['nature']))

    s = D['species'][sp]
    scored = sorted(((attack_score(sp, mv), mv) for mv in learn), reverse=True)
    scored = [(sc, mv) for sc, mv in scored if sc > 0]
    physical = s['atk'] >= s['spa']
    top_stat = max(s['atk'] * (2 if s['abilities'] & {'HUGE_POWER', 'PURE_POWER'} else 1), s['spa'])
    frail = top_stat < 70

    # --- the doubles slot(s) ---
    support = []
    if 'SPORE' in learn:
        support.append('SPORE')
    if frail:
        for pick in (['FOLLOW_ME'], ['HELPING_HAND'], ['WISH', 'SOFT_BOILED', 'RECOVER', 'MOONLIGHT', 'MORNING_SUN', 'SYNTHESIS'],
                     ['THUNDER_WAVE', 'WILL_O_WISP', 'SLEEP_POWDER', 'STUN_SPORE', 'ENCORE', 'CONFUSE_RAY']):
            mv = _first(learn, pick)
            if mv and mv not in support and len(support) < 2:
                support.append(mv)
    else:
        setup_ok = top_stat >= 100 and any(mv in learn for mv in ('DRAGON_DANCE', 'BELLY_DRUM', 'SWORDS_DANCE', 'CALM_MIND', 'BULK_UP'))
        if setup_ok and not support:
            support.append('SETUP')          # decided once the attacks are known
        elif 'FAKE_OUT' in learn and not support:
            support.append('FAKE_OUT')
    if 'PROTECT' in learn and len(support) < 2 and (frail or not support):
        support.append('PROTECT')

    # --- attacks: best hit, then coverage ---
    n_attacks = 4 - len(support)
    chosen, types = [], []
    target = cov.hittable()
    best = scored[0][0] if scored else 1
    while len(chosen) < n_attacks and scored:
        covered = cov.covered_by(types)
        def value(item):
            sc, mv = item
            t = D['moves'][mv]['type']
            if t in types:
                return -1
            if chosen and sc / best < 0.4:   # coverage has to hit reasonably hard too
                return -1
            gain = len((cov.covered_by(types + [t]) - covered) & target) / len(target)
            return gain * 3 + sc / best
        pick = max(scored, key=value)
        if value(pick) < 0:
            break
        chosen.append(pick[1])
        types.append(D['moves'][pick[1]]['type'])
        scored.remove(pick)

    if 'SETUP' in support:
        n_phys = sum(D['moves'][mv]['type'] in cov.PHYSICAL for mv in chosen)
        n_spec = len(chosen) - n_phys
        if n_phys >= 2 and n_spec == 0:
            setup = _first(learn, ['DRAGON_DANCE', 'BELLY_DRUM' if s['abilities'] & {'HUGE_POWER'} else '', 'SWORDS_DANCE', 'BULK_UP'])
        elif n_spec >= 2 and n_phys == 0:
            setup = _first(learn, ['CALM_MIND'])
        else:
            setup = None                     # mixed attacker: a boost would only help half its moves
        fallback = _first(learn, ['FAKE_OUT', 'PROTECT'])
        support = [x for x in (setup or fallback,) if x]
    moves = chosen + support
    # Top up (weak or tiny movepools) with anything useful that's left.
    if len(moves) < 4:
        extras = [mv for sc, mv in scored if mv not in moves] + \
                 [mv for mv in ('PROTECT', 'HELPING_HAND', 'WISH', 'TOXIC', 'THUNDER_WAVE', 'ENCORE', 'SUBSTITUTE',
                                'REST', 'ATTRACT', 'DOUBLE_TEAM') if mv in learn and mv not in moves] + \
                 sorted(mv for mv in learn if mv not in moves)
        for mv in extras:
            if len(moves) == 4:
                break
            if mv not in moves:
                moves.append(mv)
    dmg = {'phys': 0.0, 'spec': 0.0}
    for mv in chosen:
        dmg['phys' if D['moves'][mv]['type'] in cov.PHYSICAL else 'spec'] += attack_score(sp, mv)
    if len(learn) <= 4:
        role = 'Learns only these moves'
    elif not chosen or (frail and support):
        role = 'Support'
    elif dmg['phys'] and dmg['spec'] and min(dmg.values()) / max(dmg.values()) > 0.4:
        role = 'Mixed attacker'
    else:
        role = ('Physical' if dmg['phys'] >= dmg['spec'] else 'Special') + ' attacker'
    return _pack(sp, moves, source=None, role=role, nature=pick_nature(sp, [mv for mv in moves if mv in D['moves']], support=role == 'Support'))


def _pack(sp, moves, source, role, nature):
    D = cov.load()
    s = D['species'][sp]
    types_so_far = []
    out = []
    for mv in moves:
        m = D['moves'].get(mv)
        if not m:
            continue
        tags = []
        if m['power'] > 0:
            if m['type'] in s['types']:
                tags.append(TAG_STAB)
            elif m['type'] not in types_so_far:
                tags.append(TAG_COVER)
            types_so_far.append(m['type'])
            if m['target'] == 'MOVE_TARGET_BOTH':
                tags.append(TAG_SPREAD)
            if m['target'] == 'MOVE_TARGET_FOES_AND_ALLY':
                tags.append(TAG_ALLY)
        if m['priority'] > 0 and m['power'] > 0:
            tags.append('Priority')
        how = [h for h in D['learn'][sp][mv] if h != 'Egg move'] or ['Egg move · Move Relearner']
        out.append(dict(move=mv, type=m['type'], power=FIXED_POWER.get(mv, m['power']), accuracy=m['accuracy'],
                        how=' · '.join(how), tags=tags))
    return dict(moves=out, source=source, role=role, nature=nature)


if __name__ == '__main__':
    for sp in ['CATERPIE', 'MAGIKARP', 'PIKACHU', 'BLISSEY', 'GARCHOMP', 'MEWTWO', 'SLAKING', 'SHEDINJA', 'WOBBUFFET',
               'BLAZIKEN', 'MUDKIP', 'CHARIZARD', 'ALAKAZAM', 'GOLDUCK', 'MACHAMP', 'EXEGGUTOR', 'RELICANTH', 'DITTO',
               'UNOWN', 'SMEARGLE', 'CLEFABLE', 'SHUCKLE', 'CHANSEY', 'PICHU', 'TYROGUE', 'WAILORD', 'DEOXYS_SPEED', 'BELDUM', 'SWALOT']:
        r = suggest(sp)
        if r:
            n = r['nature']
            print(f"{sp:12} {r['role']:24} {n['name']:8} (+{n['plus']} -{n['minus']}) {[m['move'] for m in r['moves']]}")
