"""
O instalador roda antes do Quantum existir, numa maquina que talvez nao
atenda os requisitos. Isso impoe restricoes que so um teste segura:

- Ele **nao pode importar quantum**. Se importasse, falharia com ImportError
  em vez de dizer o que falta.
- Ele **nao pode usar sintaxe nova**. Um f-string e erro de sintaxe no Python
  2 e no 3.5, e erro de sintaxe derruba o arquivo INTEIRO na compilacao — o
  script morreria com traceback exatamente na maquina velha para quem a
  checagem de versao existe.
- Ele precisa **diagnosticar antes de agir** e sair com codigo != 0 quando
  algo bloqueia, para servir em CI.
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
            "importar quantum faz o instalador morrer com ImportError em vez "
            "de dizer o que falta")

    def test_it_uses_no_syntax_that_breaks_an_old_interpreter(self, tree):
        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                offenders.append("f-string na linha {0}".format(node.lineno))
            elif isinstance(node, ast.NamedExpr):
                offenders.append("walrus na linha {0}".format(node.lineno))
            elif node.__class__.__name__ == "Match":
                offenders.append("match na linha {0}".format(node.lineno))
            elif isinstance(node, ast.AnnAssign):
                offenders.append("anotacao na linha {0}".format(node.lineno))
        assert offenders == [], offenders

    def test_it_only_uses_the_standard_library(self, tree):
        stdlib = set(sys.stdlib_module_names)
        stdlib.add("urllib2")          # Python 2, no ramo de compatibilidade
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
        # A suite roda em 3.12; se isto reprovar, o portao esta errado.
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
        # gunicorn nao roda no Windows, mas o Quantum roda.
        monkeypatch.setattr(installer.platform, "system", lambda: "Windows")
        check = installer.check_os()
        assert check.status == installer.WARN
        assert "waitress" in check.note

    def test_no_disk_space_is_blocking(self, installer, monkeypatch):
        class Usage(object):
            free = 1024 * 1024      # 1 MB
        monkeypatch.setattr(installer.shutil, "disk_usage", lambda p: Usage())
        assert installer.check_disk().status == installer.FAIL


class TestTheCommandLine:
    def run(self, *args):
        return subprocess.run(
            [sys.executable, str(INSTALLER)] + list(args),
            capture_output=True, text=True, timeout=300, cwd=str(REPO))

    def test_check_only_installs_nothing_and_says_so(self):
        result = self.run("--check")
        assert result.returncode == 0, result.stdout[-500:]
        assert "nada foi instalado" in result.stdout.lower()

    def test_help_explains_itself(self):
        result = self.run("--help")
        assert result.returncode == 0
        assert "--check" in result.stdout and "--venv" in result.stdout

    def test_an_unknown_option_is_refused(self):
        result = self.run("--faz-cafe")
        assert result.returncode != 0
        assert "desconhecida" in result.stdout.lower()

    def test_it_reports_the_requirements_before_doing_anything(self):
        result = self.run("--check")
        assert "Requisitos" in result.stdout
        assert "Python" in result.stdout
