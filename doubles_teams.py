#!/usr/bin/env python3
"""Double-battle team suggestions for the Guide's "Double Battles" section (generate_guide.py).

The archetypes come from ADV (Gen 3) Doubles on Smogon — Metagross + Gengar leads,
manual rain with Swift Swim, Chlorophyll sun, Tyranitar sand, Fake Out / Follow Me support:
  https://www.smogon.com/articles/adv-doubles-intro
  https://www.smogon.com/forums/threads/adv-doubles-ou.3666831/
…re-built for this hack. Nothing here is trusted by hand: validate() checks every set
against the decomp (coverage_data.load()) and the build fails if a move, ability or item
isn't really available. Egg moves must have a real breeding chain (egg_chain()).

Mechanics quoted on the page were checked in the source:
- src/pokemon.c CalculateBaseDamage: MOVE_TARGET_BOTH moves deal half damage while both
  foes stand; MOVE_TARGET_FOES_AND_ALLY (Earthquake, Magnitude, Explosion, Self-Destruct)
  don't; Explosion halves the target's Defense.
- src/battle_util.c: Follow Me redirects only single-target moves from the other side;
  Lightning Rod only draws the *opponents'* Electric moves and grants no immunity.
- src/pokemon.c: Plus/Minus ×1.5 Sp. Atk while the other ability is on the field.
- src/battle_script_commands.c: Thunder never misses in rain (50% in sun), Blizzard never
  misses in hail; Rain Dance / Sunny Day / Sandstorm / Hail last 5 turns; Wonder Guard
  blocks every non-super-effective hit, the partner's included.
"""

from collections import deque

import coverage_data as cov

# ---------------------------------------------------------------------------
# Breeding: can this species hatch knowing an egg move?
# ---------------------------------------------------------------------------

def _family(sp):
    D = cov.load()
    root = sp
    while root in D['prevo']:
        root = D['prevo'][root]
    members = {root}
    grew = True
    while grew:
        grew = False
        for child, parent in D['prevo'].items():
            if parent in members and child not in members:
                members.add(child)
                grew = True
    return root, members


def _egg_groups(members):
    sp = cov.load()['species']
    return set().union(*(sp[m]['egg_groups'] for m in members))


def _knows_directly(sp, move):
    return any(h != 'Egg move' for h in cov.load()['learn'][sp].get(move, []))


def egg_chain(sp, move):
    """Shortest breeding chain that hands `move` down to sp's family, e.g.
    ['GYARADOS', 'CHARMANDER', 'LARVITAR'] (father → … → hatchling), or None."""
    D = cov.load()
    if 'Egg move' not in D['learn'][sp].get(move, []):
        return None
    root, members = _family(sp)
    fams = {}
    for s in D['species']:
        r, m = _family(s)
        fams.setdefault(r, m)
    # BFS outwards from the target family over fathers that share an egg group.
    start = root
    prev = {start: None}
    queue = deque([start])
    while queue:
        fam = queue.popleft()
        groups = _egg_groups(fams[fam])
        if not groups:
            continue
        for other_root, other in fams.items():
            if other_root in prev or not (groups & _egg_groups(other)) or other_root == 'DITTO':
                continue
            fathers = [m for m in sorted(other) if D['species'][m]['can_be_male'] and D['species'][m]['egg_groups']]
            if not fathers:
                continue
            direct = [m for m in fathers if _knows_directly(m, move)]
            if direct:
                chain = [direct[0], fam]
                f = prev[fam]
                while f is not None:
                    chain.append(f)
                    f = prev[f]
                return chain
            if any('Egg move' in D['learn'][m].get(move, []) for m in other):
                prev[other_root] = fam
                queue.append(other_root)
    return None


# ---------------------------------------------------------------------------
# Teams — hand-picked, validated against the game data at build time.
# m(species, ability, item, nature, [moves], note)
# ---------------------------------------------------------------------------

def m(sp, ability, item, nature, moves, note):
    return dict(sp=sp, ability=ability, item=item, nature=nature, moves=moves, note=note)


