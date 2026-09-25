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

Retrieval-augmented generation, as a language construct — this page answers a
question from the Markdown files in `knowledge/` and lists the ones it used:

```xml
<q:component name="Ask">
  <!-- The documents in knowledge/, split into chunks and embedded when the
       page runs. persist="false" keeps the index in memory; without it, it is
       stored in ./.quantum/knowledge and reused until a document changes. -->
  <q:knowledge name="docs" persist="false" chunkSize="300" chunkOverlap="30">
    <q:source type="directory" path="knowledge" pattern="*.md" />
  </q:knowledge>

  <q:set name="question" value="{query.q}" default="" />

  <q:if condition="question">
    <!-- The question retrieves the closest chunks; they reach the model
         numbered, with the instruction to answer only from them and cite
         them like [1]. -->
    <q:llm name="answer" knowledge="docs" top="2">
      <q:message role="user">{question}</q:message>
    </q:llm>
  </q:if>

  <ui:window title="Ask the store">
    <ui:form>
      <ui:input bind="q" value="{question}" placeholder="Your question" />
      <ui:button variant="primary">Ask</ui:button>
    </ui:form>
    <q:if condition="question">
      <ui:text>{answer}</ui:text>
      <q:if condition="answer_result.grounded">
        <ui:text>Sources:</ui:text>
        <q:loop items="{answer_result.sources}" var="s">
          <ui:text>[{s.n}] {s.name}</ui:text>
        </q:loop>
        <q:else>
          <ui:alert variant="warning">This answer cites none of the documents.</ui:alert>
        </q:else>
      </q:if>
    </q:if>
  </ui:window>
</q:component>
```

That splits the documents into chunks, embeds them, retrieves the closest ones
and asks the model to answer only from them, citing each one — in the markup.
`answer_result.grounded` says whether the answer cites any of them. There is no
Python file behind it. (Recipe:
[Answers with their sources](https://quantumframework.net/cookbook/ai/answer-with-sources).)

An agent whose tools you write in Quantum, same idea:

```xml
<q:component name="Assistant">
  <!-- The model never writes SQL: it picks a tool and its arguments. The
       tool is a read-only query you wrote; its q:param says the argument's
       type, and the model's value is converted to it before the query runs. -->
  <q:agent name="stock" maxIterations="4" timeout="60000" onerror="continue">
    <q:instruction>You help a shop owner. Use the tools to look at the data,
      then answer in one sentence.</q:instruction>

    <q:tool name="low_stock" description="Products with fewer units in stock than `below`">
      <q:param name="below" type="integer" default="5" />
      <q:function name="lowStock">
        <q:query name="rows" datasource="db">
          SELECT name, stock FROM products WHERE stock &lt; :below ORDER BY stock
          <q:param name="below" value="{below}" type="integer" />
        </q:query>
        <q:return value="{rows}" />
      </q:function>
    </q:tool>

    <q:execute task="Which products are running out of stock?" />
  </q:agent>

  <ui:window title="Stock assistant">
    <q:if condition="stock_result.success">
      <ui:text>{stock}</ui:text>
      <q:else>
        <ui:alert variant="warning">The assistant did not finish: {stock_result.error.message}</ui:alert>
      </q:else>
    </q:if>
    <!-- Every tool call the agent made, written out. -->
    <q:loop items="{stock_result.actions}" var="a">
      <ui:text>Called {a.call}</ui:text>
    </q:loop>
  </ui:window>
</q:component>
```

The model never writes SQL: it picks a tool and its arguments, and the
argument is converted to the `q:param`'s type before the query runs. The
reasoning loop, the tool calls and the failure contract (`onerror`,
`stock_result`) are the runtime's job. (Recipe:
[An agent over your database](https://quantumframework.net/cookbook/ai/agent-over-your-database).)

---

## The rest of the language

```xml
<q:component name="Products">
  <!-- ?name=mouse from the URL; empty when it is not there. -->
  <q:set name="term" value="{query.name}" default="" />

  <!-- :pattern is bound to the q:param: the value is sent to the database
       apart from the SQL, so it can never change what the SQL does. -->
  <q:query name="products" datasource="db">
    SELECT name, price FROM products WHERE name LIKE :pattern ORDER BY price
    <q:param name="pattern" value="%{term}%" type="string" />
  </q:query>

  <ui:window title="Products">
    <ui:text>{products_result.recordCount} products</ui:text>
    <ui:table source="{products}">
      <ui:column key="name" label="Name" />
      <ui:column key="price" label="Price" />
    </ui:table>
  </ui:window>
</q:component>
```

Saved as `components/index.q`, with the database declared in
`quantum.config.yaml`, `quantum start` serves it at `http://localhost:8080/`,
and `/?name=mouse` filters it. (Recipe:
[A query with parameters](https://quantumframework.net/cookbook/data-and-sql/query-with-parameters).)

`q:query` refuses to run SQL with an undeclared `:param` — parameterised queries are
enforced by the parser, not by discipline.

Also core: `q:set` with `session.` / `application.` / `request.` scopes, `q:if`,
`q:function`, `q:action` for form handling, `q:data` for CSV/JSON/XML import,
`q:import` / `q:slot` for composition.

The examples above are files of [Cookbook](https://quantumframework.net/cookbook/)
recipes, byte for byte, and the recipes run in CI; the quick start below is run
as shown (`tests/docs/test_readme.py` checks both).

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

For the AI examples you also need a model server — [Ollama](https://ollama.com)
at `http://localhost:11434` unless `QUANTUM_LLM_BASE_URL` says otherwise — and
the RAG extra. There is no built-in model name: say which one in
`quantum.config.yaml` (`llm: model: phi3`) or `QUANTUM_LLM_DEFAULT_MODEL`.

```bash
pip install "quantum-framework[rag]"
ollama pull phi3 && ollama pull nomic-embed-text
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
| `migrate` | Apply, roll back and plan database migrations |
| `admin` | Start the Quantum Admin (`pip install "quantum-framework[admin]"`) |
| `pkg` · `jobs` · `mq` | Component packages (a page cannot import one yet), jobs, message queues — no stability promise |

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

- **Start:** [Installation](https://quantumframework.net/guide/installation) · [Quick Start](https://quantumframework.net/guide/quick-start) · [Tutorial: build the tasks app](https://quantumframework.net/tutorial/tasks-app)
- **Learn:** [Guide](https://quantumframework.net/guide/getting-started) · [Cookbook](https://quantumframework.net/cookbook/) — short tested recipes · [Showcase](https://quantumframework.net/showcase/) — the complete apps
- **Look up:** [Reference](https://quantumframework.net/reference/) — every tag, function, command and SPEC rule, generated from the code
- **Plan:** [Stability](https://quantumframework.net/stability/) — what 1.0 promises · [Roadmap](https://quantumframework.net/roadmap/) · [Changelog](https://quantumframework.net/changelog/)

The site is also in [Português](https://quantumframework.net/pt/), [Español](https://quantumframework.net/es/) and [中文](https://quantumframework.net/zh/).

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
├── tests/           # pytest suite; conformance/ cites SPEC.md
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
