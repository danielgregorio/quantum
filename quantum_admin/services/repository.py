"""Services of the repository reading screens.

admin.dashboard.stats    dashboard.q
admin.features.list      features.q
admin.agents.list        agents.q
admin.source.read        source.q
admin.databases.list     database.q
admin.jobs.list          jobs.q

Everything only reads. What the screens had wrong and changed:
  - dashboard.q and features.q looked in src/core/features, src/core/parsers
    and src/runtime/executors — folders that do not exist since the move from
    src/ to quantum/. The dashboard showed 0 features, 0 parsers and 0
    executors, and the features screen came up empty. Now they read
    quantum/core/features and the real registries;
  - source.q showed any file under the root — .env, keys, the settings YAML
    files with the connectors' credentials. Now those are refused, and the
    path check no longer accepts the sibling folder with the same prefix;
  - database.q opened each .db with a plain sqlite3.connect (write mode, with
    journal and lock, even on databases of running applications). Now it
    opens them read-only.
"""

import datetime
import re
import sqlite3
from pathlib import Path

import yaml

from quantum.services import service
from quantum_admin.services._base import root

SKIP = {".git", "__pycache__", "node_modules", ".venv", "venv", ".claude", "build", "dist"}
TYPES = {".q": "Quantum", ".py": "Python", ".yaml": "YAML", ".yml": "YAML", ".json": "JSON", ".html": "HTML",
         ".css": "CSS", ".js": "JavaScript", ".md": "Markdown", ".txt": "Text"}
JOB_STATES = ("pending", "running", "completed", "failed")
SENSITIVE_NAMES = re.compile(r"(^\.env(\..*)?$|\.pem$|\.key$|^id_(rsa|ed25519|ecdsa)|\.db$|\.sqlite3?$)", re.I)


class RepositoryError(ValueError):
    """Invalid request for the reading screens."""


def _files(folder: Path, pattern: str):
    if not folder.is_dir():
        return []
    return [p for p in sorted(folder.rglob(pattern)) if not SKIP.intersection(p.relative_to(folder).parts)]


def _size(n: int) -> str:
    if n >= 1048576:
        return f"{n / 1048576:.1f} MB"
    return f"{n / 1024:.1f} KB" if n >= 1024 else f"{n} B"


def _registries():
    from quantum.core.parser import QuantumParser
    from quantum.runtime.component import ComponentRuntime
    parser = QuantumParser()
    registry = parser._parser_registry
    tags = sum(1 for tag in registry.registered_tags
               if type(registry.get_parser(tag)).__name__ != "HTMLParser")
    return tags, ComponentRuntime(config={})._executor_registry.executor_count


