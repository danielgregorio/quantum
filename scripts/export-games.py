#!/usr/bin/env python
"""Export the three games for the web (or any Godot preset), with Godot's export templates.

    python scripts/export-games.py                 # all three, to docs/public/games/<name>/
    python scripts/export-games.py hopper --preset Web

Godot's export templates (about 1.2 GB for a version) are not in the
repository nor downloaded by CI: install them once in Godot's editor
(Editor > Manage Export Templates) or from
https://github.com/godotengine/godot/releases, for the pinned version
(`python scripts/godot.py version`). Without them this script says so and
exits 1; the games are still built and checked by `quantum run`.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from quantum.runtime.godot_bin import GODOT_VERSION, GodotNotFound, ensure_godot, script_errors  # noqa: E402

GAMES = {'hopper': 'projects/hopper/hopper.q', 'keep': 'projects/keep/keep.q', 'drift': 'projects/drift/drift.q'}

EXPORT_PRESETS = '''[preset.0]

name="Web"
platform="Web"
runnable=true
export_filter="all_resources"
export_path="{path}"

[preset.0.options]

variant/extensions_support=false
vram_texture_compression/for_desktop=true
html/export_icon=true
html/canvas_resize_policy=2
html/focus_canvas_on_start=true
progressive_web_app/enabled=false
'''


def templates_dir() -> Path:
    return Path.home() / '.local' / 'share' / 'godot' / 'export_templates' / f'{GODOT_VERSION}.stable'


def export(name: str, preset: str, out_root: Path) -> int:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    source = REPO / GAMES[name]
    project = REPO / 'projects' / name / 'godot'
    compile_game(QuantumParser(use_cache=False).parse_file(str(source)), str(project), source_dir=str(source.parent))
    out = out_root / name
    out.mkdir(parents=True, exist_ok=True)
    target = out / 'index.html'
    (project / 'export_presets.cfg').write_text(EXPORT_PRESETS.format(path=target), encoding='utf-8')
    godot = ensure_godot()
    result = subprocess.run([str(godot), '--headless', '--path', str(project), '--export-release', preset, str(target)],
                            capture_output=True, text=True, timeout=600)
    errors = script_errors(result.stdout + result.stderr)
    if errors or not target.is_file():
        print(f'{name}: export failed\n' + '\n'.join(errors) + result.stderr[-2000:], file=sys.stderr)
        return 1
    print(f'{name}: {target}')
    return 0


def main(argv) -> int:
    names = [a for a in argv if not a.startswith('--') and a in GAMES] or list(GAMES)
    preset = 'Web'
    if '--preset' in argv:
        preset = argv[argv.index('--preset') + 1]
    try:
        ensure_godot()
    except GodotNotFound as e:
        print(f'error: {e}', file=sys.stderr)
        return 1
    if not templates_dir().is_dir():
        print(f'error: Godot {GODOT_VERSION} export templates are not installed ({templates_dir()}). '
              f'Install them from Godot\'s editor (Editor > Manage Export Templates) or from '
              f'https://github.com/godotengine/godot/releases/tag/{GODOT_VERSION}-stable', file=sys.stderr)
        return 1
    out_root = REPO / 'docs' / 'public' / 'games'
    code = 0
    for name in names:
        code |= export(name, preset, out_root)
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
