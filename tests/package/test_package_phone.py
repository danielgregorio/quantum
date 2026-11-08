"""The phone (PLAN_PLATFORMS.md Phase 6, SPEC.md UI-22): `quantum package <app> --target android|ios --server ...` is
the TUI as a hosted application's client, with a touch screen's look (tests/tui/test_tui.py's TestTouch): an .apk
signed with a debug key, and the Xcode project a Mac builds and signs.

CI's package job makes both (its runner has the Android SDK); QUANTUM_PACKAGE_TESTS=1 runs them, and without the
Android SDK here the .apk is skipped unless this is CI.
"""

import os
import subprocess
import zipfile
from pathlib import Path

import pytest

from tests.package.test_package_kanban import summary

pytestmark = pytest.mark.skipif(not os.environ.get('QUANTUM_PACKAGE_TESTS'),
                                reason='QUANTUM_PACKAGE_TESTS=1 builds packages (network, Godot templates)')

KANBAN = Path(__file__).resolve().parents[2] / 'projects' / 'kanban'
SERVER = 'https://kanban.example.com'


def test_a_phone_needs_a_hosted_application(tmp_path):
    from quantum.runtime.package import PackageError, build
    with pytest.raises(PackageError, match='a phone runs no server of its own'):
        build(KANBAN, target='android', out=tmp_path, progress=print)


@pytest.mark.skipif(not (os.environ.get('ANDROID_HOME') or os.environ.get('CI')),
                    reason='the Android SDK (ANDROID_HOME) signs an .apk; CI has it')
def test_the_kanban_for_android(tmp_path):
    from quantum.runtime.package import build
    made = build(KANBAN, target='android', out=tmp_path, server=SERVER, progress=print)
    assert made.path.name == 'kanban-android.apk'
    with zipfile.ZipFile(made.path) as apk:
        names = set(apk.namelist())
    assert 'AndroidManifest.xml' in names and 'classes.dex' in names
    assert any(n.startswith('lib/arm64-v8a/') and n.endswith('.so') for n in names)
    # the TUI's files, which Godot's Android export lays out under assets/ one by one (no single .pck)
    assert sum(1 for n in names if n.startswith('assets/')) >= 3, sorted(names)[:40]
    # signed: the SDK's own apksigner says so
    tools = sorted((Path(os.environ['ANDROID_HOME']) / 'build-tools').iterdir())
    verified = subprocess.run([str(tools[-1] / 'apksigner'), 'verify', '--print-certs', str(made.path)],
                              capture_output=True, text=True)
    assert verified.returncode == 0 and 'Android Debug' in verified.stdout, verified.stderr
    summary(f'| Kanban, android, a client | {made.size / 1e6:.1f} MB | (built, signed with a debug key) | '
            f'made in {made.seconds:.0f} s |')


def test_the_kanban_for_ios(tmp_path):
    from quantum.runtime.package import build
    made = build(KANBAN, target='ios', out=tmp_path, server=SERVER, progress=print)
    assert made.path.name == 'kanban-ios.zip'
    with zipfile.ZipFile(made.path) as project:
        names = set(project.namelist())
    assert {'kanban.xcodeproj/project.pbxproj', 'kanban.pck'} <= names
    # the client's address and its touch look are in its pack: the TUI turns on touch on a phone itself
    assert b'quantum/server' in (made.folder / 'kanban.pck').read_bytes() or \
        b'kanban.example.com' in (made.folder / 'kanban.pck').read_bytes()
    summary(f'| Kanban, ios, a client | {made.size / 1e6:.1f} MB | (an Xcode project, a Mac builds it) | '
            f'made in {made.seconds:.0f} s |')
