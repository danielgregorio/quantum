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
from quantum.runtime.godot_play import PlayError, PlaySession, condition, reflex
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
        assert PlaySession.screen(start, 'hud')['items'] == ['0 potions', '0 keys']
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


def test_each_scene_has_its_music(rpg, godot):
    with PlaySession(rpg, binary=godot) as game:
        assert game.observe()['music'] == 'meadow'
        game.until('player.row == 7', hold=['down'])
        game.until('talking', hold=['right'])
        for _ in range(3):
            fight = game.until("scene == 'combat'", tap=['select'], max_ticks=10)
        assert fight['music'] == 'clash'
        assert {'kind': 'music', 'name': 'clash', 'tick': fight['tick'] - 1} in fight['events']
        fled = game.until("scene == 'exploration'", tap=['down'], max_ticks=10)
        fled = game.until("scene == 'exploration'", tap=['down'], max_ticks=10)
        fled = game.until("scene == 'exploration'", tap=['select'], max_ticks=10)   # Attack, Defend, Flee
        assert (fled['scene'], fled['music']) == ('exploration', 'meadow')


def test_the_game_in_the_players_language(rpg, godot):
    # the observation says what the screen shows, in the language it shows it in
    with PlaySession(rpg, binary=godot) as game:
        assert game.observe()['lang'] == ''                                  # the game's own texts
    with PlaySession(rpg, binary=godot, lang='pt') as game:
        seen = game.observe()
        assert seen['lang'] == 'pt'
        assert PlaySession.screen(seen, 'hud')['items'] == ['0 poções', '0 chaves']
        game.until('player.row == 7', hold=['down'])
        said = game.until('event:say', hold=['right'])
        assert PlaySession.screen(said, 'dialogue')['text'] == 'Ei, é uma boa hora para uma luta de JRPG, não acha?'
        assert [e['who'] for e in said['events'] if e['kind'] == 'say'] == ['DESCONHECIDO']
        for _ in range(3):
            fight = game.until("scene == 'combat'", tap=['select'], max_ticks=10)
        assert [i['button'] for i in PlaySession.screen(fight, 'menu')['items']] == ['Atacar', 'Defender', 'Poção', 'Fugir']
    with PlaySession(rpg, binary=godot, lang='fr') as game:                 # a language it has not: its own
        assert game.observe()['lang'] == ''


def test_the_lobby_and_the_board_in_the_players_language(pong, chess, godot):
    # a game declaring pt or es has the lobby's own phrases too: its buttons, its status line
    with PlaySession(pong, binary=godot, lang='pt') as game:
        menu = PlaySession.screen(game.observe(), 'menu')['items']
        assert [i.get('button') or i.get('field') for i in menu] == \
            ['Dois jogadores, um teclado', 'Criar uma partida', 'Endereço', 'Entrar', 'Assistir', 'Cancelar',
             'Opções', 'Idioma: Português']
    with PlaySession(chess, binary=godot, lang='es') as game:
        seen = game.until("scene == 'game'", tap=['select'], max_ticks=10)
        assert 'Juegan blancas - haz clic en una pieza y luego adónde va' in PlaySession.screen(seen, 'hud')['items']
        assert seen['state']['status'] == 'White to move - click a piece, then where it goes'   # the state stays as written


def test_the_language_button_shows_the_next_language(pong, godot):
    # the lobby's last button: English, then each of the game's languages, then English again
    with PlaySession(pong, binary=godot) as game:
        for _ in range(6):                                   # past the local game, Host, Address, Join, Watch, Options
            game.act(tap=['down'], ticks=2)
        shown = []
        for _ in range(3):
            seen = game.act(tap=['select'], ticks=2)
            menu = PlaySession.screen(seen, 'menu')['items']
            shown.append((seen.get('lang'), menu[0]['button'], menu[-1]['button']))
        assert shown == [('pt', 'Dois jogadores, um teclado', 'Idioma: Português'),
                         ('es', 'Dos jugadores, un teclado', 'Idioma: Español'),
                         ('', 'Two players, one keyboard', 'Language: English')]
        assert [e['lang'] for e in seen['events'] if e['kind'] == 'language'] == ['']


