"""Services of the Components and Tests areas (admin.components.*, admin.tests.*).

Ported from components/admin/components.q, tests.q and component/[...path].q.

Preserved: the component listing (group, lines, size, tags used), the test
listing (functions per folder), running pytest on one file and keeping the
last result in settings/last_test_result.json, and generating a test from the
component's structure (_component_test_generator, a copy of the screens'
generator).

Fixed:
  - running tests accepted ANY file: the screen only blocked "..", and an
    absolute path got through (os.path.join discards the base) — pytest, that
    is, arbitrary code, over any .py on the machine, in a POST without login.
    Now only test_*.py inside <root>/tests;
  - generating a test overwrote tests/test_<component>.py without warning,
    losing hand-made edits. Now it refuses, unless overwrite=True;
  - the path check of the detail screen used startswith, which accepts a
    sibling folder with the same prefix (quantum2/). Now it compares paths.
"""

import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

from quantum.services import service
from quantum_admin.services._base import root, settings_dir

TYPES = {".q": "Quantum", ".py": "Python", ".yaml": "YAML", ".yml": "YAML", ".json": "JSON",
         ".html": "HTML", ".css": "CSS", ".js": "JavaScript"}


class ComponentError(ValueError):
    """Invalid request for Components/Tests."""


def _inside(relative: str, folder: str = "") -> Path:
    """Path relative to the root (or to <root>/<folder>) that does not leave it."""
    base = (root() / folder).resolve() if folder else root()
    target = (root() / (relative or "")).resolve()
    if target != base and base not in target.parents:
        raise ComponentError(f"{relative!r} is outside {base}")
    return target


def _size(n: int) -> str:
    if n >= 1048576:
        return f"{n / 1048576:.1f} MB"
    return f"{n / 1024:.1f} KB" if n >= 1024 else f"{n} B"


def _tags(content: str):
    return sorted(set(re.findall(r"<q:(\w+)", content)) - {"component", "param"})


def _test_file_for(comp_path: str) -> str:
    return f"tests/test_{comp_path.replace('/', '_').replace('.q', '')}.py"


@service("admin.components.list")
def list_components():
    folder = root() / "components"
    items, groups = [], set()
    for file in sorted(folder.rglob("*.q")) if folder.is_dir() else []:
        rel = file.relative_to(folder).as_posix()
        group = file.parent.relative_to(folder).as_posix()
        group = "root" if group == "." else group
        groups.add(group)
        content = file.read_text(encoding="utf-8", errors="ignore")
        items.append({"path": rel, "group": group, "lines": content.count("\n") + 1,
                      "size": _size(file.stat().st_size), "feature_tags": _tags(content)})
    examples = root() / "examples"
    return {"components": items, "directories": len(groups),
            "examples": sum(1 for _ in examples.rglob("*.q")) if examples.is_dir() else 0}


@service("admin.components.get")
def get_component(path: str):
    """Detail of a file under the root: type, size, actions, queries, tags, test and last result."""
    relative = (path or "").strip()
    if relative and not Path(relative).suffix:
        relative += ".q"
    file = _inside(relative)
    if not file.is_file():
        raise ComponentError(f"file not found: {relative}")
    content = file.read_text(encoding="utf-8", errors="ignore")
    name = re.search(r'<q:component\s+name="([^"]+)"', content)
    test = _test_file_for(relative)
    test_file = root() / test
    last = _last_result(test)
    functions = re.findall(r"^\s*def (test_\w+)", test_file.read_text(encoding="utf-8", errors="ignore"),
                           re.M) if test_file.is_file() else []
    return {
        "path": relative,
        "name": name.group(1) if name else file.stem,
        "type": TYPES.get(file.suffix.lower(), "Unknown"),
        "size": _size(file.stat().st_size),
        "lines": content.count("\n") + 1,
        "modified": datetime.datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        "actions": re.findall(r'<q:action\s+name="([^"]+)"', content),
        "queries": re.findall(r'<q:query\s+name="([^"]+)"', content),
        "feature_tags": _tags(content),
        "test_file": test if test_file.is_file() else None,
        "test_functions": functions,
        "last_run": last,
        # Each function of the file with the state of the last run ("not run"
        # without a run). A parametrized test counts as failed if any case
        # failed.
        "test_status": [{"name": f, "status": _state(f, last)} for f in functions],
    }


