"""Services of the screen of one application (components/admin/app/[name].q).

admin.projects.by_name / files / update / config / save_config
admin.environments.list / create / update / delete / create_defaults
admin.servers.status / start / stop / log

What the screen did that was broken, and changed:
  - "start server" ran src/cli/runner.py, which does not exist since the move
    from src/ to quantum/: the process died right away, the PID was written and
    the button did nothing. Now it runs `python -m quantum.cli.runner start` in
    the project folder;
  - "stop" on Windows used taskkill /F without /T: the reloader's child
    survived and kept serving. Now it uses quantum.cli.server_process.stop_server
    with the .quantum.pid the server itself writes (parent and child);
  - saving the config wrote any path and swallowed write errors.
    Now the path stays inside the root, the YAML must be a mapping and the
    write is atomic;
  - environments were embedded in projects.yaml; now they are the ones of the
    backend's environment_service (database), with variables, port and branch.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

from quantum.services import service
from quantum_admin.services._base import connectors, process_status, root, session, settings_dir
from quantum_admin.services.projects import ProjectError, _folder, get_project

# The server processes this admin started, by project name. They outlive
# start_server() on purpose; keeping the Popen lets stop_server() reap the
# child, which otherwise stays a zombie on POSIX and warns on collection.
_started = {}

VALID_STATUSES = ("active", "archived", "error")


def _project(db, project_id):
    from quantum_admin.core import crud
    project = crud.get_project(db, int(project_id))
    if project is None:
        raise ProjectError(f"no project with id {project_id}")
    return project


# --------------------------------------------------------------------------- project

@service("admin.projects.update")
def update_project(project_id: int, name: str = "", description: str = None, status: str = ""):
    from quantum_admin.core import models
    with session() as db:
        project = _project(db, project_id)
        new_name = (name or "").strip()
        if new_name and new_name.lower() != (project.name or "").lower():
            if len(new_name) < 2:
                raise ProjectError("the project name needs at least 2 characters")
            if db.query(models.Project).filter(models.Project.name.ilike(new_name)).first():
                raise ProjectError(f"a project named {new_name!r} already exists")
        if new_name:
            project.name = new_name
        if description is not None:
            project.description = description.strip()
        if status:
            if status not in VALID_STATUSES:
                raise ProjectError(f"status must be one of {', '.join(VALID_STATUSES)}")
            project.status = status
    return get_project(project_id)


@service("admin.projects.config")
def project_config(project_id: int):
    """The project's quantum.config.yaml, as text (for the editor) and parsed."""
    with session() as db:
        path = _project(db, project_id).source_path
    file = _folder(path) / "quantum.config.yaml"
    text = file.read_text(encoding="utf-8") if file.is_file() else ""
    try:
        parsed = yaml.safe_load(text) or {}
        error = None
    except yaml.YAMLError as exc:
        parsed, error = {}, str(exc)
    return {"path": str(file), "exists": file.is_file(), "text": text,
            "server": (parsed.get("server") or {}) if isinstance(parsed, dict) else {},
            "error": error}


@service("admin.projects.save_config")
def save_project_config(project_id: int, config_yaml: str):
    try:
        parsed = yaml.safe_load(config_yaml or "")
    except yaml.YAMLError as exc:
        raise ProjectError(f"invalid YAML: {exc}")
    if parsed is not None and not isinstance(parsed, dict):
        raise ProjectError("the configuration must be a YAML mapping (key: value)")
    with session() as db:
        path = _project(db, project_id).source_path
    folder = _folder(path)
    folder.mkdir(parents=True, exist_ok=True)
    file = folder / "quantum.config.yaml"
    temporary = file.with_name(file.name + ".tmp")
    temporary.write_text(config_yaml or "", encoding="utf-8")
    os.replace(temporary, file)
    return project_config(project_id)


@service("admin.projects.by_name")
def project_by_name(name: str):
    """The project of the URL /admin/app/<name> (name case-insensitive)."""
    from quantum_admin.core import models
    with session() as db:
        project = db.query(models.Project).filter(models.Project.name.ilike((name or "").strip())).first()
        if project is None:
            raise ProjectError(f"no project named {name!r}")
        project_id = project.id
    return get_project(project_id)