def test_the_language_chosen_is_kept_for_the_next_run(pong, godot, tmp_path):
    from quantum.runtime.godot_replay import replay, tape_from_holds
    to_the_button = [('down', t, t + 1) for t in (1, 3, 5, 7, 9, 11)]
    replay(pong, 16, tape_from_holds(to_the_button + [('select', 13, 14)]), binary=godot, persist_dir=tmp_path)
    assert (tmp_path / 'quantum-language.txt').read_text() == 'pt'
    # the next run starts in pt, so the button shows the one after it
    replay(pong, 16, tape_from_holds(to_the_button + [('select', 13, 14)]), binary=godot, persist_dir=tmp_path)
    assert (tmp_path / 'quantum-language.txt').read_text() == 'es'


def test_the_fight_comes_out_of_black(rpg, godot):
    with PlaySession(rpg, binary=godot) as game:
        game.until('player.row == 7', hold=['down'])
        game.until('talking', hold=['right'])
        fight = game.until("scene == 'combat'", tap=['select'], max_ticks=10)
        for _ in range(2):
            fight = game.until("scene == 'combat'", tap=['select'], max_ticks=10)
        assert fight['scene'] == 'combat'
        assert PlaySession.screen(fight, 'fade')['dark'] > 0.9                 # fade="0.4": 24 ticks of it
        assert 0.4 < PlaySession.screen(game.act(ticks=12), 'fade')['dark'] < 0.6
        clear = game.act(ticks=14)
        assert PlaySession.screen(clear, 'fade') is None
        assert PlaySession.screen(clear, 'menu')['items'][0]['button'] == 'Attack'


def test_an_agent_leaves_keeps_first_room_by_the_map_and_the_view(keep, godot):
    """Phase 2's check: the way out found on the map, the player found in the view, nothing else."""
    from collections import deque
    with Counted(keep, binary=godot) as game:
        assert game.until("scene == 'room-1'", tap=['select'], max_ticks=5)['scene'] == 'room-1'   # New game
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
        assert game.requests < 13


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


# --- phase 5: reflexes ---

@pytest.fixture(scope='module')
def pong(godot, tmp_path_factory) -> Path:
    return _build(godot, tmp_path_factory, 'pong')


@pytest.fixture(scope='module')
def drift(godot, tmp_path_factory) -> Path:
    return _build(godot, tmp_path_factory, 'drift')


def _paddles(left, right):
    """Reflexes that take each paddle to a height and keep it there."""
    rules = []
    for paddle, up, down, to in (('left', 'up', 'down', left), ('right', 'p2_up', 'p2_down', right)):
        rules += [{'when': f'{paddle}.y > {to + 3}', 'hold': [up]}, {'when': f'{paddle}.y < {to - 3}', 'hold': [down]}]
    return rules


def _arrives(x, y, vx, vy, at_x, low=4, high=396):
    """The ball's height when it reaches at_x, bouncing off the ceiling and the floor."""
    span = high - low
    y = (y + vy * (at_x - x) / vx - low) % (2 * span)
    return low + (y if y <= span else 2 * span - y)


def _rally(game, returns):
    """An agent plays both paddles: after each hit it works out where the ball will
    arrive, and hands the paddles to the reflexes until the next hit. Answers the
    hits, in order, and what ended the rally."""
    hits = []
    while len(hits) < returns:
        b = game.act(ticks=1)
        x0 = x1 = b['state']['named']['ball']['x']
        while x1 == x0:                                                      # two glances: where it goes
            a, b = b, game.act(ticks=1)
            x0, y0 = a['state']['named']['ball']['x'], a['state']['named']['ball']['y']
            x1, y1 = b['state']['named']['ball']['x'], b['state']['named']['ball']['y']
        nodes = b['state']['nodes']
        if x1 < x0:
            rules = _paddles(_arrives(x1, y1, x1 - x0, y1 - y0, nodes['left']['x'] + 8), 200)
        else:
            rules = _paddles(200, _arrives(x1, y1, x1 - x0, y1 - y0, nodes['right']['x'] - 8))
        seen = game.until(['event:touch with=ball', 'event:touch with=wall'], reflex=rules, max_ticks=3000)
        touched = [e for e in seen['events'] if e['kind'] == 'touch' and e.get('with') in ('ball', 'wall')]
        if any(e['with'] == 'wall' for e in touched):
            return hits, 'missed'
        hits += [e['who'] for e in touched]
    return hits, 'played'


