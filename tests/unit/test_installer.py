"""
The installer runs before Quantum exists, on a machine that may not meet the
requirements. That imposes constraints only a test holds:

- It **cannot import quantum**. If it did, it would fail with ImportError
  instead of saying what is missing.
- It **cannot use new syntax**. An f-string is a syntax error on Python 2 and
  3.5, and a syntax error brings the WHOLE file down at compile time — the
  script would die with a traceback exactly on the old machine the version
  check exists for.
- It must **diagnose before acting** and exit with a non-zero code when
  something blocks, so it works in CI.
"""

import ast
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
INSTALLER = REPO / "install.py"


@pytest.fixture(scope="module")
def source():
    return INSTALLER.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def tree(source):
    return ast.parse(source)


@pytest.fixture(scope="module")
def installer():
    sys.path.insert(0, str(REPO))
    import importlib
    return importlib.import_module("install")


class TestItRunsOnTheMachineThatNeedsIt:
    def test_it_exists_and_parses(self, tree):
        assert tree is not None

    def test_it_imports_nothing_from_quantum(self, tree):
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
        assert "quantum" not in imported, (
            "importing quantum makes the installer die with ImportError instead "
            "of saying what is missing")

    def test_it_uses_no_syntax_that_breaks_an_old_interpreter(self, tree):
        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                offenders.append("f-string on line {0}".format(node.lineno))
            elif isinstance(node, ast.NamedExpr):
                offenders.append("walrus on line {0}".format(node.lineno))
            elif node.__class__.__name__ == "Match":
                offenders.append("match on line {0}".format(node.lineno))
            elif isinstance(node, ast.AnnAssign):
                offenders.append("annotation on line {0}".format(node.lineno))
        assert offenders == [], offenders

    def test_it_only_uses_the_standard_library(self, tree):
        stdlib = set(sys.stdlib_module_names)
        stdlib.add("urllib2")          # Python 2, in the compatibility branch
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
        assert imported <= stdlib, imported - stdlib


class TestTheDiagnosis:
    def test_every_check_returns_a_known_status(self, installer):
        for check in installer.run_checks():
            assert check.status in (installer.OK, installer.WARN, installer.FAIL)
            assert check.name and check.found

    def test_it_recognises_this_python_as_good_enough(self, installer):
        # The suite runs on 3.12; if this fails, the gate is wrong.
        assert installer.check_python().status != installer.FAIL

    def test_an_old_python_is_blocked_with_a_useful_note(self, installer, monkeypatch):
        class FakeVersion(tuple):
            pass
        monkeypatch.setattr(installer.sys, "version_info", (3, 8, 10))
        check = installer.check_python()
        assert check.status == installer.FAIL
        assert "3.11" in check.note

    def test_it_finds_the_project(self, installer):
        assert installer.check_project().status == installer.OK

    def test_a_missing_project_is_blocking(self, installer, monkeypatch, tmp_path):
        monkeypatch.setattr(installer, "PROJECT_ROOT", str(tmp_path))
        assert installer.check_project().status == installer.FAIL

    def test_windows_is_a_warning_not_a_block(self, installer, monkeypatch):
        # gunicorn does not run on Windows, but Quantum does.
        monkeypatch.setattr(installer.platform, "system", lambda: "Windows")
        check = installer.check_os()
        assert check.status == installer.WARN
        assert "waitress" in check.note

    def test_no_disk_space_is_blocking(self, installer, monkeypatch):
        class Usage(object):
            free = 1024 * 1024      # 1 MB
        monkeypatch.setattr(installer.shutil, "disk_usage", lambda p: Usage())
        assert installer.check_disk().status == installer.FAIL


class TestConcurrentChecks:
    def test_two_checks_at_once_do_not_trip_each_other(self):
        """The write probe had a fixed name: two parallel --check runs (the
        suite under xdist) removed each other's file and failed."""
        procs = [subprocess.Popen([sys.executable, str(INSTALLER), "--check"],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  cwd=str(REPO)) for _ in range(4)]
        codes = [p.wait(timeout=300) for p in procs]
        for p in procs:
            p.stdout.close()
        assert codes == [0, 0, 0, 0]


class TestTheCommandLine:
    def run(self, *args):
        return subprocess.run(
            [sys.executable, str(INSTALLER)] + list(args),
            capture_output=True, text=True, timeout=300, cwd=str(REPO))

    def test_check_only_installs_nothing_and_says_so(self):
        result = self.run("--check")
        assert result.returncode == 0, result.stdout[-500:]
        assert "nothing was installed" in result.stdout.lower()

    def test_help_explains_itself(self):
        result = self.run("--help")
        assert result.returncode == 0
        assert "--check" in result.stdout and "--venv" in result.stdout

    def test_an_unknown_option_is_refused(self):
        result = self.run("--make-coffee")
        assert result.returncode != 0
        assert "unknown option" in result.stdout.lower()

    def test_it_reports_the_requirements_before_doing_anything(self):
        result = self.run("--check")
        assert "Requirements" in result.stdout
        assert "Python" in result.stdout
