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
                     role=x['nature'] + ' · ' + x['ability'].replace('_', ' ').title())

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
    if len(learn) <= 4:
        role = 'Learns only these moves'
    elif not chosen or (frail and support):
        role = 'Support'
    else:
        role = ('Physical' if D['moves'][chosen[0]]['type'] in cov.PHYSICAL else 'Special') + ' attacker'
    return _pack(sp, moves, source=None, role=role)


def _pack(sp, moves, source, role):
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
    return dict(moves=out, source=source, role=role)


if __name__ == '__main__':
    for sp in ['CATERPIE', 'MAGIKARP', 'PIKACHU', 'BLISSEY', 'GARCHOMP', 'MEWTWO', 'SLAKING', 'SHEDINJA', 'WOBBUFFET',
               'BLAZIKEN', 'MUDKIP', 'CHARIZARD', 'ALAKAZAM', 'GOLDUCK', 'MACHAMP', 'EXEGGUTOR', 'RELICANTH', 'DITTO',
               'UNOWN', 'SMEARGLE', 'CLEFABLE', 'SHUCKLE', 'CHANSEY', 'PICHU', 'TYROGUE', 'WAILORD', 'DEOXYS_SPEED', 'BELDUM', 'SWALOT']:
        r = suggest(sp)
        if r:
            print(f"{sp:12} {r['role']:32} {[m['move'] for m in r['moves']]} {r['source'] or ''}")
