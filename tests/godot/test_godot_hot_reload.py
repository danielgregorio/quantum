"""Hot reload (PLAN_GAMES_3.md, Phase 6): `quantum run game.q --watch`.

The game runs through quantum/runtime/godot_watch.gd, which records what is pressed. A new build makes it
write that tape and quit; started again on the new build with the tape, it plays it again quickly and is at the
same tick, under the new rules: the same inputs give the same game, as every replay test relies on. Here a
resumed session is checked against a replay of its tape, and a whole watch (a game, an edit of its .q, the
game again where it was) runs headless.
"""

import json
import shutil
import subprocess
import threading
import time
from pathlib import Path

from quantum.runtime.game_watch import WATCH_SCRIPT, GameWatch, build_game
from quantum.runtime.godot_replay import replay

REPO = Path(__file__).resolve().parents[2]

GAME = """<q:application id="watched" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="c" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <q:set name="count" value="0" type="number" />
  <qg:scene name="field" width="320" height="180">
    <q:set name="picked" value="0" type="number" />
    <qg:tilemap tileset="k" collision="true">
{floor}
    </qg:tilemap>
    <qg:character id="hero" controller="platformer" sheet="c" x="40" y="140" hitbox="14x20" />
    <qg:cursor id="aim" />
    <qg:on-select><q:set name="picked" value="{aim.x}" /></qg:on-select>
    <qg:timer every="1"><q:set name="count" value="{count + STEP}" /></qg:timer>
  </qg:scene>
</q:application>
""".replace('{floor}', '\n'.join([','.join(['0'] * 18)] * 8 + [','.join(['1'] * 18)] * 2))


def _game(folder: Path, step: int) -> Path:
    art = folder / 'assets' / 'kenney'
    art.mkdir(parents=True, exist_ok=True)
    for name in ('tilemap_packed.png', 'tilemap-characters_packed.png'):
        if not (art / name).exists():
            shutil.copy(REPO / 'assets' / 'kenney' / name, art / name)
    q = folder / 'watched.q'
    q.write_text(GAME.replace('STEP', str(step)), encoding='utf-8')
    return q


def _as_replay(tape: dict) -> dict:
    """A watched session's tape as the replay harness reads one: the mouse where it was is its cursor."""
    return {int(k): [('cursor', tuple(e[1])) if e[0] == 'mouse' else tuple(e) for e in v] for k, v in tape.items()}


def test_a_session_played_again_is_the_replay_of_its_tape(godot, tmp_path):
    project = build_game(_game(tmp_path, 1), say=lambda _: None, out=tmp_path / 'godot')
    tape = {'3': [['right', True]], '5': [['mouse', [100.0, 50.0]]], '10': [['select', True]],
            '11': [['select', False]], '40': [['right', False]]}
    (tmp_path / 'session.json').write_text(json.dumps({'ticks': 60, 'tape': tape}), encoding='utf-8')
    out, dump, stamp = tmp_path / 'out.json', tmp_path / 'dump.json', tmp_path / 'reload'
    (tmp_path / 'saves').mkdir()
    game = subprocess.Popen([str(godot), '--headless', '--path', str(project), '-s', str(WATCH_SCRIPT), '--',
                             f'--tape-out={out}', f'--stamp={stamp}', f'--resume={tmp_path / "session.json"}',
                             f'--dump={dump}', f'--persist-dir={tmp_path / "saves"}'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)                      # the tape played again quickly, then a moment of nobody playing
    stamp.write_text('reload', encoding='utf-8')
    assert game.wait(timeout=60) == 0
    session = json.loads(out.read_text(encoding='utf-8'))
    assert session['ticks'] > 60
    assert {k: v for k, v in session['tape'].items() if int(k) < 60} == tape   # recorded again as it was
    state = json.loads(dump.read_text(encoding='utf-8'))['field']
    replayed = replay(project, session['ticks'], tape=_as_replay(tape), binary=godot)['field']
    # the mouse where it was at tick 5, and the pointer moved on by right (16 a tick) as a real mouse lets it
    assert state['picked'] == 100.0 + 5 * 16
    assert state['nodes']['hero'] == replayed['nodes']['hero']                  # where the replay has it
    assert state['game']['count'] == replayed['game']['count'] > 60


def test_an_edit_brings_the_game_back_where_it_was_under_the_new_rules(godot, tmp_path):
    q = _game(tmp_path, 1)
    dump = tmp_path / 'dump.json'
    watch = GameWatch(q, lambda: build_game(q, say=lambda _: None, out=tmp_path / 'godot'), binary=godot, headless=True, poll=0.2,
                      say=lambda _: None, extra=[f'--dump={dump}'])
    runner = threading.Thread(target=watch.run, kwargs={'max_reloads': 1})
    runner.start()
    time.sleep(3)
    time.sleep(1.1)                                    # a newer modification time than the first build's
    _game(tmp_path, 2)                                 # the count goes up by 2 a tick now
    runner.join(timeout=120)
    assert watch.reloads == 1
    time.sleep(2)
    watch.stop_for_reload()
    session = json.loads(watch.tape.read_text(encoding='utf-8'))
    state = json.loads(dump.read_text(encoding='utf-8'))['field']
    assert session['ticks'] > 120                                               # it went on from where it was
    # every tick under the new rule, from the first: the new build played the session again
    replayed = replay(watch.project, session['ticks'], tape=_as_replay(session['tape']), binary=godot)['field']
    assert state['game']['count'] == replayed['game']['count'] and state['game']['count'] % 2 == 0


def test_a_build_refused_leaves_the_game_as_it_was(godot, tmp_path):
    q = _game(tmp_path, 1)
    said = []
    watch = GameWatch(q, lambda: build_game(q, say=said.append, out=tmp_path / 'godot'), binary=godot, headless=True, poll=0.2,
                      say=said.append)
    assert watch.build() is not None
    q.write_text(GAME.replace('STEP', 'nope +'), encoding='utf-8')
    assert watch.reload() is False and watch.reloads == 0
    assert any('the game plays on as it was' in s for s in said)
