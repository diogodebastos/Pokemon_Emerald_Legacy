#!/usr/bin/env python3
"""Type-coverage analysis for the Guide's "Team Building" pages (generate_guide.py).

Everything is computed from the decomp source, so it follows any balance change:
- gTypeEffectiveness (src/battle_main.c) — the Gen 3 chart, no Fairy.
- species types/abilities/base stats (src/data/pokemon/species_info.h).
- every way a species can learn a move: level-up (its own list or a pre-evolution's),
  TM/HM, move tutor, egg move of the line's base form.
- move power/type/target (src/data/battle_moves.h).

"Super effective" means the hit really does double damage against every possible
ability of the defender: Levitate / Flash Fire / Volt Absorb / Water Absorb block their
type, Thick Fat turns a 2× Fire/Ice hit neutral.
"""

import os
import re
import itertools
from functools import lru_cache

BASE = os.path.dirname(os.path.abspath(__file__))

TYPES = ['NORMAL', 'FIGHTING', 'FLYING', 'POISON', 'GROUND', 'ROCK', 'BUG', 'GHOST', 'STEEL',
         'FIRE', 'WATER', 'GRASS', 'ELECTRIC', 'PSYCHIC', 'ICE', 'DRAGON', 'DARK']
# Gen 3 split is by type.
PHYSICAL = {'NORMAL', 'FIGHTING', 'FLYING', 'POISON', 'GROUND', 'ROCK', 'BUG', 'GHOST', 'STEEL'}
TYPE_ICON_FILE = {t: t.lower() for t in TYPES} | {'FIGHTING': 'fight'}

ABILITY_BLOCKS = {'LEVITATE': 'GROUND', 'FLASH_FIRE': 'FIRE', 'VOLT_ABSORB': 'ELECTRIC',
                  'WATER_ABSORB': 'WATER'}
LEGENDARY = {'ARTICUNO', 'ZAPDOS', 'MOLTRES', 'MEWTWO', 'MEW', 'RAIKOU', 'ENTEI', 'SUICUNE',
             'LUGIA', 'HO_OH', 'CELEBI', 'REGIROCK', 'REGICE', 'REGISTEEL', 'LATIAS', 'LATIOS',
             'KYOGRE', 'GROUDON', 'RAYQUAZA', 'JIRACHI', 'DEOXYS', 'DEOXYS_SPEED', 'DEOXYS_ATTACK',
             'DEOXYS_DEFENSE'}
# Moves that can't be relied on as a coverage slot (charge turns, recharge, self-KO,
# fixed/variable damage, multi-turn lock-in, stat drops, wake-only…).
UNRELIABLE = {'EFFECT_EXPLOSION', 'EFFECT_RECHARGE', 'EFFECT_FUTURE_SIGHT', 'EFFECT_SOLAR_BEAM',
              'EFFECT_RAZOR_WIND', 'EFFECT_SKY_ATTACK', 'EFFECT_SKULL_BASH', 'EFFECT_FOCUS_PUNCH',
              'EFFECT_SEMI_INVULNERABLE', 'EFFECT_DREAM_EATER', 'EFFECT_SNORE', 'EFFECT_OHKO',
              'EFFECT_FALSE_SWIPE', 'EFFECT_FLAIL', 'EFFECT_LOW_KICK', 'EFFECT_ROLLOUT', 'EFFECT_BIDE',
              'EFFECT_UPROAR', 'EFFECT_SPIT_UP', 'EFFECT_OVERHEAT', 'EFFECT_SUPERPOWER',
              'EFFECT_RAMPAGE', 'EFFECT_MAGNITUDE', 'EFFECT_HIDDEN_POWER', 'EFFECT_ERUPTION'}
MIN_POWER = 60


def _read(rel):
    with open(os.path.join(BASE, rel), encoding='utf-8') as f:
        return f.read()