TEAMS = [
    dict(id='eq-core', name='Earthquake Core', tag='Goodstuffs · Smogon’s Metagross + Gengar lead',
         blurb='The most common lead in ADV doubles: <b>Metagross</b> and <b>Gengar</b>. Everyone is built around one rule: '
               'Earthquake hits both foes at full power <i>and</i> your partner, so every Earthquake user should stand next to '
               'a Levitate or Flying-type ally. Gengar, Salamence, Flygon and Zapdos are all immune.',
         leads=[('METAGROSS', 'GENGAR'), ('SWAMPERT', 'SALAMENCE')],
         members=[
            m('METAGROSS', 'CLEAR_BODY', 'LEFTOVERS', 'Adamant', ['METEOR_MASH', 'EARTHQUAKE', 'ROCK_SLIDE', 'PROTECT'],
              'Clear Body ignores Intimidate. Earthquake whenever Gengar or Salamence is beside it.'),
            m('GENGAR', 'LEVITATE', 'LEFTOVERS', 'Timid', ['THUNDERBOLT', 'ICE_PUNCH', 'WILL_O_WISP', 'PROTECT'],
              'Immune to Earthquake, Normal and Fighting. Will-O-Wisp cripples physical attackers, and Ice Punch uses Gengar’s Sp. Atk (Ice is special in Gen 3).'),
            m('SALAMENCE', 'INTIMIDATE', 'LEFTOVERS', 'Naive', ['DRAGON_CLAW', 'ROCK_SLIDE', 'FIRE_BLAST', 'PROTECT'],
              'Intimidate lowers both foes’ Attack on entry. Rock Slide hits both foes (at half power) and can make them flinch.'),
            m('SWAMPERT', 'TORRENT', 'LEFTOVERS', 'Relaxed', ['SURF', 'EARTHQUAKE', 'ICE_BEAM', 'PROTECT'],
              'Surf hits only the two foes, never your ally. Its only weakness is Grass.'),
            m('FLYGON', 'LEVITATE', 'SOFT_SAND', 'Naive', ['EARTHQUAKE', 'ROCK_SLIDE', 'FIRE_BLAST', 'PROTECT'],
              'Levitate, so it can sit beside another Earthquake user. Fire Blast handles Skarmory and Metagross.'),
            m('ZAPDOS', 'PRESSURE', 'LEFTOVERS', 'Mild', ['THUNDERBOLT', 'DRILL_PECK', 'LIGHT_SCREEN', 'PROTECT'],
              'The only Pokémon in the top tier of Smogon’s ADV Doubles viability rankings. Flying, so Earthquake can’t touch it. Post-game; before that, Salamence takes this role.'),
         ]),
    dict(id='pre-e4', name='Before the Elite Four', tag='Main game · no post-game Pokémon or tutors', pre_e4=True,
         blurb='Every Pokémon here can be caught before the Elite Four (or evolves from one that can), and every move comes from level-up, a TM sold in Lilycove, '
               'a main-game tutor or the Move Relearner, never the post-game Battle Frontier tutors. It is the Earthquake Core rebuilt for the Hoenn rematches: '
               'two Earthquake users, each with an immune partner (<b>Salamence</b> is Flying, <b>Weezing</b> has Levitate).',
         leads=[('METAGROSS', 'SALAMENCE'), ('SWAMPERT', 'WEEZING')],
         members=[
            m('METAGROSS', 'CLEAR_BODY', 'LEFTOVERS', 'Adamant', ['METEOR_MASH', 'EARTHQUAKE', 'BRICK_BREAK', 'PROTECT'],
              'Catch Beldum in Steven’s room in Granite Cave. Clear Body ignores Intimidate. Brick Break hits Tyranitar, Aggron and enemy screens; Rock Slide would need the post-game tutor.'),
            m('SALAMENCE', 'INTIMIDATE', 'LEFTOVERS', 'Naive', ['DRAGON_CLAW', 'FIRE_BLAST', 'AERIAL_ACE', 'PROTECT'],
              'Bagon lives deep in Meteor Falls. Intimidate lowers both foes’ Attack on entry, and Flying makes it Metagross’s safe Earthquake partner. Dragon Claw and Fire Blast are special, Aerial Ace physical, so Naive keeps both.'),
            m('SWAMPERT', 'TORRENT', 'LEFTOVERS', 'Relaxed', ['SURF', 'EARTHQUAKE', 'ICE_BEAM', 'PROTECT'],
              'Mudkip is wild on Route 103 in this hack. Surf hits only the two foes. Earthquake next to Weezing or Salamence.'),
            m('WEEZING', 'LEVITATE', 'LEFTOVERS', 'Impish', ['SLUDGE_BOMB', 'WILL_O_WISP', 'EXPLOSION', 'PROTECT'],
              'Koffing is on the Fiery Path. Levitate makes it immune to Earthquake, and Will-O-Wisp (egg move, from the Move Relearner) halves a physical attacker’s damage. Explode when it’s worn down.'),
            m('BRELOOM', 'EFFECT_SPORE', 'LUM_BERRY', 'Jolly', ['SPORE', 'SKY_UPPERCUT', 'MACH_PUNCH', 'PROTECT'],
              'Shroomish is in Petalburg Woods. Spore never misses, and Mach Punch has priority. Keep it away from its partners’ Earthquake.'),
            m('MANECTRIC', 'LIGHTNING_ROD', 'MAGNET', 'Timid', ['THUNDERBOLT', 'OVERHEAT', 'THUNDER_WAVE', 'PROTECT'],
              'Wild on Route 118. Lightning Rod pulls the foes’ single-target Electric moves onto itself, and Electric resists them. Overheat (egg move) burns through Steel and Bug types.'),
         ],
         variants=[
            dict(name='Without pseudo-legendaries',
                 blurb='<b>Beldum</b> and <b>Bagon</b> are pseudo-legendaries: 600 total base stats, a long climb to the final form (Metagross at 45, Salamence at 50) and, in Beldum’s case, a single rare catch. '
                       'Swap them for two Pokémon you can raise from the wild at a normal pace. <b>Flygon</b> takes over as the Levitate partner that lets Swampert use Earthquake, '
                       '<b>Gyarados</b> is Flying so it can use its own Earthquake beside anyone, and <b>Gardevoir</b> replaces the special power the team loses.',
                 members=[
                    m('SWAMPERT', 'TORRENT', 'LEFTOVERS', 'Relaxed', ['SURF', 'EARTHQUAKE', 'ICE_BEAM', 'PROTECT'],
                      'Same set as above. Earthquake only next to Flygon, Gyarados or Weezing.'),
                    m('FLYGON', 'LEVITATE', 'SOFT_SAND', 'Naive', ['EARTHQUAKE', 'DRAGON_CLAW', 'FIRE_BLAST', 'PROTECT'],
                      'Trapinch is wild in the Route 111 desert, and Vibrava evolves at 45. Levitate means it and Swampert can both use Earthquake. Dragon Claw and Fire Blast are special, Earthquake physical, so Naive keeps both.'),
                    m('GYARADOS', 'INTIMIDATE', 'LEFTOVERS', 'Adamant', ['DRAGON_DANCE', 'EARTHQUAKE', 'DOUBLE_EDGE', 'PROTECT'],
                      'A Magikarp from any rod, or catch Gyarados itself in Sootopolis. Intimidate weakens both foes on entry, and Flying keeps it safe from its partners’ Earthquake. Double-Edge comes from the Sootopolis tutor.'),
                    m('GARDEVOIR', 'TRACE', 'LEFTOVERS', 'Modest', ['PSYCHIC', 'THUNDERBOLT', 'CALM_MIND', 'PROTECT'],
                      'Ralts is on Route 102, right at the start. Trace copies a foe’s ability, such as Intimidate or Levitate, and Calm Mind turns it into the team’s special threat.'),
                    m('BRELOOM', 'EFFECT_SPORE', 'LUM_BERRY', 'Jolly', ['SPORE', 'SKY_UPPERCUT', 'MACH_PUNCH', 'PROTECT'],
                      'Unchanged: Spore is the best support move in the game.'),
                    m('MANECTRIC', 'LIGHTNING_ROD', 'MAGNET', 'Timid', ['THUNDERBOLT', 'OVERHEAT', 'THUNDER_WAVE', 'PROTECT'],
                      'Unchanged. With Gardevoir alongside, the team keeps two special attackers.'),
                 ]),
         ]),
    dict(id='rain', name='Rain Dance Offense', tag='Weather · Swift Swim',
         blurb='Kyogre is the only Pokémon with Drizzle, so rain comes from <b>Rain Dance</b> (5 turns). '
               'Swift Swim doubles Speed in rain, rain boosts Water moves by 50%, and <b>Thunder never misses in rain</b>. '
               'Fake Out buys the turn you need to set it up.',
         leads=[('LUDICOLO', 'JOLTEON'), ('HARIYAMA', 'KINGDRA')],
         members=[
            m('LUDICOLO', 'SWIFT_SWIM', 'LEFTOVERS', 'Modest', ['FAKE_OUT', 'RAIN_DANCE', 'SURF', 'ICE_BEAM'],
              'Lead: Fake Out the biggest threat while the partner sets rain, or set it yourself. Water/Grass is only weak to Flying, Poison and Bug.'),
            m('JOLTEON', 'VOLT_ABSORB', 'MAGNET', 'Timid', ['THUNDER', 'RAIN_DANCE', 'HELPING_HAND', 'PROTECT'],
              'An Eevee evolution, so it fits this hack’s starter. In rain, Thunder (120 power) never misses. Volt Absorb heals it when hit by Electric moves, so it can safely switch in against Electric attacks aimed at the Water types.'),
            m('KINGDRA', 'SWIFT_SWIM', 'MYSTIC_WATER', 'Modest', ['SURF', 'HYDRO_PUMP', 'ICE_BEAM', 'PROTECT'],
              'Water/Dragon is only weak to Dragon. In rain it outspeeds almost everything, and rain-boosted Hydro Pump hits very hard.'),
            m('HARIYAMA', 'THICK_FAT', 'LEFTOVERS', 'Adamant', ['FAKE_OUT', ('CROSS_CHOP', 'BRICK_BREAK'), 'ROCK_SLIDE', 'HELPING_HAND'],
              'Smogon’s Kingdra partner: Fake Out plus Helping Hand. Thick Fat halves Fire and Ice damage.'),
            m('LANTURN', 'VOLT_ABSORB', 'LEFTOVERS', 'Modest', ['THUNDER', 'SURF', 'ICE_BEAM', 'PROTECT'],
              'A second reliable Thunder in rain. Only Ground and Grass hit it for super-effective damage.'),
            m('OMASTAR', 'SWIFT_SWIM', 'MYSTIC_WATER', 'Modest', ['SURF', 'HYDRO_PUMP', 'ICE_BEAM', 'PROTECT'],
              'Another Swift Swim special attacker, with 115 Sp. Atk. Rock typing resists Flying, which Ludicolo and Kingdra don’t.'),
         ]),
    dict(id='sun', name='Sunny Day Offense', tag='Weather · Chlorophyll',
         blurb='<b>Sunny Day</b> doubles Chlorophyll users’ Speed, lets <b>Solar Beam</b> fire in one turn, and boosts Fire moves by 50%. '
               'Sun weakens Water moves, the Fire types’ usual problem. Smogon’s sun sweeper is Chlorophyll Exeggutor with Sleep Powder.',
         leads=[('NINETALES', 'EXEGGUTOR'), ('SHIFTRY', 'ARCANINE')],
         members=[
            m('NINETALES', 'FLASH_FIRE', 'CHARCOAL', 'Timid', ['SUNNY_DAY', 'HEAT_WAVE', 'WILL_O_WISP', 'PROTECT'],
              'Sets the sun and immediately fires sun-boosted Heat Wave into both foes. Flash Fire makes it immune to Fire.'),
            m('EXEGGUTOR', 'CHLOROPHYLL', 'LEFTOVERS', 'Modest', ['SLEEP_POWDER', 'SOLAR_BEAM', 'PSYCHIC', 'PROTECT'],
              'Smogon’s sun sweeper. Sleep Powder first, then one-turn Solar Beams.'),
            m('SHIFTRY', 'CHLOROPHYLL', 'LEFTOVERS', 'Mild', ['FAKE_OUT', 'SUNNY_DAY', 'SOLAR_BEAM', 'EXTRASENSORY'],
              'Fake Out plus its own Sunny Day. It learns Fake Out by level-up in this hack.'),
            m('ARCANINE', 'INTIMIDATE', 'CHARCOAL', 'Mild', ['HEAT_WAVE', 'EXTREME_SPEED', 'HELPING_HAND', 'PROTECT'],
              'Intimidate plus Helping Hand support. Extreme Speed picks off weakened foes before they move.'),
            m('CHARIZARD', 'BLAZE', 'LEFTOVERS', 'Modest', [('HEAT_WAVE', 'FLAMETHROWER'), 'DRAGON_CLAW', 'SUNNY_DAY', 'PROTECT'],
              'A second sun setter and Heat Wave user. Flying type, so it pairs with Metagross’s Earthquake.'),
            m('METAGROSS', 'CLEAR_BODY', 'LEFTOVERS', 'Adamant', ['METEOR_MASH', 'EARTHQUAKE', 'ROCK_SLIDE', 'PROTECT'],
              'Handles the Rock and Dragon types the Fire and Grass Pokémon struggle with. Only use Earthquake next to Charizard.'),
         ]),
    dict(id='sand', name='Sandstorm', tag='Weather · Tyranitar',
         blurb='<b>Sand Stream</b> sets a sandstorm that doesn’t wear off in Gen 3; only another weather replaces it. Every teammate is Rock, Ground or Steel, '
               'so no one takes sand damage. Most of them are also Flying or have Levitate, so Tyranitar and Flygon can use Earthquake freely.',
         leads=[('TYRANITAR', 'FLYGON'), ('AERODACTYL', 'CLAYDOL')],
         members=[
            m('TYRANITAR', 'SAND_STREAM', 'LEFTOVERS', 'Adamant', ['DRAGON_DANCE', 'ROCK_SLIDE', 'EARTHQUAKE', 'CRUNCH'],
              'Smogon’s Tyranitar setup sweeper: one Dragon Dance, then Rock Slide and Earthquake. This hack makes Dark physical, so Adamant powers Crunch too.'),
            m('FLYGON', 'LEVITATE', 'LEFTOVERS', 'Naive', ['EARTHQUAKE', 'ROCK_SLIDE', 'DRAGON_CLAW', 'PROTECT'],
              'Immune to both sandstorm damage and Earthquake, making it the ideal partner for Tyranitar.'),
            m('AERODACTYL', 'ROCK_HEAD', 'LEFTOVERS', 'Jolly', ['ROCK_SLIDE', 'EARTHQUAKE', 'AERIAL_ACE', 'PROTECT'],
              'Very fast Rock Slide flinches. Flying type, so partner Earthquakes can’t hit it.'),
            m('CLAYDOL', 'LEVITATE', 'LEFTOVERS', 'Quiet', ['PSYCHIC', 'ICE_BEAM', 'EARTHQUAKE', 'PROTECT'],
              'A bulky Levitate Pokémon with Ice Beam for opposing Flygon and Salamence.'),
            m('SKARMORY', 'STURDY', 'LEFTOVERS', 'Impish', ['DRILL_PECK', 'STEEL_WING', 'TAUNT', 'PROTECT'],
              'Taunt stops enemy Rain Dance, Sunny Day and Follow Me. Steel/Flying is immune to sand and Earthquake.'),
            m('SANDSLASH', 'SAND_VEIL', 'QUICK_CLAW', 'Adamant', ['EARTHQUAKE', 'ROCK_SLIDE', 'SWORDS_DANCE', 'PROTECT'],
              'Sand Veil raises its evasion in sandstorm. Only use Earthquake next to the Flying or Levitate teammates.'),
         ]),
    dict(id='redirect', name='Follow Me & Setup', tag='Support · Fake Out · Dragon Dance',
         blurb='One Pokémon <b>draws the attacks</b> while the other boosts. Follow Me redirects every single-target move from the foes '
               'for the turn (not spread moves like Rock Slide or Surf), Fake Out makes a foe flinch on its first turn, and Intimidate weakens '
               'both foes. Once a Dragon Dance user has a boost or two, it takes over.',
         leads=[('TOGETIC', 'GYARADOS'), ('HITMONTOP', 'DRAGONITE')],
         members=[
            m('TOGETIC', 'SERENE_GRACE', 'LEFTOVERS', 'Bold', ['FOLLOW_ME', 'HELPING_HAND', 'ENCORE', 'PROTECT'],
              'Follow Me every turn a sweeper boosts. Encore locks a foe into Protect or a stat move.'),
            m('GYARADOS', 'INTIMIDATE', 'LEFTOVERS', 'Adamant', ['DRAGON_DANCE', 'EARTHQUAKE', 'DOUBLE_EDGE', 'PROTECT'],
              'Intimidate on entry, then Dragon Dance behind Follow Me. Its own Earthquake still hits a grounded partner such as Togetic.'),
            m('HITMONTOP', 'INTIMIDATE', 'LEFTOVERS', 'Adamant', ['FAKE_OUT', 'HELPING_HAND', 'BRICK_BREAK', 'ROCK_SLIDE'],
              'A second Intimidate plus Fake Out. Brick Break removes Reflect and Light Screen.'),
            m('DRAGONITE', 'INNER_FOCUS', 'LEFTOVERS', 'Adamant', ['DRAGON_DANCE', 'EARTHQUAKE', 'EXTREME_SPEED', 'PROTECT'],
              'Inner Focus means Fake Out can’t make it flinch. After a Dragon Dance, Extreme Speed and Earthquake finish off foes. Flying, like Gyarados, so the two can share the field.'),
            m('BRELOOM', 'EFFECT_SPORE', 'LUM_BERRY', 'Jolly', ['SPORE', 'SKY_UPPERCUT', 'MACH_PUNCH', 'PROTECT'],
              'Spore is 100% accurate, and a sleeping foe can’t attack your sweeper. Mach Punch has priority.'),
            m('STARMIE', 'NATURAL_CURE', 'LEFTOVERS', 'Timid', ['SURF', 'THUNDERBOLT', 'ICE_BEAM', 'PROTECT'],
              'Fast special coverage for what the physical sweepers can’t break. Surf never hits your partner.'),
         ]),
    dict(id='eon', name='Espeon & Umbreon', tag='Core · Sun and Moon',
         blurb='This version’s starters, and Pokémon Colosseum’s. The two cover each other: <b>Umbreon</b> is immune to Psychic and resists Ghost and Dark, '
               'which are Espeon’s weaknesses, and <b>Espeon</b> resists Fighting, which is Umbreon’s. <b>Bug</b> is their one shared weakness, and '
               'Espeon’s screens are the answer to spread attacks. The rest of the team brings Fire, Steel and Rock resistances to cover Bug, and no one uses Earthquake, '
               'because both Eeveelutions are grounded.',
         leads=[('ESPEON', 'UMBREON'), ('METAGROSS', 'ARCANINE')],
         members=[
            m('ESPEON', 'SYNCHRONIZE', 'LEFTOVERS', 'Timid', ['PSYCHIC', 'SHADOW_BALL', 'REFLECT', 'LIGHT_SCREEN'],
              'Screens first. In doubles, Reflect and Light Screen cut damage to ⅔ while both allies stand, including spread moves. '
              'Shadow Ball hits opposing Psychic and Ghost types, and this hack makes Ghost special, so it uses Espeon’s Sp. Atk (TM30).'),
            m('UMBREON', 'SYNCHRONIZE', 'LEFTOVERS', 'Bold', ['WISH', 'HELPING_HAND', 'TAUNT', 'PROTECT'],
              'The wall. Wish heals whoever stands in its slot next turn, Helping Hand powers up Espeon’s Psychic, and Taunt stops enemy screens, weather and Follow Me. '
              'Synchronize passes burn, poison and paralysis back to the attacker.'),
            m('METAGROSS', 'CLEAR_BODY', 'LEFTOVERS', 'Adamant', ['METEOR_MASH', 'ROCK_SLIDE', 'BRICK_BREAK', 'PROTECT'],
              'Steel resists Bug, Psychic and Rock. No Earthquake here, since it would hit both Eeveelutions. Brick Break breaks enemy screens and hits Tyranitar.'),
            m('ARCANINE', 'INTIMIDATE', 'CHARCOAL', 'Mild', ['HEAT_WAVE', 'EXTREME_SPEED', ('CRUNCH', 'HELPING_HAND'), 'PROTECT'],
              'Intimidate on entry, and Heat Wave burns through the Bug types that threaten the core. Flash Fire makes it immune to Fire.'),
            m('SWAMPERT', 'TORRENT', 'LEFTOVERS', 'Relaxed', ['SURF', 'ICE_BEAM', 'ROCK_SLIDE', 'PROTECT'],
              'Surf and Rock Slide both miss your own side, and Rock Slide hits Bug and Flying foes. Water/Ground covers Arcanine’s and Metagross’s weaknesses.'),
            m('JOLTEON', 'VOLT_ABSORB', 'MAGNET', 'Timid', ['THUNDERBOLT', 'THUNDER_WAVE', 'HELPING_HAND', 'PROTECT'],
              'A third Eeveelution. Thunder Wave slows the fast sweepers Espeon and Umbreon can’t outspeed, and Thunderbolt handles the Water and Flying types that trouble Arcanine and Metagross.'),
         ],
         variants=[
            dict(name='Johto partners', region=('Johto', 152, 251),
                 blurb='Both Eeveelutions are Johto Pokémon, so swapping the other four for <b>Johto</b> ones (National Dex 152–251) makes the whole team one region. '
                       'Typhlosion and Skarmory take over the Bug duty, and Ampharos adds a second Light Screen behind Espeon’s.',
                 members=[
                    m('TYPHLOSION', 'BLAZE', 'CHARCOAL', 'Modest', ['HEAT_WAVE', 'THUNDER_PUNCH', 'SUNNY_DAY', 'PROTECT'],
                      'The Bug answer. It learns Heat Wave by level-up here, so no breeding is needed, and Sunny Day boosts it by another 50%. Thunder Punch is special in Gen 3 and covers Water and Flying types.'),
                    m('SKARMORY', 'STURDY', 'LEFTOVERS', 'Impish', ['DRILL_PECK', 'STEEL_WING', 'TAUNT', 'PROTECT'],
                      'Steel resists Bug, Ghost, Dark, Psychic and Normal, which covers both Eeveelutions. Taunt stops enemy screens, weather and Follow Me.'),
                    m('KINGDRA', 'SWIFT_SWIM', 'MYSTIC_WATER', 'Modest', ['SURF', 'HYDRO_PUMP', 'ICE_BEAM', 'PROTECT'],
                      'Water/Dragon is only weak to Dragon, and Surf hits both foes but never your partner. With no rain here, Swift Swim is idle; it is Kingdra’s only ability in this hack.'),
                    m('AMPHAROS', 'STATIC', 'LEFTOVERS', 'Modest', ['THUNDERBOLT', 'THUNDER_WAVE', 'LIGHT_SCREEN', 'PROTECT'],
                      'Electric coverage for Water and Flying types, a second Light Screen, and Thunder Wave to slow faster threats.'),
                 ]),
            dict(name='Hoenn partners', region=('Hoenn', 252, 386),
                 blurb='The same core with four <b>Hoenn</b> partners (National Dex 252–386); Espeon and Umbreon stay as the Johto exception. '
                       'Metagross and Salamence cover the Bug weakness, and Blaziken adds the Fighting moves that beat the Dark and Steel types walling Espeon.',
                 members=[
                    m('METAGROSS', 'CLEAR_BODY', 'LEFTOVERS', 'Adamant', ['METEOR_MASH', 'ROCK_SLIDE', 'BRICK_BREAK', 'PROTECT'],
                      'Steel resists Bug and Psychic. No Earthquake, since it would hit both Eeveelutions; Rock Slide hits both foes instead.'),
                    m('BLAZIKEN', 'BLAZE', 'CHARCOAL', 'Naive', ['SKY_UPPERCUT', 'ROCK_SLIDE', 'FIRE_BLAST', 'PROTECT'],
                      'Fire for the Bug types, Fighting for the Dark and Steel types. Sky Uppercut is physical and Fire Blast special, so a Naive nature keeps both.'),
                    m('SWAMPERT', 'TORRENT', 'LEFTOVERS', 'Relaxed', ['SURF', 'ICE_BEAM', 'ROCK_SLIDE', 'PROTECT'],
                      'Bulky Water: resists Fire and Steel, immune to Electric. Surf and Rock Slide hit both foes but never your own side.'),
                    m('SALAMENCE', 'INTIMIDATE', 'LEFTOVERS', 'Naive', ['DRAGON_CLAW', 'ROCK_SLIDE', 'FIRE_BLAST', 'PROTECT'],
                      'Intimidate weakens both foes on entry, and its Rock Slide and Fire Blast both answer Bug types.'),
                 ]),
         ]),
    dict(id='colosseum', name='Colosseum Core', tag='Pokémon Colosseum roster · Smogon ADV Doubles picks',
         blurb='The strongest doubles team you could build in <b>Pokémon Colosseum</b> (GameCube), where every battle is a double battle. '
               'It uses only Pokémon that game gives you: Shadow Pokémon you snag and purify, plus their evolutions. '
               'The picks follow Smogon’s ADV Doubles rankings: Raikou, Suicune and Metagross sit in tier 2, and Heracross and Flygon in tier 4. '
               '<b>Why no Tyranitar?</b> Evice’s Tyranitar is the obvious pick, but Sand Stream would hurt Raikou, Suicune, Hitmontop and Heracross every turn. '
               'Espeon and Umbreon, Colosseum’s starters, have their own team.',
         leads=[('HITMONTOP', 'RAIKOU'), ('METAGROSS', 'FLYGON')],
         members=[
            m('METAGROSS', 'CLEAR_BODY', 'LEFTOVERS', 'Adamant', ['METEOR_MASH', 'EARTHQUAKE', 'ROCK_SLIDE', 'PROTECT'],
              'Cipher Nascour’s Shadow Metagross. Only use Earthquake when Flygon is its partner, because everyone else on the team is grounded.'),
            m('RAIKOU', 'PRESSURE', 'MAGNET', 'Timid', ['THUNDERBOLT', 'SHADOW_BALL', 'CALM_MIND', 'PROTECT'],
              'Cipher Admin Ein’s Shadow Raikou. Very fast Thunderbolts hit the Water and Flying types, and Shadow Ball (special in this hack, boosted by Calm Mind) hits Psychic and Ghost types.'),
            m('SUICUNE', 'PRESSURE', 'LEFTOVERS', 'Bold', ['SURF', 'ICE_BEAM', 'CALM_MIND', 'PROTECT'],
              'Cipher Admin Venus’s Shadow Suicune. Bulky and boosts itself with Calm Mind. Surf hits both foes and never its partner. Ice Beam handles Dragon and Flying types.'),
            m('FLYGON', 'LEVITATE', 'SOFT_SAND', 'Naive', ['EARTHQUAKE', 'ROCK_SLIDE', 'DRAGON_CLAW', 'FIRE_BLAST'],
              'Evolved from Cipher Peon Remil’s Shadow Vibrava. Levitate makes it the only team member Earthquake can’t hit, so it’s Metagross’s partner. Fire Blast handles Steel types.'),
            m('HITMONTOP', 'INTIMIDATE', 'LEFTOVERS', 'Adamant', ['FAKE_OUT', 'HELPING_HAND', 'BRICK_BREAK', 'ROCK_SLIDE'],
              'Cipher Peon Skrub’s Shadow Hitmontop. Intimidate plus Fake Out on turn one lets Raikou or Suicune set up Calm Mind.'),
            m('HERACROSS', 'GUTS', 'LEFTOVERS', 'Adamant', ['MEGAHORN', 'ROCK_SLIDE', 'BRICK_BREAK', 'PROTECT'],
              'Cipher Peon Dioge’s Shadow Heracross. Megahorn hits Psychic and Dark types, Brick Break hits Tyranitar and Steel types, and Guts turns a status condition into ×1.5 Attack.'),
         ]),
    dict(id='hail', name='Hail', tag='Weather · Blizzard never misses',
         blurb='<b>Hail</b> lasts 5 turns and hurts every non-Ice Pokémon for 1/16 of its HP at the end of each turn. While it’s up, '
               '<b>Blizzard never misses</b> (120 power, hits both foes at half damage). Two Hail setters keep it running, and the Water/Ice types '
               'take away Ice’s Fire and Steel weaknesses. Metagross, the only non-Ice member, resists the Rock and Steel moves Ice types fear and holds Leftovers against the chip damage.',
         leads=[('WALREIN', 'GLALIE'), ('DEWGONG', 'REGICE')],
         members=[
            m('WALREIN', 'THICK_FAT', 'LEFTOVERS', 'Modest', ['HAIL', 'BLIZZARD', 'SURF', 'PROTECT'],
              'The main Hail setter. Water/Ice already takes neutral damage from Fire, and Thick Fat halves Fire and Ice damage on top of that.'),
            m('GLALIE', 'LEVITATE', 'NEVER_MELT_ICE', 'Modest', ['HAIL', 'BLIZZARD', 'SHADOW_BALL', 'PROTECT'],
              'Second setter. In this hack Glalie can have Levitate, which makes it immune to Ground moves, a partner’s Earthquake included. Ghost is special in this hack, so Modest powers Shadow Ball too.'),
            m('REGICE', 'CLEAR_BODY', 'LEFTOVERS', 'Modest', ['BLIZZARD', 'THUNDERBOLT', 'THUNDER_WAVE', 'PROTECT'],
              'Post-game. Base 200 Sp. Def. Thunderbolt hits the Water types that resist Blizzard, and Thunder Wave slows the fast threats.'),
            m('LAPRAS', 'WATER_ABSORB', 'LEFTOVERS', 'Modest', ['BLIZZARD', 'THUNDERBOLT', 'HAIL', 'PROTECT'],
              'A bulky third Hail user. Water Absorb makes it immune to Water.'),
            m('DEWGONG', 'THICK_FAT', 'LEFTOVERS', 'Calm', ['FAKE_OUT', 'ENCORE', 'BLIZZARD', 'PROTECT'],
              'Smogon’s Dewgong set: Fake Out to buy a turn for Hail, then Encore to lock foes into a wasted move.'),
            m('METAGROSS', 'CLEAR_BODY', 'LEFTOVERS', 'Adamant', ['METEOR_MASH', 'ROCK_SLIDE', 'BRICK_BREAK', 'PROTECT'],
              'Handles the Rock and Steel types that threaten Ice teams: Brick Break for Steel and Rock, Meteor Mash for Rock. It takes hail damage, so Leftovers is essential.'),
         ]),
    dict(id='balance', name='Balanced Core', tag='Fire · Water · Grass · Intimidate · Explosion',
         blurb='Built like Smogon’s “FWG” sample team: a <b>Fire, Water and Grass</b> trio that covers each other’s weaknesses, two <b>Intimidate</b> users to soften '
               'physical attackers, one <b>Explosion</b> for emergencies, and a Flying type so Earthquake can be used freely. No weather and no gimmick, so it works against anything.',
         leads=[('TAUROS', 'AERODACTYL'), ('ARCANINE', 'SWAMPERT')],
         members=[
            m('TAUROS', 'INTIMIDATE', 'LEFTOVERS', 'Jolly', ['RETURN', 'EARTHQUAKE', 'IRON_TAIL', 'PROTECT'],
              'Fast Intimidate lead. Use Earthquake when Aerodactyl is the partner. Iron Tail hits Rock types.'),
            m('SWAMPERT', 'TORRENT', 'LEFTOVERS', 'Relaxed', ['SURF', 'EARTHQUAKE', 'ICE_BEAM', 'PROTECT'],
              'The Water third of the core: resists Fire and Steel, immune to Electric. Surf never hits the partner.'),
            m('ARCANINE', 'INTIMIDATE', 'CHARCOAL', 'Mild', ['HEAT_WAVE', 'EXTREME_SPEED', 'HELPING_HAND', 'PROTECT'],
              'The Fire third: resists Grass, Bug, Steel and Ice. The second Intimidate lets you switch it in to weaken foes again.'),
            m('VENUSAUR', 'OVERGROW', 'LEFTOVERS', 'Modest', ['SLEEP_POWDER', 'GIGA_DRAIN', 'LEECH_SEED', 'PROTECT'],
              'The Grass third: resists Water, Electric, Grass and Fighting. Sleep Powder shuts down the biggest threat.'),
            m('METAGROSS', 'CLEAR_BODY', 'LEFTOVERS', 'Adamant', ['METEOR_MASH', 'EARTHQUAKE', 'EXPLOSION', 'PROTECT'],
              'The Explosion user. Explosion hits your partner too, so have the partner Protect that turn.'),
            m('AERODACTYL', 'ROCK_HEAD', 'LEFTOVERS', 'Jolly', ['ROCK_SLIDE', 'AERIAL_ACE', 'TAUNT', 'PROTECT'],
              'Flying, so Tauros, Swampert and Metagross can Earthquake next to it. Taunt stops setup and support moves.'),
         ]),
    dict(id='intimidate', name='Intimidate Cycling', tag='Four Intimidate users · switch to reuse',
         blurb='<b>Intimidate</b> lowers both foes’ Attack by one stage every time the Pokémon enters the battle, so switching an Intimidate user out and back in stacks the drop. '
               'Four of them here make physical attackers useless, and <b>Starmie</b> adds special damage that the foes’ own Intimidate can’t touch. '
               'Clear Body (Metagross), Hyper Cutter and White Smoke block it.',
         leads=[('HITMONTOP', 'SALAMENCE'), ('ARCANINE', 'STARMIE')],
         members=[
            m('SALAMENCE', 'INTIMIDATE', 'LEFTOVERS', 'Naive', ['DRAGON_CLAW', 'ROCK_SLIDE', 'FIRE_BLAST', 'PROTECT'],
              'Flying, so Gyarados’s Earthquake can’t hit it. Rock Slide hits both foes and can make them flinch.'),
            m('GYARADOS', 'INTIMIDATE', 'LEFTOVERS', 'Adamant', ['DRAGON_DANCE', 'EARTHQUAKE', 'DOUBLE_EDGE', 'PROTECT'],
              'The win condition: Dragon Dance behind the Attack drops. Earthquake only next to Salamence, the other Flying type.'),
            m('HITMONTOP', 'INTIMIDATE', 'LEFTOVERS', 'Adamant', ['FAKE_OUT', 'HELPING_HAND', 'BRICK_BREAK', 'ROCK_SLIDE'],
              'Intimidate plus Fake Out on the same turn it enters: the best lead in the game for buying a free turn.'),
            m('ARCANINE', 'INTIMIDATE', 'CHARCOAL', 'Mild', ['HEAT_WAVE', 'EXTREME_SPEED', 'HELPING_HAND', 'PROTECT'],
              'Heat Wave hits both foes and is special, so its own team’s Attack drops don’t matter. Extreme Speed finishes weakened foes first.'),
            m('MIGHTYENA', 'INTIMIDATE', 'LEFTOVERS', 'Adamant', ['CRUNCH', 'SUPER_FANG', 'TAUNT', 'PROTECT'],
              'The fourth Intimidate. Crunch is physical in this hack, Super Fang halves any foe’s HP, and Taunt stops enemy screens and setup.'),
            m('STARMIE', 'NATURAL_CURE', 'LEFTOVERS', 'Timid', ['SURF', 'THUNDERBOLT', 'ICE_BEAM', 'PROTECT'],
              'Special attacks, so opposing Intimidate doesn’t weaken it. Natural Cure clears its status when it switches, which fits a team that switches a lot.'),
         ]),
    dict(id='boom', name='Explosion Core', tag='Self-KO · Ghost partners',
         blurb='<b>Explosion</b> (250 power) hits both foes <i>and</i> your partner at full power, and halves the targets’ Defense. Ghost types are immune, so every '
               'Explosion user here has a <b>Ghost</b> or <b>Protect</b> partner. Trade one Pokémon for big damage to both foes, then send in a fresh one. '
               'Watch out for foes with <b>Damp</b> (Golduck, Politoed, Quagsire), which blocks Explosion entirely.',
         leads=[('GOLEM', 'GENGAR'), ('METAGROSS', 'DUSCLOPS')],
         members=[
            m('METAGROSS', 'CLEAR_BODY', 'LEFTOVERS', 'Adamant', ['METEOR_MASH', 'EARTHQUAKE', 'EXPLOSION', 'PROTECT'],
              'Bulky enough to deal damage before exploding. Earthquake only next to Gengar or Weezing (both Levitate).'),
            m('GOLEM', 'STURDY', 'SOFT_SAND', 'Adamant', ['EXPLOSION', 'EARTHQUAKE', 'ROCK_SLIDE', 'PROTECT'],
              'Sturdy blocks one-hit KO moves. Explode when it’s about to faint anyway.'),
            m('ELECTRODE', 'SOUNDPROOF', 'MAGNET', 'Timid', ['THUNDERBOLT', 'THUNDER_WAVE', 'EXPLOSION', 'PROTECT'],
              'The fastest exploder, so it goes before the foes move. Thunder Wave first, then Explosion.'),
            m('GENGAR', 'LEVITATE', 'LEFTOVERS', 'Timid', ['THUNDERBOLT', 'ICE_PUNCH', 'EXPLOSION', 'PROTECT'],
              'Immune to its partners’ Explosion (Ghost) and Earthquake (Levitate), and can explode itself.'),
            m('DUSCLOPS', 'PRESSURE', 'LEFTOVERS', 'Impish', ['WILL_O_WISP', 'HELPING_HAND', 'PAIN_SPLIT', 'PROTECT'],
              'The Ghost partner. Helping Hand plus a partner’s Explosion is ×1.5 on top. It’s immune to Explosion, Normal and Fighting moves.'),
            m('WEEZING', 'LEVITATE', 'LEFTOVERS', 'Impish', ['EXPLOSION', 'SLUDGE_BOMB', 'WILL_O_WISP', 'PROTECT'],
              'Levitate, so Earthquake can’t hit it. Burn physical attackers first, then explode.'),
         ]),
    dict(id='status', name='Sleep & Status', tag='Spore · Sleep Powder · Will-O-Wisp · Confusion',
         blurb='A foe that’s <b>asleep</b>, <b>burned</b>, <b>paralyzed</b> or <b>confused</b> barely threatens you, and in doubles there are two to disable. This game has no Sleep Clause, '
               'so you can put both foes to sleep. Grass types aren’t immune to spore moves in Gen 3.',
         leads=[('BRELOOM', 'GARDEVOIR'), ('JUMPLUFF', 'HOUNDOOM')],
         members=[
            m('BRELOOM', 'EFFECT_SPORE', 'LUM_BERRY', 'Jolly', ['SPORE', 'SKY_UPPERCUT', 'MACH_PUNCH', 'PROTECT'],
              'Spore is 100% accurate sleep. Effect Spore can inflict a status on physical attackers that hit it.'),
            m('JUMPLUFF', 'CHLOROPHYLL', 'LEFTOVERS', 'Jolly', ['SLEEP_POWDER', 'LEECH_SEED', 'ENCORE', 'PROTECT'],
              'Very fast Sleep Powder, and Encore locks a foe into its last move. Leech Seed drains HP every turn.'),
            m('GARDEVOIR', 'TRACE', 'LEFTOVERS', 'Modest', ['HYPNOSIS', 'WILL_O_WISP', 'PSYCHIC', 'PROTECT'],
              'Hypnosis and Will-O-Wisp. Trace copies a foe’s ability, such as Intimidate or Levitate.'),
            m('HOUNDOOM', 'FLASH_FIRE', 'LEFTOVERS', 'Hasty', ['WILL_O_WISP', ('HEAT_WAVE', 'FLAMETHROWER'), 'CRUNCH', 'PROTECT'],
              'Burn halves a physical attacker’s damage. Heat Wave can also burn both foes.'),
            m('CROBAT', 'INNER_FOCUS', 'LEFTOVERS', 'Jolly', ['CONFUSE_RAY', 'TAUNT', 'AERIAL_ACE', 'PROTECT'],
              'One of the fastest Pokémon in the game. Confuse Ray and Taunt go before most foes move, and Inner Focus stops Fake Out’s flinch.'),
            m('VILEPLUME', 'CHLOROPHYLL', 'LEFTOVERS', 'Modest', ['STUN_SPORE', 'SLEEP_POWDER', 'GIGA_DRAIN', 'AROMATHERAPY'],
              'Stun Spore paralyzes, Sleep Powder puts foes to sleep, and Aromatherapy cures your whole team if foes status you back.'),
         ]),
    dict(id='trap', name='Trapping & Perish Song', tag='Shadow Tag · Arena Trap · Perish Song',
         blurb='<b>Perish Song</b> gives every Pokémon on the field (yours included) 3 turns before it faints, unless it has <b>Soundproof</b>. '
               'Switching out resets the count, and trapped foes can’t switch. <b>Shadow Tag</b> traps every foe, <b>Arena Trap</b> traps every foe except Flying types and Levitate users, '
               'and <b>Mean Look</b> traps one. Trap them, sing, <b>Protect</b> and switch out before the count ends. Your side is never trapped by your own abilities.',
         leads=[('WOBBUFFET', 'LAPRAS'), ('DUGTRIO', 'MISDREAVUS')],
         members=[
            m('WOBBUFFET', 'SHADOW_TAG', 'LEFTOVERS', 'Bold', ['COUNTER', 'MIRROR_COAT', 'ENCORE', 'DESTINY_BOND'],
              'Traps both foes as soon as it’s out. Counter and Mirror Coat return double the damage, and Encore locks foes into a useless move.'),
            m('DUGTRIO', 'ARENA_TRAP', 'SOFT_SAND', 'Jolly', ['EARTHQUAKE', 'ROCK_SLIDE', 'AERIAL_ACE', 'PROTECT'],
              'Traps grounded foes. Earthquake hits your partner unless it’s Misdreavus (Levitate) or Crobat (Flying).'),
            m('LAPRAS', 'WATER_ABSORB', 'LEFTOVERS', 'Calm', ['PERISH_SONG', 'SURF', 'ICE_BEAM', 'PROTECT'],
              'Bulky Perish Song user. After singing, Protect or switch out before the count reaches 0.'),
            m('MISDREAVUS', 'LEVITATE', 'LEFTOVERS', 'Bold', ['PERISH_SONG', 'MEAN_LOOK', 'THUNDERBOLT', 'PROTECT'],
              'Mean Look plus Perish Song on its own. Levitate means Dugtrio’s Earthquake can’t hit it.'),
            m('POLITOED', 'DAMP', 'LEFTOVERS', 'Bold', ['PERISH_SONG', 'SURF', 'HYPNOSIS', 'PROTECT'],
              'A third Perish Song user. Damp blocks Explosion, which trapped foes might use as a last resort.'),
            m('CROBAT', 'INNER_FOCUS', 'LEFTOVERS', 'Jolly', ['MEAN_LOOK', 'TAUNT', 'AERIAL_ACE', 'PROTECT'],
              'Fast Mean Look before a Perish Song, and Taunt stops foes from using Protect to stall the count.'),
         ]),
    dict(id='kyogre-rain', name='Kyogre Rain', tag='Post-game · Drizzle · Swift Swim',
         blurb='<b>Drizzle</b> starts rain the moment Kyogre enters, and ability weather in Gen 3 lasts until another weather replaces it, so no one spends a turn on Rain Dance. '
               'Rain boosts Water moves by 50%, halves Fire moves, doubles Swift Swim users’ Speed, and makes <b>Thunder</b> never miss. '
               'Don’t put <b>Groudon</b> (Drought replaces the rain) or <b>Rayquaza</b> (Air Lock cancels all weather) on this team.',
         leads=[('KYOGRE', 'LATIAS'), ('KINGDRA', 'ZAPDOS')],
         members=[
            m('KYOGRE', 'DRIZZLE', 'MYSTIC_WATER', 'Modest', ['WATER_SPOUT', 'ICE_BEAM', 'THUNDER', 'PROTECT'],
              'Post-game (Marine Cave). Water Spout has 150 power at full HP and hits both foes, and rain boosts it further. Its power drops as Kyogre loses HP, so lead with it.'),
            m('LUGIA', 'PRESSURE', 'LEFTOVERS', 'Modest', ['THUNDER', 'CALM_MIND', 'RECOVER', 'PROTECT'],
              'Post-game (Navel Rock). The wall: base 154 Sp. Def, and Calm Mind fixes its ordinary 90 Sp. Atk. In rain its Thunder never misses, so Calm Mind turns into real damage. Flying, so Ground moves can’t touch it.'),
            m('LATIAS', 'LEVITATE', 'SITRUS_BERRY', 'Bold', ['DRAGON_CLAW', 'HELPING_HAND', 'RECOVER', 'PROTECT'],
              'Post-game (Southern Island). The support: Helping Hand makes Kyogre’s Water Spout ×1.5. Recover keeps it healthy, and Dragon resists the Water and Fire moves aimed at the team.'),
            m('ZAPDOS', 'PRESSURE', 'MAGNET', 'Mild', ['THUNDER', 'DRILL_PECK', 'LIGHT_SCREEN', 'PROTECT'],
              'Post-game (New Mauville). Thunder never misses in rain. It hits the opposing Water types that Kyogre can’t hurt.'),
            m('KINGDRA', 'SWIFT_SWIM', 'DRAGON_FANG', 'Modest', ['SURF', 'HYDRO_PUMP', 'ICE_BEAM', 'PROTECT'],
              'Permanent rain means permanent Swift Swim: it outspeeds almost everything without spending a turn first. Water/Dragon is only weak to Dragon, and Surf never hits its partner.'),
            m('LUDICOLO', 'SWIFT_SWIM', 'MIRACLE_SEED', 'Modest', ['FAKE_OUT', 'SURF', 'GIGA_DRAIN', 'ICE_BEAM'],
              'The second Swift Swim sweeper and the only Grass move here, which is what answers the opposing Water and Ground types. Fake Out buys a free turn on the lead. Water/Grass is only weak to Flying, Poison and Bug.'),
         ],
         variants=[
            dict(name='All legendary',
                 blurb='The same rain, built only from legendaries. <b>Mewtwo</b> and <b>Jirachi</b> replace the two Swift Swim sweepers, so the team trades speed under rain for raw stats and Steel/Psychic support. '
                       'Latias and Latios both have Levitate, so the few Ground moves aimed at them miss.',
                 members=[
                    m('KYOGRE', 'DRIZZLE', 'MYSTIC_WATER', 'Modest', ['WATER_SPOUT', 'ICE_BEAM', 'THUNDER', 'PROTECT'],
                      'Same set as above: lead with it while Water Spout is at full power.'),
                    m('LATIAS', 'LEVITATE', 'LEFTOVERS', 'Bold', ['DRAGON_CLAW', 'HELPING_HAND', 'RECOVER', 'PROTECT'],
                      'The support: Helping Hand makes Kyogre’s Water Spout ×1.5. Recover keeps it healthy.'),
                    m('LATIOS', 'LEVITATE', 'LEFTOVERS', 'Timid', ['DRAGON_CLAW', 'PSYCHIC', 'THUNDERBOLT', 'PROTECT'],
                      'The attacker: fast Dragon Claw (special in Gen 3) and Psychic.'),
                    m('MEWTWO', 'PRESSURE', 'LEFTOVERS', 'Timid', ['PSYCHIC', 'FLAMETHROWER', 'CALM_MIND', 'PROTECT'],
                      'Highest Sp. Atk of any legendary here. Rain halves Fire damage, so Flamethrower is only for Steel types that resist Psychic.'),
                    m('ZAPDOS', 'PRESSURE', 'LEFTOVERS', 'Mild', ['THUNDER', 'DRILL_PECK', 'LIGHT_SCREEN', 'PROTECT'],
                      'Thunder never misses in rain. It hits the opposing Water types that Kyogre can’t hurt.'),
                    m('JIRACHI', 'SERENE_GRACE', 'LEFTOVERS', 'Calm', ['WISH', 'HELPING_HAND', 'PSYCHIC', 'PROTECT'],
                      'Steel/Psychic support. Wish heals half of the partner’s max HP next turn, and it resists Dragon and Ice.'),
                 ]),
         ]),
    dict(id='groudon-sun', name='Groudon Sun', tag='Post-game · Drought · Chlorophyll · one-turn Solar Beam',
         blurb='<b>Drought</b> sets sun the moment Groudon enters, and ability weather in Gen 3 lasts until another weather replaces it, so no one spends a turn on Sunny Day. '
               'Sun doubles Chlorophyll users’ Speed, lets <b>Solar Beam</b> fire in one turn, boosts Fire moves by 50% and halves Water moves, Groudon’s weakness. '
               'A sun team is Grass and Fire by nature, which is exactly why Ice and Rock are the moves aimed at it, so the roster is picked to blunt both. '
               'No Grass/Flying: that typing is <b>4× Ice and 2× Rock</b>, the worst pair of weaknesses a Chlorophyll user can have. Grass/Psychic and Grass/Poison instead, which take Rock neutrally. '
               'And two Fire attackers, because <b>every Fire type resists Ice</b> and the sun halves the Water moves they normally fear. Ho-Oh is the only member Rock hits for super-effective damage. '
               'Groudon’s Earthquake is only safe next to Ho-Oh (Flying) or Latios (Levitate).',
         leads=[('GROUDON', 'HO_OH'), ('EXEGGUTOR', 'BLAZIKEN')],
         members=[
            m('GROUDON', 'DROUGHT', 'SOFT_SAND', 'Naive', ['EARTHQUAKE', 'FIRE_BLAST', 'SOLAR_BEAM', 'PROTECT'],
              'Post-game (Terra Cave). Earthquake uses its 150 Attack; sun-boosted Fire Blast and one-turn Solar Beam are special, so Naive keeps both sides. Only Earthquake next to Ho-Oh or Latios.'),
            m('HO_OH', 'PRESSURE', 'LEFTOVERS', 'Modest', ['SACRED_FIRE', 'THUNDERBOLT', 'RECOVER', 'PROTECT'],
              'Post-game (Navel Rock). Sacred Fire is special here and hits very hard in sun. Flying, so Groudon’s Earthquake never hits it. It is the one Rock weakness left on the team and it is 4× — but spread moves are halved in doubles, and 106 HP behind Recover absorbs a shared Rock Slide.'),
            m('LATIOS', 'LEVITATE', 'DRAGON_FANG', 'Timid', ['DRAGON_CLAW', 'PSYCHIC', 'THUNDERBOLT', 'PROTECT'],
              'Post-game (Southern Island). Dragon resists Water, Grass, Fire and Electric, and Levitate keeps it safe from Earthquake. Thunderbolt answers the Water types the Grass members invite in.'),
            m('EXEGGUTOR', 'CHLOROPHYLL', 'TWISTED_SPOON', 'Modest', ['SLEEP_POWDER', 'SOLAR_BEAM', 'PSYCHIC', 'PROTECT'],
              'Smogon’s sun sweeper and the strongest Solar Beam here, off 125 Sp. Atk at doubled Speed. Sleep Powder first, then one-turn Solar Beams. Grass/Psychic takes Rock neutrally.'),
            m('VICTREEBEL', 'CHLOROPHYLL', 'MIRACLE_SEED', 'Mild', ['SLEEP_POWDER', 'SOLAR_BEAM', 'SLUDGE_BOMB', 'SUNNY_DAY'],
              'The second Chlorophyll sweeper, at 140 Speed in sun, and a second Sleep Powder. Grass/Poison is neutral to Rock <i>and</i> to Bug, which Exeggutor takes 4×. Sludge Bomb is physical in this hack, off its 105 Attack, and Sunny Day brings the sun back if Groudon faints.'),
            m('BLAZIKEN', 'BLAZE', 'CHARCOAL', 'Naive', ['SKY_UPPERCUT', 'FLAMETHROWER', 'ROCK_SLIDE', 'PROTECT'],
              'Torchic is wild on Route 102 in this hack. The best defensive Fire type for this team: Fighting resists Rock, so Fire/Fighting takes it neutrally, and it halves Ice. Sky Uppercut and Rock Slide are physical and Flamethrower special, so Naive keeps both sides. Rock Slide hits both foes and answers the Fire and Flying types the Grass members fear.'),
         ]),
    dict(id='rayquaza-air', name='Rayquaza Air Lock', tag='Weather denial · Air Lock · Steel and Thick Fat backbone',
         blurb='<b>Air Lock</b> switches the weather off while Rayquaza is on the field. Rain stops boosting Water and halving Fire, sun stops boosting Fire, Swift Swim and Chlorophyll stop doubling Speed, '
               'Thunder and Blizzard lose their perfect accuracy, Solar Beam has to charge again, and sandstorm and hail stop chipping everyone. It <i>suspends</i> the weather rather than clearing it, '
               'so the rain or sun is back the moment Rayquaza leaves the field. That blanks the engine of five other teams on this page. '
               'The other five slots exist to keep Rayquaza on the field, because Dragon/Flying is <b>4× weak to Ice and 2× to Rock</b> and Rock Slide is the most common move in the format. '
               '<b>Metagross</b> and <b>Jirachi</b> are Steel, which resists both; <b>Hariyama</b> is Fighting, which resists Rock, with <b>Thick Fat</b> to halve Ice; <b>Suicune</b> is Water, which resists Ice; '
               '<b>Gengar</b> takes neutral damage from each. Rayquaza is the only member weak to either type.',
         leads=[('RAYQUAZA', 'METAGROSS'), ('HARIYAMA', 'GENGAR')],
         members=[
            m('RAYQUAZA', 'AIR_LOCK', 'DRAGON_FANG', 'Naive', ['DRAGON_CLAW', 'ROCK_SLIDE', 'EXTREME_SPEED', 'PROTECT'],
              'Sky Pillar summit, during the story — the only box legend you can catch before the Hall of Fame, and one chance only. Dragon Claw is special in Gen 3 while Rock Slide and Extreme Speed are physical, all off base 150, so Naive keeps both sides. Rock Slide hits both foes and can flinch them; Extreme Speed moves first.'),
            m('METAGROSS', 'CLEAR_BODY', 'LEFTOVERS', 'Adamant', ['METEOR_MASH', 'EARTHQUAKE', 'EXPLOSION', 'PROTECT'],
              'Smogon’s best doubles lead, and here also the insurance: Steel resists both Rock and Ice, so it switches into the moves that would take Rayquaza out. Clear Body ignores Intimidate. Earthquake only next to Rayquaza (Flying) or Gengar (Levitate).'),
            m('GENGAR', 'LEVITATE', 'MAGNET', 'Timid', ['THUNDERBOLT', 'ICE_PUNCH', 'WILL_O_WISP', 'PROTECT'],
              'The fast special attacker, and the Levitate partner that lets Metagross use Earthquake. Ghost/Poison is immune to Normal, Fighting and Ground and takes neutral damage from Rock and Ice. Will-O-Wisp halves a physical attacker’s damage, which is the cleanest answer to an opposing Rock Slide user.'),
            m('HARIYAMA', 'THICK_FAT', 'BLACK_BELT', 'Adamant', ['FAKE_OUT', ('CROSS_CHOP', 'BRICK_BREAK'), 'KNOCK_OFF', 'HELPING_HAND'],
              'The sponge for both problem types at once: Fighting resists Rock, and <b>Thick Fat</b> halves Ice. 144 base HP on top of that. Fake Out buys the turn Rayquaza needs, Helping Hand makes a Dragon Claw ×1.5, and Knock Off (Dark, physical in this hack) strips a foe’s Leftovers or berry.'),
            m('SUICUNE', 'PRESSURE', 'MYSTIC_WATER', 'Bold', ['CALM_MIND', 'SURF', 'ICE_BEAM', 'PROTECT'],
              'Post-game (Abandoned Ship, at the end of the Weather Institute trail). Water resists Ice, and 100/115/115 bulk behind a Calm Mind is very hard to break. Surf hits both foes and never your ally.'),
            m('JIRACHI', 'SERENE_GRACE', 'SITRUS_BERRY', 'Careful', ['BODY_SLAM', 'WISH', 'HELPING_HAND', 'PROTECT'],
              'Post-game (Mossdeep). The second Steel, so the team keeps a Rock and Ice resist on the field even after Metagross explodes. <b>Serene Grace</b> doubles Body Slam’s paralysis chance to 60%, and Wish heals half a partner’s max HP the turn after.'),
         ]),
    dict(id='eevee', name='Eeveelution Team', tag='This version’s starters',
         blurb='Every Gen 3 Eeveelution, plus Eevee itself. Your starter is an Eevee, Espeon or Umbreon, and the rest can be caught (see the Pokédex). '
               'All of them learn <b>Helping Hand</b>, so any pair can boost the other. Espeon and Umbreon are covered in more depth on their own team page.',
         leads=[('ESPEON', 'UMBREON'), ('VAPOREON', 'JOLTEON')],
         members=[
            m('ESPEON', 'SYNCHRONIZE', 'LEFTOVERS', 'Timid', ['PSYCHIC', 'SHADOW_BALL', 'LIGHT_SCREEN', 'PROTECT'],
              'The special attacker. Ghost is special in this hack, so Shadow Ball uses its Sp. Atk and hits Psychic and Ghost types.'),
            m('UMBREON', 'SYNCHRONIZE', 'LEFTOVERS', 'Bold', ['WISH', 'HELPING_HAND', 'CONFUSE_RAY', 'PROTECT'],
              'The wall. Immune to Psychic, and resists Ghost and Dark, which covers Espeon’s weaknesses.'),
            m('VAPOREON', 'WATER_ABSORB', 'LEFTOVERS', 'Bold', ['SURF', 'ICE_BEAM', 'WISH', 'PROTECT'],
              'Base 130 HP. Water Absorb heals it when hit by Water. Surf never hits its partner.'),
            m('JOLTEON', 'VOLT_ABSORB', 'MAGNET', 'Timid', ['THUNDERBOLT', 'THUNDER_WAVE', 'HELPING_HAND', 'PROTECT'],
              'Base 130 Speed. Thunder Wave slows the fast threats, and Volt Absorb heals it when hit by Electric.'),
            m('FLAREON', 'FLASH_FIRE', 'CHARCOAL', 'Modest', ['FLAMETHROWER', 'SHADOW_BALL', 'HELPING_HAND', 'PROTECT'],
              'Fire is special and this hack makes Ghost special too, so Flamethrower and Shadow Ball both use its 110 Sp. Atk. Flash Fire makes it immune to Fire.'),
            m('EEVEE', 'RUN_AWAY', 'LEFTOVERS', 'Bold', ['WISH', 'BATON_PASS', 'HELPING_HAND', 'PROTECT'],
              'Weak stats, but pure support: Wish heals a partner, Helping Hand boosts one, and Baton Pass passes boosts. Learns Wish at level 50.'),
         ]),
    dict(id='stat-all', group='Stat Specialists', name='One of Each', tag='A specialist for every stat',
         blurb='One specialist per stat, built to work as a team. <b>Ninjask</b> (Speed) Baton Passes Speed and Swords Dance boosts to <b>Azumarill</b> (Attack). '
               '<b>Blissey</b> (HP) Wishes the HP back after Belly Drum. <b>Steelix</b> (Defense) uses Earthquake, and three of its partners are immune: <b>Gengar</b> (Sp. Atk, Levitate), '
               '<b>Mantine</b> (Sp. Def, Flying) and Ninjask (Flying).',
         leads=[('NINJASK', 'AZUMARILL'), ('STEELIX', 'GENGAR')],
         members=[
            dict(m('BLISSEY', 'NATURAL_CURE', 'LEFTOVERS', 'Bold', ['WISH', 'SEISMIC_TOSS', 'THUNDER_WAVE', 'PROTECT'],
              'HP specialist: base 255, the highest in the game. Wish heals half of the partner’s max HP, which undoes Azumarill’s Belly Drum cost.'), stat='hp'),
            dict(m('AZUMARILL', 'HUGE_POWER', 'LEFTOVERS', 'Adamant', ['BELLY_DRUM', 'RETURN', 'BRICK_BREAK', 'PROTECT'],
              'Attack specialist: base 50, but Huge Power doubles the Attack stat. After Belly Drum (or a Baton Passed Swords Dance) it hits harder than anything else on the team.'), stat='atk'),
            dict(m('STEELIX', 'ROCK_HEAD', 'LEFTOVERS', 'Impish', ['EARTHQUAKE', 'ROCK_SLIDE', 'EXPLOSION', 'PROTECT'],
              'Defense specialist: base 200, second only to Shuckle. Earthquake next to Gengar, Mantine or Ninjask. Blissey and Azumarill are grounded.'), stat='def'),
            dict(m('GENGAR', 'LEVITATE', 'LEFTOVERS', 'Timid', ['THUNDERBOLT', 'ICE_PUNCH', 'WILL_O_WISP', 'PROTECT'],
              'Sp. Atk specialist: base 130, just behind Alakazam, but Levitate makes it Steelix’s ideal partner. Ice Punch uses Sp. Atk in Gen 3.'), stat='spa'),
            dict(m('MANTINE', 'WATER_ABSORB', 'LEFTOVERS', 'Calm', ['SURF', 'ICE_BEAM', 'HAZE', 'PROTECT'],
              'Sp. Def specialist: base 140. Flying, so Earthquake can’t hit it, and Water Absorb makes it immune to Water. Haze erases the foes’ boosts.'), stat='spd'),
            dict(m('NINJASK', 'SPEED_BOOST', 'LEFTOVERS', 'Jolly', ['SWORDS_DANCE', 'BATON_PASS', 'SUBSTITUTE', 'PROTECT'],
              'Speed specialist: base 160, the fastest non-legendary, plus Speed Boost every turn. Protect first, Swords Dance, then Baton Pass everything to Azumarill.'), stat='spe'),
         ]),
    dict(id='stat-hp', group='Stat Specialists', stat='hp', name='HP Specialists', tag='Highest base HP',
         blurb='Huge HP pools outlast the opponent. <b>Wish</b> heals half of the recipient’s max HP in Gen 3, so a high-HP partner gets more back. '
               'Protect stalls while Wish lands, and Water Spout’s power scales with the user’s HP.',
         leads=[('WOBBUFFET', 'BLISSEY'), ('HARIYAMA', 'WAILORD')],
         members=[
            m('BLISSEY', 'NATURAL_CURE', 'LEFTOVERS', 'Bold', ['WISH', 'SEISMIC_TOSS', 'THUNDER_WAVE', 'PROTECT'],
              'Base 255 HP, the highest in the game. Seismic Toss does damage equal to its level no matter the defenses, and Wish keeps the team alive.'),
            m('WOBBUFFET', 'SHADOW_TAG', 'LEFTOVERS', 'Bold', ['COUNTER', 'MIRROR_COAT', 'ENCORE', 'DESTINY_BOND'],
              'Base 190 HP. Counter and Mirror Coat return double the damage it takes, and Shadow Tag stops foes from escaping.'),
            m('WAILORD', 'WATER_VEIL', 'LEFTOVERS', 'Modest', ['WATER_SPOUT', 'ICE_BEAM', 'REST', 'PROTECT'],
              'Base 170 HP. Water Spout at full HP has 150 power and hits both foes. Water Veil prevents burns.'),
            m('SNORLAX', 'THICK_FAT', 'LEFTOVERS', 'Adamant', ['BODY_SLAM', 'ROCK_SLIDE', 'BRICK_BREAK', 'PROTECT'],
              'Base 160 HP. Thick Fat halves Fire and Ice damage, and Body Slam paralyzes 30% of the time.'),
            m('HARIYAMA', 'THICK_FAT', 'LEFTOVERS', 'Adamant', ['FAKE_OUT', ('CROSS_CHOP', 'BRICK_BREAK'), 'ROCK_SLIDE', 'HELPING_HAND'],
              'Base 144 HP. Fake Out plus Helping Hand support that can take hits.'),
            m('VAPOREON', 'WATER_ABSORB', 'LEFTOVERS', 'Bold', ['SURF', 'ICE_BEAM', 'WISH', 'PROTECT'],
              'Base 130 HP. A second Wish user, so the team heals twice as often.'),
         ]),
    dict(id='stat-atk', group='Stat Specialists', stat='atk', name='Attack Specialists', tag='Huge Power · Pure Power · Truant',
         blurb='The hardest physical hitters. <b>Huge Power</b> and <b>Pure Power</b> double the Attack stat, which is why base-50 Azumarill and base-60 Medicham belong here. '
               'Remember that only Normal, Fighting, Flying, Poison, Ground, Rock, Bug, Steel and Dark moves use Attack: this hack swaps Dark and Ghost. '
               'Support comes from Follow Me, Fake Out, Helping Hand and Intimidate.',
         leads=[('TOGETIC', 'SLAKING'), ('HITMONTOP', 'MEDICHAM')],
         members=[
            m('AZUMARILL', 'HUGE_POWER', 'LEFTOVERS', 'Adamant', ['RETURN', 'BRICK_BREAK', 'ICE_PUNCH', 'PROTECT'],
              'Huge Power doubles its Attack. Ice Punch is special in Gen 3, so it’s only for Dragon and Flying types; Return and Brick Break do the real damage.'),
            m('MEDICHAM', 'PURE_POWER', 'LEFTOVERS', 'Jolly', ['HI_JUMP_KICK', 'ROCK_SLIDE', 'BODY_SLAM', 'FAKE_OUT'],
              'Pure Power doubles its Attack. Body Slam hits what resists Hi Jump Kick and paralyzes 30% of the time. Ghost moves are special in this hack, so Shadow Ball would waste Pure Power.'),
            m('SLAKING', 'TRUANT', 'CHOICE_BAND', 'Adamant', ['RETURN', 'FAINT_ATTACK', 'ROCK_SLIDE', 'BRICK_BREAK'],
              'Base 160 Attack, the highest non-legendary. Truant makes it skip every other turn, so pair it with Togetic’s Follow Me for the loafing turns.'),
            m('HERACROSS', 'GUTS', 'LEFTOVERS', 'Adamant', ['MEGAHORN', 'ROCK_SLIDE', 'BRICK_BREAK', 'PROTECT'],
              'Base 125 Attack. Guts turns a status condition into ×1.5 Attack.'),
            m('TOGETIC', 'SERENE_GRACE', 'LEFTOVERS', 'Bold', ['FOLLOW_ME', 'HELPING_HAND', 'ENCORE', 'PROTECT'],
              'Follow Me draws single-target attacks away from the hitters, and Helping Hand makes their next hit ×1.5.'),
            m('HITMONTOP', 'INTIMIDATE', 'LEFTOVERS', 'Adamant', ['FAKE_OUT', 'HELPING_HAND', 'BRICK_BREAK', 'ROCK_SLIDE'],
              'Intimidate weakens the foes’ own physical attackers, and Fake Out buys a free turn.'),
         ]),
    dict(id='stat-def', group='Stat Specialists', stat='def', name='Defense Specialists', tag='Physical walls · Reflect',
         blurb='Walls that shrug off physical hits. <b>Reflect</b> cuts physical damage to ⅔ in doubles (½ once only one ally is left), and Rock Head removes Double-Edge’s recoil. '
               'Physical walls are weak to special attacks, so Claydol also sets <b>Light Screen</b>.',
         leads=[('CLAYDOL', 'STEELIX'), ('SKARMORY', 'AGGRON')],
         members=[
            m('SKARMORY', 'STURDY', 'LEFTOVERS', 'Impish', ['DRILL_PECK', 'TAUNT', 'WHIRLWIND', 'PROTECT'],
              'Base 140 Defense. Flying type, so Steelix’s Earthquake can’t hit it. Whirlwind forces out a foe that’s setting up.'),
            m('STEELIX', 'ROCK_HEAD', 'LEFTOVERS', 'Impish', ['EARTHQUAKE', 'ROCK_SLIDE', 'EXPLOSION', 'PROTECT'],
              'Base 200 Defense, second only to Shuckle. Use Earthquake only next to Skarmory or Claydol.'),
            m('AGGRON', 'ROCK_HEAD', 'LEFTOVERS', 'Impish', ['ROCK_SLIDE', 'IRON_TAIL', 'DOUBLE_EDGE', 'PROTECT'],
              'Base 180 Defense. Rock Head means Double-Edge has no recoil. It’s 4× weak to Ground and Fighting, so keep it away from Steelix’s Earthquake.'),
            m('CLAYDOL', 'LEVITATE', 'LEFTOVERS', 'Bold', ['REFLECT', 'LIGHT_SCREEN', 'EARTHQUAKE', 'PSYCHIC'],
              'Sets both screens. Levitate lets it partner Steelix’s Earthquake.'),
            m('FORRETRESS', 'STURDY', 'LEFTOVERS', 'Relaxed', ['EXPLOSION', 'ROCK_SLIDE', 'SPIKES', 'PROTECT'],
              'Base 140 Defense. Bug/Steel is only weak to Fire. Explosion is its way out.'),
            m('CLOYSTER', 'SHELL_ARMOR', 'LEFTOVERS', 'Bold', ['SURF', 'ICE_BEAM', 'EXPLOSION', 'PROTECT'],
              'Base 180 Defense. Shell Armor blocks critical hits, which would otherwise bypass Reflect.'),
         ]),
    dict(id='stat-spa', group='Stat Specialists', stat='spa', name='Sp. Atk Specialists', tag='Special attackers · Plus & Minus',
         blurb='The hardest special hitters. In Gen 3 the type decides it, and this hack swaps Dark and Ghost: <b>Fire, Water, Grass, Electric, Ice, Psychic, Dragon and Ghost</b> moves use Sp. Atk, including Fire, Ice and Thunder Punch. '
               'Plusle and Minun each get ×1.5 Sp. Atk while the other is on the field. These attackers are fragile, so Protect is on almost every set.',
         leads=[('PLUSLE', 'MINUN'), ('ALAKAZAM', 'GENGAR')],
         members=[
            m('ALAKAZAM', 'INNER_FOCUS', 'TWISTED_SPOON', 'Timid', ['PSYCHIC', 'FIRE_PUNCH', 'ICE_PUNCH', 'PROTECT'],
              'Base 135 Sp. Atk. Its elemental punches use Sp. Atk in Gen 3. Inner Focus stops Fake Out’s flinch.'),
            m('GENGAR', 'LEVITATE', 'LEFTOVERS', 'Timid', ['THUNDERBOLT', 'ICE_PUNCH', 'GIGA_DRAIN', 'PROTECT'],
              'Base 130 Sp. Atk. Immune to Normal, Fighting and Ground.'),
            m('GARDEVOIR', 'TRACE', 'LEFTOVERS', 'Modest', ['PSYCHIC', 'THUNDERBOLT', 'CALM_MIND', 'PROTECT'],
              'Base 125 Sp. Atk. Calm Mind boosts Sp. Atk and Sp. Def together.'),
            m('STARMIE', 'NATURAL_CURE', 'MYSTIC_WATER', 'Timid', ['SURF', 'THUNDERBOLT', 'ICE_BEAM', 'PROTECT'],
              'Base 100 Sp. Atk with 115 Speed, and the widest special coverage here.'),
            m('PLUSLE', 'PLUS', 'MAGNET', 'Timid', ['THUNDERBOLT', 'HELPING_HAND', 'ENCORE', 'PROTECT'],
              'Plus: ×1.5 Sp. Atk while Minun is on the field.'),
            m('MINUN', 'MINUS', 'MAGNET', 'Timid', ['THUNDERBOLT', 'FOLLOW_ME', 'HELPING_HAND', 'PROTECT'],
              'Minus: ×1.5 Sp. Atk while Plusle is on the field. Follow Me keeps the pair alive.'),
         ]),
    dict(id='stat-spd', group='Stat Specialists', stat='spd', name='Sp. Def Specialists', tag='Special walls · recovery',
         blurb='Walls that absorb special attacks: rain-boosted Surf, sun-boosted Heat Wave, Thunderbolt spam. <b>Light Screen</b> cuts special damage further, to ⅔. '
               'Recovery moves and Wish keep them healthy, and burns from Will-O-Wisp cover their weakness to physical attackers.',
         leads=[('MILOTIC', 'DUSCLOPS'), ('MANTINE', 'UMBREON')],
         members=[
            m('REGICE', 'CLEAR_BODY', 'LEFTOVERS', 'Calm', ['ICE_BEAM', 'THUNDERBOLT', 'REST', 'PROTECT'],
              'Post-game. Base 200 Sp. Def, the highest of any obtainable Pokémon besides Shuckle.'),
            m('MANTINE', 'WATER_ABSORB', 'LEFTOVERS', 'Calm', ['SURF', 'ICE_BEAM', 'HAZE', 'PROTECT'],
              'Base 140 Sp. Def. Water Absorb makes it immune to Water, and Haze resets every stat boost on the field.'),
            m('DUSCLOPS', 'PRESSURE', 'LEFTOVERS', 'Impish', ['WILL_O_WISP', 'HELPING_HAND', 'PAIN_SPLIT', 'PROTECT'],
              'Base 130 Sp. Def and 130 Defense. Will-O-Wisp covers the physical side.'),
            m('UMBREON', 'SYNCHRONIZE', 'LEFTOVERS', 'Calm', ['WISH', 'HELPING_HAND', 'TAUNT', 'PROTECT'],
              'Base 130 Sp. Def. Wish heals partners, and Taunt stops enemy setup.'),
            m('MILOTIC', 'MARVEL_SCALE', 'LEFTOVERS', 'Calm', ['SURF', 'ICE_BEAM', 'RECOVER', 'PROTECT'],
              'Base 125 Sp. Def. Marvel Scale gives ×1.5 Defense while it has a status condition, and Recover heals half its HP.'),
            m('TENTACRUEL', 'CLEAR_BODY', 'LEFTOVERS', 'Sassy', ['SURF', 'SLUDGE_BOMB', 'ICE_BEAM', 'PROTECT'],
              'Base 120 Sp. Def. Clear Body blocks Intimidate. Water/Poison resists Fire, Water, Ice, Fighting, Poison, Bug and Steel.'),
         ]),
    dict(id='stat-spe', group='Stat Specialists', stat='spe', name='Speed Specialists', tag='Speed Boost · Baton Pass · Thunder Wave',
         blurb='Move first, and make sure the foes don’t. There’s no Tailwind or Trick Room in Gen 3, so Speed comes from high base stats, <b>Speed Boost</b> '
               '(+1 Speed each turn) passed along with <b>Baton Pass</b>, and slowing foes with <b>Thunder Wave</b>. Fake Out and Taunt work best when you’re faster.',
         leads=[('NINJASK', 'CROBAT'), ('ELECTRODE', 'JOLTEON')],
         members=[
            m('NINJASK', 'SPEED_BOOST', 'LEFTOVERS', 'Jolly', ['SWORDS_DANCE', 'BATON_PASS', 'SUBSTITUTE', 'PROTECT'],
              'Base 160 Speed. Protect on turn one (Speed Boost still triggers), then Swords Dance, then Baton Pass the Speed and Attack boosts to Aerodactyl.'),
            m('AERODACTYL', 'ROCK_HEAD', 'LEFTOVERS', 'Jolly', ['ROCK_SLIDE', 'EARTHQUAKE', 'AERIAL_ACE', 'PROTECT'],
              'Base 130 Speed. The Baton Pass receiver. Earthquake hits a grounded partner, so use it next to Ninjask or Crobat.'),
            m('ELECTRODE', 'SOUNDPROOF', 'MAGNET', 'Timid', ['THUNDERBOLT', 'THUNDER_WAVE', 'EXPLOSION', 'PROTECT'],
              'Base 140 Speed, the fastest non-legendary after Ninjask. Soundproof blocks Perish Song.'),
            m('CROBAT', 'INNER_FOCUS', 'LEFTOVERS', 'Jolly', ['AERIAL_ACE', 'SLUDGE_BOMB', 'TAUNT', 'PROTECT'],
              'Base 130 Speed. Inner Focus stops Fake Out’s flinch, and Taunt shuts down slower support Pokémon.'),
            m('JOLTEON', 'VOLT_ABSORB', 'MAGNET', 'Timid', ['THUNDERBOLT', 'THUNDER_WAVE', 'HELPING_HAND', 'PROTECT'],
              'Base 130 Speed. Thunder Wave quarters a foe’s Speed.'),
            m('SCEPTILE', 'OVERGROW', 'MIRACLE_SEED', 'Timid', ['LEAF_BLADE', 'DRAGON_CLAW', 'THUNDER_PUNCH', 'FAKE_OUT'],
              'Base 120 Speed. Leaf Blade, Dragon Claw and Thunder Punch are all special in Gen 3, so a Timid Sceptile uses its 110 Sp. Atk. Thunder Punch (Battle Frontier tutor) hits Water and Flying types. It learns Fake Out by level-up in this hack.'),
         ]),
]

