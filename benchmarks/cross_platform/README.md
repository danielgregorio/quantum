# Quantum Framework - Cross-Platform Benchmark Suite

Comparative benchmarks between Quantum and other web technologies.

## Technologies Tested

| Technology | Version | Type |
|------------|--------|------|
| **Quantum** | 1.0 | Declarative framework (Python) |
| Pure Python | 3.12 | Language |
| Flask | 3.0 | Python microframework |
| Django | 5.0 | Python framework |
| PHP | 8.3 | Language |
| Laravel | 11.x | PHP framework |
| Ruby | 3.3 | Language |
| Rails | 7.x | Ruby framework |
| Perl CGI | 5.38 | Language |
| Node.js | 20.x | JavaScript runtime |
| Express | 4.x | Node.js framework |
| Java | 21 | Language |
| Spring Boot | 3.x | Java framework |

## Benchmark Categories

### 1. Micro-benchmarks (isolated operations)
- Expression evaluation
- Variable manipulation
- Loops (1000, 10000, 100000 iterations)
- Conditionals
- String interpolation
- JSON parse/serialize

### 2. HTTP Benchmarks (web requests)
- Hello World (minimal response)
- JSON response
- Template rendering
- Database query (SQLite)

### 3. Real-world Scenarios
- Simple CRUD
- Paginated list
- Form with validation

## How to Run

```bash
# All benchmarks
python benchmarks/cross_platform/run_all.py

# Micro-benchmarks only
python benchmarks/cross_platform/bench_micro.py

# HTTP only (requires the other technologies to be installed)
python benchmarks/cross_platform/bench_http.py
```

## Results

Results are saved to `benchmarks/results/cross_platform_YYYYMMDD_HHMMSS.json`
