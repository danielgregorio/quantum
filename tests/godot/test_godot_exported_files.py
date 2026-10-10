"""An exported game has no image, sound or font files, only Godot's imports of them.

The browser build and the desktop zips carry each asset as Godot imported it
(`.godot/imported/...`), not the file itself. The runtime read the files
directly, so on the site every picture was a magenta square, no tilemap was
drawn or solid, and a platformer's character fell through the level. Here a
project is imported, its asset files are deleted, as an export leaves them,
and the game must still load every picture, sound and font.
"""

import shutil
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project, run_godot, script_errors
from quantum.runtime.godot_replay import replay

PROJECTS = Path(__file__).resolve().parents[2] / 'projects'


def _exported_like(godot, tmp_path: Path, game: str) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = PROJECTS / game
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src / f'{game}.q')),
                            str(tmp_path / 'godot'), source_dir=str(src)))
    assert check_project(out, binary=godot) == []          # imports every asset
    gone = [f for f in out.rglob('*') if f.suffix in ('.png', '.ogg', '.wav', '.ttf')
            and '.godot' not in f.parts]
    assert gone, 'the game has assets to remove'
    for f in gone:
        f.unlink()                                          # what an export leaves out
    return out


def test_creeps_loads_its_pictures_sounds_and_font_from_the_imports(godot, tmp_path):
    out = _exported_like(godot, tmp_path, 'creeps')
    ran = run_godot(['--path', str(out), '--quit-after', '30'], godot)
    log = ran.stdout + ran.stderr
    assert 'cannot load' not in log and script_errors(log) == []


def test_robot_stands_on_its_tiles_with_the_files_gone(godot, tmp_path):
    out = _exported_like(godot, tmp_path, 'robot')
    state = replay(out, 60, binary=godot)['level']
    assert state['nodes']['robot']['y'] + 22.0 == pytest.approx(1354.0, abs=0.1)   # on the grass, not falling
    shutil.rmtree(out / '.godot' / 'imported')               # and without the imports, it is the failure it was
    ran = run_godot(['--path', str(out), '--quit-after', '5'], godot)
    assert 'cannot load the image' in ran.stdout + ran.stderr
