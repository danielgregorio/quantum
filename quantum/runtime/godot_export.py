"""Godot's export templates, and a project exported with them: the games' pipeline (scripts/export-games.py) and
`quantum package` (the TUI as an application's program, PLAN_PLATFORMS.md Phase 5) use the same.

The templates of the pinned version (about 1.2 GB) are fetched once into where Godot looks for them.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Optional

from quantum.runtime.godot_bin import GODOT_VERSION, script_errors

# A desktop's preset: Godot's platform, and its options (the games' and the package's).
DESKTOP_PRESETS = {
    'Linux': ('Linux', '''binary_format/embed_pck=true
texture_format/s3tc_bptc=true
texture_format/etc2_astc=false
binary_format/architecture="x86_64"
'''),
    'Windows': ('Windows Desktop', '''binary_format/embed_pck=true
texture_format/s3tc_bptc=true
texture_format/etc2_astc=false
binary_format/architecture="x86_64"
codesign/enable=false
application/modify_resources=false
'''),
    'macOS': ('macOS', '''binary_format/architecture="universal"
application/bundle_identifier="net.quantumframework.{id}"
application/min_macos_version="10.12"
codesign/codesign=0
notarization/notarization=0
texture_format/s3tc_bptc=true
texture_format/etc2_astc=true
'''),
}

# The browser's preset (the games' and the TUI's): threads off, so any host serves it as plain files (no
# cross-origin isolation), the canvas as large as the window, and the keyboard in it from the start.
WEB_PRESET = ('Web', '''variant/extensions_support=false
variant/thread_support=false
vram_texture_compression/for_desktop=true
html/export_icon=true
html/canvas_resize_policy=2
html/focus_canvas_on_start=true
progressive_web_app/enabled=false
''')

PRESETS = {**DESKTOP_PRESETS, 'Web': WEB_PRESET}


def templates_dir() -> Path:
    """Where Godot looks for its export templates, on this system."""
    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'Godot'
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support' / 'Godot'
    else:
        base = Path.home() / '.local' / 'share' / 'godot'
    return base / 'export_templates' / f'{GODOT_VERSION}.stable'


# The templates each preset is exported with (for a desktop, Godot checks for the debug one too).
TEMPLATE_FILES = {
    'Linux': ['linux_release.x86_64', 'linux_debug.x86_64'],
    'Windows': ['windows_release_x86_64.exe', 'windows_debug_x86_64.exe',
                'windows_release_x86_64_console.exe', 'windows_debug_x86_64_console.exe'],
    'macOS': ['macos.zip'],
    'Web': ['web_nothreads_release.zip'],
}


def have_templates(preset: Optional[str] = None) -> bool:
    """Whether the templates are where Godot looks: those of `preset`, or any."""
    target = templates_dir()
    if preset is not None:
        return all((target / name).is_file() for name in TEMPLATE_FILES.get(preset, []))
    return target.is_dir() and any(target.iterdir())


def install_templates(source: str = '', progress=print, preset: Optional[str] = None) -> Path:
    """The templates where Godot looks, from `source` (a .tpz) or downloaded (GitHub's release, then Godot's own
    download service; kept in the cache). Only what is missing is unpacked: all of them, or `preset`'s."""
    target = templates_dir()
    if have_templates(preset):
        progress(f'templates already in {target}')
        return target
    if source:
        archive = Path(source)
    else:
        archive = Path.home() / '.cache' / 'quantum' / f'godot-{GODOT_VERSION}-export-templates.tpz'
        if not archive.is_file():
            from quantum.runtime.godot_bin import fetch_release, templates_urls
            archive.parent.mkdir(parents=True, exist_ok=True)
            progress('the export templates, about 1.2 GB...')
            fetch_release(templates_urls(), archive, progress=progress,
                          check=lambda path: zipfile.ZipFile(path).close())
    target.mkdir(parents=True, exist_ok=True)
    wanted = set(TEMPLATE_FILES[preset]) if preset else None
    count = 0
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():   # the archive holds templates/<file>; Godot wants <version>.stable/<file>
            if info.is_dir():
                continue
            name = info.filename.split('/', 1)[1] if '/' in info.filename else info.filename
            if (wanted is not None and name not in wanted and name != 'version.txt') or (target / name).is_file():
                continue
            with z.open(info) as src, open(target / name, 'wb') as dst:
                shutil.copyfileobj(src, dst)
            count += 1
    progress(f'installed {count} templates in {target}')
    return target


def preset_text(preset: str, platform: str, options: str, target: Path, include: str = '') -> str:
    """export_presets.cfg with one preset; `include`: files carried as they are, besides the resources."""
    return (f'[preset.0]\n\nname="{preset}"\nplatform="{platform}"\nrunnable=true\n'
            f'export_filter="all_resources"\ninclude_filter="{include}"\nexclude_filter=""\n'
            f'export_path="{target.as_posix()}"\n'
            f'\n[preset.0.options]\n\n{options}')


def export_project(project: Path, preset: str, target: Path, godot: Path, options: Optional[str] = None,
                   include: str = '', timeout: float = 900) -> Path:
    """`project` exported with `preset` (one of PRESETS, its options formatted by the caller when they name an
    id) to `target` (for the browser, its index.html, the files beside it); raises with Godot's errors when
    nothing was made."""
    platform, default = PRESETS[preset]
    target.parent.mkdir(parents=True, exist_ok=True)
    (project / 'export_presets.cfg').write_text(preset_text(preset, platform, options or default, target, include),
                                                encoding='utf-8')
    result = subprocess.run([str(godot), '--headless', '--path', str(project), '--export-release', preset,
                             str(target)], capture_output=True, text=True, timeout=timeout)
    errors = script_errors(result.stdout + result.stderr)
    if errors or not target.is_file():
        raise RuntimeError(f'{project.name} ({preset}): the export failed\n' + '\n'.join(errors)
                           + (result.stderr or result.stdout)[-2000:])
    return target
