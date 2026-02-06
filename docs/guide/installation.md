# Installation

This guide covers the complete installation process for Quantum Framework.

## System Requirements

### Required
- **Python 3.8+** (Python 3.10+ recommended)
- **pip** (Python package manager)
- **Git** (for cloning the repository)

### Optional (by feature)
- **SQLite/PostgreSQL/MySQL** - For database features
- **pywebview** - For desktop applications
- **textual** - For terminal applications
- **Node.js** - For React Native mobile builds

## Quick Installation

```bash
# Clone the repository
git clone https://github.com/danielgregorio/quantum.git
cd quantum

# Install core dependencies
pip install -r requirements.txt

# Or install manually
pip install flask lxml
```

## Installation Options

### Minimal (Core Only)

For basic component execution without web features:

```bash
pip install lxml
```

### Web Applications

For running web servers and HTML applications:

```bash
pip install flask lxml
```

### Full Stack

For all features including database support:

```bash
pip install flask lxml sqlalchemy
```

### Desktop Applications

For building native desktop apps with pywebview:

```bash
pip install flask lxml pywebview

# On Linux, you may also need:
# sudo apt install python3-gi python3-gi-cairo gir1.2-webkit2-4.0
```

### Terminal Applications

For building terminal-based TUI applications:

```bash
pip install flask lxml textual
```

### All Features

```bash
pip install flask lxml sqlalchemy pywebview textual
```

## Verifying Installation

### Check Core Installation

```bash
python src/cli/runner.py run examples/hello.q
```

Expected output:
```
[EXEC] Executing component: HelloWorld
[SUCCESS] Result: Hello World!
```

### Check Web Server

```bash
python src/cli/runner.py start
```

The server should start on `http://localhost:5000`.

### Check UI Builder

```bash
python -c "from runtime.ui_builder import UIBuilder; print('UI Builder OK')"
```

## Project Structure

After cloning, you'll have:

```
quantum/
├── src/                    # Core source code
│   ├── core/               # Parser and AST
│   ├── runtime/            # Execution engine
│   └── cli/                # Command-line interface
├── examples/               # Example .q files
├── tests/                  # Test suite
├── docs/                   # Documentation
└── components/             # Reusable components
```

## Configuration

### Database Configuration

Create a `quantum.yaml` in your project root:

```yaml
datasources:
  default:
    driver: sqlite
    database: ./data/app.db

  production:
    driver: postgresql
    host: localhost
    port: 5432
    database: myapp
    username: ${DB_USER}
    password: ${DB_PASS}
```

### Environment Variables

Quantum supports environment variable substitution:

```bash
export DB_USER=myuser
export DB_PASS=mypassword
export QUANTUM_DEBUG=true
```

## Development Setup

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_parser.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Building Documentation

```bash
cd docs
npm install
npm run dev
```

## Troubleshooting

### Common Issues

#### "Module not found" Errors

Make sure you're running from the quantum root directory:

```bash
cd /path/to/quantum
python src/cli/runner.py run myfile.q
```

#### XML Parsing Errors

Ensure your .q files have valid XML:
- All tags must be closed
- Attributes must be quoted
- Special characters must be escaped (`&lt;`, `&gt;`, `&amp;`)

#### Database Connection Errors

Check your datasource configuration:

```xml
<q:query name="test" datasource="default">
  SELECT 1
</q:query>
```

### Getting Help

- [GitHub Issues](https://github.com/danielgregorio/quantum/issues)
- [Examples](/examples/)
- [API Reference](/api/)

## Next Steps

- [Quick Start](/guide/quick-start) - Build your first app
- [Project Structure](/guide/project-structure) - Organize your code
- [Components](/guide/components) - Learn the component system