def _root_config() -> dict:
    """The root's quantum.config.yaml, or {} if there is none or it does not open."""
    try:
        return yaml.safe_load((root() / "quantum.config.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _features_dir():
    import quantum
    return Path(quantum.__file__).resolve().parent / "core" / "features"


@service("admin.dashboard.stats")
def dashboard_stats():
    base = root()
    components = [p.relative_to(base / "components").as_posix() for p in _files(base / "components", "*.q")]
    tags, executors = _registries()
    return {
        "components": len(components), "component_list": components,
        "features": len(list_features()["features"]),
        "tests": len(_files(base / "tests", "test_*.py")),
        "parser_tags": tags, "executors": executors,
        "examples": len(_files(base / "examples", "*.q")),
    }


@service("admin.features.list")
def list_features():
    """Features of quantum/core/features, from each one's manifest.yaml."""
    features = []
    base = root()
    for manifest in sorted(_features_dir().glob("*/manifest.yaml")):
        folder = manifest.parent.name
        # It can only be opened in the code reader when the package is inside the root.
        source = manifest.relative_to(base).as_posix() if base in manifest.parents else None
        try:
            data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
            feature = data.get("feature") or {}
            description = data.get("description")
            short = description.get("short") if isinstance(description, dict) else (description or "").strip().split("\n")[0]
            features.append({"name": feature.get("name", folder), "display_name": feature.get("display_name", folder),
                             "version": feature.get("version"), "status": feature.get("status", "unknown"),
                             "category": feature.get("category"), "short_desc": short or "", "source": source})
        except (OSError, yaml.YAMLError, AttributeError) as exc:
            features.append({"name": folder, "display_name": folder, "version": None, "status": "error",
                             "category": None, "short_desc": f"manifest could not be read: {exc}", "source": source})
    counts = {}
    for f in features:
        counts[f["status"]] = counts.get(f["status"], 0) + 1
    active, planned = counts.get("active", 0), counts.get("planned", 0)
    return {"features": features, "by_status": counts,
            "summary": {"active": active, "planned": planned, "other": len(features) - active - planned}}


@service("admin.agents.list")
def list_agents():
    """q:agent and q:team declared in components/, examples/ and projects/."""
    base = root()
    attributes = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
    agents, teams = [], []
    for folder in ("components", "examples", "projects"):
        for file in _files(base / folder, "*.q"):
            text = file.read_text(encoding="utf-8", errors="ignore")
            origin = file.relative_to(base).as_posix()
            for m in re.finditer(r"<q:agent\s+([^>]*?)/?>", text, re.S):
                a = dict(attributes.findall(m.group(1)))
                agents.append({"name": a.get("name"), "model": a.get("model"),
                               "provider": a.get("provider"), "source": origin})
            for m in re.finditer(r"<q:team\s+([^>]*?)/?>", text, re.S):
                a = dict(attributes.findall(m.group(1)))
                teams.append({"name": a.get("name"), "supervisor": a.get("supervisor"), "source": origin})
    llm = _root_config().get("llm")
    return {"agents": agents, "teams": teams,
            "sources": sorted({a["source"] for a in agents} | {t["source"] for t in teams}),
            "providers": sorted({a["provider"] for a in agents if a["provider"]}),
            # Only these three fields: the llm section may have an api_key.
            "llm": {"base_url": llm.get("base_url"), "default_model": llm.get("default_model"),
                    "timeout": llm.get("timeout", 60)} if isinstance(llm, dict) else None}


@service("admin.source.read")
def read_source(path: str):
    relative = (path or "").strip().replace("\\", "/")
    if not relative:
        raise RepositoryError("a file path is required")
    base = root()
    file = (base / relative).resolve()
    if base not in file.parents:
        raise RepositoryError(f"{relative!r} is outside the project root")
    parts = file.relative_to(base).parts
    if SENSITIVE_NAMES.search(file.name) or parts[:2] == ("quantum_admin", "settings"):
        raise RepositoryError(f"{relative} may contain credentials and is not shown here")
    if not file.is_file():
        raise RepositoryError(f"file not found: {relative}")
    content = file.read_text(encoding="utf-8", errors="replace")
    stat = file.stat()
    return {"path": file.relative_to(base).as_posix(), "type": TYPES.get(file.suffix.lower(), "Unknown"),
            "size": _size(stat.st_size), "lines": content.count("\n") + 1, "content": content,
            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")}


@service("admin.databases.list")
def list_databases():
    """.db files under the root, opened READ-ONLY, with tables and rows."""
    base = root()
    databases = []
    for file in _files(base, "*.db"):
        tables, error = [], None
        try:
            connection = sqlite3.connect(f"{file.resolve().as_uri()}?mode=ro", uri=True, timeout=2)
            try:
                for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
                    try:
                        rows = connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
                    except sqlite3.DatabaseError:
                        rows = None
                    tables.append({"name": name, "rows": rows})
            finally:
                connection.close()
        except sqlite3.DatabaseError as exc:
            error = str(exc)
        stat = file.stat()
        databases.append({"path": file.relative_to(base).as_posix(), "size": _size(stat.st_size),
                          "modified": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                          "tables": tables, "error": error})
    sources = _root_config().get("datasources") or {}
    # Name, driver and database — host, user and password stay out.
    declared = [{"name": name, "driver": (cfg or {}).get("driver") or (cfg or {}).get("type"),
                 "database": (cfg or {}).get("database")} for name, cfg in sorted(sources.items())
                if isinstance(cfg, dict)] if isinstance(sources, dict) else []
    return {"databases": databases, "total_tables": sum(len(b["tables"]) for b in databases), "datasources": declared}


@service("admin.jobs.list")
def list_jobs(limit: int = 50):
    """The q:job queue (quantum_jobs.db at the root), read-only."""
    file = root() / "quantum_jobs.db"
    # The queue's four states always present, so the screen does not test for the key.
    empty = {"found": False, "counts": dict.fromkeys(JOB_STATES, 0), "total": 0, "jobs": []}
    if not file.is_file():
        return empty
    try:
        connection = sqlite3.connect(f"{file.resolve().as_uri()}?mode=ro", uri=True, timeout=2)
        connection.row_factory = sqlite3.Row
        try:
            counts = dict.fromkeys(JOB_STATES, 0)
            counts.update({r["status"]: r["cnt"] for r in
                           connection.execute("SELECT status, COUNT(*) AS cnt FROM quantum_jobs GROUP BY status")})
            jobs = [dict(r) for r in connection.execute(
                "SELECT id, name, queue, status, attempts, max_attempts, created_at, error "
                "FROM quantum_jobs ORDER BY id DESC LIMIT ?", (int(limit),))]
        finally:
            connection.close()
    except sqlite3.DatabaseError as exc:
        return {**empty, "found": True, "error": str(exc)}
    return {"found": True, "counts": counts, "total": sum(counts.values()), "jobs": jobs}
