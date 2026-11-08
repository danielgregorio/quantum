"""`quantum package <app> --on tui --target linux|windows|macos|web`: one file to hand someone (SPEC.md UI-22,
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

``--target web`` is the TUI alone, exported for the browser into the application's static folder
(``<app>/static/tui/``): the application's own server serves it, at /static/tui/index.html, and it asks that
server for the pages through the browser's fetch (quantum/runtime/tui/web.gd).
"""

from __future__ import annotations

import io
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

# The browser: the TUI alone, exported into the application's static folder; its server is the application's own.
WEB = 'web'
# The phones (Phase 6): the TUI alone, a hosted application's client (a phone runs no server of its own)
PHONES = {'android': 'Android', 'ios': 'iOS'}

# The libraries the server needs (Quantum's dependencies but the terminal's and gunicorn), and those a
# datasource's driver needs.
SERVER_LIBRARIES = ['flask', 'pyyaml', 'sqlparse', 'requests', 'bcrypt']
DRIVER_LIBRARIES = {'postgres': 'psycopg2-binary', 'postgresql': 'psycopg2-binary', 'mysql': 'pymysql',
                    'mariadb': 'pymysql'}

# The window's libraries (pywebview and what it needs on each system: pip's --platform does not read a
# library's own markers for another system, so they are named here). Linux has none: its window would need Qt
# WebEngine, half a gigabyte; its package is the TUI.
DESKTOP_LIBRARIES = {
    'windows': ['pywebview', 'proxy_tools', 'bottle', 'typing_extensions', 'pythonnet'],
    'macos': ['pywebview', 'proxy_tools', 'bottle', 'typing_extensions', 'pyobjc-core', 'pyobjc-framework-Cocoa',
              'pyobjc-framework-Quartz', 'pyobjc-framework-WebKit', 'pyobjc-framework-Security',
              'pyobjc-framework-UniformTypeIdentifiers'],
}
# Libraries published only as source, pure Python: built into a wheel here, once
SOURCE_ONLY = {'proxy_tools': '0.1.0'}
# The Windows program of a desktop package: distlib's launcher (pip's own scripts' .exe), which runs the
# Python its first line names, relative to itself, on the zip after it
DISTLIB = '0.3.9'

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


def source_wheels(names: List[str], progress: Callable[[str], None]) -> Path:
    """The wheels of the libraries among `names` published only as source (pure Python), built once."""
    folder = cache_dir() / 'wheels'
    folder.mkdir(parents=True, exist_ok=True)
    for name, version in SOURCE_ONLY.items():
        if name in names and not list(folder.glob(f'{name}-{version}-*.whl')):
            progress(f'a wheel of {name} {version} (published as source only)')
            done = subprocess.run([sys.executable, '-m', 'pip', 'wheel', '--quiet', '--disable-pip-version-check',
                                   '--use-pep517', '--no-deps', f'{name}=={version}', '-w', str(folder)],
                                  capture_output=True, text=True)
            if done.returncode != 0:
                raise PackageError(f'pip could not build {name}:\n{done.stderr[-2000:]}')
    return folder


def install_libraries(target: str, site: Path, names: List[str], progress: Callable[[str], None]) -> Dict[str, str]:
    """The libraries, built for the target's system (wheels only), into the package's site-packages."""
    spec = TARGETS[target]
    platforms = [a for p in spec['pip'] for a in ('--platform', p)]
    pins = [n if n in SOURCE_ONLY else p for n, p in zip(names, library_pins(names))]
    command = [sys.executable, '-m', 'pip', 'install', '--quiet', '--disable-pip-version-check', '--no-compile',
               '--target', str(site), *platforms, '--python-version', '3.12', '--implementation', 'cp',
               '--only-binary=:all:', '--find-links', str(source_wheels(names, progress)), *pins]
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
    `with_data`; returns what was left out that a reader should know of. The TUI made for the browser
    (`--target web`) stays out too: the package's program is the TUI."""
    from quantum.runtime.packaged_server import sqlite_files
    databases = {(app / p).resolve() for p in sqlite_files(config)}
    web_tui = web_folder(app, config)
    left_out: List[str] = []

    def ignore(folder: str, names: List[str]) -> List[str]:
        out = []
        for n in names:
            path = (Path(folder) / n).resolve()
            if n in _LEFT_OUT or n.endswith(('.pyc', '-journal', '-wal', '-shm')) or path == web_tui:
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

