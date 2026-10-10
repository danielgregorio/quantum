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
    out_dir = tmp_path_factory.mktemp(game)    # its assets are found from the project, and above it
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(PROJECTS / game / f'{game}.q')),
                            str(out_dir / 'godot'), source_dir=str(PROJECTS / game)))
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
        assert PlaySession.screen(start, 'hud')['items'] == ['Potions 0', 'Keys 0']
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
        said = PlaySession.screen(talking, 'dialogue')
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
            menu = PlaySession.screen(seen, 'menu')
            labels = [item.get('button') for item in menu['items']]
            want = labels.index('Attack')
            if menu['focus'] != want:
                seen = game.act(tap=['up'], ticks=2)
                continue
            seen = game.act(tap=['select'], ticks=2)
        seen = game.until('talking', max_ticks=30)                     # back on the map, the opponent speaks
        assert seen['scene'] == 'exploration'
        assert PlaySession.screen(seen, 'dialogue')['text'] == 'Congratulations, you won!'
        seen = game.act(tap=['select'], ticks=2)
        assert seen['state']['game']['outcome'] == '' and not seen['state'].get('talking')
        assert game.requests < 40, game.requests                       # 16 when this was written


def test_chess_is_played_with_the_cursor(chess, godot):
    with PlaySession(chess, binary=godot) as game:
        title = game.observe()
        menu = PlaySession.screen(title, 'menu')
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


# --- phase 2: perception ---

@pytest.fixture(scope='module')
def keep(godot, tmp_path_factory) -> Path:
    return _build(godot, tmp_path_factory, 'keep')


def test_the_view_draws_the_screen_as_text(rpg, godot):
    with PlaySession(rpg, binary=godot) as game:
        seen = game.view()
        assert seen['cell'] == 64 and seen['origin'] == [0, 0]
        assert seen['view'][4] == '#..P..##k........###'                       # the player, the key, the rocks
        assert seen['view'][7] == '###.........o.....##'                       # the opponent
        assert seen['legend'] == {'P': ['player'], 'k': ['key'], 'o': ['opponent'], 'p': ['potion']}
        assert game.map()['cells'][4] == '#.....##.........###'                 # the map alone: no one on it


def test_the_events_of_a_fight_tell_each_hit(rpg, godot):
    with PlaySession(rpg, binary=godot) as game:
        walked = game.until('player.row == 7', hold=['down'])
        assert walked['map']['cells'][7] == '###...............##'                # the session's first map
        met = game.until('event:say', hold=['right'])
        kinds = [e['kind'] for e in met['events']]
        order = [kinds.index(k) for k in ('touch', 'say', 'pause')]
        assert order == sorted(order)                                          # walked into it, it spoke, all stopped
        said = next(e for e in met['events'] if e['kind'] == 'say')
        assert (said['who'], said['dialogue']) == ('UNKNOWN', 'npc')
        assert 'map' not in met                                                # the same scene: no map again
        for _ in range(3):
            seen = game.act(tap=['select'], ticks=2)                         # the last line opens the fight
        assert seen['scene'] == 'combat' and seen['map'] is None              # a new scene: its map, here none
        assert {'kind': 'scene', 'name': 'combat', 'tick': seen['tick'] - 2} in seen['events']
        hit = game.until(["turn == 'player'", 'changed scene'], tap=['select'], max_ticks=120)
        sets = {e['name']: (e['from'], e['to']) for e in hit['events'] if e['kind'] == 'set'}
        assert sets['foe_life'] == (7, 5) and sets['life'] == (10, 8)          # 2 dealt; 3 taken, less 1 armor
        assert [e for e in hit['events'] if e['kind'] == 'choose'] == [
            {'kind': 'choose', 'shown': True, 'button': 'Attack', 'tick': hit['events'][0]['tick']}]
        assert not seen.get('events_dropped')


def test_an_agent_leaves_keeps_first_room_by_the_map_and_the_view(keep, godot):
    """Phase 2's check: the way out found on the map, the player found in the view, nothing else."""
    from collections import deque
    with Counted(keep, binary=godot) as game:
        cells = game.map()['cells']
        seen = game.view()
        tile = int(seen['cell'])
        start = next((x + seen['origin'][0], y + seen['origin'][1])
                     for y, row in enumerate(seen['view']) for x, ch in enumerate(row) if ch in '@P')
        rows, cols = len(cells), len(cells[0])
        exits = {(x, y) for y in range(rows) for x in range(cols)
                 if cells[y][x] == '.' and (x in (0, cols - 1) or y in (0, rows - 1))}
        came = {start: None}
        todo = deque([start])
        while todo:                                                          # the shortest way to an opening
            at = todo.popleft()
            if at in exits:
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (at[0] + dx, at[1] + dy)
                if 0 <= nxt[0] < cols and 0 <= nxt[1] < rows and cells[nxt[1]][nxt[0]] == '.' and nxt not in came:
                    came[nxt] = at
                    todo.append(nxt)
        path = [at]
        while came[path[-1]] is not None:
            path.append(came[path[-1]])
        path.reverse()
        names = {(1, 0): ('right', 'x', '>='), (-1, 0): ('left', 'x', '<='),
                 (0, 1): ('down', 'y', '>='), (0, -1): ('up', 'y', '<=')}
        i = 0
        seen = game.observe()
        while seen['scene'] == 'room-1' and i < len(path) - 1:
            step = (path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])
            j = i + 1                                                         # run on while the way goes on straight
            while j < len(path) - 1 and (path[j + 1][0] - path[j][0], path[j + 1][1] - path[j][1]) == step:
                j += 1
            key, axis, op = names[step]
            centre = (path[j][0] if axis == 'x' else path[j][1]) * tile + tile // 2
            seen = game.until([f'player.{axis} {op} {centre}', 'changed scene'], hold=[key], max_ticks=600)
            i = j
        if seen['scene'] == 'room-1':                                         # at the opening: on, out of the room
            seen = game.until('changed scene', hold=[names[step][0]], max_ticks=120)
        assert seen['scene'] == 'room-2', seen['scene']
        assert game.requests < 12


