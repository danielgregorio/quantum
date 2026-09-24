"""admin.import.*: the projects of the .q screens' old YAML go into the database without losing anything."""

import hashlib

import pytest
import yaml
from sqlalchemy import create_engine

from quantum_admin.core import models
from quantum_admin.services import _base
from quantum_admin.services import projects, yaml_import

PROJECTS = [
    {"id": "uuid-blog", "name": "blog", "description": "the blog", "status": "active",
     "source_path": "projects/blog", "created_at": "2026-01-02T03:04:05", "updated_at": "2026-02-03T04:05:06",
     "config": {"port": 8081}, "environments": []},
    {"id": "uuid-rag", "name": "archived-demo", "description": "", "status": "archived",
     "source_path": "projects\\archived-demo", "created_at": "2026-01-01T00:00:00"},
]
CONNECTORS = [
    {"id": "c-redis", "name": "cache", "type": "cache", "provider": "redis", "scope": "public"},
    {"id": "c-pg", "name": "blog pg", "type": "database", "provider": "postgres",
     "scope": "application", "application_id": "uuid-blog"},
]


@pytest.fixture(autouse=True)
def isolated(isolated_admin):
    folder = isolated_admin / "quantum_admin" / "settings"
    (folder / "projects.yaml").write_text(yaml.safe_dump(PROJECTS), encoding="utf-8")
    (folder / "connectors.yaml").write_text(yaml.safe_dump(CONNECTORS), encoding="utf-8")
    return isolated_admin


def _hash(folder):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob("*.yaml"))}


def test_pending_lists_missing_projects_and_connectors_tied_to_an_old_id():
    projects.create_project("Blog")          # already in the database (a different case counts as equal)
    assert yaml_import.pending() == {"projects": ["archived-demo"],
                                     "connectors_to_review": ["blog pg (project blog)"]}


def test_it_imports_keeping_the_fields():
    r = yaml_import.run()
    assert r["projects"] == ["blog", "archived-demo"]
    with _base.session() as db:
        blog = db.query(models.Project).filter_by(name="blog").one()
        rag = db.query(models.Project).filter_by(name="archived-demo").one()
        assert (blog.description, blog.created_at.isoformat(), rag.status, rag.source_path) == \
            ("the blog", "2026-01-02T03:04:05", "archived", "projects/archived-demo")


def test_connectors_do_not_go_to_the_database():
    # the database's connectors table is not used by the library; they stay in the YAML
    yaml_import.run()
    with _base.session() as db:
        assert db.query(models.Connector).count() == 0
    assert len(_base.connectors().list_connectors()) == 2


def test_a_backup_first_and_the_yaml_untouched(isolated):
    projects.create_project("existing")     # the database already has data: the backup must hold it
    before = _hash(isolated / "quantum_admin" / "settings")
    r = yaml_import.run()
    assert r["backup"]
    copy = create_engine(f"sqlite:///{r['backup']}")
    with copy.connect() as connection:
        names = [row[0] for row in connection.exec_driver_sql("select name from projects")]
    copy.dispose()
    assert names == ["existing"]
    assert _hash(isolated / "quantum_admin" / "settings") == before


def test_idempotent():
    yaml_import.run()
    second = yaml_import.run()
    assert second["backup"] is None and second["projects"] == []
    assert len(projects.list_projects()) == 2