def test_reflexes_are_a_condition_and_what_it_holds():
    assert condition('ball.y < left.y - 8') == {'path': 'ball.y', 'op': '<', 'value': {'path': 'left.y', 'plus': -8}}
    assert condition('ship.x >= target.x') == {'path': 'ship.x', 'op': '>=', 'value': {'path': 'target.x'}}
    assert condition("scene != combat") == {'path': 'scene', 'op': '!=', 'value': 'combat'}   # a bare word: a text
    assert reflex([{'when': 'ball.y > left.y + 4', 'hold': ['down']}, {'hold': ['jump']}]) == [
        {'hold': ['down'], 'when': {'path': 'ball.y', 'op': '>', 'value': {'path': 'left.y', 'plus': 4}}},
        {'hold': ['jump']}]                                                    # no condition: always


def test_a_reflex_follows_the_ball_every_tick(pong, godot):
    with PlaySession(pong, binary=godot) as game:
        court = game.act(tap=['select'], ticks=2)
        assert court['scene'] == 'court'
        follow = [{'when': 'ball.y < left.y - 2', 'hold': ['up']}, {'when': 'ball.y > left.y + 2', 'hold': ['down']}]
        set_only = game.act(ticks=0, reflex=follow)
        assert set_only['tick'] == court['tick']                               # ticks=0: set, nothing run
        seen = game.act(ticks=100)
        ball, left = seen['state']['named']['ball'], seen['state']['nodes']['left']
        assert abs(ball['y'] - left['y']) <= 4                                 # it went where the ball is
        assert seen['held'] == []                                              # the agent itself holds nothing
        still = game.act(ticks=60, reflex=[])['state']['nodes']['left']['y']
        assert game.act(ticks=60)['state']['nodes']['left']['y'] == still      # cleared: the paddle stays
        with pytest.raises(PlayError, match='no such action: fly'):
            game.act(reflex=[{'when': 'ball.y > 0', 'hold': ['fly']}])
        with pytest.raises(PlayError, match='a reflex is'):
            game.request({'op': 'act', 'reflex': [{'when': 'ball.y > 0'}]})


