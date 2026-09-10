# Quantum

[![CI](https://github.com/danielgregorio/quantum/actions/workflows/ci.yml/badge.svg)](https://github.com/danielgregorio/quantum/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/quantum-framework)](https://pypi.org/project/quantum-framework/)
[![Python](https://img.shields.io/pypi/pyversions/quantum-framework)](https://pypi.org/project/quantum-framework/)
[![Docs](https://img.shields.io/badge/docs-github.io-blue)](https://danielgregorio.github.io/quantum/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/danielgregorio/quantum/blob/main/LICENSE)

> **Declarative web apps in XML, with AI and RAG built into the language.
> No build chain, no JavaScript, no frontend framework.**

Quantum is a full-stack framework whose language is markup. State, database queries,
forms, LLM calls and retrieval-augmented generation are all tags — not libraries you
wire together. It takes its philosophy from ColdFusion and Adobe Flex: the markup *is*
the app.

> ⚠️ **Pre-1.0, and honest about it.** See [Stability](#stability) — the table there
> reflects what has actually been executed end-to-end, not what is aspirational.

---

## The part that isn't like the others

Retrieval-augmented generation, as a language construct:

```xml
<q:component name="DocsBot">
  <q:knowledge name="docs" model="phi3" embedModel="nomic-embed-text">
    <q:source type="directory" path="./docs/" pattern="*.md" />
  </q:knowledge>

  <q:query name="answer" datasource="knowledge:docs" mode="rag">
    SELECT answer FROM chunks WHERE content SIMILAR TO :question
    <q:param name="question" value="{form.question}" type="string" />
  </q:query>

  <p>{answer.answer}</p>
</q:component>
```

That indexes a directory, embeds it, stores the vectors, retrieves the relevant chunks
and asks the model — in the markup. There is no Python file behind it.

An agent with its own tools, same idea:

```xml
<q:agent name="calc" model="phi3" max_iterations="4">
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
| `run <file.q>` | Execute a component, app, or API |
| `start` | Start the web server (port 8080 by default; `--port` to change) |
| `stop` | Stop the server started by `start` |
| `deploy [path]` · `apps` | Deploy an application, manage deployed ones |
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

Full docs at **[danielgregorio.github.io/quantum](https://danielgregorio.github.io/quantum/)**:

- [Getting Started](https://danielgregorio.github.io/quantum/guide/getting-started) · [Installation](https://danielgregorio.github.io/quantum/guide/installation) · [Quick Start](https://danielgregorio.github.io/quantum/guide/quick-start)
- [Components](https://danielgregorio.github.io/quantum/guide/components) · [State](https://danielgregorio.github.io/quantum/guide/state-management) · [Loops](https://danielgregorio.github.io/quantum/guide/loops) · [Conditionals](https://danielgregorio.github.io/quantum/guide/conditionals)
- [Queries](https://danielgregorio.github.io/quantum/guide/query) · [Functions](https://danielgregorio.github.io/quantum/guide/functions) · [Data fetching](https://danielgregorio.github.io/quantum/guide/data-fetching)

Releases and their notes are on the [GitHub Releases](https://github.com/danielgregorio/quantum/releases) page.

---

## Stability

Support levels are defined in **[SUPPORT_TIERS.md](https://github.com/danielgregorio/quantum/blob/main/SUPPORT_TIERS.md)**. Short version:

| Surface | Status |
|---------|--------|
| Core language — `q:component`, `q:set`, `q:if`, `q:loop`, `q:function`, `q:query`, `q:action`, `q:invoke`, `q:data` | **Stable** |
| AI — `q:llm`, `q:knowledge`, `q:agent` | **Beta** — validated end-to-end against a live Ollama server |
| `q:team` (multi-agent handoff) | Beta, less exercised |
| Jobs, messaging, websockets, mail, file uploads, `ui:*`, terminal target | **Experimental** — they run, but no API stability promise |
| Python scripting (`q:python`, `q:pyclass`, `q:pyimport`) | Experimental, and a full-trust escape hatch — see [SECURITY.md](https://github.com/danielgregorio/quantum/blob/main/SECURITY.md) |

A functional audit in 2026-09 found that several of these surfaces had never been run
end-to-end despite being documented as complete. They were fixed or re-labelled, and
feature status is now verified by execution rather than asserted by hand.

Pre-1.0: APIs may change between minor versions.

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
