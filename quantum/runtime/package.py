"""`quantum package <app> --on tui --target linux|windows|macos`: one file to hand someone (SPEC.md UI-22,
PLAN_PLATFORMS.md Phase 5).

A package holds the application's server — the application, Quantum, the libraries it needs and a Python of its
own (python-build-standalone, for the target, so a package for any system can be made on any system) — beside
its client, which starts it: the TUI, exported with the games' pipeline (Godot's export templates)::

    kanban/
      kanban                 the TUI (kanban.exe on Windows; on a Mac the folder is Kanban.app)
      server/
        package.json         how the TUI starts the server: its Python, its arguments, the first page
        python/              Python, with Quantum and the libraries in its site-packages
        app/                 the application: quantum.config.yaml, components, static, migrations

The server keeps what the application writes in a folder of the user's (quantum/runtime/packaged_server.py), so
the package itself can be read-only; its SQLite databases are left out unless asked (``--with-data``) and its
migrations make them when it starts.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import zipfile
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Callable, Dict, List, Optional

import yaml

PYTHON_VERSION = '3.12.11'
PYTHON_BUILD = '20250818'           # python-build-standalone's release
_PYTHON_URL = ('https://github.com/astral-sh/python-build-standalone/releases/download/{build}/'
               'cpython-{version}%2B{build}-{triple}-install_only_stripped.tar.gz')

# What each target is made of: the Python's build, pip's platform for the libraries, Godot's preset.
TARGETS = {
    'linux': {'triple': 'x86_64-unknown-linux-gnu', 'pip': ['manylinux_2_17_x86_64', 'manylinux2014_x86_64'],
              'preset': 'Linux', 'python': 'python/bin/python3', 'site': 'python/lib/python3.12/site-packages'},
    'windows': {'triple': 'x86_64-pc-windows-msvc', 'pip': ['win_amd64'], 'preset': 'Windows',
                'python': 'python/python.exe', 'site': 'python/Lib/site-packages'},
    'macos': {'triple': 'aarch64-apple-darwin', 'pip': ['macosx_11_0_arm64'], 'preset': 'macOS',
              'python': 'python/bin/python3', 'site': 'python/lib/python3.12/site-packages'},
}

# The libraries the server needs (Quantum's dependencies but the terminal's and gunicorn), and those a
# datasource's driver needs.
SERVER_LIBRARIES = ['flask', 'pyyaml', 'sqlparse', 'requests', 'bcrypt']
DRIVER_LIBRARIES = {'postgres': 'psycopg2-binary', 'postgresql': 'psycopg2-binary', 'mysql': 'pymysql',
                    'mariadb': 'pymysql'}

# What is never carried: a checkout's, an editor's, a run's leftovers.
_LEFT_OUT = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.quantum.pid', '.DS_Store', 'dist',
             '.quantum', 'logs', 'uploads', '.godot', '.venv', 'venv'}


class PackageError(RuntimeError):
    """The package cannot be made: what is missing, and what to do."""


@dataclass
class Package:
    """What `build` made: the file to hand someone, and what it measured."""
    path: Path
    folder: Path
    size: int
    seconds: float
    libraries: Dict[str, str] = field(default_factory=dict)
    left_out: List[str] = field(default_factory=list)


def app_name(app: Path) -> str:
    return re.sub(r'[^a-z0-9-]+', '-', app.resolve().name.lower()).strip('-') or 'app'


def app_title(app: Path, config: dict) -> str:
    named = (config.get('app') or {}).get('title') if isinstance(config.get('app'), dict) else None
    return str(named or (config.get('api') or {}).get('title') or app.resolve().name.replace('-', ' ').title())


def cache_dir() -> Path:
    return Path(os.environ.get('QUANTUM_PACKAGE_CACHE') or Path.home() / '.cache' / 'quantum' / 'package')


# -- the server's Python --------------------------------------------------------------------------------------

def python_archive(target: str, progress: Callable[[str], None]) -> Path:
    """python-build-standalone's build for `target`, from the cache or downloaded into it."""
    from quantum.runtime.godot_bin import fetch_release
    triple = TARGETS[target]['triple']
    archive = cache_dir() / f'cpython-{PYTHON_VERSION}+{PYTHON_BUILD}-{triple}.tar.gz'
    if archive.is_file():
        return archive
    archive.parent.mkdir(parents=True, exist_ok=True)
    url = _PYTHON_URL.format(build=PYTHON_BUILD, version=PYTHON_VERSION, triple=triple)
    fetch_release([url], archive, progress, check=lambda p: tarfile.open(p).close())
    return archive


def unpack_python(archive: Path, server: Path) -> None:
    with tarfile.open(archive) as tar:
        tar.extractall(server, filter='tar')          # the archive's top folder is python/


