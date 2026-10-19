"""Delve, the dungeon showcase, replayed in Godot.

projects/delve/delve.q is compiled into a temporary directory and driven by
input tapes. Play alone is the title's first button: selected on tick 0,
crypt 1 starts after a fade, by tick 30 (CRYPT_1). The delver walks 70 px/s
(1.17 px a tick); crypt 1's wall is column 8 (x 144..162), its lever at
(81, 171). The whole delve, down to the vault, is a playtest tape replayed by
test_godot_playtest.py (tests/godot/playtests/delve.json); its first 800
ticks reach crypt 2 here.
"""

import json
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession
from quantum.runtime.godot_replay import replay, replay_peers, tape_from_holds

REPO = Path(__file__).resolve().parents[2]
DELVE = REPO / 'projects' / 'delve' / 'delve.q'
CRYPT_1 = 30
# down to the lever's row, then right into it
TO_THE_LEVER = [('select', 0, 1), ('down', CRYPT_1, CRYPT_1 + 62), ('right', CRYPT_1 + 62, CRYPT_1 + 82)]


@pytest.fixture(scope='module')
def delve(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    out = tmp_path_factory.mktemp('delve') / 'godot'
    compile_game(QuantumParser(use_cache=False).parse_file(str(DELVE)), str(out), source_dir=str(DELVE.parent))
    assert check_project(out, binary=godot) == []
    return out


def stored_tape(ticks: int) -> dict:
    saved = json.loads((Path(__file__).parent / 'playtests' / 'delve.json').read_text())
    return {int(k): [tuple(e) for e in v] for k, v in saved['tape'].items() if int(k) < ticks}


def skeletons(crypt: dict) -> list:
    return [v for k, v in sorted(crypt['named'].items()) if k.startswith('skeleton')]


def test_alone_one_delver_goes_down(delve, godot):
    crypt = replay(delve, CRYPT_1, tape_from_holds([('select', 0, 1)]), binary=godot)['crypt-1']
    assert list(crypt['nodes']) == ['p1']                       # the second delver is there only over the network
    assert crypt['game'] == {'message': 'A SEALED WALL. A LEVER MUST OPEN IT.',
                             'q_items': {'heart': 5, 'gem': 0}, 'q_gone': []}
    assert crypt['things'] == {'enemy': 2, 'gem': 3, 'lever': 1, 'stairs': 1}


def test_the_lever_opens_the_wall_and_the_dead_come_through(delve, godot):
    walled = replay(delve, CRYPT_1 + 60, tape_from_holds(TO_THE_LEVER), binary=godot)['crypt-1']
    assert 'tiles' not in walled
    assert [s['x'] for s in skeletons(walled)] == [190.0, 190.0]   # walled off, they wait
    opened = replay(delve, CRYPT_1 + 260, tape_from_holds(TO_THE_LEVER), binary=godot)['crypt-1']
    assert opened['tiles'] == {'8,5': 12, '8,6': 12}                # rubble, walked on
    assert opened['game']['message'] == 'THE WALL OPENS. THE DEAD WAKE.'
    assert opened['things']['lever-on'] == 1
    assert all(s['x'] < 144 for s in skeletons(opened)), skeletons(opened)   # through the gap, after the delver


def test_two_delvers_over_the_network(delve, godot):
    # the networked delve starts in crypt 1 on both machines; the second delver walks into the lever
    peers = replay_peers(delve, 120, [None, tape_from_holds([('down', 0, 30), ('right', 30, 60)])], binary=godot)
    assert peers[0] == peers[1]
    crypt = peers[0]['crypt-1']
    assert set(crypt['nodes']) == {'p1', 'p2'}
    assert crypt['tiles'] == {'8,5': 12, '8,6': 12}


def test_each_crypt_entered_is_saved_and_continue_goes_back_there(delve, godot, tmp_path):
    there = replay(delve, 800, stored_tape(800), binary=godot, persist_dir=tmp_path)
    assert list(there) == ['crypt-2']
    saved = json.loads((tmp_path / 'quantum-save.json').read_text())
    assert saved['scene'] == 'crypt-2' and saved['game']['q_items']['gem'] == 3
    assert sorted(saved['game']['q_gone']) == ['crypt-1/gem-1', 'crypt-1/gem-2', 'crypt-1/gem-3']   # they stay gone
    # the next run: Continue is the third button now
    back = replay(delve, 40, tape_from_holds([('down', 1, 2), ('down', 4, 5), ('select', 7, 8)]),
                  binary=godot, persist_dir=tmp_path)
    assert list(back) == ['crypt-2'] and back['crypt-2']['game']['q_items']['gem'] == 3


def test_the_crushers_slide_the_same_every_time(delve, godot):
    tape = stored_tape(800)
    a = replay(delve, 790, tape, binary=godot)['crypt-2']['named']
    b = replay(delve, 820, tape, binary=godot)['crypt-2']['named']
    assert all(a[s]['y'] != b[s]['y'] for s in ('slab-1', 'slab-2', 'slab-3'))      # they move
    assert all(27 <= b[s]['y'] <= 189 for s in ('slab-1', 'slab-2', 'slab-3'))      # wall to wall
    assert replay(delve, 820, tape, binary=godot)['crypt-2']['named'] == b


def test_the_title_in_portuguese(delve, godot):
    game = PlaySession(delve, binary=godot, lang='pt')
    try:
        menu = PlaySession.screen(game.observe(), 'menu')
        assert [i['button'] for i in menu['items'] if i.get('shown', True)][:2] == ['Jogar sozinho', 'Jogar junto']
    finally:
        game.close()


def test_the_music_of_each_place(delve, godot):
    game = PlaySession(delve, binary=godot)
    try:
        assert game.observe()['music'] == 'torchlight'                      # the title
        assert game.until("scene == 'crypt-1'", tap=['select'], max_ticks=60)['music'] == 'crypt'
    finally:
        game.close()


def test_the_archer_keeps_its_distance_and_shoots(delve, godot):
    # crypt 3 on the stored run: the skeleton archer, made of parts, backs off and fires
    crypt = replay(delve, 3200, stored_tape(3200), binary=godot)['crypt-3']
    assert crypt['named']['archer']['doing'] == 'keep-distance'
    assert crypt['sounds'].count('twang') == 1
    assert crypt['game']['q_items']['heart'] == 3
