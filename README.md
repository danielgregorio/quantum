# Quantum - Experimental Language

[![CI](https://github.com/danielgregorio/quantum/actions/workflows/ci.yml/badge.svg)](https://github.com/danielgregorio/quantum/actions/workflows/ci.yml)
[![Docker](https://github.com/danielgregorio/quantum/actions/workflows/docker.yml/badge.svg)](https://github.com/danielgregorio/quantum/actions/workflows/docker.yml)
[![PyPI](https://img.shields.io/pypi/v/quantum-framework)](https://pypi.org/project/quantum-framework/)
[![Docs](https://img.shields.io/badge/docs-quantum.sargas.cloud-blue)](https://quantum.sargas.cloud)

> **Codename:** FF / FireFusion
> **Status:** Initial Runner implementation

## 🚀 Project Structure

```
quantum/
├── src/                    # Quantum source code
│   └── quantum_runner.py   # Main runner
├── examples/               # .q code examples
│   ├── hello.q            # Hello World component
│   ├── webapp.q           # Web application
│   └── api.q              # API microservice
├── tests/                 # Unit tests
├── quantum.py             # CLI wrapper
└── README.md              # This file
```

## 📦 How to use

### 1. Run simple component:
```bash
python quantum.py run examples/hello.q
```

**Expected result:**
```
🔍 Analyzing file: hello.q
📄 Detected type: q:component
🔧 Executing component: HelloWorld
✅ Result: Hello World!
```

### 2. Run web application:
```bash
python quantum.py run examples/webapp.q
```

**Expected result:**
```
🔍 Analyzing file: webapp.q
📄 Detected type: q:application
🚀 Executing application: webapp
📱 Type: html
🌐 Starting web server...
🔗 Access: http://localhost:8080/webapp.q
```

### 3. Run API:
```bash
python quantum.py run examples/api.q
```

**Expected result:**
```
🔍 Analyzing file: api.q
📄 Detected type: q:application
🚀 Executing application: api
📱 Type: microservices
🛠️  Starting API server...
🔗 API running at: http://localhost:8080
```

## 🎯 Current Status

### ✅ Implemented:
- ✅ Basic XML parser
- ✅ Runner that automatically detects types
- ✅ CLI with arguments
- ✅ Functional examples
- ✅ Basic component execution

### 🚧 TODO:
- 🚧 Real web server (Flask/FastAPI)
- 🚧 Intermediate AST
- 🚧 Code generation for Python
- 🚧 Databinding {variable}
- 🚧 Control structures (<q:if>, <q:loop>)
- 🚧 Database integration
- 🚧 Hot reload

## 🔧 Debug Mode

To see detailed information:
```bash
python quantum.py run examples/hello.q --debug
```

## 📋 Next Steps

1. **AST Builder** - Create classes to represent each tag
2. **Template Engine** - Generate real Python code
3. **Web Server** - Implement server for HTML apps
4. **API Server** - Implement server for microservices
5. **Databinding** - Process {variable} expressions

---

**🎯 Philosophy:** Simplicity over configuration - Write once, deploy anywhere!
