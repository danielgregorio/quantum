# Quantum Framework Benchmarks

Sistema de benchmarks para medir a performance das funcionalidades do Quantum Framework
e comparar com outras linguagens e plataformas.

## Categorias de Benchmark

### 1. Core Language
- `q:set` - Variable assignment
- `q:loop` - Iteration performance
- `q:if` - Conditional branching
- `q:function` - Function calls
- Expression evaluation

### 2. Data Processing
- `q:query` - Database queries (SQLite, PostgreSQL)
- `q:data` - Data transformations
- JSON parsing/serialization
- List/Dict operations

### 3. HTTP & Web
- `q:invoke` - HTTP client requests
- Request handling throughput
- Response rendering
- Template processing

### 4. AI/ML Integration
- `q:llm` - LLM inference latency
- Token throughput
- Streaming responses

### 5. Messaging & Jobs
- `q:message` - Message publishing
- `q:subscribe` - Message consumption
- `q:job` - Job dispatch/execution
- `q:schedule` - Scheduled tasks

### 6. Python Scripting
- `q:python` - Python code execution
- Bridge overhead (q.variable access)
- Import performance

## Comparisons

Results are compared against:
- **Python/Flask** - Pure Python web framework
- **FastAPI** - Modern async Python framework
- **Node.js/Express** - JavaScript runtime
- **PHP 8.3** - PHP with JIT enabled
- **Ruby 3.3** - Ruby with YJIT enabled
- **Go/Gin** - Go web framework

### Cross-Platform Benchmarks

Scripts are provided to run equivalent benchmarks in other languages:

```bash
# PHP benchmarks (requires PHP 8.0+)
php benchmarks/php/benchmark.php

# Ruby benchmarks (requires Ruby 3.0+ with sqlite3 gem)
ruby benchmarks/ruby/benchmark.rb

# Compare all platforms (uses reference data if PHP/Ruby not installed)
python benchmarks/compare_platforms.py --html
```

## Running Benchmarks

```bash
# Run all benchmarks
python benchmarks/run_all.py

# Run specific category
python benchmarks/run_all.py --category core

# Run with comparisons
python benchmarks/run_all.py --compare

# Generate report
python benchmarks/run_all.py --report html
```

## Results Format

Results are saved in `benchmarks/results/` as JSON and can be exported to:
- HTML report with charts
- Markdown table
- CSV for analysis
