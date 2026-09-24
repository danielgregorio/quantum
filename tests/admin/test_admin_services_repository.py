"""Services of the reading screens (quantum_admin/services/repository.py)."""

import hashlib
import sqlite3

import pytest

from quantum_admin.services import repository as svc


@pytest.fixture(autouse=True)
def root(isolated_admin):
    base = isolated_admin
    (base / "components").mkdir()
    (base / "components" / "a.q").write_text(
        '<q:component name="A"><q:agent name="helper" model="phi3" provider="ollama"/></q:component>', encoding="utf-8")
    (base / "examples").mkdir()
    (base / "examples" / "e.q").write_text('<q:component name="E"><q:team name="crew" supervisor="boss"/></q:component>',
                                          encoding="utf-8")
    (base / "tests").mkdir()
    (base / "tests" / "test_x.py").write_text("def test_x():\n    pass\n", encoding="utf-8")
    (base / "README.md").write_text("# hi\nline 2\n", encoding="utf-8")
    (base / ".env").write_text("PASSWORD=secret\n", encoding="utf-8")
    return base


def test_the_dashboard_really_measures():
    # the screen looked in src/core/... and showed 0 features, 0 parsers, 0 executors
    s = svc.dashboard_stats()
    assert (s["components"], s["tests"], s["examples"]) == (1, 1, 1)
    assert s["features"] > 10 and s["parser_tags"] > 20 and s["executors"] > 20


def test_features_come_from_the_real_manifests():
    r = svc.list_features()
    names = {f["name"] for f in r["features"]}
    assert {"conditionals", "loops"} <= names
    assert sum(r["by_status"].values()) == len(r["features"])


def test_declared_agents_and_teams():
    r = svc.list_agents()
    assert r["agents"] == [{"name": "helper", "model": "phi3", "provider": "ollama", "source": "components/a.q"}]
    assert r["teams"] == [{"name": "crew", "supervisor": "boss", "source": "examples/e.q"}]


class TestSource:
    def test_it_reads_a_file_of_the_root(self):
        r = svc.read_source("README.md")
        assert (r["type"], r["lines"], r["content"]) == ("Markdown", 3, "# hi\nline 2\n")

    @pytest.mark.parametrize("path", [".env", "quantum_admin/settings/connectors.yaml", "data.db"])
    def test_files_with_credentials_are_refused(self, root, path):
        (root / "data.db").write_bytes(b"")
        (root / "quantum_admin" / "settings" / "connectors.yaml").write_text("- password: x\n", encoding="utf-8")
        with pytest.raises(svc.RepositoryError, match="credentials"):
            svc.read_source(path)

    def test_outside_the_root_and_a_neighbour_folder(self, root):
        neighbour = root.parent / (root.name + "2")
        neighbour.mkdir()
        (neighbour / "x.txt").write_text("x", encoding="utf-8")
        for path in ("../x.txt", f"../{neighbour.name}/x.txt"):
            with pytest.raises(svc.RepositoryError, match="outside"):
                svc.read_source(path)


def test_databases_are_opened_read_only(root):
    db = root / "app.db"
    connection = sqlite3.connect(db)
    connection.executescript("create table items (id integer); insert into items values (1), (2);")
    connection.commit()
    connection.close()
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    r = svc.list_databases()
    [b] = r["databases"]
    assert b["path"] == "app.db" and b["tables"] == [{"name": "items", "rows": 2}]
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before
    assert not (root / "app.db-journal").exists() and not (root / "app.db-wal").exists()


def test_the_job_queue(root):
    assert svc.list_jobs()["found"] is False
    connection = sqlite3.connect(root / "quantum_jobs.db")
    connection.executescript(
        "create table quantum_jobs (id integer primary key autoincrement, name text, queue text, status text,"
        " attempts integer, max_attempts integer, created_at text, error text);"
        "insert into quantum_jobs (name, queue, status, attempts, max_attempts) values"
        " ('a','q','pending',0,3), ('b','q','failed',3,3), ('c','q','pending',0,3);")
    connection.commit()
    connection.close()
    r = svc.list_jobs(limit=2)
    assert r["counts"] == {"pending": 2, "running": 0, "completed": 0, "failed": 1} and r["total"] == 3
    assert [j["name"] for j in r["jobs"]] == ["c", "b"]