def export_tui(target: str, title: str, name: str, out: Path, progress: Callable[[str], None],
               server: Optional[str] = None) -> Path:
    """The TUI exported for the target, its project named after the application; returns what Godot made (for
    the browser, its index.html, its files beside it)."""
    from quantum.runtime.godot_bin import ensure_godot
    from quantum.runtime.godot_export import PRESETS, export_project, have_templates, install_templates
    from quantum.runtime.ui_tui import project_copy
    godot = ensure_godot(download=True, progress=progress)
    preset = 'Web' if target == WEB else PHONES.get(target) or TARGETS[target]['preset']
    if not have_templates(preset):
        install_templates(progress=progress, preset=preset)
    project = project_copy()
    try:
        settings = (project / 'project.godot').read_text(encoding='utf-8')
        settings = settings.replace('config/name="Quantum TUI"', f'config/name={json.dumps(title)}')
        if target in ('macos', *PHONES) and 'import_etc2_astc' not in settings:   # Apple's chips, phones
            settings = settings.replace('[rendering]\n', '[rendering]\ntextures/vram_compression/import_etc2_astc=true\n')
        if target in PHONES:
            # a phone's screen turns: the TUI lays itself out again in as many cells as fit
            settings = settings.replace('[display]\n', '[display]\n\nwindow/handheld/orientation=6\n', 1)
        if server:
            # a hosted application's client (Phase 6): the TUI asks that server, which it does not start
            from quantum.runtime.ui_tui import design_tokens
            settings += (f'\n[quantum]\n\nserver={json.dumps(server)}\n'
                         f'tokens={json.dumps(json.dumps(design_tokens()))}\n')
        (project / 'project.godot').write_text(settings, encoding='utf-8')
        made = out / {'linux': f'{name}.x86_64', 'windows': f'{name}.exe', 'macos': f'{name}.zip',
                      WEB: 'index.html', 'android': f'{name}.apk', 'ios': f'{name}.ipa'}[target]
        options = (PRESETS[preset][1].replace('{id}', re.sub(r'[^a-z0-9]', '', name))
                   .replace('{title}', title.replace('"', ''))
                   .replace('{team}', os.environ.get('QUANTUM_IOS_TEAM_ID') or 'XXXXXXXXXX'))
        progress(f'the TUI for {target} (Godot, {preset})')
        if target == 'android':
            debug, env = android_signing(progress)
            return export_project(project, preset, made, godot, options, debug=debug, env=env)
        if target == 'ios':
            # an Xcode project (export_project_only), which a Mac builds and signs
            export_project(project, preset, made, godot, options, made=out / f'{name}.xcodeproj')
            return out
        return export_project(project, preset, made, godot, options)
    finally:
        shutil.rmtree(project, ignore_errors=True)


