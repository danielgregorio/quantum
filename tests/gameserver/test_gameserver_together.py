"""The game server, Phase 4 of PLAN_GAME_SERVER.md: players together.

The den's chat reaches whom each channel says (say: seven tiles, yell: thirty, help: everyone, party: the party),
a whisper one player, and stars the worst words; more than three lines in five seconds are refused. A party is
invited, joined and left. A trade moves both sides once and whole, even when both accept in the same tick; a new
offer takes back the acceptances. A quest is taken, done and rewarded on the ledger.
"""

from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.gameserver import GameServerError, World, read_world
from quantum.runtime.gameserver.session import WorldSession, serve_world

DEN = Path(__file__).resolve().parent / 'worlds' / 'den' / 'den.server.q'
TMX = DEN.parent / 'den.tmx'


def den_with(tmp_path, more='', changes=()):
    source = DEN.read_text().replace('</q:gameserver>', more + '\n  </q:gameserver>')
    for old, new in changes:
        assert old in source
        source = source.replace(old, new)
    (tmp_path / 'den.tmx').write_text(TMX.read_text())
    path = tmp_path / 'den.server.q'
    path.write_text(source)
    return World(read_world(QuantumParser(use_cache=False).parse_file(str(path)), str(path)))


def den():
    return World(read_world(QuantumParser(use_cache=False).parse_file(str(DEN)), str(DEN)))


class Table:
    """A den with players in it, and what each heard."""

    def __init__(self, world, *names):
        self.world, self.seq = world, 0
        self.heard = {n: [] for n in names}
        self.tick([('join', n) for n in names])

    def tick(self, inputs=()):
        out = self.world.step(list(inputs))
        for event in self.world.events:
            for account in (event.accounts or ([event.to] if event.to else [])):
                self.heard.setdefault(account, []).append(event.message)
        return out

    def do(self, account, command, **args):
        self.seq += 1
        out = self.tick([('cmd', account, self.seq, command, args)])
        refused = out.refused.get(account)
        return refused[0]['reason'] if refused else 'ok'

    def chats(self, account):
        return [m['value'] for m in self.heard[account] if m['name'] == 'chat']

    def place(self, account, x, y):
        hero = self.world.entities[f'hero:{account}']
        hero['at'] = {'x': x, 'y': y}
        self.world.reindex([hero['id']])


def test_a_hero_is_welcomed_by_the_world():
    table = Table(den(), 'ana')
    assert table.chats('ana') == [{'channel': 'system', 'from': 'world', 'text': 'Welcome to the den, ana.'}]


def test_each_channel_reaches_whom_it_says():
    table = Table(den(), 'ana', 'bo', 'cy')
    table.place('bo', 9, 3)                                      # six tiles from ana at (3, 3)
    table.place('cy', 40, 27)                                    # far away
    for n in table.heard:
        table.heard[n].clear()
    assert table.do('ana', 'chat', channel='say', text='hello') == 'ok'
    line = {'channel': 'say', 'from': 'ana', 'text': 'hello'}
    assert table.chats('ana') == [line] and table.chats('bo') == [line] and table.chats('cy') == []
    assert table.do('ana', 'chat', channel='help', text='where are the rats?') == 'ok'
    assert table.chats('cy')[-1]['text'] == 'where are the rats?'
    assert table.do('ana', 'whisper', to='cy', text='psst') == 'ok'
    assert table.chats('cy')[-1] == {'channel': 'whisper', 'from': 'ana', 'to': 'cy', 'text': 'psst'}
    assert table.chats('bo')[-1]['text'] == 'where are the rats?'          # bo heard no whisper
    assert table.do('ana', 'chat', channel='trade', text='x') == "There is no channel 'trade' (say, yell, party, help)."
    for _ in range(50):                                          # five seconds: three lines more may be said
        table.tick()
    assert table.do('ana', 'chat', channel='party', text='x') == 'You are in no party.'


def test_the_chat_stars_the_worst_words_and_holds_its_limit():
    table = Table(den(), 'ana', 'bo')
    assert table.do('ana', 'chat', channel='say', text='what the FUCK, bo') == 'ok'
    assert table.chats('bo')[-1]['text'] == 'what the ****, bo'
    assert table.do('ana', 'chat', channel='say', text='\x07' + 'a' * 300) == 'ok'
    assert table.chats('bo')[-1]['text'] == 'a' * 200
    assert table.do('ana', 'chat', channel='say', text='three') == 'ok'
    assert table.do('ana', 'chat', channel='say', text='four') == 'Too fast.'   # 3 in 5 seconds
    assert table.do('ana', 'chat', channel='say', text='   ') == 'Too fast.'


def test_a_party_is_invited_joined_heard_and_left():
    table = Table(den(), 'ana', 'bo', 'cy', 'di')
    world = table.world
    assert table.do('ana', 'party-accept', who='bo') == 'No one invited you.'
    assert table.do('ana', 'party-invite', who='bo') == 'ok'
    assert table.do('bo', 'party-accept', who='ana') == 'ok'
    ana, bo = world.entities['hero:ana'], world.entities['hero:bo']
    assert ana['party'] == bo['party'] == 'party-1'
    assert [e['id'] for e in world.party_of(ana)] == ['hero:ana', 'hero:bo']
    table.place('bo', 40, 27)
    assert [e['id'] for e in world.party_near(ana, 10)] == ['hero:ana']
    assert table.do('bo', 'chat', channel='party', text='far, but heard') == 'ok'
    assert table.chats('ana')[-1]['text'] == 'far, but heard' and table.chats('cy')[-1:] != [
        {'channel': 'party', 'from': 'bo', 'text': 'far, but heard'}]
    table.do('ana', 'party-invite', who='cy')
    table.do('cy', 'party-accept', who='ana')
    assert table.do('ana', 'party-invite', who='di') == 'The party is full.'
    assert table.do('bo', 'party-leave') == 'ok' and bo['party'] == ''
    table.do('cy', 'party-leave')
    assert ana['party'] == '' and world.parties == {}                    # one alone is no party