@lru_cache(maxsize=1)
def load():
    chart = {}
    for a, d, m in re.findall(r'TYPE_(\w+), TYPE_(\w+), TYPE_MUL_(\w+)', _read('src/battle_main.c')):
        if a in TYPES and d in TYPES:
            chart[(a, d)] = {'SUPER_EFFECTIVE': 2, 'NOT_EFFECTIVE': 0.5, 'NO_EFFECT': 0}[m]

    num_species = int(re.search(r'#define SPECIES_EGG (\d+)', _read('include/constants/species.h')).group(1))
    ids = dict((n, int(v)) for n, v in re.findall(r'#define SPECIES_(\w+)\s+(\d+)', _read('include/constants/species.h')))
    species = {}
    parts = re.split(r'\[SPECIES_(\w+)\]\s*=', _read('src/data/pokemon/species_info.h'))
    for name, body in zip(parts[1::2], parts[2::2]):
        if name == 'NONE' or name.startswith('OLD_UNOWN') or ids.get(name, num_species) >= num_species:
            continue
        types = re.search(r'\.types = \{ ?TYPE_(\w+), TYPE_(\w+)', body).groups()
        abil = set(re.search(r'\.abilities = \{([^}]*)\}', body).group(1).replace('ABILITY_', '').replace(' ', '').split(','))
        stat = lambda s: int(re.search(r'\.base%s\s*=\s*(\d+)' % s, body).group(1))
        eggs = re.search(r'\.eggGroups = \{ ?EGG_GROUP_(\w+), EGG_GROUP_(\w+)', body).groups()
        gender = re.search(r'\.genderRatio = (\w+(?:\([^)]*\))?)', body).group(1)
        species[name] = dict(types=tuple(dict.fromkeys(types)), abilities=abil - {'NONE', ''},
                             atk=stat('Attack'), spa=stat('SpAttack'),
                             bulk=stat('HP') + stat('Defense') + stat('SpDefense'),
                             base=dict(hp=stat('HP'), atk=stat('Attack'), def_=stat('Defense'), spa=stat('SpAttack'), spd=stat('SpDefense'), spe=stat('Speed')), egg_groups=set(eggs) - {'NO_EGGS_DISCOVERED'},
                             can_be_male=gender not in ('MON_FEMALE', 'MON_GENDERLESS'))

    moves = {}
    for m in re.finditer(r'\[MOVE_(\w+)\]\s*=\s*\{(.*?)\}', _read('src/data/battle_moves.h'), re.S):
        name, body = m.groups()
        g = lambda k: re.search(r'\.%s = (\w+)' % k, body).group(1)
        moves[name] = dict(type=g('type').replace('TYPE_', ''), power=int(g('power')), effect=g('effect'),
                           spread=g('target') == 'MOVE_TARGET_FOES_AND_ALLY', target=g('target'),
                           accuracy=int(g('accuracy')), priority=int(re.search(r'\.priority = (-?\d+)', body).group(1)))

    # Every way each species can learn each move, e.g. {'EARTHQUAKE': ['Lv 61', 'TM26']}.
    learn = {s: {} for s in species}
    lu = _read('src/data/pokemon/level_up_learnsets.h')
    arrays = {a: re.findall(r'LEVEL_UP_MOVE\(\s*(\d+),\s*MOVE_(\w+)\)', b)
              for a, b in re.findall(r'static const u16 (\w+)\[\] = \{(.*?)\};', lu, re.S)}
    levelup = {s: arrays[a] for s, a in re.findall(r'\[SPECIES_(\w+)\] = (\w+),', _read('src/data/pokemon/level_up_learnset_pointers.h'))}
    prevo = {}
    for s, body in re.findall(r'\[SPECIES_(\w+)\]\s*=\s*\{(.*?)\}\},', _read('src/data/pokemon/evolution.h'), re.S):
        for t in re.findall(r'SPECIES_(\w+)\}', body + '}'):
            prevo.setdefault(t, s)
    tm_order = re.findall(r'F\((\w+)\)', _read('include/constants/tms_hms.h'))
    n_tm = len(re.findall(r'F\((\w+)\)', _read('include/constants/tms_hms.h').split('#define FOREACH_HM')[0]))
    tm_label = {mv: (f'TM{i + 1:02d}' if i < n_tm else f'HM{i - n_tm + 1:02d}') for i, mv in enumerate(tm_order)}
    tmhm = {s: re.findall(r'\.(\w+) = TRUE', b) for s, b in
            re.findall(r'\[SPECIES_(\w+)\] = \{ \.learnset = \{(.*?)\}', _read('src/data/pokemon/tmhm_learnsets.h'), re.S)}
    tutor = {s: re.findall(r'TUTOR\(MOVE_(\w+)\)', b) for s, b in
             re.findall(r'\[SPECIES_(\w+)\]\s*=\s*\((.*?)\),', _read('src/data/pokemon/tutor_learnsets.h'), re.S)}
    # Tutor NPC → where they stand (all of them teach any number of times in this hack).
    tutor_where = {}
    for label, mv in re.findall(r'(\w+?)_EventScript_\w+Tutor::.*?TUTOR_MOVE_(\w+)', _read('data/scripts/move_tutors.inc'), re.S):
        place = re.sub(r'(?<=[a-z])(?=[A-Z0-9])', ' ', label.split('_')[0])
        tutor_where[mv] = place
    for block in re.findall(r'sBattleFrontier_TutorMoves\d\[\] =\s*\{(.*?)\};', _read('src/field_specials.c'), re.S):
        for mv in re.findall(r'MOVE_(\w+)', block):
            tutor_where.setdefault(mv, 'Battle Frontier')
    egg = {s: re.findall(r'MOVE_(\w+)', b) for s, b in
           re.findall(r'egg_moves\((\w+),(.*?)\)', _read('src/data/pokemon/egg_moves.h'), re.S)}

    for s in species:
        L = learn[s]
        add = lambda mv, how: L.setdefault(mv, []).append(how) if how not in L.get(mv, []) else None
        for lvl, mv in levelup.get(s, []):
            add(mv, f'Lv {int(lvl)}')
        chain = [s]
        while chain[-1] in prevo:
            chain.append(prevo[chain[-1]])
        for c in chain[1:]:
            for lvl, mv in levelup.get(c, []):
                if mv not in L:
                    add(mv, f'Lv {int(lvl)} as {c.replace("_", " ").title()}')
        for c in chain:
            for mv in egg.get(c, []):
                add(mv, 'Egg move')
        for mv in tmhm.get(s, []):
            add(mv, tm_label.get(mv, 'TM'))
        for mv in tutor.get(s, []):
            add(mv, f'Tutor ({tutor_where[mv]})' if mv in tutor_where else 'Tutor')

    return dict(chart=chart, species=species, moves=moves, learn=learn, prevo=prevo)