def _state(function: str, last) -> str:
    cases = [t["status"] for t in (last or {}).get("tests", []) if t["name"].split("[")[0] == function]
    for worst in ("ERROR", "FAILED", "PASSED", "XFAIL", "XPASS", "SKIPPED"):
        if worst in cases:
            return worst
    return "not run"


@service("admin.tests.list")
def list_tests():
    folder = root() / "tests"
    files, groups = [], {}
    for file in sorted(folder.rglob("test_*.py")) if folder.is_dir() else []:
        group = file.parent.relative_to(folder).as_posix()
        group = "root" if group == "." else group
        functions = len(re.findall(r"^\s*def test_", file.read_text(encoding="utf-8", errors="ignore"), re.M))
        files.append({"path": file.relative_to(folder).as_posix(), "directory": group, "functions": functions})
        g = groups.setdefault(group, {"name": group, "files": 0, "functions": 0})
        g["files"] += 1
        g["functions"] += functions
    return {"files": files, "directories": [groups[k] for k in sorted(groups)],
            "total_functions": sum(a["functions"] for a in files)}


def _last_result(test_file: str = None):
    file = settings_dir() / "last_test_result.json"
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if not test_file or data.get("test_file") == test_file else None


@service("admin.tests.run")
def run_tests(test_file: str, timeout: int = 120):
    """pytest on a test_*.py of <root>/tests; stores and returns the result."""
    relative = (test_file or "").strip().replace("\\", "/")
    if not relative:
        raise ComponentError("there is no test file to run; generate one first")
    file = _inside(relative, "tests")
    if not (file.is_file() and file.name.startswith("test_") and file.suffix == ".py"):
        raise ComponentError(f"not a test file under tests/: {relative!r}")
    # The child process uses the same `quantum` the admin is using, running
    # from a clone or installed — without this, a project outside the
    # repository could not import the package in its tests.
    import os
    import quantum
    environment = dict(os.environ)
    package = str(Path(quantum.__file__).resolve().parents[1])
    environment["PYTHONPATH"] = os.pathsep.join(p for p in (package, environment.get("PYTHONPATH")) if p)
    try:
        process = subprocess.run([sys.executable, "-m", "pytest", str(file), "-v", "--tb=short", "--no-header"],
                                 capture_output=True, text=True, timeout=int(timeout), cwd=str(root()),
                                 env=environment)
    except subprocess.TimeoutExpired:
        raise ComponentError(f"tests did not finish in {timeout}s: {relative}")
    output = process.stdout + process.stderr
    tests = [{"id": m.group(1), "name": m.group(2), "status": m.group(3)}
             for m in re.finditer(r"^(.+?::(\S+))\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b",
                                  process.stdout, re.M)]
    summary = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    summary.update({key: int(m.group(1)) for key, pattern in (("passed", r"(\d+) passed"), ("failed", r"(\d+) failed"),
                                                             ("errors", r"(\d+) errors?"), ("skipped", r"(\d+) skipped"))
                    if (m := re.search(pattern, output))})
    duration = re.search(r"in ([\d.]+)s", output)
    result = {"test_file": relative, "passed": process.returncode == 0, "returncode": process.returncode,
              "tests": tests, "summary": {**summary, "duration": duration.group(1) if duration else None},
              "output": output, "ran_at": datetime.datetime.now().isoformat(timespec="seconds")}
    target = settings_dir()
    target.mkdir(parents=True, exist_ok=True)
    (target / "last_test_result.json").write_text(json.dumps(result), encoding="utf-8")
    return result


@service("admin.tests.generate")
def generate_tests(comp_path: str, overwrite: bool = False):
    """Generates tests/test_<component>.py from the structure of the .q."""
    from quantum_admin.services._component_test_generator import ComponentTestGenerator
    relative = (comp_path or "").strip().replace("\\", "/")
    # As in get_component: the URL /admin/component/components/shop.q arrives
    # without the .q (the server strips the extension from the path).
    if relative and not Path(relative).suffix:
        relative += ".q"
    file = _inside(relative, "components")
    if not (file.is_file() and file.suffix == ".q"):
        raise ComponentError(f"not a .q component under components/: {relative!r}")
    target = root() / _test_file_for(relative)
    if target.exists() and not overwrite:
        raise ComponentError(f"{target.relative_to(root()).as_posix()} already exists; "
                             f"pass overwrite=true to replace it")
    generator = ComponentTestGenerator(file.relative_to(root() / "components").as_posix(), str(root()))
    generator.analyze()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(generator.generate(), encoding="utf-8")
    return {"test_file": target.relative_to(root()).as_posix(), "overwritten": bool(overwrite)}
