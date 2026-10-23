"""`quantum run <app> --on web|desktop|tui|terminal`: one application, its versions by one parameter (UI-18).

Every version is the same application served by the same runtime: only the
renderer changes. `web` is `quantum start`, `desktop` the pages in a window
(`quantum desktop`, UI-4), `terminal` the pages in the terminal (`quantum
console`, UI-3). `tui`, a text screen drawn by Godot, is PLAN_PLATFORMS.md's
Phase 3 and says so until it exists.
"""

import os
import sys
from pathlib import Path
from typing import Optional

VERSIONS = ('web', 'desktop', 'tui', 'terminal')
CONFIG = 'quantum.config.yaml'


def find_app(target: str) -> Optional[Path]:
    """The application's folder: the folder given, or the folder of the quantum.config.yaml given."""
    path = Path(target)
    if path.is_dir() and (path / CONFIG).is_file():
        return path.resolve()
    if path.is_file() and path.name.endswith(('.yaml', '.yml')):
        return path.resolve().parent
    return None


def run_on(target: str, on: str, path: str = '/', port: Optional[int] = None) -> int:
    """Run the application at `target` in the version `on`; the exit code."""
    app = find_app(target)
    if app is None:
        print(f'[ERROR] --on {on}: {target} is not an application (a folder with {CONFIG})', file=sys.stderr)
        return 1
    if on == 'tui':
        print('[ERROR] --on tui: the text screen drawn by Godot is not built yet (PLAN_PLATFORMS.md, Phase 3). '
              'The other versions: --on web, --on desktop, --on terminal', file=sys.stderr)
        return 2
    # The application's paths (components, its database, its uploads) are relative to its folder,
    # as when `quantum start` runs in it.
    os.chdir(app)
    if on == 'web':
        from quantum.runtime.web_server import start_server
        return start_server(CONFIG, port=port) or 0
    if on == 'desktop':
        from quantum.runtime.ui_desktop import run_desktop
        return run_desktop(CONFIG, path)
    if on == 'terminal':
        from quantum.runtime.ui_console import run_console
        return run_console(CONFIG, path)
    print(f'[ERROR] --on {on}: use one of {", ".join(VERSIONS)}', file=sys.stderr)
    return 1
