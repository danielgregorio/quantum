# Quantum

[![CI](https://github.com/danielgregorio/quantum/actions/workflows/ci.yml/badge.svg)](https://github.com/danielgregorio/quantum/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/quantum-framework)](https://pypi.org/project/quantum-framework/)
[![Python](https://img.shields.io/pypi/pyversions/quantum-framework)](https://pypi.org/project/quantum-framework/)
[![Docs](https://img.shields.io/badge/docs-quantumframework.net-blue)](https://quantumframework.net/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/danielgregorio/quantum/blob/main/LICENSE)

> **Declarative web apps in XML, with AI and RAG built into the language.
> No build chain, no JavaScript, no frontend framework.**

Quantum is a full-stack framework whose language is markup. State, database queries,
forms, LLM calls and retrieval-augmented generation are all tags — not libraries you
wire together. It takes its philosophy from ColdFusion and Adobe Flex: the markup *is*
the app.

> **1.0, and honest about it.** See [Stability](#stability) — the table there
> reflects what has actually been executed end-to-end, not what is aspirational.

---

## The part that isn't like the others

Retrieval-augmented generation, as a language construct:

```xml
<q:component name="DocsBot">
  <q:knowledge name="docs" embedModel="nomic-embed-text">
    <q:source type="directory" path="./docs/" pattern="*.md" />
  </q:knowledge>

  <q:llm name="answer" model="phi3" knowledge="docs" minRelevance="0.79">
    <q:message role="user">{form.question}</q:message>
  </q:llm>

  <p>{answer}</p>
  <q:loop type="array" items="{answer_result.sources}" var="s">
    <p>[{s.n}] {s.name}</p>
  </q:loop>
</q:component>
```

That indexes a directory, embeds it, stores the vectors, retrieves the relevant chunks
and asks the model to answer from them, citing each one — in the markup. When no
chunk is relevant enough, the model is not asked at all. There is no Python file
behind it.

An agent with its own tools, same idea:

```xml
<q:agent name="calc" model="phi3" maxIterations="4">
  <q:instruction>Use the add tool, then answer.</q:instruction>

  <q:tool name="add" description="Add two numbers">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:function name="doAdd">
      <q:set name="sum" value="{a + b}" type="number" />
      <q:return value="{sum}" />
    </q:function>
  </q:tool>

  <q:execute task="What is 17 plus 25?" />
</q:agent>
```

The tool body is Quantum, not Python. The reasoning loop, the tool call and the type
coercion of the model's arguments are the runtime's job.

---

## The rest of the language

```xml
<q:component name="Orders">
  <q:query name="orders" datasource="db">
    SELECT id, customer, total FROM orders WHERE total > :min
    <q:param name="min" value="100" type="decimal" />
  </q:query>

  <table>
    <q:loop query="orders">
      <tr><td>{orders.customer}</td><td>{orders.total}</td></tr>
    </q:loop>
  </table>
</q:component>
```

Save it as `components/orders.q`, run `quantum start`, and it is served at
`http://localhost:8080/orders`.

`q:query` refuses to run SQL with an undeclared `:param` — parameterised queries are
enforced by the parser, not by discipline.

Also core: `q:set` with `session.` / `application.` / `request.` scopes, `q:if`,
`q:function`, `q:action` for form handling, `q:data` for CSV/JSON/XML import,
`q:import` / `q:slot` for composition.

---

## Quick start

**Requirements:** Python 3.12+ and `pip`.

```bash
pip install quantum-framework
```

Create `hello.q`:

```xml
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello World!" />
</q:component>
```

```bash
quantum run hello.q
```

```
[EXEC] Executing component: HelloWorld
[SUCCESS] Result: Hello World!
```

For a web app, put `.q` files in `components/` and run `quantum start`
(`components/index.q` is served at `/`). `quantum stop` stops it.

For the AI examples you also need an [Ollama](https://ollama.com) server and the RAG
extra:

```bash
pip install "quantum-framework[rag]"
ollama pull phi3 && ollama pull nomic-embed-text
export QUANTUM_LLM_BASE_URL=http://localhost:11434
```

Declare datasources in `quantum.config.yaml` (next to `components/`) and `q:query` works
with nothing else running — SQLite needs no extra; PostgreSQL and MySQL drivers come with
`pip install "quantum-framework[db]"`:

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
```

### CLI

| Command | What it does |
|---------|--------------|
| `run <file.q>` | Execute a component, or build a `q:application` (`ui`, `terminal`, `game`) |
| `start` | Start the web server (port 8080 by default; `--port` to change) |
| `stop` | Stop the server started by `start` |
| `check` | Check that pages parse, SQL compiles and query fields exist |
| `test` | Run the app's `*.test.q` tests |
| `console` · `desktop` | The application's pages in the terminal, or in a desktop window |
| `admin` | Start the Quantum Admin (`pip install "quantum-framework[admin]"`) |
| `pkg` · `jobs` · `mq` · `migrate` | Packages, jobs, message queues, migrations |

### From source

To work on Quantum itself:

```bash
git clone https://github.com/danielgregorio/quantum.git
cd quantum
pip install -e ".[dev]"
quantum run examples/hello.q
```

See [CONTRIBUTING.md](https://github.com/danielgregorio/quantum/blob/main/CONTRIBUTING.md) for the test suite and the architecture.

---

## Documentation

Full docs at **[quantumframework.net](https://quantumframework.net/)**:

- [Getting Started](https://quantumframework.net/guide/getting-started) · [Installation](https://quantumframework.net/guide/installation) · [Quick Start](https://quantumframework.net/guide/quick-start)
- [Components](https://quantumframework.net/guide/components) · [State](https://quantumframework.net/guide/state-management) · [Loops](https://quantumframework.net/guide/loops) · [Conditionals](https://quantumframework.net/guide/conditionals)
- [Queries](https://quantumframework.net/guide/query) · [Functions](https://quantumframework.net/guide/functions)

Releases and their notes are on the [GitHub Releases](https://github.com/danielgregorio/quantum/releases) page.

---

## Stability

Support levels are defined in **[SUPPORT_TIERS.md](https://github.com/danielgregorio/quantum/blob/main/SUPPORT_TIERS.md)**. Short version:

| Tier | Surface |
|------|---------|
| **Core** — documented, tested end to end, stable | `q:component`, `q:set`, `q:if`, `q:loop`, `q:function`, `q:query`, `q:transaction`, `q:action`, `q:invoke`, `q:data`, `q:import` / `q:slot`, `q:file`, `q:mail`, the Core set of `ui:*`, `require_auth` / `require_role` |
| **AI** — the Core contract plus a live test against a real model | `q:llm`, `q:knowledge`, `q:agent` |
| **Experimental** — they run, but no API stability promise | `q:team`, jobs, messaging, websockets, `q:log` / `q:dump`, `ui:*` outside the Core set, the terminal target |
| Experimental, and a full-trust escape hatch | Python scripting (`q:python`, `q:pyclass`, `q:pyimport`) — off by default, see [SECURITY.md](https://github.com/danielgregorio/quantum/blob/main/SECURITY.md) |

A functional audit in 2026-09 found that several of these surfaces had never been run
end-to-end despite being documented as complete. They were fixed or re-labelled, and
feature status is now verified by execution rather than asserted by hand.

From 1.0, **Core and AI follow semantic versioning**: a 1.x release does not break a
program that uses only them — their meaning is fixed by the rules in
[SPEC.md](https://github.com/danielgregorio/quantum/blob/main/SPEC.md), and a break
waits for 2.0. Experimental and Laboratory surfaces carry no such promise and may
change in any release.

---

## Project layout

```
quantum/
├── quantum/
│   ├── core/        # Parser & AST (registry-based, modular)
│   ├── runtime/     # Execution engine, web server, renderer
│   └── cli/         # Command-line entry point
├── examples/        # runnable .q examples
├── tests/           # pytest suite (~3.8k tests)
├── scripts/         # dev tools
└── docs/            # VitePress documentation
```

Adding a tag is one parser + one executor + a registry entry — see
[CONTRIBUTING.md](https://github.com/danielgregorio/quantum/blob/main/CONTRIBUTING.md).

---

## Contributing

Read **[CONTRIBUTING.md](https://github.com/danielgregorio/quantum/blob/main/CONTRIBUTING.md)** for dev setup and how the modular
parser/executor architecture works. By participating you agree to the
[Code of Conduct](https://github.com/danielgregorio/quantum/blob/main/CODE_OF_CONDUCT.md).

Found a security issue? Follow [SECURITY.md](https://github.com/danielgregorio/quantum/blob/main/SECURITY.md) — **do not** open a public issue.

## License

MIT — see [LICENSE](https://github.com/danielgregorio/quantum/blob/main/LICENSE).