def android_tools() -> None:
    """Godot signs an .apk with the Android SDK's build tools (apksigner) run by a JDK: their folders, from
    ANDROID_HOME (or ANDROID_SDK_ROOT) and JAVA_HOME (or the java on the PATH), written into Godot's editor
    settings, where its export looks for them."""
    sdk = os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT')
    if not sdk or not Path(sdk, 'build-tools').is_dir():
        raise PackageError('an Android package is signed with the Android SDK\'s build tools (apksigner): set '
                           'ANDROID_HOME to the SDK, with its build-tools installed (sdkmanager "build-tools;34.0.0")')
    java = os.environ.get('JAVA_HOME')
    if not java and shutil.which('java'):
        java = str(Path(shutil.which('java')).resolve().parents[1])
    if not java:
        raise PackageError('an Android package is signed by a JDK\'s tools: set JAVA_HOME (JDK 17)')
    from quantum.runtime.godot_bin import GODOT_VERSION
    folder = (Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'Godot' if sys.platform == 'win32'
              else Path.home() / 'Library' / 'Application Support' / 'Godot' if sys.platform == 'darwin'
              else Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'godot')
    settings = folder / f'editor_settings-{".".join(GODOT_VERSION.split(".")[:2])}.tres'
    text = settings.read_text(encoding='utf-8') if settings.is_file() else \
        '[gd_resource type="EditorSettings" format=3]\n\n[resource]\n'
    lines = [line for line in text.splitlines() if not line.startswith(('export/android/android_sdk_path',
                                                                        'export/android/java_sdk_path'))]
    at = lines.index('[resource]') + 1 if '[resource]' in lines else len(lines)
    lines[at:at] = [f'export/android/android_sdk_path = {json.dumps(str(Path(sdk)))}',
                    f'export/android/java_sdk_path = {json.dumps(java)}']
    folder.mkdir(parents=True, exist_ok=True)
    settings.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def android_signing(progress: Callable[[str], None]):
    """How an .apk is signed: (debug, environment for Godot). A release key when QUANTUM_ANDROID_KEYSTORE (with
    _USER and _PASSWORD) names one; otherwise a debug key, made once in the cache with the JDK's keytool."""
    if os.environ.get('QUANTUM_ANDROID_KEYSTORE'):
        return False, {'GODOT_ANDROID_KEYSTORE_RELEASE_PATH': os.environ['QUANTUM_ANDROID_KEYSTORE'],
                       'GODOT_ANDROID_KEYSTORE_RELEASE_USER': os.environ.get('QUANTUM_ANDROID_KEYSTORE_USER', ''),
                       'GODOT_ANDROID_KEYSTORE_RELEASE_PASSWORD': os.environ.get('QUANTUM_ANDROID_KEYSTORE_PASSWORD', '')}
    keystore = cache_dir() / 'debug.keystore'
    if not keystore.is_file():
        keytool = shutil.which('keytool')
        if not keytool:
            raise PackageError('an Android package is signed with a key: the debug key is made with the JDK\'s '
                               'keytool, which is not on this machine (install a JDK, or set QUANTUM_ANDROID_KEYSTORE)')
        keystore.parent.mkdir(parents=True, exist_ok=True)
        progress('a debug key for the Android package (keytool)')
        done = subprocess.run([keytool, '-genkeypair', '-keystore', str(keystore), '-storepass', 'android',
                               '-alias', 'androiddebugkey', '-keypass', 'android', '-keyalg', 'RSA', '-keysize', '2048',
                               '-validity', '10000', '-dname', 'CN=Android Debug,O=Android,C=US'],
                              capture_output=True, text=True)
        if done.returncode != 0:
            raise PackageError(f'keytool could not make the debug key:\n{done.stderr[-1000:]}')
    return True, {'GODOT_ANDROID_KEYSTORE_DEBUG_PATH': str(keystore), 'GODOT_ANDROID_KEYSTORE_DEBUG_USER': 'androiddebugkey',
                  'GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD': 'android'}


def build_phone(app: Path, name: str, title: str, target: str, out: Optional[Path], server: str, started: float,
                progress: Callable[[str], None]) -> 'Package':
    """The TUI for a phone, a client of the application hosted at `server`: an .apk, or an Xcode project's zip."""
    if target == 'android':
        android_tools()                       # before anything is fetched: the SDK and the JDK are there
    out = Path(out or app / 'dist').resolve()
    work = out / f'.{name}-{target}'
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    made = export_tui(target, title, name, work, progress, server)
    if target == 'android':
        archive = out / f'{name}-android.apk'
        archive.unlink(missing_ok=True)
        made.rename(archive)
    else:
        archive = out / f'{name}-ios.zip'
        archive.unlink(missing_ok=True)
        folder = out / f'{name}-ios'
        shutil.rmtree(folder, ignore_errors=True)
        work.rename(folder)
        progress(f'packing {archive.name}')
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            for path in sorted(folder.rglob('*')):
                if path.is_file():
                    z.write(path, path.relative_to(folder).as_posix())
    shutil.rmtree(work, ignore_errors=True)
    return Package(path=archive, folder=archive if target == 'android' else out / f'{name}-ios',
                   size=archive.stat().st_size, seconds=time.monotonic() - started)


# -- the client: the desktop's window --------------------------------------------------------------------------

def windows_launcher(progress: Callable[[str], None]) -> bytes:
    """distlib's GUI launcher (w64.exe), from its wheel, kept in the cache."""
    exe = cache_dir() / f'distlib-{DISTLIB}-w64.exe'
    if not exe.is_file():
        progress(f"distlib {DISTLIB}'s launcher (the Windows program)")
        folder = cache_dir() / 'distlib'
        folder.mkdir(parents=True, exist_ok=True)
        done = subprocess.run([sys.executable, '-m', 'pip', 'download', '--quiet', '--disable-pip-version-check',
                               '--no-deps', f'distlib=={DISTLIB}', '-d', str(folder)], capture_output=True, text=True)
        wheels = list(folder.glob(f'distlib-{DISTLIB}-*.whl'))
        if done.returncode != 0 or not wheels:
            raise PackageError(f'pip could not get distlib {DISTLIB}:\n{done.stderr[-2000:]}')
        with zipfile.ZipFile(wheels[0]) as z:
            exe.write_bytes(z.read('distlib/w64.exe'))
    return exe.read_bytes()


