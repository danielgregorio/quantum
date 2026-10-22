"""Crates (projects/crates/crates.q), replayed in Godot.

The worker pushes crates onto pads in three rooms drawn in Tiled. The keys step it a cell at a time; a
click walks it there by the shortest way, up to a crate (and a click beside one pushes it), into the
foreman (who talks, typing, with a face, and offers a choice). A room solved opens its gate while the
camera goes to show it; in the yard the key on the pier is carried over the worker's head to the locked
gate. The moves are a solver's, found once for each room as drawn.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay

CRATES = Path(__file__).resolve().parents[2] / 'projects' / 'crates' / 'crates.q'
STEP = 11                                    # a step of step-frames="10", and the tick it is asked on
KEYS = {'R': 'right', 'L': 'left', 'U': 'up', 'D': 'down'}
DOCK = 'RRRRRRRRRRRRLLLLDLLLLDRRRRRRRR'
YARD = 'RRDRRRRDRRDRDLUUUURDDDLUUULDDRDDRRRDRULURDRULURDLLLLLULLDRRRRRRDRUULURRRR'
LOFT = 'RUURUURDRRRDDRRRUURRRDLLDRDRUUDDLLLLLLLULDDRDLULLLUUURRURDDRDDLLURRRRRRRRRRRRDRULLUUUULLDDDDLDRURD'
SHOT = 120                                   # the camera there and back (0.5 + 0.8 + 0.5 seconds), and a little


@pytest.fixture(scope='module')
def crates(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    out = tmp_path_factory.mktemp('crates') / 'godot'
    compile_game(QuantumParser(use_cache=False).parse_file(str(CRATES)), str(out), source_dir=str(CRATES.parent))
    assert check_project(out, binary=godot) == []
    return out


class Tape:
    """A tape written as a player plays: New game, then moves, clicks and taps, one after another."""

    def __init__(self):
        self.tape = {}
        self.t = 40
        self.tap('select', 2)                 # New game, the title's first button

    def at(self, t, *events):
        self.tape.setdefault(t, []).extend(list(e) for e in events)

    def tap(self, action, t=None):
        t = self.t if t is None else t
        self.at(t, (action, True))
        self.at(t + 1, (action, False))
        return self

    def moves(self, keys):
        for k in keys:
            self.tap(KEYS[k])
            self.t += STEP
        return self

    def click(self, x, y, steps):
        self.at(self.t, ('cursor', [x, y]), ('click', True))
        self.at(self.t + 1, ('click', False))
        self.t += steps * STEP
        return self

    def wait(self, ticks):
        self.t += ticks
        return self


def play(project, tape, godot, extra=0):
    state = replay(project, tape.t + extra, tape=tape.tape, binary=godot)
    scene = next(k for k in state if not k.startswith('_'))
    return scene, state[scene]


def where(room, tag):
    return sorted((x, y) for t, x, y, *_ in room['where'] if t == tag)


def test_the_dock_as_drawn_in_tiled(crates, godot):
    scene, dock = play(crates, Tape().wait(1), godot)
    assert scene == 'dock'
    assert dock['nodes']['worker'] == {'col': 0, 'row': 5, 'x': 8.0, 'y': 88.0, 'facing': [1, 0]}   # in the door
    assert where(dock, 'crate') == [(72.0, 88.0), (88.0, 120.0)]
    assert [w for w in dock['where'] if w[0] in ('gate', 'foreman')] == [
        ['foreman', 56.0, 56.0, 'waiting'], ['gate', 312.0, 88.0, 'shut']]


def test_a_click_walks_to_the_foreman_who_talks_and_offers_a_choice(crates, godot):
    tape = Tape().click(56, 56, 5)                       # four cells round, and into him
    _, talking = play(crates, tape, godot)
    assert talking['talking'] == 'foreman' and talking['nodes']['worker']['col'] == 3
    assert talking['game']['message'] == 'PUSH THE CRATES ONTO THE PADS.'   # the sign by the door, on the way
    tape.wait(70).tap('select').wait(80)                 # typed in, then the next line, typed in
    _, choosing = play(crates, tape, godot)
    assert choosing['talking'] == 'foreman' and choosing['line'] == 1
    tape.tap('select').wait(3)                           # the first choice: How do I push?
    _, how = play(crates, tape, godot)
    assert how['talking'] == 'how' and how['line'] == 0 and how['paused']


def test_a_far_crate_is_walked_up_to_and_a_near_one_pushed(crates, godot):
    tape = Tape().click(88, 120, 9)                      # the crate at (5, 7): the walk ends beside it
    _, beside = play(crates, tape, godot)
    assert where(beside, 'crate') == [(72.0, 88.0), (88.0, 120.0)]
    worker = beside['nodes']['worker']
    assert abs(worker['col'] - 5) + abs(worker['row'] - 7) == 1
    tape.click(88, 120, 2)                               # beside it: pushed away from the worker
    _, pushed = play(crates, tape, godot)
    away = (5 + (5 - worker['col'])) * 16 + 8, (7 + (7 - worker['row'])) * 16 + 8
    assert (float(away[0]), float(away[1])) in where(pushed, 'crate')


def test_r_starts_the_room_over(crates, godot):
    tape = Tape().moves('RRRRR')                         # out of the door, and the first crate two cells on
    _, pushed = play(crates, tape, godot)
    assert (104.0, 88.0) in where(pushed, 'crate')
    tape.tap('restart').wait(5)
    _, again = play(crates, tape, godot)
    assert where(again, 'crate') == [(72.0, 88.0), (88.0, 120.0)]
    assert again['nodes']['worker']['col'] == 0                          # in the door, which does not send it off


def test_the_dock_solved_opens_the_gate_and_the_camera_shows_it(crates, godot):
    tape = Tape().moves(DOCK).wait(20)
    _, shot = play(crates, tape, godot)
    assert shot['game']['message'] == 'THE GATE OPENS.'
    assert shot['paused'] and 'gate' not in shot['things']             # the scene waits while the camera is away
    tape.wait(SHOT)
    _, back = play(crates, tape, godot)
    assert not back.get('paused')
    tape.click(312, 88, 20)                              # through where the gate was
    scene, yard = play(crates, tape, godot)
    assert scene == 'yard' and yard['nodes']['worker']['col'] == 0


def test_the_three_rooms(crates, godot):
    tape = Tape().moves(DOCK).wait(SHOT).click(312, 88, 20)
    tape.moves(YARD).wait(SHOT).click(120, 24, 18)        # up the pier, into the key
    _, carrying = play(crates, tape, godot)
    worker, key = carrying['nodes']['worker'], carrying['named']['key']
    assert (key['x'], key['y']) == (worker['x'], worker['y'] - 10)      # over its head
    assert carrying['game']['message'] == 'GOT THE KEY.'
    tape.click(312, 88, 22)                              # beside the locked gate, and into it
    _, unlocked = play(crates, tape, godot)
    assert unlocked['game']['message'] == 'UNLOCKED.' and 'key' not in unlocked['things']
    tape.click(312, 88, 3)
    tape.moves(LOFT).wait(130)
    scene, loft = play(crates, tape, godot)
    assert scene == 'loft' and loft['game']['message'] == 'ALL STOWED. GOOD WORK.'
    assert loft['things'] == {'crate': 4, 'foreman': 1}                  # two crates, two barrels: crates too
    assert ['foreman', 136.0, 136.0, 'pleased'] in loft['where']
    tape.click(136, 136, 14).wait(120)                   # the foreman, pleased: the last words
    _, done = play(crates, tape, godot)
    assert done['talking'] == 'done'
    tape.tap('down').wait(2).tap('select').wait(40)       # Home time.
    scene, _ = play(crates, tape, godot)
    assert scene == 'title'


def test_the_same_tape_gives_the_same_dock(crates, godot):
    tape = Tape().click(88, 120, 9).click(88, 120, 2).moves('URRD')
    assert play(crates, tape, godot) == play(crates, tape, godot)
