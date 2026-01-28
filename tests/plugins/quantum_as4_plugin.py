"""
Pytest plugin that discovers and executes AS4 transpiler test scripts.

Scans quantum-as4/ for test_*.py files and runs each as a subprocess.
test_demos.py (Selenium) is excluded by default.

Strategy:
- pytest_ignore_collect prevents default Python import of AS4 files
- pytest_collect_file is never called for ignored files, so we inject items
  during pytest_make_collect_report / pytest_collection_modifyitems instead
"""

import subprocess
import sys
import pytest
from pathlib import Path


_EXCLUDED = {"test_demos.py"}
_AS4_DIR = Path(__file__).resolve().parent.parent.parent / "quantum-as4"


def _is_as4_test(path: Path) -> bool:
    if path.suffix != ".py" or not path.name.startswith("test_"):
        return False
    try:
        path.resolve().relative_to(_AS4_DIR.resolve())
        return True
    except ValueError:
        return False


def pytest_ignore_collect(collection_path, config):
    """Block default Python import of AS4 test files."""
    if _is_as4_test(collection_path):
        return True
    return None


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(session, config, items):
    """Inject AS4 subprocess test items after normal collection."""
    if not _AS4_DIR.is_dir():
        return

    for f in sorted(_AS4_DIR.glob("test_*.py")):
        if f.name in _EXCLUDED:
            continue
        item = AS4TestItem.from_parent(session, name=f.stem, path=f)
        items.append(item)


class AS4TestItem(pytest.Item):
    """Run an AS4 test script as a subprocess."""

    def __init__(self, name, parent, path=None):
        super().__init__(name, parent)
        if path:
            self._script_path = path
        self.add_marker(pytest.mark.transpiler)
        self.add_marker(pytest.mark.as4)
        if "demo" in name.lower():
            self.add_marker(pytest.mark.selenium)

    def runtest(self):
        result = subprocess.run(
            [sys.executable, str(self._script_path)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(self._script_path.parent),
        )
        if result.returncode != 0:
            output = result.stdout + "\n" + result.stderr
            pytest.fail(f"AS4 script {self.name} exited with code {result.returncode}\n{output}")

    def repr_failure(self, excinfo):
        return f"AS4 transpiler test failed: {self.name}\n{excinfo.getrepr()}"

    def reportinfo(self):
        return self._script_path, None, f"as4:{self.name}"