def desktop_program(target: str, title: str, name: str, work: Path, progress: Callable[[str], None]):
    """The desktop's program: (the folder it is in, the server folder beside it)."""
    if target == 'windows':
        folder = work / name
        folder.mkdir()
        # the launcher runs its first line's Python (beside it) on the zip after it: __main__ starts the desktop
        body = io.BytesIO()
        with zipfile.ZipFile(body, 'w') as z:
            z.writestr('__main__.py', 'from quantum.runtime.packaged_desktop import main\nraise SystemExit(main())\n')
        shebang = b'#!<launcher_dir>\\server\\python\\pythonw.exe -E -s\r\n'
        program = re.sub(r'[\\/:*?"<>|]', '', title) or name
        (folder / f'{program}.exe').write_bytes(windows_launcher(progress) + shebang + body.getvalue())
        return folder, folder / 'server'
    # a Mac's .app: its program a script that runs the package's Python
    folder = work / f'{title}.app'
    (folder / 'Contents' / 'MacOS').mkdir(parents=True)
    (folder / 'Contents' / 'Info.plist').write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key><string>{title}</string>
  <key>CFBundleIdentifier</key><string>net.quantumframework.{re.sub(r'[^a-z0-9]', '', name)}</string>
  <key>CFBundleName</key><string>{title}</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
