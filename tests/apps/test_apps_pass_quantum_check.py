"""The repository's apps pass `quantum check` (DEV-3): every SQL compiles
against the migrations' database and every field the pages read exists."""

import shutil
from pathlib import Path

import pytest

PROJECTS = Path(__file__).resolve().parents[2] / "projects"


@pytest.mark.parametrize("app", ["tarefas", "blog", "quantum-dashboard", "helpdesk", "shop-agent", "bank-transfer"])
def test_the_app_passes_quantum_check(app, tmp_path, monkeypatch):
    # DEV-3
    project = tmp_path / app
    shutil.copytree(PROJECTS / app, project, ignore=shutil.ignore_patterns("data", "__pycache__"))
    monkeypatch.chdir(project)
    from quantum.cli.migrations import MigrationRunner
    MigrationRunner(project).up()
    from quantum.cli.check import ProjectChecker
    checker = ProjectChecker(project, project / "quantum.config.yaml")
    assert [str(p) for p in checker.run()] == []
    assert checker.queries_checked > 0 and checker.notes == []
