"""Services of the Projects area (admin.projects.*).

Ported from components/admin/applications.q, which did everything in q:python
over quantum_admin/settings/projects.yaml. The preserved behaviours:

  - create requires a unique name (case-insensitive) and creates the project
    folder with components/, static/ and a default quantum.config.yaml,
    without overwriting one that already exists;
  - sync registers each folder of projects/ that is not a project yet,
    ignoring the ones starting with "." or "_";
  - delete removes only the record, never the files;
  - the listing shows the process state, port, whether there is a config, how
    many .q components and how many connectors the project has.

What changed on purpose:
  - the data goes to the admin database (the same as the FastAPI's), not to the YAML;
  - an invalid or repeated name is an error — the old screen silently ignored
    it and redirected as if it had created it;
  - the project path cannot leave the root (the screen accepted any);
  - the default config listens on 127.0.0.1 without debug (it was 0.0.0.0 with debug).
"""

import datetime
from pathlib import Path

import yaml

from quantum.services import service
from quantum_admin.services._base import connectors, process_status, root, session

DEFAULT_CONFIG = {
    "server": {"port": 8080, "host": "127.0.0.1", "debug": False},
    "paths": {"components": "./components", "static": "./static"},
}


class ProjectError(ValueError):
    """Invalid request for the Projects area (the message is for whoever uses the screen)."""


def _crud():
    from quantum_admin.core import crud, models
    return crud, models


def _folder(source_path: str) -> Path:
    base = root()
    folder = (base / (source_path or "")).resolve()
    if folder != base and base not in folder.parents:
        raise ProjectError(f"the project path must be inside {base}: {source_path!r}")
    return folder


def _config_from_disk(folder: Path) -> dict:
    file = folder / "quantum.config.yaml"
    if not file.is_file():
        return {}
    try:
        return yaml.safe_load(file.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _iso(value):
    return value.isoformat(timespec="seconds") if isinstance(value, datetime.datetime) else value


def _record(project, models, db) -> dict:
    folder = _folder(project.source_path) if project.source_path else None
    server = (_config_from_disk(folder).get("server") or {}) if folder else {}
    components = sum(1 for _ in (folder / "components").rglob("*.q")) \
        if folder and (folder / "components").is_dir() else 0
    process = process_status(project.name)
    try:
        modified = datetime.datetime.fromtimestamp(folder.stat().st_mtime).strftime("%Y-%m-%d %H:%M") \
            if folder and folder.is_dir() else None
    except OSError:
        modified = None
    # Connectors live in settings/connectors.yaml (connector_service); the
    # database's `connectors` table is not used by anything in the backend.
    of_project = len(connectors().list_connectors(application_id=project.id, include_public=False))
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description or "",
        "status": project.status or "active",
        "source_path": project.source_path or "",
        "created_at": _iso(project.created_at),
        "updated_at": _iso(project.updated_at),
        "running": process["running"],
        "pid": process["pid"],
        "port": server.get("port"),
        "debug": server.get("debug"),
        "has_config": bool(folder and (folder / "quantum.config.yaml").is_file()),
        "component_count": components,
        "connector_count": of_project,
        "last_modified": modified,
        "initial": (project.name or "?")[0].upper(),
    }


@service("admin.projects.list")
def list_projects(search: str = ""):
    """Projects ordered by name; `search` filters by name or description."""
    crud, models = _crud()
    term = (search or "").strip().lower()
    with session() as db:
        projects = db.query(models.Project).order_by(models.Project.name).all()
        return [_record(p, models, db) for p in projects
                if not term or term in (p.name or "").lower() or term in (p.description or "").lower()]


@service("admin.projects.summary")
def summary():
    """Totals for the header of the applications screen."""
    projects = list_projects()
    return {
        "total": len(projects),
        "active": sum(1 for p in projects if p["status"] == "active"),
        "running": sum(1 for p in projects if p["running"]),
        "with_config": sum(1 for p in projects if p["has_config"]),
        "connectors": len(connectors().list_connectors()),
    }


@service("admin.projects.get")
def get_project(project_id: int):
    crud, models = _crud()
    with session() as db:
        project = crud.get_project(db, int(project_id))
        if project is None:
            raise ProjectError(f"no project with id {project_id}")
        return _record(project, models, db)


@service("admin.projects.create")
def create_project(name: str, description: str = "", source_path: str = ""):
    """Registers the project and creates its folder (without overwriting what exists)."""
    crud, models = _crud()
    name = (name or "").strip()
    if len(name) < 2:
        raise ProjectError("the project name needs at least 2 characters")
    path = (source_path or "").strip() or f"projects/{name}"
    folder = _folder(path)
    with session() as db:
        repeated = db.query(models.Project).filter(models.Project.name.ilike(name)).first()
        if repeated is not None:
            raise ProjectError(f"a project named {repeated.name!r} already exists")
        (folder / "components").mkdir(parents=True, exist_ok=True)
        (folder / "static").mkdir(parents=True, exist_ok=True)
        config = folder / "quantum.config.yaml"
        if not config.is_file():
            config.write_text(yaml.safe_dump(DEFAULT_CONFIG, sort_keys=False), encoding="utf-8")
        project = models.Project(name=name, description=(description or "").strip(),
                                 status="active", source_path=path.replace("\\", "/"))
        db.add(project)
        db.flush()
        return _record(project, models, db)


@service("admin.projects.delete")
def delete_project(project_id: int):
    """Removes the record (and what belongs to it in the database). The files stay."""
    crud, _ = _crud()
    with session() as db:
        if not crud.delete_project(db, int(project_id)):
            raise ProjectError(f"no project with id {project_id}")
    return {"deleted": int(project_id)}


@service("admin.projects.sync")
def sync_projects():
    """Registers the folders of <root>/projects that are not projects yet."""
    _, models = _crud()
    projects_dir = root() / "projects"
    created = []
    with session() as db:
        paths = {p.source_path for p in db.query(models.Project).all()}
        names = {(p.name or "").lower() for p in db.query(models.Project).all()}
        if projects_dir.is_dir():
            for folder in sorted(projects_dir.iterdir()):
                if not folder.is_dir() or folder.name.startswith((".", "_")):
                    continue
                path = f"projects/{folder.name}"
                if path in paths or folder.name.lower() in names:
                    continue
                db.add(models.Project(name=folder.name, description="", status="active", source_path=path))
                created.append(folder.name)
    return {"created": created, "total": len(list_projects())}