''', encoding='utf-8')
    program = folder / 'Contents' / 'MacOS' / title
    program.write_text('#!/bin/sh\n# the package\'s Python, with the desktop (quantum.runtime.packaged_desktop)\n'
                       'here="$(cd "$(dirname "$0")/.." && pwd)"\n'
                       'exec "$here/Resources/server/python/bin/python3" -I -m quantum.runtime.packaged_desktop "$@"\n',
                       encoding='utf-8')
    program.chmod(0o755)
    return folder, folder / 'Contents' / 'Resources' / 'server'


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


def web_folder(app: Path, config: dict) -> Path:
    """Where the TUI for the browser goes unless `--out` says: tui/ in the application's static folder, which its
    server serves at /static/tui/."""
    paths = config.get('paths') if isinstance(config.get('paths'), dict) else {}
    return (app / str(paths.get('static') or './static') / 'tui').resolve()


def build_web(app: Path, config: dict, name: str, title: str, out: Optional[Path], started: float,
              progress: Callable[[str], None]) -> Package:
    """`--target web`: the TUI exported for the browser into the application's static folder, so the
    application's own server serves it (/static/tui/index.html) — the same origin as its pages, so the browser's
    cookies are the session. Nothing else is carried: the server is the application's."""
    folder = Path(out).resolve() if out else web_folder(app, config)
    page = export_tui(WEB, title, name, folder, progress)
    size = sum(f.stat().st_size for f in folder.glob('index.*') if f.is_file())
    return Package(path=page, folder=folder, size=size, seconds=time.monotonic() - started)


def server_url(server: str) -> str:
    """A hosted application's address, checked: http(s), a host, nothing after its path."""
    from urllib.parse import urlsplit
    parts = urlsplit(server.strip())
    if parts.scheme not in ('http', 'https') or not parts.netloc or parts.query or parts.fragment:
        raise PackageError(f'--server {server}: the address of the application, as https://kanban.example.com')
    return f'{parts.scheme}://{parts.netloc}{parts.path.rstrip("/")}'


def build(app: Path, on: str = 'tui', target: str = 'linux', out: Optional[Path] = None, with_data: bool = False,
          progress: Callable[[str], None] = print, server: Optional[str] = None) -> Package:
    """The package of `app` for `target`: the file, and the folder it holds (kept beside it, ready to run). With
    `server`, a client of the application hosted there: its program alone, which asks that server."""
    started = time.monotonic()
    app = Path(app).resolve()
    if on not in ('tui', 'desktop'):
        raise PackageError(f'--on {on}: a package\'s program is the TUI (--on tui) or a window (--on desktop)')
    if target not in TARGETS and target != WEB and target not in PHONES:
        raise PackageError(f'--target {target}: one of {", ".join([*TARGETS, WEB, *PHONES])}')
    if target in PHONES and (on != 'tui' or not server):
        raise PackageError(f'--target {target}: a phone runs no server of its own; its package is the TUI as a '
                           f'hosted application\'s client: --server https://... (--on tui)')
    if on == 'desktop' and target not in DESKTOP_LIBRARIES:
        if target == WEB:
            raise PackageError('--on desktop --target web: in a browser the pages are the web\'s own; '
                               '--target web puts the TUI there (--on tui)')
        raise PackageError(f'--on desktop --target {target}: a window of its own on Linux needs Qt WebEngine, '
                           f'about 550 MB; Linux\'s package is the TUI (--on tui)')
    if server is not None:
        if target == WEB:
            raise PackageError('--target web --server: the TUI in a browser asks the server that serves it; '
                               'put it in the hosted application (--target web, on its own folder)')
        server = server_url(server)
    config_file = app / 'quantum.config.yaml'
    if not config_file.is_file():
        raise PackageError(f'{app} has no quantum.config.yaml: `quantum package` takes an application\'s folder')
    config = yaml.safe_load(config_file.read_text(encoding='utf-8')) or {}
    name, title = app_name(app), app_title(app, config)
    if target == WEB:
        return build_web(app, config, name, title, out, started, progress)
    if target in PHONES:
        return build_phone(app, name, title, target, out, server, started, progress)
    out = Path(out or app / 'dist').resolve()
    kind = (f'{target}-desktop' if on == 'desktop' else target) + ('-client' if server else '')
    work = out / f'.{name}-{kind}'
    shutil.rmtree(work, ignore_errors=True)
    folder = work / (f'{title}.app' if target == 'macos' else name)
    work.mkdir(parents=True)

    # the client first: it is the program, and on a Mac the folder the rest goes into
    if on == 'desktop':
        folder, beside = desktop_program(target, title, name, work, progress)
    else:
        folder, beside = tui_program(target, title, name, work, folder, progress, server)

    libraries: Dict[str, str] = {}
    left_out: List[str] = []
    if not (server and on == 'tui'):            # a TUI that asks a hosted server needs nothing beside it
        beside.mkdir(parents=True)
        progress(f'Python {PYTHON_VERSION} for {target}')
        unpack_python(python_archive(target, progress), beside)
        site = beside / TARGETS[target]['site']
        if server:                              # a window on a hosted server: the window's libraries alone
            names = ['requests'] + DESKTOP_LIBRARIES[target]
        else:
            names = libraries_for(config) + (DESKTOP_LIBRARIES[target] if on == 'desktop' else [])
        libraries = install_libraries(target, site, names, progress)
        copy_quantum(site)
        if not server:
            left_out = copy_app(app, beside / 'app', config, with_data)
        from quantum.runtime.ui_tui import design_tokens
        (beside / 'package.json').write_text(json.dumps({
            'name': name, 'title': title, 'page': '/', 'program': on,
            'python': TARGETS[target]['python'],
            'args': ['-I', '-m', 'quantum.runtime.packaged_server', '--app', '{server}/app', '--name', name],
            'tokens': design_tokens(),
            **({'server': server} if server else {}),
        }, indent=2) + '\n', encoding='utf-8')

    suffix = '.tar.gz' if target == 'linux' else '.zip'
    archive = out / f'{name}-{kind}{suffix}'
    archive.unlink(missing_ok=True)
    progress(f'packing {archive.name}')
    (_tar if target == 'linux' else _zip)(folder, archive)
    kept = out / f'{name}-{kind}'             # the package unpacked, ready to run: <kept>/<name>/<name>
    shutil.rmtree(kept, ignore_errors=True)
    work.rename(kept)
    return Package(path=archive, folder=kept / folder.name, size=archive.stat().st_size,
                   seconds=time.monotonic() - started, libraries=libraries, left_out=left_out)


def tui_program(target: str, title: str, name: str, work: Path, folder: Path, progress: Callable[[str], None],
                server: Optional[str] = None):
    """The TUI's program, exported: (the folder it is in, the server folder beside it)."""
    made = export_tui(target, title, name, work, progress, server)
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
    return folder, server


def main(args) -> int:
    """The `quantum package` command."""
    try:
        made = build(Path(args.app), on=args.on, target=args.target, out=Path(args.out) if args.out else None,
                     with_data=args.with_data, server=getattr(args, 'server', None))
    except PackageError as exc:
        print(f'[ERROR] {exc}', file=sys.stderr)
        return 1
    if args.target == WEB:
        served = '' if args.out else '; the application serves it at /static/tui/index.html'
        print(f'{made.path} ({made.size / 1e6:.1f} MB, made in {made.seconds:.0f} s){served}')
        return 0
    print(f'{made.path} ({made.size / 1e6:.1f} MB, made in {made.seconds:.0f} s)')
    server = getattr(args, 'server', None)
    if server and server.startswith('http://') and not server.startswith(('http://127.', 'http://localhost')):
        print(f'{server} is not https: the session\'s cookie and what is typed cross the network unencrypted')
    if made.left_out:
        print(f'left out (the migrations make them when it starts; --with-data carries them): '
              f'{", ".join(made.left_out)}')
    return 0