def effectiveness(atk, def_types):
    chart = load()['chart']
    x = 1
    for d in def_types:
        x *= chart.get((atk, d), 1)
    return x


def super_effective(atk, sp):
    d = load()['species'][sp]
    e = effectiveness(atk, d['types'])
    if e < 2:
        return False
    for a in d['abilities']:
        if ABILITY_BLOCKS.get(a) == atk:
            return False
        if a == 'THICK_FAT' and atk in ('FIRE', 'ICE') and e < 4:
            return False
    return True


@lru_cache(maxsize=None)
def immune_to(atk, sp):
    d = load()['species'][sp]
    return effectiveness(atk, d['types']) == 0 or any(ABILITY_BLOCKS.get(a) == atk for a in d['abilities'])


@lru_cache(maxsize=1)
def coverage():
    sp = load()['species']
    return {t: frozenset(s for s in sp if super_effective(t, s)) for t in TYPES}


def uncoverable():
    cov = coverage()
    hit = frozenset().union(*cov.values())
    return sorted(s for s in load()['species'] if s not in hit)


def hittable():
    return frozenset(load()['species']) - set(uncoverable())


def covered_by(types):
    cov = coverage()
    return frozenset().union(*(cov[t] for t in types)) if types else frozenset()


@lru_cache(maxsize=1)
def minimum_covers():
    """(k, [type sets]) — the fewest attacking types that hit every hittable species."""
    target = hittable()
    for k in range(1, len(TYPES) + 1):
        sols = [c for c in itertools.combinations(TYPES, k) if covered_by(c) >= target]
        if sols:
            return k, sols


@lru_cache(maxsize=None)
def best_sets(k, limit=6):
    target = hittable()
    ranked = sorted(itertools.combinations(TYPES, k), key=lambda c: -len(covered_by(c) & target))
    return ranked[:limit]


def best_move(sp, t, partner=None):
    """Strongest reliable move of type t for sp → dict, or None. With a partner, spread
    moves that would also hit the partner (Earthquake…) are skipped."""
    return _best_move(sp, t, bool(partner) and not immune_to(t, partner))


