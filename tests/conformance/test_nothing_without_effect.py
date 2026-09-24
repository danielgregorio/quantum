"""PARSE-3: nothing is accepted without effect.

Walks the node classes the Core parsers fill and looks, in the code that runs
and draws (quantum/runtime), for each field they store. A field stored and
never read is an attribute the user writes that does nothing — that is how
`require_auth` on an action, `csrf`, `accept` and `returnType` spent months
accepted and ignored, and each was found by chance.

The comparison with EXCEPTIONS is exact: a new unused field fails here, and
so does an exception that is no longer needed — the list only shrinks.
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "quantum"

# Core and AI features (SUPPORT_TIERS.md). Laboratory and Experimental stay
# out of the sweep: they carry no promise.
CORE = {"core", "state_management", "loops", "conditionals", "functions", "query",
        "invocation", "data_import", "forms_actions", "component_composition",
        "authentication", "llm_integration", "agents", "knowledge_base",
        "file_uploads", "email_sending", "session_management"}

# Runtime files that belong to Laboratory/Experimental targets.
OUTSIDE = ("game", "godot", "terminal", "ui_", "textual", "desktop", "mobile", "compiler")

REFUSED = "refused by the parser (PARSE-3 / FN-2 / DB-5 / AUTH-7); the field only exists on the node"
INTERNAL = "internal: filled by the parser itself, not by a user attribute"
LAB = "Laboratory or Experimental, outside the promise (SUPPORT_TIERS.md)"

EXCEPTIONS = {
    "ActionNode.rate_limit": REFUSED, "ActionNode.validate_csrf": REFUSED,
    "AgentHandoffNode.target_agent": "q:team: to review when handoff is validated end to end",
    "AgentNode.in_team": INTERNAL,
    "ApplicationNode.*": "q:application: only the ui/game/terminal types remain (APP-1, APP-2); read by the CLI and the targets, outside the Core's quantum/runtime",
    "ComponentNode.base_path": REFUSED, "ComponentNode.health_endpoint": REFUSED,
    "ComponentNode.metrics_provider": REFUSED, "ComponentNode.trace_provider": REFUSED,
    "ComponentNode.has_html": INTERNAL, "ComponentNode.resources": INTERNAL, "ComponentNode.script_blocks": INTERNAL,
    "DispatchEventNode.routing_key": LAB, "OnEventNode.concurrent": LAB, "OnEventNode.max_retries": LAB,
    "FunctionNode.access": REFUSED, "FunctionNode.async_func": REFUSED, "FunctionNode.memoize": REFUSED,
    "FunctionNode.rest_config": REFUSED, "FunctionNode.validate_params": REFUSED,
    "HTMLNode.has_events": INTERNAL,
    "ImportNode.behavior": LAB, "ImportNode.prefab": LAB, "ImportNode.tilemap": LAB,
    "InvokeNode.transform": REFUSED,
    "PyExprNode.expr": LAB, "PyExprNode.format_spec": LAB,
    "QuantumParam.validation": REFUSED,
    "QueryNode.maxrows": REFUSED, "QueryNode.reactive": REFUSED,
    "RestConfig.*": REFUSED,
    "SetNode.mask": REFUSED,
    "ThreadNode.on_complete": LAB,
}


def fields_by_class():
    sources = [ROOT / "core/ast_nodes.py"] + sorted((ROOT / "core/features").glob("*/src/ast_node.py"))
    for source in sources:
        feature = source.parts[-3] if "features" in source.parts else "core"
        if feature not in CORE:
            continue
        for cls in (n for n in ast.parse(source.read_text(encoding="utf-8")).body if isinstance(n, ast.ClassDef)):
            fields = set()
            for item in cls.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    fields |= {n.attr for n in ast.walk(item) if isinstance(n, ast.Attribute)
                               and isinstance(n.ctx, ast.Store) and isinstance(n.value, ast.Name) and n.value.id == "self"}
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.add(item.target.id)
            yield cls.name, {f for f in fields if not f.startswith("_")}


def test_every_stored_field_is_read_or_explained():
    # PARSE-3
    runtime = "".join(p.read_text(encoding="utf-8", errors="ignore")
                      for p in list((ROOT / "runtime").rglob("*.py")) + [ROOT / "core/guards.py"]
                      if not any(f in p.name for f in OUTSIDE))
    never_read = set()
    for cls, fields in fields_by_class():
        for field in fields:
            if not re.search(r"\." + re.escape(field) + r"\b|['\"]" + re.escape(field) + r"['\"]", runtime):
                never_read.add(f"{cls}.{field}")
    wildcards = {k[:-2] for k in EXCEPTIONS if k.endswith(".*")}
    found = {c for c in never_read if c.split(".")[0] not in wildcards}
    explained = {k for k in EXCEPTIONS if not k.endswith(".*")}
    new = sorted(found - explained)
    resolved = sorted(explained - found)
    assert not new, ("stored fields nothing reads — make them work, refuse them in the parser (PARSE-3) "
                     f"or explain them in EXCEPTIONS: {new}")
    assert not resolved, f"exceptions no longer needed — remove them from EXCEPTIONS: {resolved}"


# ------------------------------------------------------------------ read where the node runs
#
# The sweep above accepts a field whose NAME appears anywhere in the runtime.
# That let through `unique=` on q:set (the word is an operation name),
# `range=` and eight other rules on q:column (other nodes have a `.range`), and
# `encoding=` on q:data. Here a field must be read — `.field` or
# getattr(x, 'field') — by the code that runs ITS node: the executor whose
# `handles` lists the class, or the handler named in HANDLED_BY.

RUNTIME = ROOT / "runtime"

HANDLED_BY = {
    "ColumnNode": ["executors/data/data_executor.py"],
    "FieldNode": ["executors/data/data_executor.py"],
    "HeaderNode": ["executors/data/data_executor.py"],
    "TransformNode": ["executors/data/data_executor.py"],
    "FilterNode": ["executors/data/data_executor.py"],
    "SortNode": ["executors/data/data_executor.py"],
    "LimitNode": ["executors/data/data_executor.py"],
    "ComputeNode": ["executors/data/data_executor.py"],
    "QueryParamNode": ["executors/data/query_executor.py"],
    "InvokeHeaderNode": ["executors/data/invoke_executor.py"],
    "LLMMessageNode": ["executors/ai/llm_executor.py"],
    "KnowledgeSourceNode": ["executors/ai/knowledge_executor.py", "knowledge_service.py"],
    "AgentToolNode": ["executors/ai/agent_executor.py"],
    "AgentToolParamNode": ["executors/ai/agent_executor.py"],
    "AgentExecuteNode": ["executors/ai/agent_executor.py"],
    "AgentInstructionNode": ["executors/ai/agent_executor.py"],
    "FlashNode": ["action_handler.py"],
    "RedirectNode": ["action_handler.py", "executors/control_flow/redirect_executor.py"],
}

NOT_USER = "not filled from an attribute: the parser never sets it"

READ_ELSEWHERE = {
    # Refused by the parser: the field only exists on the node (same as EXCEPTIONS).
    "InvokeNode.endpoint": REFUSED, "InvokeNode.transform": REFUSED, "SetNode.mask": REFUSED,
    "QueryNode.cache": REFUSED, "QueryNode.interval": REFUSED, "QueryNode.maxrows": REFUSED,
    "QueryNode.reactive": REFUSED, "QueryNode.timeout": REFUSED, "QueryNode.ttl": REFUSED,
    "AgentNode.in_team": INTERNAL,
    "AgentToolParamNode.required": "passed as p.to_dict() and read by AgentService as p['required'] (IA-4)",
    "LoopNode.condition": NOT_USER, "MailNode.charset": NOT_USER,
    "AgentExecuteNode.entry": LAB, "JobNode.job_id": LAB, "JobNode.schedule": LAB, "JobNode.timeout": LAB,
    "QueueNode.dead_letter_queue": LAB, "ScheduleNode.retry": LAB, "ScheduleNode.timeout": LAB,
    "ThreadNode.on_complete": LAB, "ThreadNode.on_error": LAB,
}


def handler_files():
    files = {}
    for path in (RUNTIME / "executors").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"def handles.*?return\s*\[([^\]]*)\]", text, re.S):
            for cls in re.findall(r"\w+", match.group(1)):
                files.setdefault(cls, set()).add(path)
    for cls, paths in HANDLED_BY.items():
        files.setdefault(cls, set()).update(RUNTIME / p for p in paths)
    return files


def test_every_stored_field_is_read_where_its_node_runs():
    # PARSE-3
    files = handler_files()
    unread = set()
    for cls, fields in fields_by_class():
        paths = files.get(cls)
        if not paths:
            continue
        missing = [p for p in paths if not p.exists()]
        assert not missing, f"HANDLED_BY names files that do not exist: {missing}"
        code = "".join(p.read_text(encoding="utf-8") for p in paths)
        for field in fields:
            if not re.search(r"\." + re.escape(field) + r"\b|getattr\(\s*\w+,\s*['\"]" + re.escape(field) + r"['\"]",
                             code):
                unread.add(f"{cls}.{field}")
    new = sorted(unread - set(READ_ELSEWHERE))
    resolved = sorted(set(READ_ELSEWHERE) - unread)
    assert not new, ("fields the code that runs their node never reads — make them work, refuse them in the "
                     f"parser (PARSE-3), or explain them in READ_ELSEWHERE: {new}")
    assert not resolved, f"entries of READ_ELSEWHERE no longer needed: {resolved}"