COMBOS = [
    dict(name='Wonder Guard shield', pair=[
            m('SHEDINJA', 'WONDER_GUARD', 'BRIGHT_POWDER', 'Adamant', ['FAINT_ATTACK', 'AERIAL_ACE', 'TOXIC', 'PROTECT'], ''),
            m('GOLEM', 'STURDY', 'SOFT_SAND', 'Adamant', ['EARTHQUAKE', 'EXPLOSION', 'ROCK_SLIDE', 'PROTECT'], '')],
         html='Wonder Guard blocks every hit that isn’t super effective, <b>including your partner’s</b>. Ground is not very effective on Bug/Ghost, '
              'and Normal can’t touch Ghost, so Golem can use Earthquake and Explosion freely beside Shedinja. '
              '<b>Risk:</b> Shedinja has 1 HP. Sandstorm, hail, poison, burn and any Fire, Flying, Rock, Ghost or Dark attack faint it. '
              'That includes spread Rock Slide and Heat Wave.'),
    dict(name='Lightning Rod bodyguard', pair=[
            m('MAROWAK', 'LIGHTNING_ROD', 'THICK_CLUB', 'Adamant', ['EARTHQUAKE', 'ROCK_SLIDE', 'SWORDS_DANCE', 'PROTECT'], ''),
            m('GYARADOS', 'INTIMIDATE', 'LEFTOVERS', 'Adamant', ['DRAGON_DANCE', 'DOUBLE_EDGE', 'BOUNCE', 'PROTECT'], '')],
         html='Lightning Rod pulls the <b>opponents’</b> single-target Electric moves onto Marowak, which is a Ground type and takes no damage. '
              'That protects Gyarados’s 4× Electric weakness. Gyarados is Flying, so Thick Club Earthquake never hits it. '
              'Lightning Rod doesn’t redirect your own team’s moves.'),
    dict(name='Plus & Minus', pair=[
            m('PLUSLE', 'PLUS', 'MAGNET', 'Timid', ['THUNDERBOLT', 'HELPING_HAND', 'ENCORE', 'PROTECT'], ''),
            m('MINUN', 'MINUS', 'MAGNET', 'Timid', ['THUNDERBOLT', 'FOLLOW_ME', 'HELPING_HAND', 'PROTECT'], '')],
         html='While both are on the field, each gets <b>×1.5 Sp. Atk</b>. Minun’s Follow Me or Encore protects Plusle while it attacks. '
              'Both are caught on Route 110, making this a strong early-game pair.'),
    dict(name='Explosion + Ghost', pair=[
            m('METAGROSS', 'CLEAR_BODY', 'LEFTOVERS', 'Adamant', ['METEOR_MASH', 'EARTHQUAKE', 'EXPLOSION', 'PROTECT'], ''),
            m('GENGAR', 'LEVITATE', 'LEFTOVERS', 'Timid', ['THUNDERBOLT', 'ICE_PUNCH', 'EXPLOSION', 'PROTECT'], '')],
         html='Explosion hits everyone else on the field and halves the targets’ Defense. Gengar is a Ghost type, so it’s immune to '
              'Metagross’s Explosion, and Levitate makes it immune to Earthquake too. Smogon lists this as the classic ADV doubles lead. '
              'Smogon’s current tournament rules ban Explosion, but this game allows it. Make sure the Explosion also takes out something that matters.'),
    dict(name='Rain Thunder', pair=[
            m('PELIPPER', 'KEEN_EYE', 'MYSTIC_WATER', 'Modest', ['RAIN_DANCE', 'SURF', 'ICE_BEAM', 'PROTECT'], ''),
            m('LANTURN', 'VOLT_ABSORB', 'MAGNET', 'Modest', ['THUNDER', 'SURF', 'ICE_BEAM', 'PROTECT'], '')],
         html='In rain, Thunder has 120 power and <b>never misses</b>, while Surf gets a 50% boost and hits both foes. '
              'Lanturn’s Water/Electric typing resists the Electric attacks aimed at Pelipper, so it’s a safe switch-in (Volt Absorb even heals it). Pelipper’s Flying type makes it immune to Ground attacks aimed at Lanturn.'),
    dict(name='Follow Me + Belly Drum', pair=[
            m('TOGETIC', 'SERENE_GRACE', 'LEFTOVERS', 'Bold', ['FOLLOW_ME', 'HELPING_HAND', 'ENCORE', 'PROTECT'], ''),
            m('AZUMARILL', 'HUGE_POWER', 'LEFTOVERS', 'Adamant', ['BELLY_DRUM', 'RETURN', 'BRICK_BREAK', 'PROTECT'], '')],
         html='<b>Belly Drum</b> costs half of Azumarill’s max HP and maxes its Attack (+6). Huge Power then doubles that. The drum turn is the risky one, '
              'so Togetic uses <b>Follow Me</b> that same turn to draw the foes’ single-target attacks. Spread moves like Rock Slide still hit both.'),
    dict(name='Heal your partner with Volt Absorb', pair=[
            m('JOLTEON', 'VOLT_ABSORB', 'MAGNET', 'Timid', ['THUNDERBOLT', 'THUNDER_WAVE', 'HELPING_HAND', 'PROTECT'], ''),
            m('LANTURN', 'VOLT_ABSORB', 'LEFTOVERS', 'Modest', ['THUNDERBOLT', 'SURF', 'ICE_BEAM', 'PROTECT'], '')],
         html='In doubles you can aim a single-target move at <b>your own partner</b>. An Electric attack into a Volt Absorb ally does no damage and heals it '
              '<b>¼ of its max HP</b> (Water into Water Absorb works the same way). Both of these Pokémon have Volt Absorb, so each can heal the other with Thunderbolt, and '
              'neither fears the other side’s Electric attacks. It costs a turn, so do it while the partner Protects or the foes are slowed.'),
    dict(name='Flash Fire power-up', pair=[
            m('NINETALES', 'FLASH_FIRE', 'CHARCOAL', 'Timid', ['FLAMETHROWER', 'HEAT_WAVE', 'WILL_O_WISP', 'PROTECT'], ''),
            m('ARCANINE', 'FLASH_FIRE', 'CHARCOAL', 'Modest', ['FLAMETHROWER', 'HEAT_WAVE', 'EXTREME_SPEED', 'PROTECT'], '')],
         html='On turn one, each <b>Flamethrowers its partner</b>. Flash Fire absorbs the hit (no damage) and powers up the holder’s own Fire moves <b>×1.5</b> until it switches out. '
              'After that, both fire boosted Heat Waves into the foes, and Heat Wave never hits your own side. Will-O-Wisp won’t work here: it fails against Fire types before Flash Fire can activate.'),
    dict(name='Skill Swap away Truant', pair=[
            m('GARDEVOIR', 'TRACE', 'LEFTOVERS', 'Modest', ['SKILL_SWAP', 'PSYCHIC', 'CALM_MIND', 'PROTECT'], ''),
            m('SLAKING', 'TRUANT', 'CHOICE_BAND', 'Adamant', ['RETURN', 'FAINT_ATTACK', 'ROCK_SLIDE', 'BRICK_BREAK'], '')],
         html='Skill Swap trades abilities with the target, and in Gen 3 it only fails on Wonder Guard. Swap with Slaking: <b>Slaking loses Truant</b> and attacks every turn with base 160 Attack and Choice Band. '
              'Gardevoir now has Truant, so on its next active turn it can Skill Swap again with a dangerous foe, handing Truant to that foe.'),
    dict(name='Soundproof + Perish Song', pair=[
            m('EXPLOUD', 'SOUNDPROOF', 'SILK_SCARF', 'Hasty', ['HYPER_VOICE', 'ICE_BEAM', 'FLAMETHROWER', 'PROTECT'], ''),
            m('LAPRAS', 'WATER_ABSORB', 'LEFTOVERS', 'Calm', ['PERISH_SONG', 'SURF', 'ICE_BEAM', 'PROTECT'], '')],
         html='Perish Song starts a 3-turn countdown on every Pokémon on the field, <b>except those with Soundproof</b>. Exploud ignores it and keeps attacking with Hyper Voice (hits both foes), '
              'so only Lapras has to switch out before the count ends.'),
    dict(name='Imprison + Protect', pair=[
            m('BANETTE', 'INSOMNIA', 'LEFTOVERS', 'Modest', ['IMPRISON', 'PROTECT', 'WILL_O_WISP', 'SHADOW_BALL'], ''),
            m('GOLEM', 'STURDY', 'SOFT_SAND', 'Adamant', ['EXPLOSION', 'EARTHQUAKE', 'ROCK_SLIDE', 'PROTECT'], '')],
         html='<b>Imprison</b> stops both foes from using any move the user also knows. Because Banette knows <b>Protect</b>, the foes can’t Protect, so Golem’s Earthquake and Explosion land. '
              'Banette is a Ghost, so Explosion can’t hurt it. In Gen 3 Imprison fails if no foe shares a move with the user, but almost everything carries Protect.'),
    dict(name='Swagger + Own Tempo', pair=[
            m('CROBAT', 'INNER_FOCUS', 'LEFTOVERS', 'Jolly', ['SWAGGER', 'AERIAL_ACE', 'TAUNT', 'PROTECT'], ''),
            m('LICKITUNG', 'OWN_TEMPO', 'LEFTOVERS', 'Adamant', ['RETURN', 'EARTHQUAKE', 'KNOCK_OFF', 'PROTECT'], '')],
         html='Swagger raises the target’s Attack by 2 and then tries to confuse it. <b>Own Tempo</b> blocks the confusion but not the boost, so fast Crobat can Swagger Lickitung for a free +2. '
              'Crobat is Flying, so Lickitung’s boosted Earthquake never hits it. The same trick works once on any partner holding a <b>Lum Berry</b>, which cures confusion.'),
    dict(name='Memento into a sweeper', pair=[
            m('WEEZING', 'LEVITATE', 'LEFTOVERS', 'Impish', ['MEMENTO', 'WILL_O_WISP', 'SLUDGE_BOMB', 'PROTECT'], ''),
            m('GYARADOS', 'INTIMIDATE', 'LEFTOVERS', 'Adamant', ['DRAGON_DANCE', 'EARTHQUAKE', 'DOUBLE_EDGE', 'PROTECT'], '')],
         html='<b>Memento</b> makes Weezing faint and sharply lowers one foe’s Attack <i>and</i> Sp. Atk (−2 each). Use it on the foe most able to hurt Gyarados, while Gyarados uses Dragon Dance. '
              'Before that, Weezing’s Levitate lets Gyarados use Earthquake freely.'),
    dict(name='Magnet Pull trap', pair=[
            m('MAGNETON', 'MAGNET_PULL', 'MAGNET', 'Modest', ['THUNDERBOLT', 'THUNDER_WAVE', 'SUBSTITUTE', 'PROTECT'], ''),
            m('ARCANINE', 'INTIMIDATE', 'CHARCOAL', 'Modest', ['FLAMETHROWER', 'HEAT_WAVE', 'EXTREME_SPEED', 'PROTECT'], '')],
         html='<b>Magnet Pull</b> stops Steel types from switching out, so Skarmory, Metagross, Aggron and Forretress are stuck in front of Arcanine’s Fire attacks. '
              '<b>Careful:</b> in Gen 3 it checks the whole field, so Magneton also traps <b>your own</b> Steel types. Arcanine isn’t one.'),
    dict(name='Forecast in the rain', pair=[
            m('CASTFORM', 'FORECAST', 'MYSTIC_WATER', 'Modest', ['RAIN_DANCE', 'WEATHER_BALL', 'THUNDER', 'PROTECT'], ''),
            m('KINGDRA', 'SWIFT_SWIM', 'MYSTIC_WATER', 'Modest', ['SURF', 'HYDRO_PUMP', 'ICE_BEAM', 'PROTECT'], '')],
         html='<b>Forecast</b> turns Castform into a Water type in rain (Fire in sun, Ice in hail). In weather, <b>Weather Ball</b> doubles to 100 power and takes the weather’s type, so in rain it’s a boosted Water move. '
              'Castform sets the rain, and Kingdra’s Swift Swim doubles its Speed. Thunder never misses in rain.'),
    dict(name='Cloud Nine against weather', pair=[
            m('GOLDUCK', 'CLOUD_NINE', 'LEFTOVERS', 'Modest', ['SURF', 'ICE_BEAM', 'CALM_MIND', 'PROTECT'], ''),
            m('ARCANINE', 'INTIMIDATE', 'CHARCOAL', 'Mild', ['HEAT_WAVE', 'EXTREME_SPEED', 'HELPING_HAND', 'PROTECT'], '')],
         html='While <b>Cloud Nine</b> Golduck is on the field, weather has no effect at all: rain stops boosting Water and weakening Fire, Swift Swim and Chlorophyll stop doubling Speed, '
              'and Thunder and Solar Beam go back to normal. That shuts down the post-game Kyogre rain and Groudon sun teams, and it lets Arcanine’s Heat Wave hit full strength into rain.'),
    dict(name='Psych Up + Belly Drum', pair=[
            m('AZUMARILL', 'HUGE_POWER', 'LEFTOVERS', 'Adamant', ['BELLY_DRUM', 'RETURN', 'BRICK_BREAK', 'PROTECT'], ''),
            m('GOLDUCK', 'CLOUD_NINE', 'LEFTOVERS', 'Adamant', ['PSYCH_UP', 'CROSS_CHOP', 'RETURN', 'PROTECT'], '')],
         html='Azumarill uses <b>Belly Drum</b> (half its HP for maximum Attack). Next turn Golduck uses <b>Psych Up on its own partner</b>, which copies every stat change, so both now have +6 Attack. '
              'Golduck is faster, so it must wait a turn for the Belly Drum to happen first. Pair it with Follow Me or Fake Out support to survive the setup turn.'),
    dict(name='Screens + Dragon Dance', pair=[
            m('CLAYDOL', 'LEVITATE', 'LEFTOVERS', 'Bold', ['REFLECT', 'LIGHT_SCREEN', 'EARTHQUAKE', 'EXPLOSION'], ''),
            m('DRAGONITE', 'INNER_FOCUS', 'LEFTOVERS', 'Adamant', ['DRAGON_DANCE', 'EARTHQUAKE', 'EXTREME_SPEED', 'PROTECT'], '')],
         html='Claydol sets <b>Reflect and Light Screen</b>, which cut damage to ⅔ in doubles (spread moves included) for 5 turns, while Dragonite uses Dragon Dance behind them. '
              'Inner Focus stops Fake Out from flinching it on the setup turn. Claydol has Levitate and Dragonite is Flying, so both can Earthquake freely. Claydol explodes once the screens are up and its job is done.'),
    dict(name='Rest + Heal Bell', pair=[
            m('SNORLAX', 'THICK_FAT', 'LEFTOVERS', 'Adamant', ['CURSE', 'BODY_SLAM', 'REST', 'BRICK_BREAK'], ''),
            m('MILTANK', 'THICK_FAT', 'LEFTOVERS', 'Impish', ['HEAL_BELL', 'MILK_DRINK', 'BODY_SLAM', 'PROTECT'], '')],
         html='Snorlax uses <b>Curse</b> to raise Attack and Defense, and <b>Rest</b> when it gets low: full HP, but asleep for two turns. On the next turn Miltank uses <b>Heal Bell</b>, '
              'which cures the whole team’s status, so Snorlax wakes up at once and keeps its boosts. Miltank is faster, so it must wait until the turn after Rest.'),
    dict(name='Guts from your own partner', pair=[
            m('SWELLOW', 'GUTS', 'LEFTOVERS', 'Jolly', ['FACADE', 'AERIAL_ACE', 'QUICK_ATTACK', 'PROTECT'], ''),
            m('UMBREON', 'SYNCHRONIZE', 'LEFTOVERS', 'Bold', ['TOXIC', 'WISH', 'HELPING_HAND', 'PROTECT'], '')],
         html='Umbreon targets <b>its own partner</b> with Toxic. Poisoned Swellow gets <b>Guts ×1.5 Attack</b>, and Facade doubles to 140 power while it has a status condition. '
              'Wish heals back the poison damage. Guts also ignores burn’s Attack drop, so a partner’s Will-O-Wisp works too, if it isn’t a Fire type.'),
]