@pytest.mark.skipif(shutil.which('xvfb-run') is None, reason='frame needs a virtual display (xvfb-run)')
def test_a_frame_is_the_picture_on_the_screen(rpg, godot, tmp_path):
    with PlaySession(rpg, binary=godot, frames=True) as game:
        game.act(ticks=5)
        shot = game.frame(tmp_path / 'shot.png')
        assert (shot['width'], shot['height']) == (1280, 720)
        png = Path(shot['frame']).read_bytes()
        assert png[:8] == b'\x89PNG\r\n\x1a\n'
        assert len(png) > 50_000                     # a drawn map: one colour over 1280x720 is a few KB
    with PlaySession(rpg, binary=godot) as game:
        with pytest.raises(PlayError, match='headless'):
            game.frame(tmp_path / 'none.png')


# --- phase 3: branching, and every session is a tape ---

def _to_the_fight(game):
    game.until('player.row == 7', hold=['down'])
    game.until('talking', hold=['right'])
    seen = game.observe()
    while seen['scene'] == 'exploration':
        seen = game.act(tap=['select'], ticks=2)
    return seen


def test_a_snapshot_is_come_back_to_and_branches_from(rpg, godot):
    with PlaySession(rpg, binary=godot) as game:
        fight = _to_the_fight(game)
        assert fight['scene'] == 'combat'
        snap = game.snapshot()
        here = game.observe()
        attacked = game.until(["turn == 'player'", 'changed scene'], tap=['select'], max_ticks=120)
        back = game.restore(snap)
        assert back['stopped'] == 'replayed' and back['tick'] == snap['ticks'] and back['events'] == []
        assert back['state'] == here['state'] and back['screen'] == here['screen']   # where it was, exactly
        game.act(tap=['down'], ticks=2)                                       # the other branch: Defend
        defended = game.until(["turn == 'player'", 'changed scene'], tap=['select'], max_ticks=120)
        assert (attacked['state']['foe_life'], attacked['state']['life']) == (5, 8)
        assert (defended['state']['foe_life'], defended['state']['life']) == (7, 9)   # 3 less armor 2
        game.restore(snap)                                                     # and the first branch again
        again = game.until(["turn == 'player'", 'changed scene'], tap=['select'], max_ticks=120)
        assert again['state'] == attacked['state'] and again['tick'] == attacked['tick']


def test_what_is_held_stays_held_across_a_restore(rpg, godot):
    with PlaySession(rpg, binary=godot) as game:
        game.act(press=['down'], ticks=10)
        snap = game.snapshot()
        assert snap['held'] == ['down']
        back = game.restore(snap)
        assert back['held'] == ['down']
        walked = game.act(ticks=40)                                            # still walking down
        assert walked['state']['nodes']['player']['row'] == 8                  # 50 ticks held: 4 steps down


def test_a_session_saved_as_a_tape_replays_as_a_test(rpg, godot, tmp_path):
    """Phase 3's check: a session played by looking is a regression test as it is."""
    import json
    with PlaySession(rpg, binary=godot) as game:
        seen = _to_the_fight(game)
        while seen['scene'] == 'combat':
            if seen['state']['turn'] == 'player':
                seen = game.act(tap=['select'], ticks=2)
            else:
                seen = game.until(["turn == 'player'", 'changed scene'], max_ticks=120)
        seen = game.until('talking', max_ticks=30)
        saved = json.loads(game.save_tape(tmp_path / 'won.json').read_text())
    assert saved['ticks'] == seen['tick']
    tape = {int(k): [tuple(e) for e in v] for k, v in saved['tape'].items()}
    replayed = replay(rpg, saved['ticks'], tape=tape, binary=godot)['exploration']
    assert replayed['talking'] == 'won' and replayed['game']['outcome'] == 'won'
    assert replayed['nodes'] == seen['state']['nodes'] and replayed['game'] == seen['state']['game']