def library_pins(names: List[str]) -> List[str]:
    """Each library at the version this Quantum runs with here, when it is installed; else the latest."""
    pins = []
    for name in names:
        try:
            pins.append(f'{name}=={metadata.version(name)}')
        except metadata.PackageNotFoundError:
            pins.append(name)
    return pins


def install_libraries(target: str, site: Path, names: List[str], progress: Callable[[str], None]) -> Dict[str, str]:
    """The libraries, built for the target's system (wheels only), into the package's site-packages."""
    spec = TARGETS[target]
    platforms = [a for p in spec['pip'] for a in ('--platform', p)]
    command = [sys.executable, '-m', 'pip', 'install', '--quiet', '--disable-pip-version-check', '--no-compile',
               '--target', str(site), *platforms, '--python-version', '3.12', '--implementation', 'cp',
               '--only-binary=:all:', *library_pins(names)]
    progress(f'libraries for {target}: {", ".join(names)}')
    done = subprocess.run(command, capture_output=True, text=True)
    if done.returncode != 0:
        raise PackageError(f'pip could not get the libraries for {target}:\n{done.stderr[-2000:]}')
    installed = {}
    for info in site.glob('*.dist-info'):
        meta = info.name[:-len('.dist-info')]
        name, _, version = meta.rpartition('-')
        installed[name] = version
    return installed


def copy_quantum(site: Path) -> None:
    """Quantum itself, as it runs here (a checkout or an installed package)."""
    import quantum
    source = Path(quantum.__file__).resolve().parent
    shutil.copytree(source, site / 'quantum', ignore=shutil.ignore_patterns(
        '__pycache__', '*.pyc', '*.so', '*.pyd', 'logs', '.godot'))


# -- the application ------------------------------------------------------------------------------------------

def copy_app(app: Path, target: Path, config: dict, with_data: bool) -> List[str]:
    """The application's folder without what is never carried, and without its SQLite databases unless
    `with_data`; returns what was left out that a reader should know of."""
    from quantum.runtime.packaged_server import sqlite_files
    databases = {(app / p).resolve() for p in sqlite_files(config)}
    left_out: List[str] = []

    def ignore(folder: str, names: List[str]) -> List[str]:
        out = []
        for n in names:
            path = (Path(folder) / n).resolve()
            if n in _LEFT_OUT or n.endswith(('.pyc', '-journal', '-wal', '-shm')):
                out.append(n)
            elif path in databases and not with_data:
                out.append(n)
                left_out.append(str(path.relative_to(app.resolve())))
        return out

    shutil.copytree(app, target, ignore=ignore)
    return left_out


def libraries_for(config: dict) -> List[str]:
    names = list(SERVER_LIBRARIES)
    for source in (config.get('datasources') or {}).values():
        driver = str((source or {}).get('driver', '')).lower() if isinstance(source, dict) else ''
        if driver in DRIVER_LIBRARIES and DRIVER_LIBRARIES[driver] not in names:
            names.append(DRIVER_LIBRARIES[driver])
    return names


# -- the client: the TUI, exported ----------------------------------------------------------------------------

def export_tui(target: str, title: str, name: str, out: Path, progress: Callable[[str], None]) -> Path:
    """The TUI exported for the target, its project named after the application; returns what Godot made."""
    from quantum.runtime.godot_bin import ensure_godot
    from quantum.runtime.godot_export import DESKTOP_PRESETS, export_project, have_templates, install_templates
    from quantum.runtime.ui_tui import project_copy
    godot = ensure_godot(download=True, progress=progress)
    preset = TARGETS[target]['preset']
    if not have_templates(preset):
        install_templates(progress=progress, preset=preset)
    project = project_copy()
    try:
        settings = (project / 'project.godot').read_text(encoding='utf-8')
        settings = settings.replace('config/name="Quantum TUI"', f'config/name={json.dumps(title)}')
        if target == 'macos' and 'import_etc2_astc' not in settings:
            settings = settings.replace('[rendering]\n', '[rendering]\ntextures/vram_compression/import_etc2_astc=true\n')
        (project / 'project.godot').write_text(settings, encoding='utf-8')
        made = out / {'linux': f'{name}.x86_64', 'windows': f'{name}.exe', 'macos': f'{name}.zip'}[target]
        options = DESKTOP_PRESETS[preset][1].replace('{id}', re.sub(r'[^a-z0-9]', '', name))
        progress(f'the TUI for {target} (Godot, {preset})')
        return export_project(project, preset, made, godot, options)
    finally:
        shutil.rmtree(project, ignore_errors=True)


# -- the file -------------------------------------------------------------------------------------------------