# ---------------------------------------------------------------------------
# Held items: one each per line-up
# ---------------------------------------------------------------------------
# The Battle Tower and Frontier refuse a party that holds two of the same item
# (src/battle_tower.c), so no team or pair here may repeat one. Sets declare the item they
# want; where two members want the same thing, the one that needs it keeps it and the others
# fall back to a type-boosting item for something they actually attack with, then to a
# generic hold item.
TYPE_ITEM = {
    'NORMAL': 'SILK_SCARF', 'FIGHTING': 'BLACK_BELT', 'FLYING': 'SHARP_BEAK', 'POISON': 'POISON_BARB',
    'GROUND': 'SOFT_SAND', 'ROCK': 'HARD_STONE', 'BUG': 'SILVER_POWDER', 'GHOST': 'SPELL_TAG',
    'STEEL': 'METAL_COAT', 'FIRE': 'CHARCOAL', 'WATER': 'MYSTIC_WATER', 'GRASS': 'MIRACLE_SEED',
    'ELECTRIC': 'MAGNET', 'PSYCHIC': 'TWISTED_SPOON', 'ICE': 'NEVER_MELT_ICE', 'DRAGON': 'DRAGON_FANG',
    'DARK': 'BLACK_GLASSES',
}
FILLER_ITEMS = ['LUM_BERRY', 'SITRUS_BERRY', 'CHESTO_BERRY', 'SHELL_BELL', 'BRIGHT_POWDER', 'QUICK_CLAW',
                'SCOPE_LENS', 'FOCUS_BAND', 'WHITE_HERB', 'MENTAL_HERB', 'LAX_INCENSE', 'KINGS_ROCK']