def test_a_trade_accepted_by_both_at_once_moves_once_and_whole():
    table = Table(den(), 'ana', 'bo')
    world = table.world
    ana, bo = world.entities['hero:ana'], world.entities['hero:bo']
    table.do('ana', 'buy', item='cheese')                                  # ana: 8 gold, a cheese
    assert table.do('ana', 'trade-offer', who='bo', gold=0, items={'cheese': 1}) == 'ok'
    assert table.do('bo', 'trade-offer', who='ana', gold=5, items={}) == 'ok'
    table.seq += 2
    both = table.tick([('cmd', 'ana', table.seq - 1, 'trade-accept', {'who': 'bo'}),
                       ('cmd', 'bo', table.seq, 'trade-accept', {'who': 'ana'})])
    assert both.acks == {'ana': [table.seq - 1], 'bo': [table.seq]}
    assert (ana['gold'], ana['bag'], bo['gold'], bo['bag']) == (13, {}, 5, {'cheese': 1})
    assert table.do('ana', 'trade-accept', who='bo') == 'No trade with them.'   # done: nothing more to accept
    assert world.trades == {} and world.balanced() == {}
    assert any(m['name'] == 'trade' and m['value'].get('done') for m in table.heard['bo'])


def test_a_new_offer_takes_back_the_acceptances_and_not_enough_is_refused():
    table = Table(den(), 'ana', 'bo')
    world = table.world
    table.do('ana', 'trade-offer', who='bo', gold=3, items={})
    table.do('bo', 'trade-accept', who='ana')
    assert world.trades['hero:ana|hero:bo']['accepted'] == ['hero:bo']
    table.do('ana', 'trade-offer', who='bo', gold=4, items={})
    assert world.trades['hero:ana|hero:bo']['accepted'] == []
    assert table.do('ana', 'trade-offer', who='bo', gold=50, items={}) == 'Not enough gold.'
    assert table.do('ana', 'trade-offer', who='bo', gold=1, items={'sword': 1}) == 'Not enough sword.'
    table.do('ana', 'trade-accept', who='bo')
    table.do('ana', 'buy', item='sword')                                   # spends 8 of her 10
    assert table.do('bo', 'trade-accept', who='ana') == 'Not enough gold.'   # she has 2 now: refused whole
    assert (world.entities['hero:ana']['gold'], world.entities['hero:bo']['gold']) == (2, 10)
    table.tick([('leave', 'bo')])
    assert world.trades == {} and world.balanced() == {}


def test_a_quest_taken_done_and_rewarded(tmp_path):
    world = den_with(tmp_path, changes=[('goal="kill:Rat:2"', 'goal="kill:Rat:1"')])
    table = Table(world, 'ana')
    assert table.do('ana', 'turn-in') == 'It is not done.'
    assert table.do('ana', 'take-quest', name='dragons') == 'No such quest.'
    assert table.do('ana', 'take-quest', name='rats') == 'ok'
    assert table.do('ana', 'take-quest', name='rats') == 'One quest at a time.'
    ana = world.entities['hero:ana']
    rat = next(e for e in world.entities.values() if e['kind'] == 'Rat')
    table.do('ana', 'go', to={'x': rat['at']['x'] - 3, 'y': rat['at']['y']})
    for _ in range(60):
        table.tick()
    table.do('ana', 'attack', who=rat['id'])
    while rat['id'] in world.entities:
        table.tick()
    assert ana['quest'] == {'name': 'rats', 'done': 1} and world.quest_done(ana)
    gold = ana['gold']
    assert table.do('ana', 'turn-in') == 'ok'
    assert ana['gold'] == gold + 20 and ana['xp'] == 50 and ana['bag'].get('sword') == 1 and ana['quest'] == {}
    assert world.books['made']['gold']['q:command turn-in'] == 20 and world.balanced() == {}


def test_a_chat_line_reaches_a_player_through_the_protocol():
    with serve_world(DEN) as server:
        with WorldSession(server.url, 'ana') as ana, WorldSession(server.url, 'bo') as bo:
            welcome = ana.observe()['events']
            assert {'name': 'chat', 'value': {'channel': 'system', 'from': 'world',
                                              'text': 'Welcome to the den, ana.'}} in welcome
            ana.act(send=[('chat', {'channel': 'say', 'text': 'hi bo'})], ticks=1)
            heard = [e['value'] for e in bo.observe()['events'] if e['name'] == 'chat']
            assert {'channel': 'say', 'from': 'ana', 'text': 'hi bo'} in heard


@pytest.mark.parametrize('more, says', [
    ('<q:command name="chat"></q:command>', "the world's chat has that command"),
    ('<q:quest name="q" title="Q" goal="slay:Rat" />', 'kill:Kind:n or bring:item:n'),
    ('<q:quest name="q" title="Q" goal="kill:Rat:2" reward="gold:many" />', 'its amount is a whole number'),
])
def test_what_together_refuses_in_a_file(tmp_path, more, says):
    with pytest.raises(GameServerError, match=says):
        den_with(tmp_path, more)