def _route(relative: str) -> str:
    """components/shop/index.q -> /shop (ROUTE-1)."""
    parts = relative[:-2].split("/")
    if parts[-1] == "index":
        parts = parts[:-1]
    return "/" + "/".join(parts)


@service("admin.projects.files")
def project_files(project_id: int):
    """Components, routes, static files and disk size of the project folder."""
    import re
    with session() as db:
        path = _project(db, project_id).source_path
    folder = _folder(path)
    components = []
    components_dir = folder / "components"
    for file in sorted(components_dir.rglob("*.q")) if components_dir.is_dir() else []:
        relative = file.relative_to(components_dir).as_posix()
        content = file.read_text(encoding="utf-8", errors="ignore")
        name = re.search(r'<q:component\s+name="([^"]+)"', content)
        components.append({
            "name": name.group(1) if name else file.stem, "path": relative,
            "source": file.relative_to(root()).as_posix(), "lines": content.count("\n") + 1,
            "size": file.stat().st_size, "route": _route(relative), "dynamic": "[" in relative,
            "tags": sorted(set(re.findall(r"<q:(\w+)", content)) - {"component", "param"}),
        })
    static = folder / "static"
    size = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file()) if folder.is_dir() else 0
    return {"components": components,
            "static_files": sum(1 for f in static.rglob("*") if f.is_file()) if static.is_dir() else 0,
            "disk_size": f"{size / 1048576:.1f} MB" if size >= 1048576 else f"{size / 1024:.1f} KB"}


# --------------------------------------------------------------------------- environments

def _public_environment(env) -> dict:
    variables = json.loads(env.env_vars_json) if env.env_vars_json else {}
    return {"id": env.id, "project_id": env.project_id, "name": env.name, "display_name": env.display_name,
            "order": env.order, "port": env.port, "branch": env.branch, "health_url": env.health_url,
            "requires_approval": bool(env.requires_approval), "is_active": bool(env.is_active),
            "variables": variables,
            # The same format that create/update accept: NAME=value per line.
            "variables_text": "\n".join(f"{k}={v}" for k, v in variables.items())}