def _flat(text):
    return ''.join(c for c in (text or '').lower() if c.isalnum() or c == ' ')


def _wants_item(mem, prose):
    """True when the prose names this item for this Pokémon, so the set must keep it: its own
    note naming the item, or shared prose naming both the item and this species."""
    item = _flat(mem['item'].replace('_', ' '))
    if item in _flat(mem['note']):
        return True
    shared = _flat(prose)
    return item in shared and _flat(mem['sp'].replace('_', ' ')) in shared


def _item_candidates(mem):
    """What this set would like to hold, best first."""
    D = cov.load()
    sp = D['species'][mem['sp']]
    yield mem['item']
    moves = [mv for x in mem['moves'] for mv in ((x,) if isinstance(x, str) else x)]
    attacks = [D['moves'][mv] for mv in moves if D['moves'][mv]['power'] > 1]
    for stab in (True, False):
        for m in sorted(attacks, key=lambda m: -m['power']):
            if (m['type'] in sp['types']) == stab and m['type'] in TYPE_ITEM:
                yield TYPE_ITEM[m['type']]
    yield from FILLER_ITEMS


def dedupe_items(members, prose=''):
    """Give every member of one line-up a different held item, in place."""
    bulk = lambda m: cov.load()['species'][m['sp']]['bulk']
    # Sets whose note names the item keep it; then unusual items over Leftovers; then the bulkiest.
    order = sorted(range(len(members)), key=lambda i: (
        not _wants_item(members[i], prose),
        members[i]['item'] == 'LEFTOVERS', -bulk(members[i])))
    taken = set()
    for i in order:
        for cand in _item_candidates(members[i]):
            if cand not in taken:
                taken.add(cand)
                members[i]['item'] = cand
                break
        else:
            raise ValueError(f"{members[i]['sp']}: no free held item")


