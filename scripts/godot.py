#!/usr/bin/env python
"""The Godot binary the games are checked and replayed with.

    python scripts/godot.py install   # download the pinned version into the cache
    python scripts/godot.py path      # print the binary in use (exit 1 if none)
    python scripts/godot.py version   # the pinned version

quantum/runtime/godot_bin.py knows the version and where to look; this is
its command line, for CI and for a developer setting up.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantum.runtime.godot_bin import GODOT_VERSION, GodotNotFound, ensure_godot, find_godot  # noqa: E402


def main(argv):
    command = argv[1] if len(argv) > 1 else 'path'
    if command == 'version':
        print(GODOT_VERSION)
        return 0
    if command == 'install':
        try:
            print(ensure_godot(download=True, progress=lambda m: print(m, file=sys.stderr)))
        except GodotNotFound as e:
            print(f'error: {e}', file=sys.stderr)
            return 1
        return 0
    if command == 'path':
        found = find_godot()
        if not found:
            print(f'error: Godot {GODOT_VERSION} not found; run `python scripts/godot.py install`',
                  file=sys.stderr)
            return 1
        print(found)
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
