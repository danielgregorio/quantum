# Installation

## Requirements

- **Python 3.12+**
- **pip**

## Install

```bash
pip install quantum-framework
```

This installs the `quantum` command and the `quantum` Python package. Check it:

```bash
quantum --version
```

```
quantum 0.9.0
```

::: tip Use a virtual environment
`python -m venv .venv`, then activate it (`source .venv/bin/activate`, or
`.venv\Scripts\activate` on Windows) before `pip install`.
:::

### Optional extras

The base install covers components, the web server, SQLite queries and the
terminal target. Everything else is an extra:

| Extra | Install | Adds |
|-------|---------|------|
| `db` | `pip install "quantum-framework[db]"` | PostgreSQL and MySQL drivers for `q:query` |
| `rag` | `pip install "quantum-framework[rag]"` | Vector store for `q:knowledge` / RAG queries |
| `jobs` | `pip install "quantum-framework[jobs]"` | Scheduler behind `q:schedule` |
| `websocket` | `pip install "quantum-framework[websocket]"` | Transport behind `q:websocket` |

Extras combine: `pip install "quantum-framework[db,jobs]"`.

The **desktop** target also needs `pip install pywebview` (on Linux, pywebview
has system dependencies of its own — see its documentation).

The AI tags (`q:llm`, `q:knowledge`, `q:agent`) talk to an
[Ollama](https://ollama.com) server — `http://localhost:11434` unless
`QUANTUM_LLM_BASE_URL` says otherwise.

See [SUPPORT_TIERS.md](https://github.com/danielgregorio/quantum/blob/main/SUPPORT_TIERS.md)
for which of these are stable and which are experimental.

## Verify

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

### Web server

Put components in a `components/` folder and start the server from the folder
that contains it:

```
myapp/
└── components/
    └── index.q      # served at /
```

```bash
quantum start               # http://localhost:8080
quantum start --port 9000   # another port
quantum stop                # stops the server started above
```

`components/orders.q` is served at `/orders`, and so on.

## Configuration

Settings live in `quantum.config.yaml`, next to `components/`. Datasources for
`q:query`:

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
```

::: warning
Values in `quantum.config.yaml` are read literally: `${VAR}` is **not**
replaced by an environment variable.
:::

## From source

To work on Quantum itself:

```bash
git clone https://github.com/danielgregorio/quantum.git
cd quantum
pip install -e ".[dev,db,jobs,websocket]" -r quantum_admin/backend/requirements.txt
pytest
```

The docs site is built from the repository root:

```bash
npm ci
npm run docs:dev
```

[CONTRIBUTING.md](https://github.com/danielgregorio/quantum/blob/main/CONTRIBUTING.md)
covers the architecture and how to add a tag.

## Troubleshooting

**`quantum: command not found`** — the environment where you ran `pip install`
is not active, or its `Scripts`/`bin` folder is not on `PATH`.
`python -m quantum.cli.runner --version` works either way.

**XML parse errors** — a `.q` file is XML: every tag closes, attributes are
quoted, and `<`, `>`, `&` in text are written `&lt;`, `&gt;`, `&amp;`. The error
names the line and column.

**`Port 8080 already in use`** — another server is running. `quantum stop`, or
`quantum start --port <other>`.

## Next steps

- [Quick Start](/guide/quick-start) — build your first app
- [Components](/guide/components) — the component system
- [Help and issues](https://github.com/danielgregorio/quantum/issues)
