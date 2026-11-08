"""The Godot 4 binary a game is checked and replayed with.

One place knows the version (``GODOT_VERSION``). The binary is looked for,
in this order:

1. ``$QUANTUM_GODOT`` — a path, for a developer who has their own build;
2. ``godot4`` / ``godot`` on ``$PATH``, if it reports the pinned version;
3. the cache, ``~/.cache/quantum/godot/<version>/`` (``$QUANTUM_GODOT_CACHE``
   overrides the directory), where ``ensure_godot(download=True)`` puts the
   official headless-capable release from GitHub.

Nothing here imports Godot into Python: Godot is a subprocess
(``run_godot``), and its output is parsed for the lines that mean a script
did not load (``script_errors``), since the process exits 0 either way.
"""

from __future__ import annotations

import os
import platform
import shutil
import stat
import subprocess
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import List, Optional, Sequence

GODOT_VERSION = '4.4.1'

_RELEASE_URL = ('https://github.com/godotengine/godot/releases/download/'
                '{version}-stable/Godot_v{version}-stable_{platform}.zip')
# The same release from Godot's own download service (what godotengine.org's buttons link to), asked when
# GitHub's release CDN keeps failing; its `platform` names, by the release's.
_GODOT_DOWNLOADS_URL = ('https://downloads.godotengine.org/?version={version}&flavor=stable'
                        '&slug={platform}.zip&platform={service}')
_SERVICE_PLATFORMS = {'linux.x86_64': 'linux.64', 'linux.arm64': 'linux.arm64', 'win64.exe': 'windows.64'}

# The official release names, by (system, machine).
_PLATFORMS = {
    ('Linux', 'x86_64'): 'linux.x86_64',
    ('Linux', 'aarch64'): 'linux.arm64',
    ('Darwin', 'x86_64'): 'macos.universal',
    ('Darwin', 'arm64'): 'macos.universal',
    ('Windows', 'AMD64'): 'win64.exe',
}

# A line of Godot's output that means a script did not load or failed at
# run time. ``--import`` and a run both exit 0 on these.
_ERROR_PREFIXES = ('SCRIPT ERROR:', 'ERROR:', 'USER ERROR:')


class GodotNotFound(RuntimeError):
    """No Godot binary of the pinned version is available."""


def release_platform() -> str:
    key = (platform.system(), platform.machine())
    try:
        return _PLATFORMS[key]
    except KeyError:
        raise GodotNotFound(f'no official Godot {GODOT_VERSION} release for {key[0]} {key[1]}')


def cache_dir() -> Path:
    base = os.environ.get('QUANTUM_GODOT_CACHE')
    if base:
        return Path(base).expanduser() / GODOT_VERSION
    return Path.home() / '.cache' / 'quantum' / 'godot' / GODOT_VERSION


def _cached_binary() -> Optional[Path]:
    d = cache_dir()
    if not d.is_dir():
        return None
    for p in sorted(d.iterdir()):
        if p.is_file() and p.name.startswith('Godot_v') and not p.name.endswith('.zip'):
            return p
    return None


