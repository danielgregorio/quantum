"""The play protocol (PLAN_PLAY_PROTOCOL.md), phase 1: a game an agent plays.

A ``PlaySession`` runs a built game step by step: the game waits for each
request, runs exactly the ticks asked for, and answers with what a player
would know by looking. The tests here are agents in miniature: each step is
decided from the last observation, not from a tape written beforehand.
"""

import shutil
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlayError, PlaySession, condition
from quantum.runtime.godot_replay import replay, tape_from_holds

PROJECTS = Path(__file__).resolve().parents[2] / 'projects'


def _build(godot, tmp_path_factory, game: str) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp(game)
    shutil.copytree(PROJECTS / game, src / game, ignore=shutil.ignore_patterns('godot'))
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src / game / f'{game}.q')),
                            str(src / 'godot'), source_dir=str(src / game)))
    assert check_project(out, binary=godot) == []
    return out


@pytest.fixture(scope='module')
def rpg(godot, tmp_path_factory) -> Path:
    return _build(godot, tmp_path_factory, 'rpg')


@pytest.fixture(scope='module')
def chess(godot, tmp_path_factory) -> Path:
    return _build(godot, tmp_path_factory, 'chess')


class Counted(PlaySession):
    """A session that counts the requests an agent needed."""
    requests = 0

    def request(self, req):
        if req.get('op') != 'end':
            self.requests += 1
        return super().request(req)


def test_the_game_waits_and_an_act_runs_exactly_its_ticks(rpg, godot):
    with PlaySession(rpg, binary=godot) as game:
        start = game.observe()
        assert (start['tick'], start['scene']) == (0, 'exploration')
        assert start['state']['nodes']['player'] == {'col': 3, 'row': 4, 'x': 224.0, 'y': 288.0, 'facing': [1, 0]}
        assert {'left', 'right', 'up', 'down', 'select'} <= set(start['controls'])
        assert PlaySession.view(start, 'hud')['items'] == ['Potions 0', 'Keys 0']
        assert game.observe()['tick'] == 0                          # observing runs nothing
        moved = game.act(hold=['right'], ticks=16)                   # a step is 15 ticks and the one that reads it
        assert (moved['tick'], moved['stopped']) == (16, 'ticks')
        assert (moved['state']['nodes']['player']['col'], moved['state']['nodes']['player']['x']) == (4, 288.0)
        assert game.act(ticks=30)['state']['nodes']['player']['col'] == 4   # released: it stays


def test_the_same_requests_give_what_a_replay_gives(rpg, godot):
    with PlaySession(rpg, binary=godot) as game:
        game.act(hold=['down'], ticks=40)
        game.act(ticks=10)
        played = game.act(hold=['right'], tap=['select'], ticks=60)
    replayed = replay(rpg, 110, tape=tape_from_holds([('down', 0, 40), ('right', 50, 110), ('select', 50, 51)]),
                      binary=godot)['exploration']
    assert played['state']['nodes'] == replayed['nodes'] and played['state']['game'] == replayed['game']


def test_until_stops_on_its_condition_or_its_ticks(rpg, godot):
    with PlaySession(rpg, binary=godot) as game:
        walked = game.until('player.row == 7', hold=['down'])
        assert walked['stopped'] == 'condition' and walked['state']['nodes']['player']['row'] == 7
        talking = game.until('talking', hold=['right'])              # right along row 7, into the opponent
        assert talking['stopped'] == 'condition' and talking['state']['talking'] == 'npc'
        said = PlaySession.view(talking, 'dialogue')
        assert (said['who'], said['text']) == ('UNKNOWN', "Hey, it's a good time to have a JRPG fight, right?")
        assert game.until('changed scene', max_ticks=30)['stopped'] == 'max_ticks'   # paused: nothing changes


def test_what_it_refuses(rpg, godot):
    with PlaySession(rpg, binary=godot) as game:
        with pytest.raises(PlayError, match='no such action: fly'):
            game.act(hold=['fly'])
        with pytest.raises(PlayError, match='no such request'):
            game.request({'op': 'teleport', 'x': 3})
        assert game.observe()['tick'] == 0                          # a refused request runs nothing
    assert condition('player.col == 11') == {'path': 'player.col', 'op': '==', 'value': 11}
    assert condition("scene != 'combat'") == {'path': 'scene', 'op': '!=', 'value': 'combat'}
    assert condition(['talking', 'changed scene']) == {'any': [{'path': 'talking', 'op': 'truthy'},
                                                               {'changed': 'scene'}]}


def test_an_agent_wins_the_rpg_by_looking(rpg, godot):
    """Phase 1's check: the RPG won by deciding each step from the last observation, in under 40 requests."""
    with Counted(rpg, binary=godot) as game:
        seen = game.observe()
        seen = game.until('player.row == 7', hold=['down'])          # the opponent stands on row 7
        seen = game.until('talking', hold=['right'])                  # walk into it
        while seen['scene'] == 'exploration' and seen['state'].get('talking'):
            seen = game.act(tap=['select'], ticks=2)                  # its lines, to the last
        seen = game.until("scene == 'combat'", max_ticks=10)
        while seen['scene'] == 'combat':
            if seen['state']['turn'] != 'player':
                seen = game.until(["turn == 'player'", 'changed scene'], max_ticks=120)
                continue
            menu = PlaySession.view(seen, 'menu')
            labels = [item.get('button') for item in menu['items']]
            want = labels.index('Attack')
            if menu['focus'] != want:
                seen = game.act(tap=['up'], ticks=2)
                continue
            seen = game.act(tap=['select'], ticks=2)
        seen = game.until('talking', max_ticks=30)                     # back on the map, the opponent speaks
        assert seen['scene'] == 'exploration'
        assert PlaySession.view(seen, 'dialogue')['text'] == 'Congratulations, you won!'
        seen = game.act(tap=['select'], ticks=2)
        assert seen['state']['game']['outcome'] == '' and not seen['state'].get('talking')
        assert game.requests < 40, game.requests                       # 16 when this was written


def test_chess_is_played_with_the_cursor(chess, godot):
    with PlaySession(chess, binary=godot) as game:
        title = game.observe()
        menu = PlaySession.view(title, 'menu')
        assert menu['items'][menu['focus']]['button'] == 'Two players, one board'
        board = game.act(tap=['select'], ticks=2)
        assert board['scene'] == 'game'

        def square(name):   # 62 px squares, a8 at the top left
            return ('abcdefgh'.index(name[0]) * 62 + 31, (8 - int(name[1])) * 62 + 31)

        def move(a, b):
            for name in (a, b):
                game.act(cursor=square(name), ticks=2)
                seen = game.act(tap=['select'], ticks=4)
            return seen

        before = board['state']['board']
        after = move('e2', 'e4')
        e2, e4 = 6 * 8 + 4, 4 * 8 + 4
        assert after['state']['board'][e4] == before[e2] and not after['state']['board'][e2]
        after = move('e7', 'e5')                                      # the same mouse plays black
        assert after['state']['board'][3 * 8 + 4] == before[1 * 8 + 4]
