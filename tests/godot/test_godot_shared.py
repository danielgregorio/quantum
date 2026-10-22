"""Shared fields in Godot (PLAN_GAMES_3.md, Phase 5): what a player types and sends reaches every machine.

One small game for two, on two machines or one (with the lockstep, or the rollback). Its room has a local menu (the menu of whoever plays at this
machine) with one shared field: what is sent there becomes the sender's name, on every machine on the same
tick, and the last line said. While the field is typed in, the keys type: "w" does not walk.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession
from quantum.runtime.godot_replay import replay, replay_peers, tape_from_holds, typed_at

REPO = Path(__file__).resolve().parents[2]

WALKERS = '''    <qg:character id="p1" controller="topdown" player="1" sheet="c" x="60" y="80" hitbox="14x14" speed="60" />
    <qg:character id="p2" controller="topdown" player="2" sheet="c" x="180" y="80" hitbox="14x14" speed="60"
                  if="{net_players() >= 2}" />'''

CHAT = '''<q:application id="chat" type="game">
  <qg:spritesheet name="c" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:multiplayer players="2" start="room" {rollback} />
  <qg:scene name="room" width="240" height="160">
    <q:set name="names" type="array" value='["", ""]' />
    <q:set name="line" value="" />
    <q:set name="said" value="" />
    <q:set name="last" value="0" type="number" />
{walkers}
    <qg:menu local="true" position="bottom-center" size="8">
      <qg:field bind="line" label="Say" shared="true" max-length="20">
        <q:set name="names" index="{{sender - 1}}" value="{{text}}" />
        <q:set name="said" value="{{'P' + str(sender) + ': ' + text}}" />
        <q:set name="last" value="{{sender}}" />
      </qg:field>
    </qg:menu>
  </qg:scene>
</q:application>
'''


def _build(tmp_path_factory, godot, rollback: str = '') -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    folder = tmp_path_factory.mktemp('chat')
    src = folder / 'chat.q'
    # the rollback takes no walkers (their physics is not rolled back): the menu and the state only
    src.write_text(CHAT.format(rollback=rollback, walkers='' if rollback else WALKERS), encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(folder / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


@pytest.fixture(scope='module')
def chat(tmp_path_factory, godot):
    return _build(tmp_path_factory, godot)


@pytest.fixture(scope='module')
def chat_rollback(tmp_path_factory, godot):
    return _build(tmp_path_factory, godot, 'rollback="6"')


def _says(text: str, at: int = 20):
    """A player's tape: the field chosen (select), then `text` typed and sent on tick `at`."""
    return typed_at(tape_from_holds([('select', 2, 3)]), at, text)


def test_alone_what_is_sent_is_the_state_on_the_next_tick(chat, godot):
    tape = typed_at(_says('wAna\n'), 10, 'www')               # w typed: the keys type, they do not walk
    tape = {**tape, **tape_from_holds([('up', 40, 60)])}       # after Enter they play again
    state = replay(chat, 39, tape=tape)['room']
    assert (state['names'], state['said'], state['last'], state['line']) == (['wwwwAna', ''], 'P1: wwwwAna', 1,
                                                                           'wwwwAna')
    assert state['nodes']['p1']['y'] == 80
    assert replay(chat, 70, tape=tape)['room']['nodes']['p1']['y'] < 70


def test_a_field_that_is_not_sent_changes_nothing(chat, godot):
    state = replay(chat, 40, tape=typed_at(tape_from_holds([('select', 2, 3)]), 10, 'Ana'))['room']
    assert (state['names'], state['line'], state['last']) == (['', ''], '', 0)   # a draft, until Enter


def test_an_agent_types_and_sends(chat, godot):
    with PlaySession(chat, binary=godot) as game:
        game.act(tap=['select'], ticks=2)
        typing = game.act(text='Ana', ticks=2)
        field = [v for v in typing['screen'] if v['kind'] == 'menu'][0]['items'][0]
        assert field['typing'] and field['value'] == ''
        sent = game.act(text='\n', ticks=2)
        kinds = [e['kind'] for e in sent['events']]
        assert 'sent' in kinds and 'message' in kinds
        message = [e for e in sent['events'] if e['kind'] == 'message'][0]
        assert (message['sender'], message['text']) == (1, 'Ana')
        assert sent['state']['said'] == 'P1: Ana'
        assert ('type', 'Ana') in [e for v in game.tape()['tape'].values() for e in v]
        snap = game.snapshot()                                     # the typing is in the tape: it comes back
        game.act(tap=['select'], ticks=2)
        game.act(text='Bo\n', ticks=2)
        assert game.observe()['state']['said'] == 'P1: AnaBo'                 # on from where it was
        assert game.restore(snap)['state']['said'] == 'P1: Ana'


@pytest.mark.parametrize('game', ['chat', 'chat_rollback'])
def test_both_machines_get_both_names_on_the_same_tick(game, request, godot):
    project = request.getfixturevalue(game)
    states = replay_peers(project, 90, [_says('Ana\n'), _says('Bo\n', at=24)], binary=godot,
                          latency_ms=[0, 60] if game == 'chat_rollback' else None)
    assert states[0] == states[1]
    room = states[0]['room']
    assert room['names'] == ['Ana', 'Bo'] and room['said'] == 'P2: Bo' and room['last'] == 2