def _reports_version(binary: Path) -> bool:
    try:
        out = subprocess.run([str(binary), '--headless', '--version'],
                             capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return out.stdout.strip().startswith(GODOT_VERSION)


def find_godot() -> Optional[Path]:
    """The Godot binary to use, or None. Does not download."""
    explicit = os.environ.get('QUANTUM_GODOT')
    if explicit:
        p = Path(explicit).expanduser()
        return p if p.is_file() else None
    for name in ('godot4', 'godot'):
        found = shutil.which(name)
        if found and _reports_version(Path(found)):
            return Path(found)
    return _cached_binary()


# A release asset is served through GitHub's CDN, which now and then answers 502/503/504, for a moment or
# for a while (on 2026-11-08, for an hour, every try from CI's runners): each source is tried again after
# these many seconds before the next source is asked.
RETRY_WAITS = (5, 15, 30, 60)


def _fetch_to(url: str, target: Path, progress=None, sleep=None, waits=None) -> None:
    """The bytes at `url`, written to `target` a chunk at a time; a server's failure (5xx) or a dropped
    connection is tried again (RETRY_WAITS). `target` is whole or absent: a part is written beside it first."""
    part = target.with_name(target.name + '.part')
    for wait in (*(RETRY_WAITS if waits is None else waits), None):
        try:
            with urllib.request.urlopen(url, timeout=300) as resp, open(part, 'wb') as out:
                shutil.copyfileobj(resp, out, 1 << 20)
            part.replace(target)
            return
        except urllib.error.HTTPError as exc:
            part.unlink(missing_ok=True)
            if exc.code < 500 or wait is None:
                raise
            why = f'HTTP {exc.code}'
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            part.unlink(missing_ok=True)
            if wait is None:
                raise
            why = str(getattr(exc, 'reason', exc))
        if progress:
            progress(f'{why}; trying again in {wait}s')
        (sleep or time.sleep)(wait)


def fetch_release(urls: Sequence[str], target: Path, progress=None, check=None) -> Path:
    """The first of `urls` that answers, in `target` (each tried again on a 5xx before the next is asked).
    `check(target)` raises when what came is not the file (an error page): the next source is asked."""
    last: Exception = GodotNotFound('no source')
    for url in urls:
        if progress:
            progress(f'downloading {url}')
        try:
            _fetch_to(url, target, progress)
            if check:
                check(target)
            return target
        except (urllib.error.URLError, TimeoutError, ConnectionError, zipfile.BadZipFile, GodotNotFound) as exc:
            last = exc
            target.unlink(missing_ok=True)
            if progress:
                progress(f'{url} failed: {exc}')
    raise last


def release_urls(plat: str) -> List[str]:
    """Where the pinned release is fetched from, in order: GitHub, then Godot's own download service."""
    urls = [_RELEASE_URL.format(version=GODOT_VERSION, platform=plat)]
    if plat in _SERVICE_PLATFORMS:
        urls.append(_GODOT_DOWNLOADS_URL.format(version=GODOT_VERSION, platform=plat,
                                                service=_SERVICE_PLATFORMS[plat]))
    return urls


def templates_urls() -> List[str]:
    """Where the export templates of the pinned release are fetched from (about 1.2 GB), in order."""
    return [f'https://github.com/godotengine/godot/releases/download/{GODOT_VERSION}-stable/'
            f'Godot_v{GODOT_VERSION}-stable_export_templates.tpz',
            f'https://downloads.godotengine.org/?version={GODOT_VERSION}&flavor=stable'
            f'&slug=export_templates.tpz&platform=templates']


def download_godot(progress=None) -> Path:
    """Download the pinned release into the cache and return the binary."""
    plat = release_platform()
    if plat.startswith('macos'):
        raise GodotNotFound('the macOS release is an .app bundle; set QUANTUM_GODOT to its '
                            'Contents/MacOS/Godot')
    d = cache_dir()
    d.mkdir(parents=True, exist_ok=True)
    archive = d / f'Godot_v{GODOT_VERSION}-stable_{plat}.zip'

    def has_binary(path: Path) -> None:
        with zipfile.ZipFile(path) as zf:
            if not any(n.startswith('Godot_v') for n in zf.namelist()):
                raise GodotNotFound(f'{path.name} holds no Godot binary')

    fetch_release(release_urls(plat), archive, progress, check=has_binary)
    with zipfile.ZipFile(archive) as zf:
        names = [n for n in zf.namelist() if n.startswith('Godot_v')]
        zf.extract(names[0], d)
    archive.unlink(missing_ok=True)
    binary = d / names[0]
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    if progress:
        progress(f'installed {binary}')
    return binary


def ensure_godot(download: bool = False, progress=None) -> Path:
    """The Godot binary, downloading it into the cache when asked to.

    Raises GodotNotFound when there is none and ``download`` is false.
    """
    found = find_godot()
    if found:
        return found
    if download:
        return download_godot(progress)
    raise GodotNotFound(
        f'Godot {GODOT_VERSION} was not found. Run `python scripts/godot.py install` '
        f'(downloads it into {cache_dir()}), or set QUANTUM_GODOT to a binary.')


def run_godot(args: Sequence[str], binary: Optional[Path] = None,
              timeout: float = 300) -> subprocess.CompletedProcess:
    """Run Godot headless with ``args``; captures its output."""
    binary = binary or ensure_godot()
    return subprocess.run([str(binary), '--headless', *args],
                          capture_output=True, text=True, timeout=timeout)


def script_errors(output: str) -> List[str]:
    """The lines of Godot's output that report an error (``SCRIPT ERROR:``,
    ``ERROR:``), each with its ``at:`` line when one follows."""
    lines = output.splitlines()
    errors = []
    for i, line in enumerate(lines):
        if line.lstrip().startswith(_ERROR_PREFIXES):
            msg = line.strip()
            if i + 1 < len(lines) and lines[i + 1].lstrip().startswith('at:'):
                msg += ' ' + lines[i + 1].strip()
            errors.append(msg)
    return errors


def check_project(project_dir: Path, binary: Optional[Path] = None) -> List[str]:
    """Import the project and load its main scene, headless; return the errors.

    An empty list means every script parsed and the first frames ran clean.
    """
    project_dir = Path(project_dir)
    if not (project_dir / 'project.godot').is_file():
        return [f'{project_dir} has no project.godot']
    imported = run_godot(['--path', str(project_dir), '--import'], binary)
    errors = script_errors(imported.stdout + imported.stderr)
    if errors:
        return errors
    ran = run_godot(['--path', str(project_dir), '--quit-after', '3'], binary)
    return script_errors(ran.stdout + ran.stderr)
