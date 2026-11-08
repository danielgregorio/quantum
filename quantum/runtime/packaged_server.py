"""The application's server inside a package made by `quantum package` (PLAN_PLATFORMS.md Phase 5, SPEC.md UI-22).

The package's client (the TUI, or the desktop's window) starts this with the package's own Python::

    python -I -m quantum.runtime.packaged_server --app <the package's app folder> --name kanban

and reads one line from it — ``QUANTUM-SERVER http://127.0.0.1:<port>/`` — before it asks for the first page. The
server runs until its standard input closes: the client holds it open, so when the client goes, however it goes,
so does the server.

The package is read-only (an .app on a Mac, a folder in Program Files): what the application writes lives in a
folder of the user's (``data_dir``): its SQLite databases, its uploads, its logs. Its pages, static files and
migrations stay in the package. On each start the application's pending migrations run; a database the package
carries (``quantum package --with-data``) is copied there the first time, before them.
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List


READY = 'QUANTUM-SERVER '
ERROR = 'QUANTUM-ERROR '

# The paths of quantum.config.yaml that are the application's (in the package) and not the user's.
PACKAGE_PATHS = ('components', 'static', 'migrations')
DEFAULTS = {'components': './components', 'static': './static', 'migrations': './migrations'}


def data_dir(name: str) -> Path:
    """Where the application `name` keeps what it writes, for this user on this system."""
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local') / 'Quantum' / name
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'Quantum' / name
    return Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share') / 'quantum' / name


def sqlite_sources(config: Dict[str, Any]) -> Dict[str, str]:
    """The SQLite datasources the configuration declares, by name, with their relative paths."""
    found = {}
    for name, source in (config.get('datasources') or {}).items():
        if isinstance(source, dict) and str(source.get('driver', '')).lower() == 'sqlite':
            path = str(source.get('database') or '')
            if path and path != ':memory:' and not Path(path).is_absolute() and '$' not in path:
                found[name] = path
    return found


def sqlite_files(config: Dict[str, Any]) -> List[str]:
    """The relative paths of the SQLite databases the configuration names."""
    return list(sqlite_sources(config).values())


def prepare(app: Path, data: Path) -> Dict[str, Any]:
    """The user's folder made ready: its quantum.config.yaml (the package's, with the application's paths into the
    package) and the databases the package carries, copied the first time. Returns the configuration."""
    import yaml                          # here: a hosted application's window (packaged_desktop) has no PyYAML
    raw = yaml.safe_load((app / 'quantum.config.yaml').read_text(encoding='utf-8')) or {}
    paths = dict(raw.get('paths') or {})
    for key in PACKAGE_PATHS:
        folder = (app / (paths.get(key) or DEFAULTS[key])).resolve()
        if folder.is_dir():
            paths[key] = folder.as_posix()
    raw['paths'] = paths
    data.mkdir(parents=True, exist_ok=True)
    (data / 'quantum.config.yaml').write_text(
        '# Written by the package on each start from the one it carries (quantum.runtime.packaged_server).\n'
        + yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding='utf-8')
    for path in sqlite_files(raw):
        carried, mine = app / path, data / path
        if carried.is_file() and not mine.exists():
            mine.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(carried, mine)
    return raw


def migrate(data: Path, config: Dict[str, Any]) -> None:
    """The application's pending migrations, as `quantum migrate up` runs them, for each SQLite database."""
    migrations = Path((config.get('paths') or {}).get('migrations') or '')
    if not migrations.is_dir() or not any(migrations.glob('*.sql')):
        return
    from quantum.cli.migrations import MigrationRunner
    sources = sqlite_sources(config)
    for path in sources.values():
        (data / path).parent.mkdir(parents=True, exist_ok=True)
    # `quantum migrate up`'s datasource: the only one, else the only SQLite one (another is a server's)
    declared = config.get('datasources') or {}
    if len(declared) > 1 and len(sources) != 1:
        raise RuntimeError(f"the migrations are for one datasource; {', '.join(declared)} are declared and "
                           f"{len(sources)} of them are SQLite")
    results = MigrationRunner(project_path=data, datasource=None if len(declared) == 1 else next(iter(sources))).up()
    failed = [r for r in results if r.get('status') == 'failed']
    if failed:
        raise RuntimeError(f"a migration failed: {failed[0].get('version')} {failed[0].get('error', '')}")


def start(app: Path, name: str, port: int = 0):
    """Prepare the user's folder, migrate, and serve on 127.0.0.1 in a thread; returns (server, its URL)."""
    data = data_dir(name)
    config = prepare(app.resolve(), data)
    os.chdir(data)
    migrate(data, config)
    from werkzeug.serving import make_server
    from quantum.runtime.web_server import QuantumWebServer
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    server = make_server('127.0.0.1', port, QuantumWebServer(str(data / 'quantum.config.yaml')).app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_port}/'


def log_to(path: Path):
    """Everything the process writes goes to `path` (descriptors 1 and 2 too); returns a handle on what the
    standard output was, for the one line a client reads (None when there was none: a window's Python)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        protocol = os.fdopen(os.dup(sys.stdout.fileno()), 'w', encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        protocol = None
    log = open(path, 'w', encoding='utf-8', buffering=1)
    for fd in (1, 2):
        try:
            os.dup2(log.fileno(), fd)
        except OSError:
            pass
    sys.stdout = sys.stderr = log
    return protocol


def serve(app: Path, name: str, port: int = 0, out=None, stdin=None) -> None:
    """Prepare the user's folder, migrate, serve on 127.0.0.1 and say where; until `stdin` closes."""
    out = out or sys.stdout
    stdin = stdin or sys.stdin
    server, url = start(app, name, port)
    out.write(f'{READY}{url}\n')
    out.flush()
    try:
        while stdin.readline():
            pass                         # the client says nothing; its end is the end of the input
    except (KeyboardInterrupt, OSError):
        pass
    server.shutdown()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='packaged_server', description=__doc__.split('\n')[0])
    parser.add_argument('--app', required=True, help="the package's application folder")
    parser.add_argument('--name', required=True, help='the folder of the user\'s data (data_dir)')
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args(argv)
    # The standard output is the client's: one line, where the server is (or what went wrong). Everything
    # else the process writes — the application's log, its migrations, Python's warnings — goes to
    # server.log in the user's folder, so the client's pipes never fill (it reads only that line).
    log_path = data_dir(args.name) / 'server.log'
    protocol = log_to(log_path)
    try:
        serve(Path(args.app), args.name, args.port, out=protocol)
    except Exception as exc:              # the client shows what went wrong rather than wait for a line
        import traceback
        traceback.print_exc()
        protocol.write(f'{ERROR}{type(exc).__name__}: {exc} (the log: {log_path})\n')
        protocol.flush()
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
