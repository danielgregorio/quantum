#!/usr/bin/env python
"""Write os/config/screen/screen.toml and font.png from os/config/screen/screen.q. Never by hand.

    python scripts/generate-screen-config.py          # rewrite both files
    python scripts/generate-screen-config.py --check  # exit 1 when either is stale

screen.q is the Hive's screen in Quantum (quantum/runtime/screen): what
hive-screen draws on the machine's console and what happens in it on the
Hive's events. screen.toml and the font sheet are what the daemon loads,
next to the sprite sheets scripts/art/hive_screen.py draws; they are
committed as generated, and tests/screen/test_screen_config_is_generated.py
fails when they are not this script's output.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from quantum.core.parser import QuantumParser  # noqa: E402
from quantum.runtime.screen import font, png, read_screen, screen_toml  # noqa: E402
from quantum.runtime.screen.schema import FONT_FILE  # noqa: E402

SOURCE = REPO / 'os' / 'config' / 'screen' / 'screen.q'
OUT = SOURCE.parent


def build() -> dict:
    """{file name: its bytes}, from screen.q."""
    screen = read_screen(QuantumParser(use_cache=False).parse_file(str(SOURCE)))
    width, height, rows = font.render()
    font_png = OUT / FONT_FILE
    scratch = font_png.with_suffix('.tmp.png')
    png.write(scratch, width, height, rows)
    data = scratch.read_bytes()
    scratch.unlink()
    return {'screen.toml': screen_toml(screen).encode('utf-8'), FONT_FILE: data}


def main() -> int:
    files = build()
    if '--check' in sys.argv:
        stale = [name for name, data in files.items()
                 if not (OUT / name).is_file() or (OUT / name).read_bytes() != data]
        if stale:
            print(f'stale: {", ".join(stale)} (run python scripts/generate-screen-config.py)')
            return 1
        print('os/config/screen/screen.toml and font.png are current')
        return 0
    for name, data in files.items():
        (OUT / name).write_bytes(data)
        print(f'wrote {(OUT / name).relative_to(REPO)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
