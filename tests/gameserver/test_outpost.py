"""Outpost, played (PLAN_GAME_SERVER.md, Phase 4: "Outpost is playable from start to end").

A bot plays the world as a player would, by its commands alone: Ana signs in (her ticket's name), walks from the
temple to Captain Rhea at the gate, takes the sewers' quest, goes down and kills ten rats (eating when she is hurt,
coming back from the temple when she falls), turns it in, buys a sword from Old Marta and wears it; then she hunts
wolves in the forest until she is of the level for the pelts, takes them, brings five furs and is paid. The world's
books hold all the while, and Marta's gold is what was paid her less what she paid.

Each is played twice: on world.py, and on the Rust engine's world (native_world.py, PLAN_WORLD_ENGINE.md's E3c),
which plays it by the same commands to the same end.
"""

from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.gameserver import World, read_world
from quantum.runtime.gameserver.native_world import NativeWorld, quantum_world
from quantum.runtime.gameserver.npc import answer_of

OUTPOST = Path(__file__).resolve().parents[2] / 'projects' / 'outpost' / 'outpost.server.q'
GATE = (40, 29)
FOODS = ('health-potion', 'meat', 'cheese')


class Player:
    """A bot at the keyboard: the world's commands, and nothing else of it but what its player sees."""

    def __init__(self, world, account, name):
        self.world, self.account, self.seq = world, account, 0
        self.step([('join', account, name)])

    @property
    def me(self):
        return self.world.entities[self.world.players[self.account]]

    def step(self, inputs=()):
        self.world.step(list(inputs))

    def do(self, command, **args):
        self.seq += 1
        out = self.world.step([('cmd', self.account, self.seq, command, args)])
        refused = out.refused.get(self.account)
        return refused[0]['reason'] if refused else 'ok'

    def talk(self, kind, text, mind):
        """Words to the NPC of a kind, and its answer as the server would bring it from the mind, a tick later."""
        npc = next(e for e in self.world.entities.values() if e['kind'] == kind)
        said = self.do('talk', npc=npc['id'], text=text)
        if said != 'ok':
            return said
        for ask in self.world.asks:
            self.world.step([('npc', ask['account'], ask['npc'], answer_of(mind(ask)))])
            return next(e.message['value'] for e in self.world.events
                        if e.message['name'] == 'npc-says' and self.account in (e.accounts or []))

    def at(self):
        return self.me['at']['x'], self.me['at']['y']

    def go(self, to, max_ticks=1500):
        """There (within a tile), as a click on the map: a way longer than one click goes by the gate."""
        by_gate = False
        for _ in range(max_ticks):
            x, y = self.at()
            if max(abs(x - to[0]), abs(y - to[1])) <= 1:
                return True
            if not self.me.get('_path'):
                said = self.do('go', to={'x': to[0], 'y': to[1]})
                if said == 'No way there.' and not by_gate:
                    by_gate = True
                    assert self.go(GATE, max_ticks) is True
                    continue
                assert said in ('ok', 'Too fast.'), said
            self.step()
        return False

    def go_near(self, kind):
        entity = next(e for e in self.world.entities.values() if e['kind'] == kind)
        return self.go((entity['at']['x'], entity['at']['y'] + 2))

    def hunt(self, kind, where, done, max_ticks=40000):
        """Attack the nearest of a kind, eat when hurt, and go back to where they are when there are none near."""
        for _ in range(max_ticks):
            me = self.me
            if done(me):
                return True
            if me['hp'] < me['max_hp'] * 0.4:
                food = next((f for f in FOODS if me['bag'].get(f)), None)
                if food:
                    self.do('use', item=food)
                    continue
            prey = self.world.entities.get(me['target']) if me['target'] else None
            if prey is None:
                prey = self.world.nearest(me, kind, 12)
                if prey is None:
                    self.go(where, 600)
                    self.step()
                    continue
                if self.do('attack', who=prey['id']) != 'ok':
                    self.step()
                    continue
            far = max(abs(prey['at']['x'] - me['at']['x']), abs(prey['at']['y'] - me['at']['y']))
            if far > 1 and not me.get('_path'):
                self.do('go', to=prey['at'])
            self.step()
        return False