def _variables(text_or_dict):
    """'KEY=value' per line (like the screen's form) or a dict."""
    if isinstance(text_or_dict, dict):
        return {str(k): str(v) for k, v in text_or_dict.items()}
    variables = {}
    for line in (text_or_dict or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ProjectError(f"variable line must be NAME=value: {line!r}")
        key, value = line.split("=", 1)
        variables[key.strip()] = value.strip()
    return variables


def _environment_service(db):
    from quantum_admin.core.environment_service import EnvironmentService
    return EnvironmentService(db=db)


@service("admin.environments.list")
def list_environments(project_id: int):
    with session() as db:
        _project(db, project_id)
        return [_public_environment(e) for e in _environment_service(db).list_environments(int(project_id),
                                                                                           active_only=False)]


@service("admin.environments.create")
def create_environment(project_id: int, name: str, display_name: str = "", port: int = None,
                       branch: str = "main", variables="", health_url: str = ""):
    env_name = (name or "").strip().lower()
    if not env_name:
        raise ProjectError("environment name is required")
    with session() as db:
        _project(db, project_id)
        svc = _environment_service(db)
        if svc.get_environment_by_name(int(project_id), env_name):
            raise ProjectError(f"environment {env_name!r} already exists in this project")
        env = svc.create_environment(int(project_id), {
            "name": env_name, "display_name": display_name or None, "port": int(port) if port else None,
            "branch": branch or "main", "env_vars": _variables(variables), "health_url": health_url or None})
        return _public_environment(env)


@service("admin.environments.update")
def update_environment(environment_id: int, display_name: str = None, port: int = None, branch: str = None,
                       variables=None, health_url: str = None):
    data = {k: v for k, v in {"display_name": display_name, "branch": branch, "health_url": health_url}.items()
            if v is not None}
    if port not in (None, ""):
        data["port"] = int(port)
    with session() as db:
        svc = _environment_service(db)
        env = svc.update_environment(int(environment_id), data) if data else svc.get_environment(
            int(environment_id))
        if env is None:
            raise ProjectError(f"no environment with id {environment_id}")
        if variables is not None:
            svc.set_env_vars(int(environment_id), _variables(variables))
            env = svc.get_environment(int(environment_id))
        return _public_environment(env)


@service("admin.environments.delete")
def delete_environment(environment_id: int):
    with session() as db:
        if not _environment_service(db).delete_environment(int(environment_id)):
            raise ProjectError(f"no environment with id {environment_id}")
    return {"deleted": int(environment_id)}


@service("admin.environments.create_defaults")
def create_default_environments(project_id: int):
    with session() as db:
        _project(db, project_id)
        return [_public_environment(e) for e in _environment_service(db).create_default_environments(int(project_id))]


# --------------------------------------------------------------------------- project server

def _project_folder(project_id):
    with session() as db:
        project = _project(db, project_id)
        name, path = project.name, project.source_path
    folder = _folder(path)
    if not (folder / "quantum.config.yaml").is_file():
        raise ProjectError(f"{path}/quantum.config.yaml not found; save a configuration first")
    return name, folder


def _log(name):
    folder = settings_dir() / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{name}.log"


@service("admin.servers.status")
def server_status(project_id: int):
    name, folder = _project_folder(project_id)
    from quantum.cli.server_process import pid_alive, read_pids
    file = folder / ".quantum.pid"
    try:
        alive = [p for p in read_pids(file) if pid_alive(p)]
    except (OSError, ValueError):
        alive = []
    process = process_status(name)
    return {"running": bool(alive) or process["running"], "pids": alive or ([process["pid"]] if process["pid"] else [])}


@service("admin.servers.start")
def start_server(project_id: int, port: int = None, wait: float = 15.0):
    """Starts `quantum start` in the project folder and waits for the PID file to appear."""
    name, folder = _project_folder(project_id)
    if server_status(project_id)["running"]:
        raise ProjectError(f"{name} is already running")
    command = [sys.executable, "-m", "quantum.cli.runner", "start", "--config", "quantum.config.yaml"]
    if port:
        command += ["--port", str(int(port))]
    import quantum
    environment = dict(os.environ)
    package = str(Path(quantum.__file__).resolve().parents[1])
    environment["PYTHONPATH"] = os.pathsep.join(p for p in (package, environment.get("PYTHONPATH")) if p)
    log = open(_log(name), "a", encoding="utf-8")
    options = {"stdout": log, "stderr": subprocess.STDOUT, "cwd": str(folder), "env": environment}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    process = subprocess.Popen(command, **options)
    _started[name] = process
    log.close()
    pids = settings_dir() / "pids"
    pids.mkdir(parents=True, exist_ok=True)
    (pids / f"{name}.pid").write_text(str(process.pid), encoding="utf-8")

    deadline = time.time() + float(wait)
    while time.time() < deadline:
        if process.poll() is not None:
            _started.pop(name, None)
            raise ProjectError(f"{name} exited with code {process.returncode}; see the log: "
                               f"{server_log(project_id, 20)['text']}")
        if (folder / ".quantum.pid").is_file():
            return server_status(project_id)
        time.sleep(0.2)
    return server_status(project_id)


@service("admin.servers.stop")
def stop_server(project_id: int):
    name, folder = _project_folder(project_id)
    from quantum.cli import server_process
    file = folder / ".quantum.pid"
    if file.is_file():
        server_process.stop_server(file)
    else:
        process = process_status(name)
        if process["running"]:
            server_process._terminate(process["pid"], True)
    child = _started.pop(name, None)
    if child is not None:
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
    (settings_dir() / "pids" / f"{name}.pid").unlink(missing_ok=True)
    return server_status(project_id)


@service("admin.servers.log")
def server_log(project_id: int, lines: int = 50):
    with session() as db:
        name = _project(db, project_id).name
    file = _log(name)
    text = file.read_text(encoding="utf-8", errors="replace") if file.is_file() else ""
    return {"text": "".join(text.splitlines(keepends=True)[-int(lines):])}
