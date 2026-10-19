"""Writes what hive-screen loads: screen.toml, the font sheet, and the sprite sheets beside them."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, Optional

from quantum.runtime.hive.compiler import _s as _string
from quantum.runtime.screen import font, png
from quantum.runtime.screen.model import Screen, read_screen
from quantum.runtime.screen.schema import FONT_CELL, FONT_FILE, TAGS

HEADER = ('# Written by Quantum from {source}: the Hive\'s screen. Do not edit; edit the .q and run it again '
          '(`quantum run {source}`).\n')

SCENE_FILE = 'screen.toml'


def _value(v: object) -> str:
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(float(v))
    if isinstance(v, (list, tuple)):
        return '[' + ', '.join(_value(x) for x in v) + ']'
    return _string(str(v))


def _source(screen: Screen) -> str:
    return Path(screen.source_path).name if screen.source_path else 'a screen file'


def screen_toml(screen: Screen) -> str:
    """The scene and the rules, for hive-screen. Every attribute of a node or an
    action is written under its own name, in the schema's order, so the file reads
    like the .q."""
    out = [HEADER.format(source=_source(screen)),
           '\n[meta]\nversion = 1\n',
           f'\n[scene]\nwidth = {screen.width}\nheight = {screen.height}\n'
           f'background = {_string(screen.background)}\n',
           f'\n[font]\nsrc = {_string(FONT_FILE)}\ncell = {_value(FONT_CELL)}\n']
    for sheet in screen.sheets.values():
        out.append(f'\n[[sheets]]\nname = {_string(sheet.name)}\nsrc = {_string(sheet.src)}\n'
                   f'tile = {_value(sheet.tile)}\nframes = {sheet.frames}\n')
        for a in sheet.animations.values():
            out.append(f'\n[[sheets.animations]]\nname = {_string(a.name)}\nframes = {_value(a.frames)}\n'
                       f'fps = {_value(a.fps)}\nloop = {_value(a.loop)}\n')
    for p in screen.particles.values():
        out.append(f'\n[[particles]]\nname = {_string(p.name)}\npreset = {_string(p.preset)}\n')
        for k in ('color', 'amount', 'lifetime', 'speed', 'size'):
            if k in p.overrides:
                out.append(f'{k} = {_value(p.overrides[k])}\n')
    for node in screen.nodes:
        out.append(f'\n[[nodes]]\nkind = {_string(node.kind)}\n')
        for name in TAGS[node.kind].attrs:
            value = node.attrs.get(name)
            if value is not None:
                out.append(f'{name.replace("-", "_")} = {_value(value)}\n')
    for rule in screen.rules:
        out.append(f'\n[[rules]]\nevent = {_string(rule.event)}\n')
        for action in rule.actions:
            out.append(f'\n[[rules.actions]]\nkind = {_string(action.kind)}\n')
            for name in TAGS[action.kind].attrs:
                value = action.attrs.get(name)
                if value is not None:
                    out.append(f'{name} = {_value(value)}\n')
    return ''.join(out)


def write_font(path: Path) -> None:
    width, height, rows = font.render()
    png.write(path, width, height, rows)


def compile_screen(app, output_dir: str, source_dir: Optional[str] = None) -> Dict[str, str]:
    """Reads the application and writes screen.toml, the font and the sheets
    into output_dir. Returns the paths written, by name."""
    screen = read_screen(app)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: Dict[str, str] = {}
    scene = out / SCENE_FILE
    scene.write_text(screen_toml(screen), encoding='utf-8')
    written[SCENE_FILE] = str(scene)
    write_font(out / FONT_FILE)
    written[FONT_FILE] = str(out / FONT_FILE)
    for sheet in screen.sheets.values():
        target = out / sheet.src
        if target.resolve() != sheet.path.resolve():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(sheet.path, target)
        written[sheet.src] = str(target)
    return written