@pytest.fixture(params=['python', 'native'])
def world(request):
    if request.param == 'native' and quantum_world is None:
        pytest.skip('the Rust engine is not built here (pip install ./native/world)')
    cls = World if request.param == 'python' else NativeWorld
    return cls(read_world(QuantumParser(use_cache=False).parse_file(str(OUTPOST)), str(OUTPOST)))


def hand(world, entity, fields):
    """The test's hand on an entity's numbers: world.py's dict, or the engine's world."""
    if isinstance(world, NativeWorld):
        world.hand(entity, fields)
    else:
        entity.update(fields)


def test_ana_plays_the_sewers_and_the_pelts(world):
    ana = Player(world, 'ana@site', 'Ana')
    me = ana.me
    assert (me['name'], me['level'], me['gold'], me['bag']) == ('Ana', 1, 20, {})
    marta = next(e for e in world.entities.values() if e['kind'] == 'Trader')
    assert ana.do('take-quest', name='sewers') == 'Captain Rhea is at the gate.'

    assert ana.go_near('Captain') and ana.do('take-quest', name='pelts') == 'Come back when you are stronger.'
    assert ana.do('take-quest', name='sewers') == 'ok'
    assert ana.hunt('Rat', (23, 52), lambda m: m['quest']['done'] >= 10)
    assert ana.go_near('Captain') and ana.do('turn-in') == 'ok'
    me = ana.me
    assert me['level'] == 2 and me['quest'] == {} and me['gold'] >= 80          # 20, 60 of the reward, the rats'

    marta_had = marta['gold']
    assert ana.go((30, 22)) and ana.do('buy', item='wooden-sword') == 'ok'       # across the counter
    assert ana.do('equip', item='wooden-sword') == 'ok' and me['attack'] == 5 + 1 + 3 and me['weapon'] == 'wooden-sword'
    assert marta['gold'] == marta_had + 50
    for _ in range(3):
        ana.do('buy', item='cheese')
        ana.step([])
        ana.step([])

    assert ana.hunt('Wolf', (60, 40), lambda m: m['level'] >= 3)
    assert ana.go_near('Captain') and ana.do('take-quest', name='pelts') == 'ok'
    assert ana.hunt('Wolf', (60, 40), lambda m: m['bag'].get('fur', 0) >= 5)
    gold = me['gold']
    assert ana.go_near('Captain') and ana.do('turn-in') == 'ok'
    assert me['gold'] == gold + 150 and 'fur' not in me['bag']                     # the furs went to Rhea
    assert world.books['spent']['fur'] == {'q:command turn-in': 5}
    assert world.balanced() == {} and world.errors == []