def _groups():
    for t in TEAMS:
        for g in [t] + list(t.get('variants') or []):
            yield g['members'], t.get('blurb', '') + g.get('blurb', '')
    for c in COMBOS:
        yield c['pair'], c.get('html', '')


for _members, _prose in _groups():
    dedupe_items(_members, _prose)
    _items = [m['item'] for m in _members]
    assert len(set(_items)) == len(_items), f'duplicate held item in {[m["sp"] for m in _members]}'


# Obtainability exceptions: species the Pokédex marks as unobtainable.
UNOBTAINABLE = {'SUDOWOODO'}


def _move_title(mv):
    return 'Will-O-Wisp' if mv == 'WILL_O_WISP' else mv.replace('_', ' ').title()


RELEARNER = 'Move Relearner (Fallarbor Town or Artisan Cave, 1 Heart Scale)'


def _spec(mv):
    return mv if isinstance(mv, tuple) else (mv, None)


def validate(member, item_keys):
    """Raise ValueError unless the set is legal in this hack. Returns per-move details.

    Egg moves are always fine: this hack's Move Relearner also offers a Pokémon's egg moves
    (FLAG_EGG_MOVES_TUTOR, src/move_relearner.c). An egg move that breeding can't deliver
    (no father, or two egg moves no single father knows) must name a non-egg fallback,
    written as (move, fallback), which is shown when hovering the move."""
    D = cov.load()
    sp = member['sp']
    info = D['species'].get(sp)
    if not info:
        raise ValueError(f'{sp}: unknown species')
    if sp in UNOBTAINABLE:
        raise ValueError(f'{sp}: unobtainable')
    if member['ability'] not in info['abilities']:
        raise ValueError(f'{sp}: ability {member["ability"]} not in {sorted(info["abilities"])}')
    if 'ITEM_' + member['item'] not in item_keys:
        raise ValueError(f'{sp}: item {member["item"]} has no source in-game')
    specs = [_spec(x) for x in member['moves']]
    if len(specs) != 4 or len({mv for mv, _ in specs}) != 4:
        raise ValueError(f'{sp}: needs 4 distinct moves')

    def detail_for(mv):
        how = D['learn'][sp].get(mv)
        if not how:
            raise ValueError(f'{sp} cannot learn {mv}')
        return dict(move=mv, type=D['moves'][mv]['type'], power=D['moves'][mv]['power'], how=list(how))

    moves, egg_only = [], []
    for mv, alt in specs:
        d = detail_for(mv)
        if 'Egg move' in d['how']:
            d['chain'] = egg_chain(sp, mv)
            if d['how'] == ['Egg move']:
                egg_only.append(d)
                if not d['chain']:
                    d['warn'] = 'No Pokémon in this hack can pass it down by breeding.'
        if alt:
            fb = detail_for(alt)
            if fb['how'] == ['Egg move']:
                raise ValueError(f'{sp}: fallback {alt} is itself egg-only')
            d['alt'] = fb
        moves.append(d)
    breedable = [d for d in egg_only if d['chain']]
    if len(breedable) > 1:
        groups = _egg_groups(_family(sp)[1])
        together = any(all(_knows_directly(f, d['move']) for d in breedable) for f in D['species']
                       if D['species'][f]['can_be_male'] and D['species'][f]['egg_groups'] & groups)
        if not together:
            for d in breedable:
                if d.get('alt'):
                    others = [x['move'] for x in breedable if x is not d]
                    d['warn'] = ('No single father can pass it down together with '
                                 + ', '.join(_move_title(o) for o in others) + '.')
            if not any(d.get('warn') for d in breedable):
                raise ValueError(f'{sp}: egg moves {[d["move"] for d in breedable]} need a fallback')
    for d in moves:
        if d.get('warn') and not d.get('alt'):
            raise ValueError(f'{sp}: {d["move"]} needs a fallback ({d["warn"]})')
    return moves


if __name__ == '__main__':
    import generate_items as gi, io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        keys = {o['key'] for o in gi.build_data()[0]}
    for t in TEAMS + COMBOS:
        for mem in t.get('members') or t['pair']:
            for d in validate(mem, keys):
                if 'chain' in d or d.get('warn'):
                    print(f"{mem['sp']:10} {d['move']:14} breed: {' → '.join(d['chain'] or [])} {d.get('warn', '')} alt={d.get('alt', {}).get('move')}")
    print('all sets valid')
