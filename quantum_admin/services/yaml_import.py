"""Imports the projects from the .q screens' old YAML into the database (admin.import.*).

The .q screens stored projects in quantum_admin/settings/projects.yaml; the
FastAPI (crud), in the database. Measured on 2026-09-10: no project in common —
the 14 real ones were in the YAML, and the database only had the three demo
ones from seed_db. The admin.projects service uses the database; this import
brings the projects there.

Connectors are NOT imported: the backend library (connector_service) keeps
them in settings/connectors.yaml, the same file as the screens — there is no
split. The database's `connectors` table is not used by anything. What the
import does with connectors is only point out the ones tied to a project by
the old YAML id (a uuid), which connector_service does not recognize.

Guarantees (the data belongs to the owner, it cannot be recreated):
  - before writing, it copies the database file to quantum_admin/backups/;
  - it never changes or deletes the YAML files;
  - idempotent: a project that already exists (same name, case-insensitive)
    is skipped.
"""

import datetime
import shutil
from pathlib import Path

import yaml

from quantum.services import service
from quantum_admin.services._base import root, session, settings_dir


def _read_yaml(name):
    file = settings_dir() / name
    if not file.is_file():
        return []
    data = yaml.safe_load(file.read_text(encoding="utf-8")) or []
    return data if isinstance(data, list) else []


def _date(value):
    if isinstance(value, datetime.datetime):
        return value
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


def _models():
    from quantum_admin.core import models
    return models


@service("admin.import.pending")
def pending():
    """YAML projects the database does not have yet, and connectors tied to old ids."""
    models = _models()
    projects = _read_yaml("projects.yaml")
    with session() as db:
        names = {(p.name or "").lower() for p in db.query(models.Project).all()}
    return {
        "projects": [p.get("name") for p in projects if p.get("name") and p["name"].lower() not in names],
        "connectors_to_review": _connectors_with_old_id(projects),
    }


def _connectors_with_old_id(projects):
    yaml_ids = {str(p.get("id")): p.get("name") for p in projects if p.get("id")}
    to_review = []
    for c in _read_yaml("connectors.yaml"):
        owner = c.get("application_id")
        if owner is not None and str(owner) in yaml_ids:
            to_review.append(f"{c.get('name')} (project {yaml_ids[str(owner)]})")
    return to_review


def _backup():
    from quantum_admin.core import database
    file = database.engine.url.database
    if database.engine.url.get_backend_name() != "sqlite" or not file or not Path(file).is_file():
        return None
    target = root() / "quantum_admin" / "backups"
    target.mkdir(parents=True, exist_ok=True)
    copy = target / f"quantum_admin-{datetime.datetime.now():%Y%m%d-%H%M%S}.db"
    database.engine.dispose()               # nothing pending on open connections
    shutil.copy2(file, copy)
    return str(copy)


@service("admin.import.run")
def run():
    """Imports the missing projects; returns the report. Does not touch the YAML files."""
    models = _models()
    projects = _read_yaml("projects.yaml")
    missing = pending()
    report = {"backup": None, "projects": [], "connectors_to_review": missing["connectors_to_review"]}
    if not missing["projects"]:
        return report
    report["backup"] = _backup()
    with session() as db:
        names = {(p.name or "").lower() for p in db.query(models.Project).all()}
        for item in projects:
            name = (item.get("name") or "").strip()
            if not name or name.lower() in names:
                continue
            project = models.Project(
                name=name, description=item.get("description") or "",
                status=item.get("status") or "active",
                source_path=(item.get("source_path") or "").replace("\\", "/"))
            created, changed = _date(item.get("created_at")), _date(item.get("updated_at"))
            if created:
                project.created_at = created
            if changed:
                project.updated_at = changed
            db.add(project)
            names.add(name.lower())
            report["projects"].append(name)
    return report
