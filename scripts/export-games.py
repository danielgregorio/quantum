#!/usr/bin/env python
"""Export the games with Godot's export templates: for the browser, Linux and Windows.

    python scripts/export-games.py --install-templates [FILE.tpz]   # once: Godot's templates (1.2 GB)
    python scripts/export-games.py                                  # every game, every preset
    python scripts/export-games.py hopper chess --preset Web        # some games, one preset
    python scripts/export-games.py --out /some/dir                  # elsewhere than docs/public/games/

The games are every projects/<name>/<name>.q. Each lands in docs/public/games/<name>/:
the web build as index.html next to its files (threads off, so it runs on
a static host such as GitHub Pages), and <name>-linux.zip / <name>-windows.zip.
docs/public/games/manifest.json lists what was built; the page
docs/targets/play.md links it. The Deploy Docs workflow runs this before the
site is built; nothing here is committed.

Templates: --install-templates downloads Godot's archive for the pinned
version from GitHub (or takes a file) and unpacks it where Godot looks.
"""

import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from quantum.runtime.godot_bin import GODOT_VERSION, GodotNotFound, ensure_godot, script_errors  # noqa: E402

PRESETS = {
    'Web': ('Web', 'index.html', '''variant/extensions_support=false
variant/thread_support=false
vram_texture_compression/for_desktop=true
html/export_icon=true
html/canvas_resize_policy=2
html/focus_canvas_on_start=true
progressive_web_app/enabled=false
'''),
    'Linux': ('Linux', '{name}.x86_64', '''binary_format/embed_pck=true
texture_format/s3tc_bptc=true
texture_format/etc2_astc=false
binary_format/architecture="x86_64"
'''),
    'Windows': ('Windows Desktop', '{name}.exe', '''binary_format/embed_pck=true
texture_format/s3tc_bptc=true
texture_format/etc2_astc=false
binary_format/architecture="x86_64"
codesign/enable=false
application/modify_resources=false
'''),
}

TEMPLATES_URL = (f'https://github.com/godotengine/godot/releases/download/{GODOT_VERSION}-stable/'
                 f'Godot_v{GODOT_VERSION}-stable_export_templates.tpz')


def templates_dir() -> Path:
    return Path.home() / '.local' / 'share' / 'godot' / 'export_templates' / f'{GODOT_VERSION}.stable'


def games() -> dict:
    return {p.parent.name: p for p in sorted(REPO.glob('projects/*/*.q')) if p.stem == p.parent.name}


def install_templates(source: str = '') -> int:
    target = templates_dir()
    if target.is_dir() and any(target.iterdir()):
        print(f'templates already in {target}')
        return 0
    if source:
        archive = Path(source)
    else:
        archive = Path.home() / '.cache' / 'quantum' / f'godot-{GODOT_VERSION}-export-templates.tpz'
        if not archive.is_file():
            archive.parent.mkdir(parents=True, exist_ok=True)
            print(f'downloading {TEMPLATES_URL} (about 1.2 GB)...')
            urllib.request.urlretrieve(TEMPLATES_URL, archive)
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():   # the archive holds templates/<file>; Godot wants <version>.stable/<file>
            if info.is_dir():
                continue
            name = info.filename.split('/', 1)[1] if '/' in info.filename else info.filename
            with z.open(info) as src, open(target / name, 'wb') as dst:
                shutil.copyfileobj(src, dst)
    print(f'installed {len(list(target.iterdir()))} templates in {target}')
    return 0


def preset_file(name: str, preset: str, target: Path) -> str:
    platform, _, options = PRESETS[preset]
    return (f'[preset.0]\n\nname="{preset}"\nplatform="{platform}"\nrunnable=true\n'
            f'export_filter="all_resources"\ninclude_filter=""\nexclude_filter=""\nexport_path="{target}"\n'
            f'\n[preset.0.options]\n\n{options}')


def export(name: str, source: Path, preset: str, out_root: Path, godot: Path) -> dict:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    project = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(source)),
                                str(source.parent / 'godot'), source_dir=str(source.parent)))
    out = out_root / name
    out.mkdir(parents=True, exist_ok=True)
    platform, filename, _ = PRESETS[preset]
    if preset == 'Web':
        target = out / 'index.html'
        work = target
    else:
        work_dir = out / f'.{preset.lower()}'
        shutil.rmtree(work_dir, ignore_errors=True)
        work_dir.mkdir(parents=True)
        work = work_dir / filename.format(name=name)
        target = out / f'{name}-{preset.lower()}.zip'
    (project / 'export_presets.cfg').write_text(preset_file(name, preset, work), encoding='utf-8')
    result = subprocess.run([str(godot), '--headless', '--path', str(project), '--export-release', preset, str(work)],
                            capture_output=True, text=True, timeout=900)
    errors = script_errors(result.stdout + result.stderr)
    if errors or not work.is_file():
        raise RuntimeError(f'{name} ({preset}): export failed\n' + '\n'.join(errors) + result.stderr[-2000:])
    if preset != 'Web':
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
            for f in sorted(work.parent.iterdir()):
                z.write(f, f'{name}/{f.name}')
        shutil.rmtree(work.parent)
    size = sum(f.stat().st_size for f in out.iterdir() if f.is_file()) if preset == 'Web' else target.stat().st_size
    print(f'{name} {preset}: {target.relative_to(REPO) if target.is_relative_to(REPO) else target} ({size // 1024} KB)')
    return {'preset': preset, 'file': target.name}


def main(argv) -> int:
    if '--install-templates' in argv:
        i = argv.index('--install-templates')
        return install_templates(argv[i + 1] if i + 1 < len(argv) and not argv[i + 1].startswith('--') else '')
    all_games = games()
    names = [a for a in argv if not a.startswith('--') and a in all_games]
    presets = [argv[argv.index('--preset') + 1]] if '--preset' in argv else list(PRESETS)
    out_root = Path(argv[argv.index('--out') + 1]) if '--out' in argv else REPO / 'docs' / 'public' / 'games'
    known = {a for a in argv if not a.startswith('--')} - set(all_games) - set(PRESETS) - {str(out_root)}
    known -= {argv[argv.index('--preset') + 1]} if '--preset' in argv else set()
    if known - {str(out_root)}:
        print(f'unknown game(s): {", ".join(sorted(known - {str(out_root)}))} (there are: {", ".join(all_games)})',
              file=sys.stderr)
        return 2
    try:
        godot = ensure_godot()
    except GodotNotFound as e:
        print(f'error: {e}', file=sys.stderr)
        return 1
    if not templates_dir().is_dir():
        print(f'error: Godot {GODOT_VERSION} export templates are not installed ({templates_dir()}): '
              f'python scripts/export-games.py --install-templates', file=sys.stderr)
        return 1
    manifest = {'godot': GODOT_VERSION, 'games': {}}
    for name in names or list(all_games):
        manifest['games'][name] = []
        for preset in presets:
            manifest['games'][name].append(export(name, all_games[name], preset, out_root, godot))
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / 'manifest.json').write_text(json.dumps(manifest, indent=1), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
