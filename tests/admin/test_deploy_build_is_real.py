"""
The admin's deploy "build" step reported success without building.

It looked for src/cli/runner.py (removed by the packaging refactor), took the
"CLI not found, skipping compilation" branch, and then marked the step
"completed / Build successful" regardless. When the path DID resolve it slept
for a second and logged "Build completed: 0 errors, 0 warnings" without
invoking anything.

It now parses the project's .q files with the real parser. Parsing IS what
build means for a .q project — there is no compile-to-binary step — so a file
that does not parse is a 400 in production, which is exactly what a deploy
gate should stop.
"""

import pathlib
import sys
import types

import pytest

ADMIN = pathlib.Path(__file__).resolve().parents[2] / "quantum_admin"
if str(ADMIN) not in sys.path:
    sys.path.insert(0, str(ADMIN))


@pytest.fixture
def svc(tmp_path):
    from backend.deploy_service import DeployService

    s = DeployService.__new__(DeployService)
    s.quantum_root = str(tmp_path)
    (tmp_path / "quantum" / "cli").mkdir(parents=True)
    (tmp_path / "quantum" / "cli" / "runner.py").write_text("#", encoding="utf-8")
    (tmp_path / "projects" / "app").mkdir(parents=True)

    s.logs, s.steps = [], []
    s._log = lambda d, m: s.logs.append(m)
    s._update_step = lambda d, n, st, m: s.steps.append((n, st, m))
    return s, tmp_path / "projects" / "app"


def _deployment():
    return types.SimpleNamespace(project_name="app", status=None, error_message=None)


class TestItReallyBuilds:
    def test_a_valid_project_passes(self, svc):
        s, proj = svc
        (proj / "ok.q").write_text(
            '<q:component name="A"><p>oi</p></q:component>', encoding="utf-8")
        assert s._step_build(_deployment()) is True
        assert s.steps[-1][1] == "completed"
        assert "1 file" in s.steps[-1][2]

    def test_an_unparseable_file_fails_the_deploy(self, svc):
        s, proj = svc
        (proj / "ok.q").write_text(
            '<q:component name="A"><p>oi</p></q:component>', encoding="utf-8")
        (proj / "bad.q").write_text(
            '<q:component name="B"><p>sem fechar</q:component>', encoding="utf-8")
        assert s._step_build(_deployment()) is False
        assert s.steps[-1][1] == "failed"

    def test_the_failing_file_is_named_in_the_log(self, svc):
        s, proj = svc
        (proj / "bad.q").write_text(
            '<q:component name="B"><p>sem fechar</q:component>', encoding="utf-8")
        s._step_build(_deployment())
        assert any("bad.q" in line for line in s.logs)

    def test_an_empty_project_is_not_a_green_build(self, svc):
        s, _proj = svc
        assert s._step_build(_deployment()) is False
        assert s.steps[-1][1] == "failed"


class TestAMissingCompilerFails:
    def test_it_does_not_report_success(self, svc):
        s, proj = svc
        (proj / "ok.q").write_text(
            '<q:component name="A"><p>oi</p></q:component>', encoding="utf-8")
        (pathlib.Path(s.quantum_root) / "quantum" / "cli" / "runner.py").unlink()
        assert s._step_build(_deployment()) is False
        assert s.steps[-1][1] == "failed"
