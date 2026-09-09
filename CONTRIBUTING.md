# Contributing to Quantum

Thanks for your interest in improving Quantum! This guide gets you from a fresh clone to
a merged pull request. If anything here is unclear, open a
[Discussion](https://github.com/danielgregorio/quantum/discussions) — improving this doc
is itself a great first contribution.

By participating you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## 1. Dev setup

**Requirements:** Python 3.11+ and `pip`.

```bash
git clone https://github.com/danielgregorio/quantum.git
cd quantum
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -e ".[dev]"
```

Verify everything works:

```bash
quantum run examples/hello.q   # should print "Hello World!"
pytest tests/ -q                                 # the suite should pass
```

---

## 2. The big picture

Quantum turns an `.q` file into a running app through a small, well-defined pipeline:

```
.q file ──▶ Parser ──▶ AST ──▶ Executor/Codegen ──▶ HTML | Desktop | Terminal | Godot
          (XML→nodes)         (runs or generates code)
```

The parser and runtime are **modular**: every tag has a `Parser` (XML → AST node) and an
`Executor` (AST node → behaviour), each registered in a central registry. To add a feature
you write small, isolated classes — you almost never touch the orchestrator.

Key files:

| File | Role |
|------|------|
| `src/core/parser.py` | Parser orchestrator |
| `src/core/parser_registry.py` | Registry of tag parsers |
| `src/core/ast_nodes.py` | AST node definitions |
| `src/runtime/component.py` | Execution orchestrator |
| `src/runtime/executor_registry.py` | Registry of node executors |
| `src/runtime/service_container.py` | Dependency injection for services |

Parsers live under `src/core/parsers/{category}/` and executors under
`src/runtime/executors/{category}/`, where `category` is one of `control_flow`, `data`,
`ai`, `messaging`, `jobs`, `services`, `scripting`, or `html`.

---

## 3. Adding a new tag (the 4-step recipe)

Say you want to add `<q:greet name="...">`. You touch four places:

### 1. Define the AST node — `src/core/ast_nodes.py`

```python
@dataclass
class GreetNode(ASTNode):
    name: str
```

### 2. Write the parser — `src/core/parsers/control_flow/greet_parser.py`

```python
from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser
from core.ast_nodes import GreetNode

class GreetParser(BaseTagParser):
    @property
    def tag_names(self) -> List[str]:
        return ['greet']

    def parse(self, element: ET.Element) -> GreetNode:
        return GreetNode(name=self.get_attr(element, 'name'))
```

### 3. Write the executor — `src/runtime/executors/control_flow/greet_executor.py`

```python
from typing import Any, List, Type
from runtime.executors.base import BaseExecutor
from core.ast_nodes import GreetNode

class GreetExecutor(BaseExecutor):
    @property
    def handles(self) -> List[Type]:
        return [GreetNode]

    def execute(self, node: GreetNode, exec_context) -> Any:
        return f"Hello, {node.name}!"
```

### 4. Register both

- Parser → add to `QuantumParser._register_parsers()` in `src/core/parser.py`
- Executor → add to `ComponentRuntime._register_executors()` in `src/runtime/component.py`

Then write a test (see below) and you're done. Larger features should follow the
**Option C** structure under `src/core/features/{feature}/` — see `CLAUDE.md` and existing
features for the full layout (`manifest.yaml`, `intentions/`, `dataset/`).

---

## 4. Testing

Tests live in `tests/`, mirroring `src/`, and use pytest.

```bash
pytest tests/ -q                      # full suite
pytest tests/test_expression_cache.py # a single file
pytest tests/ -k "greet"             # by keyword
```

**Every behavioural change needs a test.** A typical tag test parses a snippet, executes
it, and asserts the output. Fixtures live in `tests/conftest.py`.

---

## 5. Code style

- **Python:** type hints on public functions, docstrings on non-trivial ones, absolute
  imports (`from core.parser import QuantumParser`), AST nodes as `@dataclass`.
- **Linting:** `ruff check src/ tests/` and `black src/ tests/` before pushing.
- **`.q` files:** Quantum tags use the `q:` prefix; databinding uses `{braces}`; components
  need `<q:component name="...">`.

---

## 6. Pull request workflow

1. **Fork** and create a branch: `git checkout -b feat/my-feature` (or `fix/`, `docs/`).
2. Make your change **with tests**.
3. Run `pytest tests/ -q` and `ruff check src/ tests/` — both green.
4. Use clear, conventional commit messages (`feat:`, `fix:`, `docs:`, `chore:`, `test:`).
5. Open a PR using the template; link any related issue and describe the *why*.

Small, focused PRs get reviewed faster than large ones. When in doubt, open an issue or
Discussion first to align on the approach.

---

## 7. Reporting bugs & requesting features

Use the [issue templates](https://github.com/danielgregorio/quantum/issues/new/choose).
For bugs, a **minimal `.q` file that reproduces the problem** is worth a thousand words.

Thank you for helping make Quantum better! 🚀