def test_an_agent_returns_ten_balls_in_a_row_in_pong(pong, godot):
    """Phase 5's check: the agent plays the strategy (where will the ball arrive?), the reflexes hold the paddles."""
    with Counted(pong, binary=godot) as game:
        game.act(tap=['select'], ticks=2)
        hits, ended = _rally(game, 20)
        assert ended == 'played' and hits.count('left') >= 10, hits         # the ball never got past
        assert hits == ['left', 'right'] * (len(hits) // 2)
        assert game.requests < 80                                            # 3 a hit: a glance, a glance, an until


def test_a_session_with_reflexes_replays_as_its_tape(pong, godot):
    with PlaySession(pong, binary=godot) as game:
        game.act(tap=['select'], ticks=2)
        hits, _ = _rally(game, 4)
        snap = game.snapshot()
        played = game.act(ticks=120)
        assert snap['reflex']['rules'] and len(hits) == 4
        back = game.restore(snap)                                            # the reflexes come back with it
        assert back['tick'] == snap['ticks']
        again = game.act(ticks=120)
        assert again['state']['nodes'] == played['state']['nodes']
        tape = game.tape()
    replayed = replay(pong, tape['ticks'], tape=tape['tape'], binary=godot)['court']
    assert replayed['nodes'] == again['state']['nodes'] and replayed['named'] == again['state']['named']


def test_an_agent_clears_drifts_first_wave(drift, godot):
    """Phase 5's check: every few ticks the agent picks the lowest drone; the reflexes steer under it and fire."""
    def kills(seen):
        return sum(1 for e in seen.get('events', []) if e['kind'] == 'death')

    with PlaySession(drift, binary=godot) as game:
        firing = game.act(hold=['jump'], ticks=420)                           # firing alone, not moving
        assert kills(firing) < 8
    with Counted(drift, binary=godot) as game:
        seen, dead = game.observe(), 0
        while dead < 8 and seen['tick'] < 600:
            drones = [w for w in seen['state']['where'] if w[0] == 'enemy' and w[2] > 0]
            to = max(drones, key=lambda w: w[2])[1] if drones else 128
            seen = game.until(['event:death', 'changed lives'], max_ticks=12, reflex=[
                {'hold': ['jump']},
                {'when': f'ship.x < {to - 2}', 'hold': ['right']},
                {'when': f'ship.x > {to + 2}', 'hold': ['left']}])
            dead += kills(seen)
        assert dead == 8 and seen['tick'] < 500                              # before the tanks come
        assert (seen['state']['game']['score'], seen['state']['game']['lives']) == (800, 3)
        assert game.requests < 60


# --- phase 6: live, and playing with people ---

def test_a_live_game_does_not_wait(rpg, godot):
    import time
    with PlaySession(rpg, binary=godot, live=True) as game:
        first = game.observe()['tick']
        time.sleep(1.0)
        later = game.observe()['tick']
        assert 30 <= later - first <= 120                                    # about 60 ticks a second, by the clock
        walked = game.until('player.row == 7', hold=['down'], max_ticks=600)
        assert walked['stopped'] == 'condition'
        with pytest.raises(PlayError, match='no tape'):
            game.tape()
        with pytest.raises(PlayError, match='cannot go back'):
            game.restore({'ticks': 0, 'held': [], 'tape': {}})


def _person(godot, project: Path, port: int, ticks: int, tmp: Path):
    """A person at the other machine: a Godot that hosts the game and plays for `ticks` ticks,
    in real time, pressing nothing."""
    import subprocess
    from quantum.runtime.godot_replay import REPLAY_SCRIPT
    (tmp / 'tape.json').write_text('{}')
    (tmp / 'persist').mkdir()
    return subprocess.Popen(
        [str(godot), '--headless', '--path', str(project), '-s', str(REPLAY_SCRIPT), '--', f'--ticks={ticks}',
         f'--out={tmp / "state.json"}', f'--persist-dir={tmp / "persist"}', f'--tape={tmp / "tape.json"}',
         f'--q-host={port}'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def test_an_agent_joins_a_persons_pong_and_never_misses(pong, godot, tmp_path):
    """Phase 6's check, on the desktop: the agent takes the second seat of a networked game that runs at
    the person's speed; reflexes keep its paddle on the ball, as no request could, every tick."""
    import time
    from quantum.runtime.godot_replay import free_port
    port = free_port()
    person = _person(godot, pong, port, 1500, tmp_path)
    try:
        time.sleep(1.0)                                                      # the person hosts first
        with PlaySession(pong, binary=godot, join=f'127.0.0.1:{port}') as game:
            seen = game.until("net.status == 'playing'", max_ticks=900)
            assert (seen['scene'], seen['net']['player']) == ('court', 2)
            game.act(ticks=0, reflex=[{'when': 'ball.y < right.y - 2', 'hold': ['up']},
                                      {'when': 'ball.y > right.y + 2', 'hold': ['down']}])
            touches = []
            while seen['net']['status'] == 'playing':
                seen = game.until(['event:touch with=ball', 'event:touch with=wall', "net.status != 'playing'"],
                                  max_ticks=1200)
                touches += [e['who'] if e['with'] == 'ball' else 'wall' for e in seen.get('events', [])
                            if e['kind'] == 'touch' and e['with'] in ('ball', 'wall')]
            assert not seen['net']['desync']
        heading, missed = 'left', []                                         # the ball starts towards the person
        for t in touches:
            if t == 'wall':
                missed.append('the agent' if heading == 'right' else 'the person')
                heading = 'left'                                             # back to the middle, as it was
            else:
                heading = 'right' if t == 'left' else 'left'
        assert touches.count('right') >= 2 and 'the agent' not in missed, touches
    finally:
        person.wait(timeout=60)


# --- PLAN_GAMES_3.md, Phase 5: who sits where ---

@pytest.fixture(scope='module')
def bricks(godot, tmp_path_factory) -> Path:
    return _build(godot, tmp_path_factory, 'bricks')


def test_player_n_presses_that_players_keys_by_player_ones_names(pong, godot):
    with PlaySession(pong, binary=godot) as game:
        game.act(tap=['select'], ticks=2)                                    # two players, one keyboard
        before = game.act(ticks=1)['state']['nodes']
        after = game.act(hold=['up'], player=2, ticks=30)['state']['nodes']
        assert after['right']['y'] < before['right']['y'] - 20               # p2_up: the right paddle
        assert after['left']['y'] == before['left']['y']
        down = game.act(ticks=30, reflex=[{'hold': ['down']}], player=2)['state']['nodes']
        assert down['right']['y'] > after['right']['y'] + 20                 # a reflex's actions too
        assert game.tape()['reflex']['rules'][0]['hold'] == ['p2_down']
        with pytest.raises(PlayError, match='no such action: p3_up'):
            game.act(hold=['up'], player=3)
        with pytest.raises(PlayError, match='player= is 1 or more'):
            game.act(hold=['up'], player=0)


def test_agents_sit_in_the_seats_they_ask_for_in_bricks(bricks, godot):
    """Four machines, three of them agents that ask for seats 3, 4 and 2 in that order; one more
    asks for seat 3 and is turned away. The third gives its name, which every machine shows;
    each plays its own paddle by player 1's names."""
    from quantum.runtime.godot_replay import free_port
    port = free_port()
    address = f'127.0.0.1:{port}'
    with PlaySession(bricks, binary=godot, host=port) as host:
        assert host.until("net.status == 'hosting'", max_ticks=600)['net']['player'] == 1
        third = PlaySession(bricks, binary=godot, join=address, seat=3)
        try:
            assert third.until('net.player == 3', max_ticks=600)['net']['player'] == 3
            with PlaySession(bricks, binary=godot, join=address, seat=3) as late:
                assert late.until("net.status == 'failed'", max_ticks=600)['net']['player'] == 0
            with PlaySession(bricks, binary=godot, join=address, seat=4) as fourth, \
                    PlaySession(bricks, binary=godot, join=address, seat=2) as second:
                seats = [s.until("net.status == 'playing'", max_ticks=900)['net']['player']
                         for s in (host, second, third, fourth)]
                assert seats == [1, 2, 3, 4]
                third.act(tap=['select'], ticks=20)                          # who is who: its name box
                third.act(text='Tri\n', ticks=20)
                named = host.until("event:message", max_ticks=600)          # sent to every machine
                said = [e for e in named['events'] if e['kind'] == 'message'][0]
                assert (said['sender'], said['text']) == (3, 'Tri')
                assert 'Tri' in [i for v in named['screen'] if v['kind'] == 'hud' for i in v['items']]
                host.act(tap=['jump'], ticks=2)                              # player 1 starts the level
                assert third.until("scene == 'level'", max_ticks=600)['scene'] == 'level'
                x = third.act(ticks=1)['state']['nodes']['p3']['x']
                moved = third.act(hold=['right'], player=3, ticks=40)['state']['nodes']
                assert moved['p3']['x'] > x + 40
                with pytest.raises(PlayError, match='sits in seat 4, not 2'):
                    fourth.act(hold=['right'], player=2)
                seen = host.until(f'p3.x > {x + 40}', max_ticks=600)                # every machine plays it
                assert seen['stopped'] == 'condition' and not seen['net']['desync']
        finally:
            third.close()


def test_a_seat_is_for_one_who_joins():
    with pytest.raises(PlayError, match='seat= is the seat a joining session asks for'):
        PlaySession('.', seat=2)
