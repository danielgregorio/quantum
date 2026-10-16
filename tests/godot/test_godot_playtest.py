"""The playtest job (PLAN_PLAY_PROTOCOL.md, phase 7).

The job hands each game to an agent, watches every call against the game's
goal, and writes a report and the session's tape. Here the agents are
scripted, so the job itself is what is tested: reached, stuck, out of
calls, and a reached goal's tape kept as a test. The Claude agent is driven
by a fake client: what it sends, and how it reads what comes back.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from quantum.runtime.playtest import (ClaudeAgent, OutOfCalls, PlayTools, goals, holds, playtest, report)

REPO = Path(__file__).resolve().parents[2]
PLAYTESTS = Path(__file__).parent / 'playtests'


def test_the_job_reads_conditions_as_the_driver_does():
    obs = {'scene': 'combat', 'state': {'turn': 'player', 'nodes': {'player': {'col': 4}}, 'named': {'ball': {'y': 10}},
                                        'game': {'outcome': 'won', 'lives': 3}},
           'screen': [{'kind': 'dialogue', 'text': 'Hi'}], 'events': [{'kind': 'touch', 'with': 'key'}]}
    assert holds("game.outcome == 'won'", obs) and holds('outcome == won', obs)
    assert holds('player.col >= 4', obs) and not holds('player.col > 4', obs)
    assert holds('ball.y < player.col + 7', obs)                               # another path, and a number added
    assert holds("dialogue.text == 'Hi'", obs) and holds('event:touch with=key', obs)
    assert holds({'all': ['lives == 3', "scene == 'combat'"]}, obs)
    assert not holds({'all': ['lives == 3', "scene == 'map'"]}, obs)
    assert holds(['nothing', 'turn'], obs) and not holds('nothing', obs)


def test_every_goal_names_a_condition_and_a_budget():
    found = goals(REPO / 'projects')
    assert {'rpg', 'keep', 'drift', 'hopper'} <= set(found)
    for game, goal in found.items():
        assert goal['say'] and goal['done'] and goal['calls'] > 0, game


def test_the_report_has_a_line_a_game():
    rows = [{'game': 'rpg', 'goal': 'win', 'result': 'reached', 'calls': 9, 'ticks': 700, 'tape': 'rpg.json', 'note': ''},
            {'game': 'keep', 'goal': 'leave', 'result': 'stuck', 'calls': 12, 'ticks': 90, 'tape': 'keep.json',
             'note': 'a | b'}]
    text = report(rows)
    assert '| rpg | win | **reached** | 9 | 700 | rpg.json |  |' in text
    assert 'a \\| b' in text and '1 of 2 reached.' in text and 'tests/godot/playtests/' in text


class Fight:
    """A scripted agent: the RPG's fight, as test_godot_play.py's agent wins it."""

    def play(self, run, goal, start):
        run.until('player.row == 7', hold=['down'])
        seen = run.until('talking', hold=['right'])
        while seen['scene'] == 'exploration':
            seen = run.act(tap=['select'], ticks=2)
        while True:
            if seen['state']['turn'] == 'player':
                seen = run.act(tap=['select'], ticks=2)
            else:
                seen = run.until(["turn == 'player'", 'changed scene'], max_ticks=120)


class Idle:
    def play(self, run, goal, start):
        while True:
            run.act(ticks=10)


class Walker:
    def play(self, run, goal, start):
        while True:
            run.act(hold=['down'], ticks=16)


def test_a_goal_reached_is_reported_with_its_tape(godot, tmp_path):
    tools = PlayTools(binary=godot)
    try:
        goal = goals(REPO / 'projects', ['rpg'])['rpg']
        row = playtest('rpg', goal, Fight(), tools, tmp_path)
    finally:
        tools.close()
    assert row['result'] == 'reached' and row['calls'] < goal['calls'], row
    saved = json.loads((tmp_path / 'rpg.json').read_text())
    assert (saved['game'], saved['done'], saved['result']) == ('rpg', goal['done'], 'reached')
    assert saved['ticks'] == row['ticks'] > 0
    assert not tools.sessions                                                # the job closed the game


def test_a_run_that_changes_nothing_is_stuck_and_one_with_no_calls_left_ends(godot, tmp_path):
    tools = PlayTools(binary=godot)
    try:
        stuck = playtest('rpg', {'say': 'win', 'done': "game.outcome == 'won'", 'calls': 60}, Idle(), tools, tmp_path)
        spent = playtest('rpg', {'say': 'win', 'done': "game.outcome == 'won'", 'calls': 3}, Walker(), tools, tmp_path)
    finally:
        tools.close()
    assert (stuck['result'], stuck['calls']) == ('stuck', 11)               # one call, then ten that changed nothing
    assert (spent['result'], spent['note']) == ('not reached', 'out of calls (3)')


@pytest.mark.parametrize('tape', sorted(PLAYTESTS.glob('*.json')), ids=lambda p: p.stem)
def test_a_goal_once_reached_is_reached_again(godot, tmp_path_factory, tape):
    """The tapes of tests/godot/playtests/: sessions that reached their goal, replayed."""
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    from quantum.runtime.godot_bin import check_project
    from quantum.runtime.godot_replay import replay
    saved = json.loads(tape.read_text())
    source = REPO / 'projects' / saved['game'] / f'{saved["game"]}.q'
    project = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(source)),
                                str(tmp_path_factory.mktemp(saved['game']) / 'godot'), source_dir=str(source.parent)))
    assert check_project(project, binary=godot) == []
    dumped = replay(project, saved['ticks'], tape={int(k): [tuple(e) for e in v] for k, v in saved['tape'].items()},
                    binary=godot)
    assert any(holds(saved['done'], {'scene': scene, 'state': state}) for scene, state in dumped.items()), saved['goal']


# --- the Claude agent, against a fake client ---

def _block(kind, **fields):
    return SimpleNamespace(type=kind, **fields)


class FakeClient:
    """Answers with the given responses in order, and keeps what it was sent."""

    def __init__(self, responses):
        self.sent = []
        self._responses = iter(responses)
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.sent.append({**kwargs, 'messages': list(kwargs['messages'])})
        return next(self._responses)


class FakeRun:
    def __init__(self):
        self.calls = []

    def until(self, cond, **kwargs):
        self.calls.append(('until', cond, kwargs))
        return {'tick': 40, 'scene': 'exploration', 'stopped': 'condition'}

    def act(self, **kwargs):
        self.calls.append(('act', kwargs))
        if kwargs.get('hold') == ['fly']:
            from quantum.runtime.godot_play import PlayError
            raise PlayError('no such action: fly')
        return {'tick': 41}

    def view(self):
        raise OutOfCalls()


def test_the_claude_agent_plays_through_the_tools_and_says_why_it_stops():
    client = FakeClient([
        SimpleNamespace(stop_reason='tool_use', content=[
            _block('text', text='Down to the opponent.'),
            _block('tool_use', id='t1', name='play_until', input={'condition': ['player.row == 7'], 'hold': ['down']}),
            _block('tool_use', id='t2', name='play_act', input={'hold': ['fly'], 'ticks': 4, 'nonsense': 1})]),
        SimpleNamespace(stop_reason='tool_use', content=[
            _block('tool_use', id='t3', name='give_up', input={'why': 'the door never opens'})]),
    ])
    run = FakeRun()
    note = ClaudeAgent(client=client).play(run, 'win the fight', {'session': 's1', 'tick': 0, 'scene': 'exploration'})
    assert note == 'the door never opens'
    assert run.calls == [('until', 'player.row == 7', {'hold': ['down']}), ('act', {'hold': ['fly'], 'ticks': 4})]
    first, second = client.sent
    assert first['model'] == 'claude-opus-5-5' and first['output_config'] == {'effort': 'medium'}
    assert first['fallbacks'] == 'default' and first['betas'] == ['server-side-fallback-2026-07-01']
    assert 'win the fight' in first['messages'][0]['content'] and '"session"' not in first['messages'][0]['content']
    assert {t['name'] for t in first['tools']} >= {'play_act', 'play_until', 'give_up'}
    results = second['messages'][-1]['content']                              # both results, in one message
    assert [r['tool_use_id'] for r in results] == ['t1', 't2']
    assert json.loads(results[0]['content'])['stopped'] == 'condition'
    assert results[1]['is_error'] and 'no such action: fly' in results[1]['content']


def test_the_job_stops_the_claude_agent_from_inside_a_tool():
    client = FakeClient([SimpleNamespace(stop_reason='tool_use', content=[
        _block('tool_use', id='t1', name='play_view', input={})])])
    with pytest.raises(OutOfCalls):
        ClaudeAgent(client=client).play(FakeRun(), 'win', {})
    refused = FakeClient([SimpleNamespace(stop_reason='refusal', content=[])])
    assert ClaudeAgent(client=refused).play(FakeRun(), 'win', {}) == 'the model declined to go on'