@lru_cache(maxsize=None)
def _best_move(sp, t, avoid_spread):
    D = load()
    s = D['species'][sp]
    best = None
    for mv, how in D['learn'][sp].items():
        m = D['moves'].get(mv)
        if not m or m['type'] != t or m['power'] < MIN_POWER or m['effect'] in UNRELIABLE:
            continue
        if avoid_spread and m['spread']:
            continue
        stab = t in s['types']
        score = m['power'] * (1.5 if stab else 1) * (s['atk'] if t in PHYSICAL else s['spa'])
        if not best or score > best['score']:
            best = dict(move=mv, type=t, power=m['power'], how=' · '.join(how), stab=stab, spread=m['spread'], score=score)
    return best


def duo(a, a_types, b, b_types, partner_safe=False):
    """Movesets for a pair given which attacking types each one carries."""
    ma = [best_move(a, t, b if partner_safe else None) for t in a_types]
    mb = [best_move(b, t, a if partner_safe else None) for t in b_types]
    if None in ma or None in mb:
        raise ValueError(f'{a}/{b} cannot learn {a_types}/{b_types}')
    types = list(a_types) + list(b_types)
    hits = covered_by(types)
    # Spread moves: does the partner take the hit?
    ally_hits = [(a, m['move'], b) for m in ma if m['spread'] and not immune_to(m['type'], b)] + \
                [(b, m['move'], a) for m in mb if m['spread'] and not immune_to(m['type'], a)]
    return dict(a=a, b=b, a_moves=ma, b_moves=mb, hit=len(hits & hittable()), total=len(hittable()),
                missed=sorted(hittable() - hits), ally_hits=ally_hits,
                score=sum(m['score'] for m in ma + mb))


@lru_cache(maxsize=None)
def final_forms(legendary=False):
    D = load()
    evolves = set(D['prevo'].values())
    return [s for s in D['species'] if s not in evolves and (legendary or s not in LEGENDARY)
            and s not in ('SHEDINJA', 'SMEARGLE', 'UNOWN')]


@lru_cache(maxsize=None)
def _duo_scores(partner_safe):
    """Best 8-type split per pair (legendaries included) → {(a, b): (score, A, B)}."""
    cands = final_forms(legendary=True)
    best_k = max(len(covered_by(c) & hittable()) for c in best_sets(8, 1))
    sets = [c for c in best_sets(8, 12) if len(covered_by(c) & hittable()) == best_k]
    results = {}
    for ts in sets:
        for a, b in itertools.combinations(cands, 2):
            for A in itertools.combinations(ts, 4):
                B = tuple(t for t in ts if t not in A)
                ma = [best_move(a, t, b if partner_safe else None) for t in A]
                if None in ma:
                    continue
                mb = [best_move(b, t, a if partner_safe else None) for t in B]
                if None in mb:
                    continue
                score = sum(m['score'] for m in ma + mb)
                if score > results.get((a, b), (0,))[0]:
                    results[(a, b)] = (score, A, B)
    return results


def rank_duos(partner_safe=True, top=10, legendary=False):
    """Best fully-evolved pairs over the best 8-type sets. legendary=True keeps only pairs
    with at least one legendary; False keeps only pairs with none."""
    res = _duo_scores(partner_safe)
    keep = lambda a, b: (a in LEGENDARY or b in LEGENDARY) == legendary
    ranked, seen = [], {}
    for (a, b), v in sorted(((k, v) for k, v in res.items() if keep(*k)), key=lambda kv: -kv[1][0]):
        if legendary and (seen.get(a, 0) >= 2 or seen.get(b, 0) >= 2):
            continue
        seen[a] = seen.get(a, 0) + 1
        seen[b] = seen.get(b, 0) + 1
        ranked.append(((a, b), v))
        if len(ranked) == top:
            break
    return [duo(a, A, b, B, partner_safe) for (a, b), (_, A, B) in ranked]


# ---------------------------------------------------------------------------
# Defensive duos — no shared weakness; each one's weaknesses resisted by the other.
# ---------------------------------------------------------------------------

