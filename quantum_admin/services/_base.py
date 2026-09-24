"""Common infrastructure of the admin services: database session, root, processes."""

import contextlib
import os
from pathlib import Path

_initialized = False


def _database():
    from quantum_admin.core import database
    return database


@contextlib.contextmanager
def session():
    """Session on the admin database (the same one as the FastAPI), with the tables created.

    commit at the end of the block, rollback if it raises.
    """
    global _initialized
    database = _database()
    if not _initialized:
        database.Base.metadata.create_all(bind=database.engine)
        _initialized = True
    db = database.SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def root() -> Path:
    """Folder the project paths are relative to.

    The old screens used os.getcwd() — `quantum start` at the repository
    root. QUANTUM_ADMIN_ROOT allows pointing somewhere else.
    """
    return Path(os.environ.get("QUANTUM_ADMIN_ROOT") or os.getcwd()).resolve()


def settings_dir() -> Path:
    """quantum_admin/settings: PIDs, logs, connectors.yaml, global.yaml.

    The same folder the backend library uses (connector_service and
    settings_service resolve it relative to their own file). The old screens
    used os.getcwd()/quantum_admin/settings — the same when `quantum start`
    runs at the repository root, different anywhere else.
    QUANTUM_ADMIN_SETTINGS_DIR allows pointing somewhere else (tests).
    """
    if os.environ.get("QUANTUM_ADMIN_SETTINGS_DIR"):
        return Path(os.environ["QUANTUM_ADMIN_SETTINGS_DIR"])
    from quantum_admin.core import connector_service
    return Path(connector_service.SETTINGS_DIR)


def connectors():
    """The backend's ConnectorService (persists to settings/connectors.yaml)."""
    from quantum_admin.core.connector_service import get_connector_service
    return get_connector_service()


def process_status(project_name: str) -> dict:
    """{'running': bool, 'pid': int|None} from settings/pids/<name>.pid.

    Uses quantum.cli.server_process.pid_alive. The screens' version (_lib.py)
    called OpenProcess on Windows and took an open handle as a live
    process — a process that had already ended kept showing "Running".
    """
    from quantum.cli.server_process import pid_alive
    file = settings_dir() / "pids" / f"{project_name}.pid"
    try:
        pid = int(file.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return {"running": False, "pid": None}
    if pid_alive(pid):
        return {"running": True, "pid": pid}
    with contextlib.suppress(OSError):
        file.unlink()
    return {"running": False, "pid": None}
