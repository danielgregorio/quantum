"""
Contract tests: every service method an executor calls must actually exist.

This is the guard for the defect class that the 2026-09 audit found nine
times over (FULL_AUDIT_2026-09.md): an executor calling
`self.services.<service>.<method>(...)` where `<method>` — or the service
property itself — never existed. Every one of those had a passing unit test,
because the test mocked the same invented interface the executor called.

Mocks can agree with the executor and both be wrong. Only the real class can
settle it, so this test statically walks the executor sources and checks each
call against the real service class.
"""

import ast
import importlib
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
# The package was renamed src/ -> quantum/ (FRAMEWORK_PLAN Fase 1.1) and this
# path was not updated. rglob returned nothing, the parametrize list came out
# empty, and pytest reported the test as SKIPPED — so the guard against this
# project's signature bug class (nine executors calling service methods that
# did not exist) silently stopped guarding anything. See
# test_the_guard_is_actually_guarding below, which now makes an empty sweep a
# failure instead of a skip.
EXECUTORS_DIR = REPO_ROOT / "quantum" / "runtime" / "executors"

# services.<property> -> the class ServiceContainer actually returns.
SERVICE_CLASSES = {
    "agent": "quantum.runtime.agent_service.AgentService",
    "multi_agent": "quantum.runtime.agent_service.MultiAgentService",
    "llm": "quantum.runtime.llm_service.LLMService",
    "knowledge": "quantum.runtime.knowledge_service.KnowledgeService",
    "database": "quantum.runtime.database_service.DatabaseService",
    "message_queue": "quantum.runtime.message_queue_service.MessageQueueService",
    "websocket": "quantum.runtime.websocket_service.WebSocketService",
    "job_executor": "quantum.runtime.job_executor.JobExecutor",
    "email": "quantum.runtime.email_service.EmailService",
    "invocation": "quantum.core.features.invocation.src.runtime.InvocationService",
    "data_import": "quantum.core.features.data_import.src.runtime.DataImportService",
    "file_upload": "quantum.runtime.file_upload_service.FileUploadService",
    "logging": "quantum.core.features.logging.src.LoggingService",
    "dump": "quantum.core.features.dump.src.DumpService",
    "function_registry": "quantum.runtime.function_registry.FunctionRegistry",
}

# Sub-services reached through a facade (instance attributes, so they are not
# visible via hasattr on the class).
SUB_SERVICES = {
    ("job_executor", "schedule"): "quantum.runtime.job_executor.ScheduleService",
    ("job_executor", "thread"): "quantum.runtime.job_executor.ThreadService",
    ("job_executor", "job_queue"): "quantum.runtime.job_executor.JobQueueService",
}

# self.runtime.<attribute> -> class, for services held directly on the runtime.
RUNTIME_ATTR_CLASSES = {
    "knowledge_service": "quantum.runtime.knowledge_service.KnowledgeService",
    "llm_service": "quantum.runtime.llm_service.LLMService",
}


def _load(dotted: str):
    module_path, class_name = dotted.rsplit(".", 1)
    return getattr(importlib.import_module(module_path), class_name)


def _attribute_chain(node: ast.Attribute):
    """Flatten a.b.c into (root_node, ['b', 'c'])."""
    parts = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    parts.reverse()
    return current, parts


def _iter_service_calls(tree: ast.AST):
    """Yield (chain, lineno) for every self.services.* / self.runtime.* call."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue

        root, parts = _attribute_chain(node.func)
        if not isinstance(root, ast.Name) or root.id != "self":
            continue
        if not parts or parts[0] not in ("services", "runtime"):
            continue

        yield parts, node.lineno


def _executor_files():
    return sorted(
        p for p in EXECUTORS_DIR.rglob("*.py")
        if p.name != "__init__.py" and "__pycache__" not in p.parts
    )


@pytest.mark.parametrize(
    "executor_path", _executor_files(), ids=lambda p: p.stem
)
def test_executor_service_calls_exist(executor_path):
    tree = ast.parse(executor_path.read_text(encoding="utf-8"))
    problems = []

    for parts, lineno in _iter_service_calls(tree):
        root_kind, rest = parts[0], parts[1:]
        if len(rest) < 2:
            # e.g. self.services.foo() — not a service.method call
            continue

        if root_kind == "runtime":
            attr, method = rest[0], rest[-1]
            dotted = RUNTIME_ATTR_CLASSES.get(attr)
            if dotted is None:
                continue  # not a service we track (executor_registry, etc.)
            target, label = _load(dotted), f"quantum.runtime.{attr}"
        else:
            service, method = rest[0], rest[-1]
            if service not in SERVICE_CLASSES:
                problems.append(
                    f"line {lineno}: services.{service} is not a known "
                    f"ServiceContainer property"
                )
                continue

            if len(rest) > 2:
                sub = rest[1]
                dotted = SUB_SERVICES.get((service, sub))
                if dotted is None:
                    problems.append(
                        f"line {lineno}: services.{service}.{sub} is not a "
                        f"known sub-service"
                    )
                    continue
                target, label = _load(dotted), f"services.{service}.{sub}"
            else:
                target, label = _load(SERVICE_CLASSES[service]), f"services.{service}"

        if not hasattr(target, method):
            problems.append(
                f"line {lineno}: {label}.{method}() does not exist on "
                f"{target.__name__}"
            )

    assert not problems, (
        f"{executor_path.relative_to(REPO_ROOT)} calls service methods that "
        f"do not exist:\n  " + "\n  ".join(problems)
    )


def test_service_class_map_matches_service_container():
    """Every property this test maps must still exist on ServiceContainer."""
    from quantum.runtime.service_container import ServiceContainer

    missing = [
        name for name in SERVICE_CLASSES
        if not isinstance(getattr(ServiceContainer, name, None), property)
    ]
    assert not missing, (
        f"SERVICE_CLASSES maps properties that ServiceContainer no longer has: "
        f"{missing}"
    )


def test_the_guard_is_actually_guarding():
    """An empty sweep must FAIL, not skip.

    This whole module exists to catch the bug class that produced nine broken
    executor->service bridges: an executor calling `self.services.X.Y()` where
    Y does not exist on the real service, with a unit test mocking the same
    imagined method so everything stayed green.

    It stopped working silently. The package moved from src/ to quantum/ and
    EXECUTORS_DIR was not updated, so rglob found nothing, the parametrize
    list was empty, and pytest reported SKIPPED — which reads as "fine" in a
    summary. A guard that can quietly guard nothing is the same disease this
    codebase keeps producing, one level up.
    """
    files = _executor_files()
    assert files, (
        f"no executors found under {EXECUTORS_DIR} — this test cannot see the "
        f"code it is supposed to check. Fix the path rather than letting the "
        f"sweep come back empty."
    )
    assert len(files) >= 20, (
        f"only {len(files)} executor files found under {EXECUTORS_DIR}; the "
        f"registry has 27 executors, so the sweep is missing some."
    )
