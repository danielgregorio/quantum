"""Chess — the rules in the language — replayed in Godot, click by click.

projects/chess/chess.q is compiled and driven by tapes of clicks: the cursor
on a square (62 px cells), then select, from the player whose turn it is.
The board in the state is row-major from the eighth rank.
"""

import shutil
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import cursor_at, replay, replay_peers

CHESS = Path(__file__).resolve().parents[2] / 'projects' / 'chess' / 'chess.q'
FILES = 'abcdefgh'


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src_dir = tmp_path_factory.mktemp('chess')
    shutil.copytree(CHESS.parent, src_dir / 'chess', ignore=shutil.ignore_patterns('godot'))
    app = QuantumParser(use_cache=False).parse_file(str(src_dir / 'chess' / 'chess.q'))
    out = compile_game(app, str(src_dir / 'chess-godot'), source_dir=str(src_dir / 'chess'))
    assert check_project(Path(out), binary=godot) == []
    return Path(out)


def square(name):
    """'e4' -> (row, col) with row 0 the eighth rank."""
    return 8 - int(name[1]), FILES.index(name[0])


def game(moves, peers=False):
    """Tapes from moves in order ('e2e4', 'e7e5', ...): white clicks, then black clicks, 10 ticks each.
    One tape, or two (white's and black's) for the peers."""
    white, black = {}, {}
    tick = 10
    for i, move in enumerate(moves):
        player = 1 if i % 2 == 0 else 2
        for name in (move[:2], move[2:]):
            row, col = square(name)
            tape = white if (player == 1 or not peers) else black
            cursor_at(tape, tick, col * 62 + 31, row * 62 + 31)
            action = 'select'   # on one machine the same mouse plays both colours; peers each their own
            tape.setdefault(tick + 2, []).append((action, True))
            tape.setdefault(tick + 4, []).append((action, False))
            tick += 10
    if peers:
        return white, black, tick
    # alone: the title's "Two players, one board" on tick 0, everything else one tick later
    local = {0: [('select', True)], 2: [('select', False)]}
    for t, events in white.items():
        local.setdefault(t + 1, []).extend(events)
    return local, tick + 1


def board_of(state):
    return {f'{FILES[i % 8]}{8 - i // 8}': p for i, p in enumerate(state['board']) if p}


def test_the_scholars_mate(godot, project):
    tape, end = game(['e2e4', 'e7e5', 'd1h5', 'b8c6', 'f1c4', 'g8f6', 'h5f7'])
    s = replay(project, end, tape=tape)['game']
    assert s['status'] == 'Checkmate - White wins' and s['finished'] is True
    assert s['things'] == {'marker': 1, 'piece': 31, 'last': 2, 'check': 1}     # no dots left
    assert s['named']['check_mark'] == {'x': 279.0, 'y': 31.0}                   # glowing under e8's king
    assert (s['named']['last_from'], s['named']['last_to']) == ({'x': 465.0, 'y': 217.0}, {'x': 341.0, 'y': 93.0})
    b = board_of(s)
    assert b['f7'] == 'wQ' and b['c4'] == 'wB' and b['c6'] == 'bN' and 'h5' not in b and b['e8'] == 'bK'


def test_a_click_that_is_not_a_move_does_nothing(godot, project):
    tape, end = game(['e2e5', 'e7e6'])        # e2 cannot reach e5; then it is still white's turn
    s = replay(project, end, tape=tape)['game']
    assert s['turn'] == 'w' and board_of(s)['e2'] == 'wP' and board_of(s)['e7'] == 'bP'
    assert s['status'] == 'White to move'


def test_en_passant_takes_the_pawn_that_passed(godot, project):
    tape, end = game(['e2e4', 'a7a6', 'e4e5', 'd7d5', 'e5d6'])
    s = replay(project, end, tape=tape)['game']
    b = board_of(s)
    assert b['d6'] == 'wP' and 'd5' not in b and 'e5' not in b and s['things']['piece'] == 31


def test_castling_moves_the_rook_too(godot, project):
    tape, end = game(['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1c4', 'f8c5', 'e1g1'])
    s = replay(project, end, tape=tape)['game']
    b = board_of(s)
    assert b['g1'] == 'wK' and b['f1'] == 'wR' and 'e1' not in b and 'h1' not in b
    assert s['named']['mark'] == {'x': -100.0, 'y': -100.0}


def test_a_pawn_on_the_last_rank_is_a_queen(godot, project):
    tape, end = game(['h2h4', 'g7g5', 'h4g5', 'h7h6', 'g5h6', 'g8f6', 'h6h7', 'h8g8', 'h7g8'])
    s = replay(project, end, tape=tape)['game']
    assert board_of(s)['g8'] == 'wQ' and s['things']['piece'] == 29
    assert s['status'] == 'Black to move'


def test_white_and_black_on_two_peers(godot, project):
    white, black, end = game(['e2e4', 'e7e5', 'd1h5', 'b8c6', 'f1c4', 'g8f6', 'h5f7'], peers=True)
    peers = replay_peers(project, end, [white, black], binary=godot)
    assert peers[0] == peers[1]
    assert peers[0]['game']['status'] == 'Checkmate - White wins'


def test_a_picked_piece_shows_where_it_may_go(godot, project):
    tape, _ = game(['e2e4', 'e7e5', 'g1f3', 'b8c6'])
    # then white picks the knight on f3, and leaves it picked
    row, col = square('f3')
    cursor_at(tape, 100, col * 62 + 31, row * 62 + 31)
    tape.setdefault(102, []).append(('select', True))
    tape.setdefault(104, []).append(('select', False))
    s = replay(project, 110, tape=tape)['game']
    assert (s['sel_r'], s['sel_c']) == (5.0, 5.0)
    # g1, d4, h4 empty; e5 holds a black pawn (a ring); g5 empty
    assert s['things']['dot'] == len(s['legal']) == 5
    dots = sorted((w[1], w[2]) for w in s['where'] if w[0] == 'dot')
    assert (row - 2) * 62 + 31 in [y for _, y in dots]


def test_black_moves_with_the_same_mouse_on_one_machine(godot, project):
    tape, end = game(['e2e4', 'e7e5'])            # every click is player 1's select
    s = replay(project, end, tape=tape)['game']
    assert s['turn'] == 'w' and board_of(s)['e5'] == 'bP' and s['status'] == 'White to move'
