"""
`quantum migrate up` executed the rollback files.

`migrate create` writes a PAIR — V001_name.sql and V001_name.down.sql — and
_get_pending_migrations globbed "*.sql", which matches both. Worse, the
rollback sorts FIRST ('.down.sql' < '.sql'), so `up` ran DROP TABLE before the
CREATE TABLE it belongs to, then recorded the version as applied.

On an already-migrated database that is data destruction from the command
whose entire job is to move forward.
"""

import sqlite3

import pytest

from quantum.cli.commands.migrate import MigrationRunner


@pytest.fixture
def project(tmp_path):
    mig = tmp_path / "migrations"
    mig.mkdir()
    (mig / "V001_create_users.sql").write_text(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT);\n"
        "INSERT INTO users (id, email) VALUES (1, 'ana@x.com');",
        encoding="utf-8",
    )
    (mig / "V001_create_users.down.sql").write_text(
        "DROP TABLE users;", encoding="utf-8"
    )
    (mig / "V002_add_name.sql").write_text(
        "ALTER TABLE users ADD COLUMN name TEXT;", encoding="utf-8"
    )
    (mig / "V002_add_name.down.sql").write_text(
        "DROP TABLE users;", encoding="utf-8"
    )
    return mig


def _pending(mig_dir):
    """Exercise the selection without needing a live database."""
    runner = MigrationRunner.__new__(MigrationRunner)
    runner.migrations_dir = mig_dir
    runner._get_applied_migrations = lambda: {}
    return runner._get_pending_migrations()


class TestSelection:
    def test_down_files_are_not_pending_migrations(self, project):
        names = [m.path.name for m in _pending(project)]
        assert not any(n.endswith(".down.sql") for n in names), names

    def test_the_real_migrations_are_still_picked_up(self, project):
        names = sorted(m.path.name for m in _pending(project))
        assert names == ["V001_create_users.sql", "V002_add_name.sql"]

    def test_versions_are_not_duplicated(self, project):
        versions = [m.version for m in _pending(project)]
        assert len(versions) == len(set(versions)), versions

    def test_order_is_by_version(self, project):
        assert [m.version for m in _pending(project)] == ["V001", "V002"]


class TestTheDestructionIsGone:
    def test_running_the_selected_files_in_order_leaves_the_table(self, project, tmp_path):
        """Execute exactly what `up` would execute, against a real sqlite file.

        Before the fix the first statement executed was `DROP TABLE users`.
        """
        db = tmp_path / "app.db"
        con = sqlite3.connect(str(db))
        for m in _pending(project):
            con.executescript(m.path.read_text(encoding="utf-8"))
        con.commit()
        rows = con.execute("SELECT id, email FROM users").fetchall()
        con.close()
        assert rows == [(1, "ana@x.com")]
