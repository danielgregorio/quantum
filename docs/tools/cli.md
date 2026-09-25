# CLI Commands

`pip install quantum-framework` installs the `quantum` command.

```bash
quantum <command>
python -m quantum.cli.runner <command>   # the same, without the script on PATH
```

Every command takes `-h` / `--help`. This page is about the everyday ones;
the [command-line reference](/reference/cli), generated from the code, lists
every command and option.

## Commands Overview

| Command | Description |
|---------|-------------|
| `run` | Execute a `.q` file |
| `start` | Serve the application's pages |
| `stop` | Stop the server `quantum start` started |
| `console` | The application's pages in the terminal |
| `desktop` | The application's pages in a desktop window |
| `check` | Pages parse, SQL compiles, query fields exist |
| `test` | Run the app's `*.test.q` tests |
| `migrate` | Apply, roll back and plan database migrations |

## quantum run

Execute a Quantum file (`.q`).

```bash
quantum run <file.q> [options]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--debug` | Print what is parsed and run | off |
| `--config` | Path to config file | `quantum.config.yaml` |
| `--target` | Standalone UI build (`type="ui"`): `html`, `textual` (layout only), `mobile` (Laboratory) | `html` |

```bash
$ quantum run hello.q
[EXEC] Executing component: HelloWorld
[SUCCESS] Result: Hello World!

$ quantum run hello.q --debug
[DEBUG] Parsing file: hello.q
[DEBUG] AST generated: ComponentNode
[DEBUG] Validating AST...
[EXEC] Executing component: HelloWorld
   Type: pure
   Params: 0
   Returns: 1
[SUCCESS] Result: Hello World!
```

What `run` does depends on the file:

| File | Behavior |
|------|----------|
| `q:component` | Executes it and prints the result |
| `q:application type="ui"` | Builds the standalone UI (Experimental) |
| `q:application type="terminal"` | Builds the terminal app (Experimental) |
| `q:application type="game"` | Builds the game (Laboratory) |
| `q:job` | Runs the job (Experimental) |

A web app is not a `q:application`: it is pages in `components/`, served by
`quantum start` (APP-1).

A file that does not exist, does not parse or fails exits with `1`.

## quantum start

Serve the pages in `components/` on the port in `quantum.config.yaml`
(8080 by default).

```bash
quantum start                  # in the application's folder
quantum start --port 3000
quantum start --hot-reload     # reload the open pages on every save
```

Debug mode — the [/_dev panel](/tools/dev-panel) and detailed
[error pages](/tools/error-pages) — is `server.debug: true` in
`quantum.config.yaml`. The `--debug` flag only prints the traceback when the
server fails to start. See also [Hot Reload](/tools/hot-reload).

## quantum stop

Stops the server that `quantum start` started from this folder (it records its
process in `.quantum.pid`). A process it cannot be sure is that server is not
killed: the command says so and exits with `1` (RUN-3).

## quantum console

The same pages in the terminal:

```bash
quantum console              # the home page
quantum console /reports     # another page
quantum console --config other.config.yaml
```

## quantum desktop

The same pages in a desktop window ([Desktop](/targets/desktop)):

```bash
quantum desktop
quantum desktop /reports --width 800 --height 600
```

## quantum check

Parses every page and compiles every query against the database, without
running them ([quantum check](/tools/check)):

```bash
quantum check
quantum check --config other.config.yaml
```

## quantum test

Runs the `*.test.q` files of the app ([Testing an App](/guide/testing)):

```bash
quantum test                   # every *.test.q under the current folder
quantum test tests/            # a folder, or files
```

It exits with `1` when a test fails, so it fits in CI.

## quantum migrate

Database migrations in `migrations/` ([Database Queries](/guide/query)):

```bash
quantum migrate status
quantum migrate up
quantum migrate down           # the last one
quantum migrate create add_due_date
quantum migrate plan           # compare schema.sql with the migrations
```

## Other commands

`quantum admin` starts the [Quantum Admin](/guide/admin). `quantum jobs` and
`quantum mq` belong to jobs and messaging, which are Experimental (see
[Stability](/stability/)). `quantum pkg` packs and installs component
folders, but a page cannot import a component from an installed package yet:
`q:import from=` is a folder under `paths.components`. Their options are in
the [command-line reference](/reference/cli).

## Related

- [Hot Reload](/tools/hot-reload) - `quantum start --hot-reload`
- [VS Code Extension](/tools/vscode-extension) - Editor support
- [Project Structure](/guide/project-structure) - File organization
