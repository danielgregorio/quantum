# CLI Commands

The Quantum CLI provides commands for developing, building, and deploying Quantum applications.

## Installation

`pip install quantum-framework` installs the `quantum` command.

```bash
quantum <command>
python -m quantum.cli.runner <command>   # the same, without the script on PATH
```

## Commands Overview

| Command | Description |
|---------|-------------|
| `run` | Execute a .q file |
| `start` | Start web server |
| `console` | The application's pages in the terminal |
| `desktop` | The application's pages in a desktop window |
| `check` | Pages parse, SQL compiles, query fields exist |
| `pkg` | Package management |

## quantum run

Execute a Quantum file (.q).

```bash
quantum run <file.q> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `file` | Path to .q file to execute |

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--debug` | Enable debug output | false |
| `--config` | Path to config file | quantum.config.yaml |
| `--target` | Standalone UI build (`type="ui"`): html, textual (layout only), mobile (Laboratory) | html |

### Examples

```bash
# Run a component
quantum run examples/hello.q

# Run with debug output
quantum run examples/hello.q --debug

# Standalone layout build of a type="ui" application
quantum run myapp.q --target textual

# Run with custom config
quantum run myapp.q --config production.yaml
```

### Behavior by Application Type

The `run` command behaves differently based on the application type:

| Type | Behavior |
|------|----------|
| `q:component` | Executes and prints result |
| `q:application type="ui"` | Builds to target output |
| `q:application type="game"` | Builds HTML game file |
| `q:application type="terminal"` | Builds TUI app |
| `q:job` | Executes job |

A web app is not a `q:application`: it is pages in `components/`, served by
`quantum start` (APP-1).

### Debug Output

With `--debug`, you see:
- File parsing details
- AST generation info
- Validation steps
- Execution flow

```bash
$ quantum run hello.q --debug
[DEBUG] Parsing file: hello.q
[DEBUG] AST generated: ComponentNode
[DEBUG] Validating AST...
[EXEC] Executing component: HelloWorld
[SUCCESS] Result: Hello World!
```

## quantum start

Start the Quantum web server.

```bash
quantum start [options]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--port` | Server port | 8080 |
| `--config` | Config file | quantum.config.yaml |
| `--debug` | Debug mode | false |
| `--hot-reload` | Reload the open pages when a component or static file changes ([Hot Reload](/tools/hot-reload)) | off |
| `--hot-reload-port` | WebSocket port for `--hot-reload` | 35729 |

### Examples

```bash
# Start with default settings
quantum start

# Start on custom port
quantum start --port 3000

# Start in debug mode
quantum start --debug

# Reload the browser on every save
quantum start --hot-reload
```

### Configuration File

The server reads settings from `quantum.config.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8080
  debug: false

datasources:
  db:
    driver: sqlite
    database: ./data/app.db

security:
  secret_key: ${SECRET_KEY}
```

## quantum console

Open the application's pages in the terminal. It starts the application's
server and draws each page with Textual; buttons and forms send the page's
`q:action`s, with a session, so login, validation and flash are the web's.

```bash
quantum console              # the home page
quantum console /reports     # another page
quantum console --config other.config.yaml
```

## quantum desktop

Open the application's pages in a native window (pywebview). It needs the
`[desktop]` extra. See [Desktop](/targets/desktop).

```bash
pip install "quantum-framework[desktop]"
quantum desktop
quantum desktop /reports --width 800 --height 600
```

Both render the same pages as `quantum start` — see
[One App, Many Screens](/guide/ui).

## quantum check

Check every page against the database: pages parse, each `q:query` compiles,
each `{query.field}` a page reads is a column the query returns. Exit code 1
on any problem. See [quantum check](/tools/check).

```bash
quantum check
quantum check --config other.config.yaml
```

## quantum pkg

Package management for Quantum components.

```bash
quantum pkg <subcommand> [options]
```

### Subcommands

| Subcommand | Description |
|------------|-------------|
| `init <path>` | Initialize new package |
| `install <path>` | Install package |
| `list` | List installed packages |
| `uninstall <name>` | Uninstall package |
| `publish` | Publish package |

### pkg init

Create a new Quantum package:

```bash
quantum pkg init ./my-component
```

Creates this structure:

```
my-component/
  package.yaml       # Package manifest
  src/
    component.q      # Main component
  tests/
    test_component.q # Test file
  README.md          # Documentation
```

### pkg install

Install a package:

```bash
# Install from local path
quantum pkg install ./my-package

# Install from URL (future)
quantum pkg install https://github.com/user/quantum-pkg
```

Packages are installed to `components/` directory.

### pkg list

List installed packages:

```bash
$ quantum pkg list

Installed Packages:
  - form-validator@1.0.0
  - data-grid@2.1.0
  - chart-components@1.2.0
```

### pkg uninstall

Remove a package:

```bash
quantum pkg uninstall form-validator
```

### Package Manifest

`package.yaml` format:

```yaml
name: my-component
version: 1.0.0
description: A useful Quantum component
author: Your Name
license: MIT

# Component entry point
main: src/component.q

# Dependencies
dependencies:
  - utils@^1.0.0

# Keywords for discovery
keywords:
  - ui
  - form
  - validation
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (parse, validation, execution) |
| 2 | Configuration error |
| 3 | File not found |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `QUANTUM_CONFIG` | Config file path | quantum.config.yaml |
| `QUANTUM_DEBUG` | Enable debug mode | false |
| `QUANTUM_PORT` | Default server port | 8080 |

## Related

- [Hot Reload](/tools/hot-reload) - `quantum start --hot-reload`
- [VS Code Extension](/tools/vscode-extension) - Editor support
- [Project Structure](/guide/project-structure) - File organization
