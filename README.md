# Quantum

[![CI](https://github.com/danielgregorio/quantum/actions/workflows/ci.yml/badge.svg)](https://github.com/danielgregorio/quantum/actions/workflows/ci.yml)
[![Docker](https://github.com/danielgregorio/quantum/actions/workflows/docker.yml/badge.svg)](https://github.com/danielgregorio/quantum/actions/workflows/docker.yml)
[![Docs](https://img.shields.io/badge/docs-quantum.sargas.cloud-blue)](https://quantum.sargas.cloud)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

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

`q:query` refuses to run SQL with an undeclared `:param` — parameterised queries are
enforced by the parser, not by discipline.

Also core: `q:set` with `session.` / `application.` / `request.` scopes, `q:if`,
`q:function`, `q:action` for form handling, `q:data` for CSV/JSON/XML import,
`q:import` / `q:slot` for composition.

---

## Quick start

**Requirements:** Python 3.11+ and `pip`.

```bash
git clone https://github.com/danielgregorio/quantum.git
cd quantum
pip install -e ".[dev]"

quantum run examples/hello.q
```

```
[EXEC] Executing component: HelloWorld
[SUCCESS] Result: Hello World!
```

For the AI examples you also need an [Ollama](https://ollama.com) server and the RAG
extra:

```bash
pip install -e ".[rag]"
ollama pull phi3 && ollama pull nomic-embed-text
export QUANTUM_LLM_BASE_URL=http://localhost:11434
```

Declare datasources in `quantum.config.yaml` and `q:query` works with nothing else
running:

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
| `start` | Start the web server |
| `deploy <dir>` | Deploy an application |
| `pkg` · `jobs` · `mq` · `migrate` | Packages, jobs, message queues, migrations |

---

## Documentation

Full docs (VitePress) at **[quantum.sargas.cloud](https://quantum.sargas.cloud)** and in
[`docs/`](docs/):

- [Getting Started](docs/guide/getting-started.md) · [Installation](docs/guide/installation.md) · [Quick Start](docs/guide/quick-start.md)
- [Components](docs/guide/components.md) · [State](docs/guide/state-management.md) · [Loops](docs/guide/loops.md) · [Conditionals](docs/guide/conditionals.md)
- [Queries](docs/guide/query.md) · [Functions](docs/guide/functions.md) · [Data fetching](docs/guide/data-fetching.md)

---

## Stability

Support levels are defined in **[SUPPORT_TIERS.md](SUPPORT_TIERS.md)**. Short version:

| Surface | Status |
|---------|--------|
| Core language — `q:component`, `q:set`, `q:if`, `q:loop`, `q:function`, `q:query`, `q:action`, `q:invoke`, `q:data` | **Stable** |
| AI — `q:llm`, `q:knowledge`, `q:agent` | **Beta** — validated end-to-end against a live Ollama server |
| `q:team` (multi-agent handoff) | Beta, less exercised |
| Jobs, messaging, websockets, mail, file uploads, `ui:*`, terminal target | **Experimental** — they run, but no API stability promise |
| Python scripting (`q:python`, `q:pyclass`, `q:pyimport`) | Experimental, and a full-trust escape hatch — see [SECURITY.md](SECURITY.md) |

A functional audit in 2026-09 found that several of these surfaces had never been run
end-to-end despite being documented as complete. The findings and the fixes are in
[`FULL_AUDIT_2026-09.md`](FULL_AUDIT_2026-09.md) and
[`AUDIT_FIX_PLAN.md`](AUDIT_FIX_PLAN.md). Feature status is now verified by execution
rather than asserted by hand.

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
├── tests/           # pytest suite (~2.4k tests)
├── scripts/         # dev tools
└── docs/            # VitePress documentation
```

Adding a tag is one parser + one executor + a registry entry — see
[CONTRIBUTING.md](CONTRIBUTING.md).

---

## Contributing

Read **[CONTRIBUTING.md](CONTRIBUTING.md)** for dev setup and how the modular
parser/executor architecture works. By participating you agree to the
[Code of Conduct](CODE_OF_CONDUCT.md).

Found a security issue? Follow [SECURITY.md](SECURITY.md) — **do not** open a public issue.

## License

MIT — see [LICENSE](LICENSE).
