"""Deleting a project broke, or left garbage pointing at it.

`Project` declared `cascade="all, delete-orphan"` for THREE relationships —
datasources, components, endpoints — and nineteen tables have a foreign key to
`projects.id`. The other sixteen had no relationship at all, so
`db.delete(project)` did not touch them:

  * the eight with a NOT NULL `project_id` violated the foreign key. With
    SQLite enforcing foreign keys that is an IntegrityError, that is an HTTP
    500 when deleting any project that had been used; without enforcing them
    (SQLite's default) the rows kept pointing at a project that no longer
    exists.
  * the eight nullable ones were orphaned, and `secrets`/`port_allocations`
    held resources of a project nobody can see any more.

These tests run with `PRAGMA foreign_keys=ON`, where the defect is an error
instead of silent corruption.
"""

import pathlib
import sys

import pytest

ADMIN = pathlib.Path(__file__).resolve().parents[2] / "quantum_admin"
for path in (str(ADMIN), str(ADMIN / "backend")):
    if path not in sys.path:
        sys.path.insert(0, path)

pytest.importorskip("sqlalchemy")

from sqlalchemy import create_engine, event                    # noqa: E402
from sqlalchemy.orm import sessionmaker                        # noqa: E402

from backend import crud, models                               # noqa: E402


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'admin.db'}")

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, _record):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    models.Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _with_children(db):
    """A project with one row in each child table the policy knows."""
    project = models.Project(name="app", description="x")
    db.add(project)
    db.commit()

    created = {}
    for model, column, _action in crud._project_child_tables():
        row = model()
        setattr(row, column, project.id)
        # Fill in the NOT NULL columns without a default, so the row really exists.
        for col in model.__table__.columns:
            if col.name == column:
                continue
            type_ = col.type.python_type if hasattr(col.type, 'python_type') \
                else str
            if col.primary_key:
                # An integer primary key autoincrements; a text one (Connector.id)
                # needs a value.
                if type_ is not int and col.default is None:
                    setattr(row, col.name, f"{model.__name__}-1")
                continue
            if col.nullable or col.default is not None or col.server_default:
                continue
            if type_ is int:
                value = 1
            elif type_ is float:
                value = 1.0
            elif type_ is bool:
                value = False
            else:
                value = "x"
            setattr(row, col.name, value)
        db.add(row)
        created[model.__name__] = (model, column, _action)
    db.commit()
    return project, created


class TestEveryChildTableHasAPolicy:
    def test_introspection_covers_every_foreign_key_to_projects(self):
        """No table with a project_id is left out without someone deciding."""
        covered = {m.__name__ for m, _c, _a in crud._project_child_tables()}
        # 19 tables point to projects.id.
        assert len(covered) == 19, sorted(covered)

    def test_a_table_without_a_policy_is_an_error_not_silence(self, monkeypatch):
        policy = dict(crud._PROJECT_CHILD_POLICY)
        policy.pop('TestRun')
        monkeypatch.setattr(crud, '_PROJECT_CHILD_POLICY', policy)
        with pytest.raises(RuntimeError, match="TestRun"):
            crud._project_child_tables()


class TestDeletingAUsedProject:
    def test_it_does_not_raise_with_foreign_keys_enforced(self, db):
        project, _ = _with_children(db)
        assert crud.delete_project(db, project.id) is True
        assert crud.get_project(db, project.id) is None

    def test_the_not_null_children_are_gone(self, db):
        project, created = _with_children(db)
        pid = project.id
        crud.delete_project(db, pid)

        for name, (model, column, action) in created.items():
            if action != 'delete':
                continue
            left = db.query(model).filter(
                getattr(model, column) == pid).count()
            assert left == 0, f"{name} kept {left} orphans"

    def test_the_history_loses_its_owner_and_is_not_deleted(self, db):
        project, created = _with_children(db)
        pid = project.id
        crud.delete_project(db, pid)

        for name, (model, column, action) in created.items():
            if action != 'null':
                continue
            assert db.query(model).filter(
                getattr(model, column) == pid).count() == 0, name
            # The row still exists — it only lost its owner.
            assert db.query(model).count() >= 1, f"{name} was deleted"

    def test_the_audit_log_survives(self, db):
        """Deleting the audit_log with the project would delete the record
        that the project was deleted."""
        project, _ = _with_children(db)
        pid = project.id
        before = db.query(models.AuditLog).count()
        crud.delete_project(db, pid)
        assert db.query(models.AuditLog).count() == before

    def test_a_secret_does_not_become_global(self, db):
        """project_id=NULL on a secret would make it visible to other projects."""
        project, _ = _with_children(db)
        pid = project.id
        crud.delete_project(db, pid)
        assert db.query(models.Secret).filter(
            models.Secret.project_id.is_(None)).count() == 0

    def test_the_allocated_port_is_released(self, db):
        project, _ = _with_children(db)
        crud.delete_project(db, project.id)
        assert db.query(models.PortAllocation).count() == 0

    def test_a_missing_project_still_returns_false(self, db):
        assert crud.delete_project(db, 99999) is False

    def test_another_project_is_not_affected(self, db):
        project, created = _with_children(db)
        other = models.Project(name="other")
        db.add(other)
        db.commit()
        model, column, _a = created['Datasource']
        kept = model(name="d", type="sqlite", connection_type="local")
        setattr(kept, column, other.id)
        db.add(kept)
        db.commit()

        crud.delete_project(db, project.id)

        assert crud.get_project(db, other.id) is not None
        assert db.query(models.Datasource).filter(
            models.Datasource.project_id == other.id).count() == 1