def _zip(folder: Path, archive: Path) -> None:
    """A .zip that keeps what can run as runnable, and symbolic links as links (a Mac's unzip makes them)."""
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(folder.rglob('*')):
            name = path.relative_to(folder.parent).as_posix()
            if path.is_symlink():
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(info, os.readlink(path))
            elif path.is_dir():
                continue
            else:
                info = zipfile.ZipInfo.from_file(path, name)
                info.create_system = 3
                info.compress_type = zipfile.ZIP_DEFLATED
                with open(path, 'rb') as f:
                    z.writestr(info, f.read(), compresslevel=9)


def _tar(folder: Path, archive: Path) -> None:
    with tarfile.open(archive, 'w:gz', compresslevel=9) as tar:
        tar.add(folder, arcname=folder.name)


def build(app: Path, on: str = 'tui', target: str = 'linux', out: Optional[Path] = None, with_data: bool = False,
          progress: Callable[[str], None] = print) -> Package:
    """The package of `app` for `target`: the file, and the folder it holds (kept beside it, ready to run)."""
    started = time.monotonic()
    app = Path(app).resolve()
    if on != 'tui':
        raise PackageError(f'--on {on}: a package is made with the TUI as its program (--on tui); the desktop '
                           f'window is PLAN_PLATFORMS.md Phase 5b')
    if target not in TARGETS:
        raise PackageError(f'--target {target}: one of {", ".join(TARGETS)}')
    config_file = app / 'quantum.config.yaml'
    if not config_file.is_file():
        raise PackageError(f'{app} has no quantum.config.yaml: `quantum package` takes an application\'s folder')
    config = yaml.safe_load(config_file.read_text(encoding='utf-8')) or {}
    name, title = app_name(app), app_title(app, config)
    out = Path(out or app / 'dist').resolve()
    work = out / f'.{name}-{target}'
    shutil.rmtree(work, ignore_errors=True)
    folder = work / (f'{title}.app' if target == 'macos' else name)
    work.mkdir(parents=True)

    # the client first: it is the program, and on a Mac the folder the rest goes into
    made = export_tui(target, title, name, work, progress)
    if target == 'macos':
        with zipfile.ZipFile(made) as z:
            z.extractall(work)
        made.unlink()
        apps = [p for p in work.iterdir() if p.suffix == '.app']
        if not apps:
            raise PackageError('the macOS export holds no .app')
        if apps[0] != folder:
            apps[0].rename(folder)
        for program in (folder / 'Contents' / 'MacOS').iterdir():
            program.chmod(program.stat().st_mode | 0o111)
        server = folder / 'Contents' / 'Resources' / 'server'
    else:
        folder.mkdir()
        program = folder / (f'{name}.exe' if target == 'windows' else name)
        made.rename(program)
        program.chmod(program.stat().st_mode | 0o111)
        server = folder / 'server'

    server.mkdir(parents=True)
    progress(f'Python {PYTHON_VERSION} for {target}')
    unpack_python(python_archive(target, progress), server)
    site = server / TARGETS[target]['site']
    libraries = install_libraries(target, site, libraries_for(config), progress)
    copy_quantum(site)
    left_out = copy_app(app, server / 'app', config, with_data)
    from quantum.runtime.ui_tui import design_tokens
    (server / 'package.json').write_text(json.dumps({
        'name': name, 'title': title, 'page': '/',
        'python': TARGETS[target]['python'],
        'args': ['-I', '-m', 'quantum.runtime.packaged_server', '--app', '{server}/app', '--name', name],
        'tokens': design_tokens(),
    }, indent=2) + '\n', encoding='utf-8')

    suffix = '.tar.gz' if target == 'linux' else '.zip'
    archive = out / f'{name}-{target}{suffix}'
    archive.unlink(missing_ok=True)
    progress(f'packing {archive.name}')
    (_tar if target == 'linux' else _zip)(folder, archive)
    kept = out / f'{name}-{target}'           # the package unpacked, ready to run: <kept>/<name>/<name>
    shutil.rmtree(kept, ignore_errors=True)
    work.rename(kept)
    return Package(path=archive, folder=kept / folder.name, size=archive.stat().st_size,
                   seconds=time.monotonic() - started, libraries=libraries, left_out=left_out)


def main(args) -> int:
    """The `quantum package` command."""
    try:
        made = build(Path(args.app), on=args.on, target=args.target, out=Path(args.out) if args.out else None,
                     with_data=args.with_data)
    except PackageError as exc:
        print(f'[ERROR] {exc}', file=sys.stderr)
        return 1
    print(f'{made.path} ({made.size / 1e6:.1f} MB, made in {made.seconds:.0f} s)')
    if made.left_out:
        print(f'left out (the migrations make them when it starts; --with-data carries them): '
              f'{", ".join(made.left_out)}')
    return 0
