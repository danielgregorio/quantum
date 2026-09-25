# Contributing to Quantum

Thanks for your interest in improving Quantum! This guide gets you from a fresh clone to
a merged pull request. If anything here is unclear, open an
[issue](https://github.com/danielgregorio/quantum/issues/new/choose) — improving this doc
is itself a great first contribution.

By participating you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## 1. Dev setup

**Requirements:** Python 3.12+ and `pip`.

```bash
git clone https://github.com/danielgregorio/quantum.git
cd quantum
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -e ".[dev,db,jobs,websocket]" -r quantum_admin/backend/requirements.txt
```

That is the same install CI uses. `.[dev]` alone is enough to work on the
language, but not to run the whole suite: the admin tests and a few runtime
tests need the other extras and the admin's requirements.

Verify everything works:

```bash
quantum run examples/hello.q   # should print "Hello World!"
pytest -q                      # the suite should pass
```

---

## 2. The big picture

Quantum turns an `.q` file into a running app through a small, well-defined pipeline:

```
.q file ──▶ Parser ──▶ AST ──▶ Executors ──▶ the page: browser, console, desktop window
          (XML→nodes)         (run the tags)
```

(The Laboratory's game codegen turns the same AST into a Godot or HTML5 project.)

The parser and runtime are **modular**: every tag has a `Parser` (XML → AST node) and an
`Executor` (AST node → behaviour), each registered in a central registry. To add a feature
you write small, isolated classes — you almost never touch the orchestrator.

Key files:

| File | Role |
|------|------|
| `quantum/core/parser.py` | Parser orchestrator |
| `quantum/core/parser_registry.py` | Registry of tag parsers |
| `quantum/core/ast_nodes.py` | AST node definitions |
| `quantum/runtime/component.py` | Execution orchestrator |
| `quantum/runtime/executor_registry.py` | Registry of node executors |
| `quantum/runtime/service_container.py` | Dependency injection for services |

Parsers live under `quantum/core/parsers/{category}/` and executors under
`quantum/runtime/executors/{category}/`, where `category` is one of `control_flow`, `data`,
`ai`, `messaging`, `jobs`, `services`, `scripting`, or `html`.

---

## 3. Adding a new tag (the 4-step recipe)

Say you want to add `<q:greet name="...">`. You touch four places:

### 1. Define the AST node — `quantum/core/ast_nodes.py`

```python
from dataclasses import dataclass
from quantum.core.ast_nodes import QuantumNode

@dataclass
class GreetNode(QuantumNode):
    name: str

    def to_dict(self):
        return {"type": "greet", "name": self.name}

    def validate(self):
        return [] if self.name else ["q:greet needs name="]
```

### 2. Write the parser — `quantum/core/parsers/control_flow/greet_parser.py`

```python
from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import GreetNode

class GreetParser(BaseTagParser):
    @property
    def tag_names(self) -> List[str]:
        return ['greet']

    def parse(self, element: ET.Element) -> GreetNode:
        return GreetNode(name=self.get_attr(element, 'name'))
```

### 3. Write the executor — `quantum/runtime/executors/control_flow/greet_executor.py`

```python
from typing import Any, List, Type
from quantum.runtime.executors.base import BaseExecutor
from quantum.core.ast_nodes import GreetNode

class GreetExecutor(BaseExecutor):
    @property
    def handles(self) -> List[Type]:
        return [GreetNode]

    def execute(self, node: GreetNode, exec_context) -> Any:
        return f"Hello, {node.name}!"
```

### 4. Register both

- Parser → add to `_create_parser_registry()` in `quantum/core/parser.py`
- Executor → add to `_create_executor_registry()` in `quantum/runtime/component.py`

Then write a test (see below) and you're done. Larger features should follow the
**Option C** structure under `quantum/core/features/{feature}/` — see the existing features under `quantum/core/features/` for the full layout (`manifest.yaml`, `intentions/`, `dataset/`).

---

## 4. Testing

Tests live in `tests/` and use pytest: `conformance/` holds one test per SPEC
rule (each cites the rule's ID), `unit/` the modules, `apps/` the proving apps in
`projects/`, and `docs/` the site's examples.

```bash
pytest -q                             # full suite
pytest tests/test_expression_cache.py # a single file
pytest tests/ -k "greet"             # by keyword
pytest -q -n 4                        # in parallel (pytest-xdist, in the [dev] extra)
```

The suite runs in parallel in CI. A test must not depend on the order it runs in
or on state another test left behind; the root `conftest.py` restores the logging
state after every test for that reason. A test that genuinely cannot share the
machine — a fixed port, a file outside `tmp_path` — is marked
`@pytest.mark.isolated`, and CI runs those afterwards, one at a time.

**Every behavioural change needs a test.** A typical tag test parses a snippet, executes
it, and asserts the output. Fixtures live in `tests/conftest.py`.

---

## 5. Code style

- **Python:** type hints on public functions, docstrings on non-trivial ones, absolute
  imports (`from quantum.core.parser import QuantumParser`), AST nodes as `@dataclass`.
- **Linting:** `ruff check quantum/ tests/` before pushing — it is what CI enforces, and
  it fails on any finding. The rules left out, and why, are in `pyproject.toml`
  (`[tool.ruff.lint]`). There is no formatter to run: the code is not auto-formatted.
- **`.q` files:** Quantum tags use the `q:` prefix; databinding uses `{braces}`; components
  need `<q:component name="...">`.

---

## 6. Pull request workflow

1. **Fork** and create a branch: `git checkout -b feat/my-feature` (or `fix/`, `docs/`).
2. Make your change **with tests**.
3. Run `pytest -q` and `ruff check quantum/ tests/` — both green.
4. Use clear, conventional commit messages (`feat:`, `fix:`, `docs:`, `chore:`, `test:`).
5. Open a PR using the template; link any related issue and describe the *why*.

Small, focused PRs get reviewed faster than large ones. When in doubt, open an issue
first to align on the approach.

---

## 7. Reporting bugs & requesting features

Use the [issue templates](https://github.com/danielgregorio/quantum/issues/new/choose).
For bugs, a **minimal `.q` file that reproduces the problem** is worth a thousand words.

Thank you for helping make Quantum better! 🚀