def test_a_party_of_four_brings_down_the_old_bear(world):
    """The end: the Old Bear, for a party. Four heroes of level 8 (as if they had hunted: the test's hand sets their
    numbers, and before each bear gives each three potions through the ledger, as Marta would sell them), Ana with
    the quest; they wake the bear in its cave and bring it down, every blow a tick of the world as the server runs it.
    A claw falls one bear in four: the party waits in the cave for the next (fifteen minutes), until one does. Ana
    brings it to Rhea: 800 gold and the iron sword."""
    party = [Player(world, f'{n}@site', n.title()) for n in ('ana', 'bo', 'cy', 'di')]
    ana = party[0]
    for p in party:
        hand(world, p.me, {'level': 8, 'max_hp': 170, 'hp': 170, 'attack': 15, 'defense': 9, 'xp': 2450})
    for p in party[1:]:
        assert ana.do('party-invite', who=p.account) == 'ok' and p.do('party-accept', who=ana.account) == 'ok'
    assert ana.go_near('Captain') and ana.do('take-quest', name='old-bear') == 'ok'
    for p in party:
        assert p.go((68, 11), 3000)                                                  # the cave's mouth
    bears, seq = 0, 1000
    while not any(p.me['bag'].get('bear-claw') for p in party):
        bear = next((e for e in world.entities.values() if e['kind'] == 'Bear'), None)
        if bear is None:
            world.step([])
            continue
        bears += 1
        assert bears <= 8, 'eight bears and no claw'
        world.source = 'the test\'s hand'
        for p in party:                                     # between two bears they bought potions from Marta
            world.give(p.me, 'health-potion', 3 - p.me['bag'].get('health-potion', 0), None, None, None)
        for _ in range(3000):
            if bear['id'] not in world.entities:
                break
            inputs = []
            for p in party:
                me = p.me
                seq += 1
                far = max(abs(bear['at']['x'] - me['at']['x']), abs(bear['at']['y'] - me['at']['y']))
                if me['hp'] < 70 and me['bag'].get('health-potion'):
                    inputs.append(('cmd', p.account, seq, 'use', {'item': 'health-potion'}))
                elif far > 1 and not me.get('_path'):                         # to it (a rock may hide it)
                    inputs.append(('cmd', p.account, seq, 'go', {'to': bear['at']}))
                elif me['target'] != bear['id']:
                    inputs.append(('cmd', p.account, seq, 'attack', {'who': bear['id']}))
            world.step(inputs)
        assert bear['id'] not in world.entities, 'the bear outlived three thousand ticks'
    holder = next(p for p in party if p.me['bag'].get('bear-claw'))
    if holder is not ana:                                   # the claw goes to Ana, by a trade
        assert holder.do('trade-offer', who=ana.account, gold=0, items={'bear-claw': 1}) == 'ok'
        assert ana.do('trade-offer', who=holder.account, gold=0, items={}) == 'ok'
        assert holder.do('trade-accept', who=ana.account) == 'ok' and ana.do('trade-accept', who=holder.account) == 'ok'
    gold = ana.me['gold']
    assert ana.go_near('Captain') and ana.do('turn-in') == 'ok'
    assert ana.me['gold'] == gold + 800 and ana.me['bag'].get('iron-sword') == 1 and 'bear-claw' not in ana.me['bag']
    assert world.balanced() == {} and world.errors == []


def test_marta_and_rhea_act_by_their_tools_and_the_rules_hold(world):
    """Phase 5 in Outpost: a scripted mind (no model) for each. Rhea gives what she is asked for, and the world
    gives only what its rules allow: the bear's quest to a hero of level 1 is refused, the sewers' is given. Marta
    sells meat at the price named, within a fifth of the list's, and not below it."""
    ana = Player(world, 'ana@site', 'Ana')

    def rhea(ask):
        quest = 'old-bear' if 'bear' in ask['text'] else 'sewers'
        return {'say': f'The {quest}, then.', 'do': [{'tool': 'give-quest', 'args': {'quest': quest}}],
                'remember': 'Wants work.'}
    assert ana.go_near('Captain')
    assert ana.talk('Captain', 'Give me the bear!', rhea) == {'npc': 'rhea-1', 'who': 'Captain Rhea',
                                                            'text': 'The old-bear, then.', 'did': []}
    assert ana.me['quest'] == {}
    for _ in range(40):                                                    # talk is once every three seconds
        ana.step()
    said = ana.talk('Captain', 'Any work for a newcomer?', rhea)
    assert said['did'] == ['give-quest'] and ana.me['quest'] == {'name': 'sewers', 'done': 0}

    def marta(ask):
        price = int(''.join(c for c in ask['text'] if c.isdigit()))
        return {'say': f'{price} it is.', 'do': [{'tool': 'npc-sell', 'args': {'item': 'meat', 'price': price}}]}
    assert ana.go((30, 22))
    assert ana.talk('Trader', 'Meat for 3?', marta)['did'] == []          # the list says 5: 4 at the least
    for _ in range(40):
        ana.step()
    assert ana.talk('Trader', 'Meat for 4?', marta)['did'] == ['npc-sell']
    assert ana.me['bag'] == {'meat': 1} and ana.me['gold'] == 16
    assert world.balanced() == {} and world.errors == []
