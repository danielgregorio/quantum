# CLI Commands

The Quantum CLI provides commands for developing, building, and deploying Quantum applications.

## Installation

The CLI is included with Quantum. No separate installation needed.

```bash
# Run directly
python src/cli/runner.py <command>

# Or create an alias
alias quantum="python /path/to/quantum/src/cli/runner.py"
```

## Commands Overview

| Command | Description |
|---------|-------------|
| `run` | Execute a .q file |
| `start` | Start web server |
| `deploy` | Deploy to cloud |
| `apps` | Manage deployed apps |
| `pkg` | Package management |

## quantum run

Execute a Quantum file (.q).

```bash
python src/cli/runner.py run <file.q> [options]
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
| `--target` | UI target (html, textual, desktop) | html |

### Examples

```bash
# Run a component
python src/cli/runner.py run examples/hello.q

# Run with debug output
python src/cli/runner.py run examples/hello.q --debug

# Run UI app with specific target
python src/cli/runner.py run myapp.q --target desktop

# Run with custom config
python src/cli/runner.py run myapp.q --config production.yaml
```

### Behavior by Application Type

The `run` command behaves differently based on the application type:

| Type | Behavior |
|------|----------|
| `q:component` | Executes and prints result |
| `q:application type="html"` | Starts web server |
| `q:application type="api"` | Starts API server |
| `q:application type="ui"` | Builds to target output |
| `q:application type="game"` | Builds HTML game file |
| `q:application type="terminal"` | Builds TUI app |
| `q:application type="testing"` | Builds pytest file |
| `q:job` | Executes job |

### Debug Output

With `--debug`, you see:
- File parsing details
- AST generation info
- Validation steps
- Execution flow

```bash
$ python src/cli/runner.py run hello.q --debug
[DEBUG] Parsing file: hello.q
[DEBUG] AST generated: ComponentNode
[DEBUG] Validating AST...
[EXEC] Executing component: HelloWorld
[SUCCESS] Result: Hello World!
```

## quantum start

Start the Quantum web server.

```bash
python src/cli/runner.py start [options]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--port` | Server port | 8080 |
| `--config` | Config file | quantum.config.yaml |
| `--debug` | Debug mode | false |

### Examples

```bash
# Start with default settings
python src/cli/runner.py start

# Start on custom port
python src/cli/runner.py start --port 3000

# Start in debug mode
python src/cli/runner.py start --debug
```

### Configuration File

The server reads settings from `quantum.config.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8080
  debug: false

database:
  default:
    driver: sqlite
    database: ./data.db

auth:
  secret_key: "your-secret-key"
  session_timeout: 3600
```

## quantum deploy

Deploy application to cloud infrastructure.

```bash
python src/cli/runner.py deploy <path> [options]
```

**Note**: Requires `requests` package: `pip install requests`

### Arguments

| Argument | Description |
|----------|-------------|
| `path` | Path to application directory |

### Options

| Option | Description |
|--------|-------------|
| `--name` | Application name |
| `--env` | Environment (dev, staging, prod) |
| `--force` | Force redeploy |

### Examples

```bash
# Deploy application
python src/cli/runner.py deploy ./my-app

# Deploy with custom name
python src/cli/runner.py deploy ./my-app --name myapp-prod

# Deploy to staging
python src/cli/runner.py deploy ./my-app --env staging

# Force redeploy
python src/cli/runner.py deploy ./my-app --force
```

## quantum apps

Manage deployed applications.

```bash
python src/cli/runner.py apps [subcommand] [options]
```

### Subcommands

| Subcommand | Description |
|------------|-------------|
| (none) | List all applications |
| `logs <app>` | View application logs |
| `status <app>` | Check application status |
| `stop <app>` | Stop application |
| `restart <app>` | Restart application |
| `delete <app>` | Delete application |

### Examples

```bash
# List all apps
python src/cli/runner.py apps

# View logs
python src/cli/runner.py apps logs my-app

# Check status
python src/cli/runner.py apps status my-app

# Restart app
python src/cli/runner.py apps restart my-app

# Delete app
python src/cli/runner.py apps delete my-app
```

## quantum pkg

Package management for Quantum components.

```bash
python src/cli/runner.py pkg <subcommand> [options]
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
python src/cli/runner.py pkg init ./my-component
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
python src/cli/runner.py pkg install ./my-package

# Install from URL (future)
python src/cli/runner.py pkg install https://github.com/user/quantum-pkg
```

Packages are installed to `components/` directory.

### pkg list

List installed packages:

```bash
$ python src/cli/runner.py pkg list

Installed Packages:
  - form-validator@1.0.0
  - data-grid@2.1.0
  - chart-components@1.2.0
```

### pkg uninstall

Remove a package:

```bash
python src/cli/runner.py pkg uninstall form-validator
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

## Future Commands

These commands are planned for future releases:

### quantum new

Create new projects and components:

```bash
# Create new project
quantum new project my-app

# Create new component
quantum new component UserProfile

# Create new feature
quantum new feature authentication
```

### quantum dev

Start development server with hot reload:

```bash
quantum dev myapp.q
```

See [Hot Reload](/tools/hot-reload) for details.

### quantum build

Build for production:

```bash
# Build for specific target
quantum build myapp.q --target html --output dist/

# Build with minification
quantum build myapp.q --minify

# Build with source maps
quantum build myapp.q --sourcemaps
```

### quantum serve

Serve built files:

```bash
# Serve dist folder
quantum serve dist/

# Serve on specific port
quantum serve dist/ --port 3000
```

### quantum test

Run tests:

```bash
# Run all tests
quantum test

# Run specific test file
quantum test tests/test_component.q

# Run with coverage
quantum test --coverage

# Run in watch mode
quantum test --watch
```

### quantum lint

Lint Quantum files:

```bash
# Lint all files
quantum lint

# Lint specific file
quantum lint myapp.q

# Auto-fix issues
quantum lint --fix

# Check only (no output on success)
quantum lint --quiet
```

### quantum docs

Generate documentation:

```bash
# Generate docs
quantum docs

# Generate to specific folder
quantum docs --output docs/api/

# Include private members
quantum docs --include-private
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

- [Hot Reload](/tools/hot-reload) - Development server
- [VS Code Extension](/tools/vscode-extension) - Editor support
- [Project Structure](/guide/project-structure) - File organization
