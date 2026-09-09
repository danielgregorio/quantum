"""
A repo-wide guard against expressions built out of data and then executed.

This exists because the pattern kept coming back in places nobody was looking:

- q:data interpolated imported CSV values into a filter string and ran a bare
  eval() on it (fixed, 97fa08e).
- ComponentRuntime fell through a denylist's ValueError straight into an
  unrestricted eval() (fixed, 97fa08e).
- Two deployment configs and a startup script in projects/ monkeypatched
  ComponentRuntime._evaluate_condition at gunicorn worker start to reinstate
  the whole pattern — tracked files, found only by an independent audit
  sweeping a directory the earlier one had skipped.

Grep-based tests are usually a smell. This one earns its place: the defect is
textual, it recurred four times in one codebase, and the last instance was
invisible to every behavioural test because it lived in deployment config that
the test suite never imports.
"""

import ast
import pathlib
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]

# Places that run author-supplied code on purpose. Documented in SECURITY.md
# and gated by security.python_scripting.
BY_DESIGN = {
    "quantum/runtime/executors/scripting/python_executor.py",
    "quantum/runtime/executors/scripting/pyclass_executor.py",
    "quantum/runtime/action_handler.py",
}

# Kept for its LRU/compile machinery but no longer reachable from the runtime:
# nothing in quantum/ calls its evaluate()/evaluate_condition() any more. Its
# regex denylist is NOT a security control — see test_the_denylist_is_not_a_control.
QUARANTINED = {"quantum/runtime/expression_cache.py"}


# Trees whose whole job is to exercise or measure eval/exec. Including them
# would make this test permanently red and therefore ignored — which is how
# the projects/ instance survived in the first place.
EXEMPT_TREES = ("tests/", "benchmarks/", "quantum-as4/")


def _tracked_python_files(shipped_only=True):
    out = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout.replace("\\", "/").split("\n")
    files = [f for f in out if f.strip()]
    if shipped_only:
        files = [f for f in files if not f.startswith(EXEMPT_TREES)]
    return files


def _eval_calls(path: pathlib.Path):
    """(line, name) for every literal eval/exec/compile CALL in the file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return []
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec"):
                hits.append((node.lineno, node.func.id))
    return hits


class TestNoUnexpectedEval:
    def test_no_new_eval_or_exec_anywhere_tracked(self):
        """A new eval() has to be added to BY_DESIGN deliberately, with a
        SECURITY.md entry, rather than slipping in.

        Scoped to shipped code. tests/ and benchmarks/ exist partly to exercise
        and measure eval, so including them would make this permanently red and
        therefore ignored — which is how the projects/ instance survived.
        """
        offenders = []
        for rel in _tracked_python_files():
            if rel in BY_DESIGN or rel in QUARANTINED:
                continue
            path = REPO / rel
            if not path.exists():
                continue
            for line, name in _eval_calls(path):
                offenders.append(f"{rel}:{line} {name}()")

        assert not offenders, (
            "eval/exec outside the documented set:\n  "
            + "\n  ".join(offenders)
            + "\n\nIf it is deliberate, add it to BY_DESIGN here AND to "
            "SECURITY.md, and make it honour security.python_scripting."
        )

    def test_deployment_configs_do_not_monkeypatch_the_runtime(self):
        """projects/*/gunicorn.conf.py used to patch
        ComponentRuntime._evaluate_condition at worker start, reinstating the
        interpolate-then-eval pattern in production only."""
        offenders = []
        for rel in _tracked_python_files():
            path = REPO / rel
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "ComponentRuntime._evaluate_condition" in text and "=" in text:
                for i, line in enumerate(text.split("\n"), 1):
                    if "ComponentRuntime._evaluate_condition" in line and "=" in line \
                            and not line.strip().startswith("#"):
                        offenders.append(f"{rel}:{i}")
        assert not offenders, (
            "the runtime's condition evaluation is being replaced at "
            f"deploy time: {offenders}"
        )


class TestTheCacheIsUnreachable:
    """ExpressionCache compiles and evals behind a regex denylist. It is kept
    for its caching machinery, but the runtime must not route evaluation
    through it."""

    def test_component_runtime_does_not_evaluate_through_the_cache(self):
        source = (REPO / "quantum/runtime/component.py").read_text(encoding="utf-8")
        code_lines = [
            l for l in source.split("\n")
            if not l.strip().startswith("#")
        ]
        code = "\n".join(code_lines)
        assert "_expr_cache.evaluate" not in code
        assert "expression_cache.evaluate" not in code

    def test_nothing_in_the_package_evaluates_through_the_cache(self):
        offenders = []
        for path in (REPO / "quantum").rglob("*.py"):
            if path.name == "expression_cache.py":
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(text.split("\n"), 1):
                if line.strip().startswith("#"):
                    continue
                # Only the cache's own API — `self.evaluate_condition(...)`
                # on a BaseExecutor is the runtime's own method, not this.
                if "_expr_cache.evaluate" in line or "expression_cache.evaluate" in line:
                    offenders.append(f"{path.relative_to(REPO)}:{i}")
        assert not offenders, offenders

    def test_the_denylist_is_not_a_control(self):
        """Pinned as a fact, not a wish.

        The denylist scans SOURCE TEXT, so splitting a dunder across adjacent
        string literals walks straight past it — Python concatenates them at
        parse time — and `format` is in the cache's SAFE_BUILTINS. This test
        asserts the bypass still works, so that nobody re-describes the
        denylist as a boundary, and so the quarantine above stays load-bearing.
        """
        from quantum.runtime.expression_cache import get_expression_cache
        cache = get_expression_cache()

        with pytest.raises(ValueError):
            cache.evaluate('"{0.__class__}".format(x)', {"x": ()})

        leaked = cache.evaluate('("{0.__cla" "ss__}").format(x)', {"x": ()})
        assert "tuple" in str(leaked), (
            "if this now raises, the denylist was hardened — good, but the "
            "quarantine and this test's reasoning need revisiting rather than "
            "the test simply being deleted"
        )