def defense_multiplier(sp, atk):
    d = load()['species'][sp]
    if any(ABILITY_BLOCKS.get(a) == atk for a in d['abilities']):
        return 0
    x = effectiveness(atk, d['types'])
    if 'THICK_FAT' in d['abilities'] and atk in ('FIRE', 'ICE'):
        x /= 2
    return x


RESIST_WEIGHT = 25   # one resisted/immune attacking type is worth 25 points of base bulk
MIN_RESISTS = 12


@lru_cache(maxsize=None)
def rank_defensive_duos(top=10, legendary=False, per_species=2):
    """Pairs with no shared weakness where every weakness of one is resisted (or blocked)
    by the other. Score = RESIST_WEIGHT × attacking types at least one resists
    + base HP/Def/SpD of both + 10 × immunities. Each species appears at most per_species times."""
    cands = final_forms(legendary=True)
    mult = {s: [defense_multiplier(s, t) for t in TYPES] for s in cands}
    sp = load()['species']
    rows = []
    for a, b in itertools.combinations(cands, 2):
        if (a in LEGENDARY or b in LEGENDARY) != legendary:
            continue
        ma, mb = mult[a], mult[b]
        if any((x > 1 and y >= 1) or (y > 1 and x >= 1) for x, y in zip(ma, mb)):
            continue
        resist = sum(min(x, y) < 1 for x, y in zip(ma, mb))
        if resist < MIN_RESISTS:
            continue
        immune = sum(min(x, y) == 0 for x, y in zip(ma, mb))
        bulk = sp[a]['bulk'] + sp[b]['bulk']
        rows.append((resist * RESIST_WEIGHT + bulk + immune * 10, a, b, resist, immune, bulk))
    rows.sort(key=lambda r: -r[0])
    seen, out = {}, []
    for score, a, b, resist, immune, bulk in rows:
        if seen.get(a, 0) >= per_species or seen.get(b, 0) >= per_species:
            continue
        seen[a] = seen.get(a, 0) + 1
        seen[b] = seen.get(b, 0) + 1
        out.append(dict(a=a, b=b, resist=resist, immune=immune, bulk=bulk,
                        matchups={x: [defense_multiplier(x, t) for t in TYPES] for x in (a, b)}))
        if len(out) == top:
            break
    return out


def best_split(a, b, partner_safe=True):
    """Best attacking split for an arbitrary pair: 4 types each, most species hit, then damage."""
    def usable(sp, other):
        ts = [t for t in TYPES if best_move(sp, t, other if partner_safe else None)]
        return sorted(ts, key=lambda t: -len(coverage()[t]))[:9]
    ta, tb = usable(a, b), usable(b, a)
    target = hittable()
    best = None
    for A in itertools.combinations(ta, min(4, len(ta))):
        ca = covered_by(A)
        for B in itertools.combinations([t for t in tb if t not in A], min(4, len([t for t in tb if t not in A]))):
            n = len((ca | covered_by(B)) & target)
            if best and n < best[0]:
                continue
            score = sum(best_move(a, t, b if partner_safe else None)['score'] for t in A) + \
                    sum(best_move(b, t, a if partner_safe else None)['score'] for t in B)
            if not best or (n, score) > best[:2]:
                best = (n, score, A, B)
    return duo(a, best[2], b, best[3], partner_safe)


if __name__ == '__main__':
    k, sols = minimum_covers()
    print('uncoverable:', uncoverable(), '| hittable:', len(hittable()), '| min types:', k)
    for s in sols:
        print('  ', s)
    for c in best_sets(8, 3):
        print(len(covered_by(c) & hittable()), c, sorted(hittable() - covered_by(c)))
    import time; t0 = time.time()
    for leg in (False, True):
        for d in rank_duos(True, 6, leg):
            print(d['hit'], d['a'], [m['move'] for m in d['a_moves']], '|', d['b'], [m['move'] for m in d['b_moves']], d['ally_hits'])
    print('duos', time.time() - t0)
    for leg in (False, True):
        for d in rank_defensive_duos(10, leg):
            print(d)
    d = rank_defensive_duos(10)[0]
    x = best_split(d['a'], d['b'])
    print(x['hit'], [m['move'] for m in x['a_moves']], [m['move'] for m in x['b_moves']], time.time() - t0)
