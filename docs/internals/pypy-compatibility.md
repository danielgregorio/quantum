# PyPy Compatibility - Phase 3 Performance Optimization

Quantum Framework is fully compatible with PyPy, enabling automatic JIT compilation for 5-10x performance improvement on hot code paths.

## What is PyPy?

PyPy is an alternative Python implementation with a Just-In-Time (JIT) compiler:

```
CPython (standard):
┌──────────┐    ┌──────────────┐
│  Python  │ -> │ Interpreter  │ -> Slow execution
└──────────┘    └──────────────┘

PyPy:
┌──────────┐    ┌──────────┐    ┌────────────────┐
│  Python  │ -> │   JIT    │ -> │ Machine Code   │ -> Fast execution
└──────────┘    └──────────┘    └────────────────┘
                     ↑
              Detects hot paths
              and compiles to native
```

## Performance Comparison

| Operation | CPython | PyPy | Speedup |
|-----------|---------|------|---------|
| Loop 10,000 iterations | 17ms | 2ms | **8x** |
| Expression evaluation | 50ms | 8ms | **6x** |
| JSON parse/serialize | 1ms | 0.2ms | **5x** |
| Startup time | 50ms | 500ms | **-10x** |

**Key insights:**
- PyPy excels at long-running processes
- Startup is slower (JIT warmup)
- Best for servers, not CLI scripts

## Installation

### Windows

```powershell
# Download PyPy from https://www.pypy.org/download.html
# Extract to C:\pypy3

# Add to PATH
$env:PATH = "C:\pypy3;$env:PATH"

# Verify
pypy3 --version
```

### Linux/macOS

```bash
# Using pyenv (recommended)
pyenv install pypy3.10-7.3.15
pyenv local pypy3.10-7.3.15

# Or using package manager
# Ubuntu/Debian
sudo apt install pypy3

# macOS
brew install pypy3
```

### Create Virtual Environment

```bash
# Create venv with PyPy
pypy3 -m venv venv-pypy

# Activate
source venv-pypy/bin/activate  # Linux/macOS
venv-pypy\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Running Quantum with PyPy

```bash
# Start the server
pypy3 src/cli/runner.py start

# Run a component
pypy3 src/cli/runner.py run examples/counter.q

# Run benchmarks
pypy3 benchmarks/run_all.py
```

## Compatibility Check

Run the compatibility report:

```python
from runtime.pypy_compat import print_compatibility_report

print_compatibility_report()
```

Or via CLI:

```bash
python -c "from runtime.pypy_compat import print_compatibility_report; print_compatibility_report()"
```

Output:
```
======================================================================
  QUANTUM FRAMEWORK - PYTHON COMPATIBILITY REPORT
======================================================================

  Implementation: PyPy
  Version: 7.3.15
  Platform: linux
  64-bit: True

  Status: Running on PyPy (JIT enabled)

  Recommendations:
    - PyPy JIT is warming up - first requests may be slower
    - Avoid using eval() in hot paths - use pre-compiled expressions
    - Large dictionaries perform well on PyPy
    ...

  Dependency Compatibility:
    [OK] flask: Flask works well with PyPy
    [OK] jinja2: Jinja2 works well with PyPy
    [WARNING] watchdog: watchdog works but may need extra setup
    ...
======================================================================
```

## Dependency Compatibility

| Package | Status | Notes |
|---------|--------|-------|
| flask | ✅ OK | Fully compatible |
| jinja2 | ✅ OK | Fully compatible |
| requests | ✅ OK | Fully compatible |
| pyyaml | ✅ OK | Uses pure Python mode |
| sqlite3 | ✅ OK | Standard library |
| lxml | ⚠️ Caveat | Use `pip install lxml-cffi` |
| watchdog | ⚠️ Caveat | May need extra setup |
| uvloop | ❌ No | Use standard asyncio |

## JIT Warmup

PyPy's JIT needs time to analyze and compile hot code. Optimize warmup:

```python
from runtime.pypy_compat import PyPyOptimizer

# During application startup
PyPyOptimizer.warmup_jit(iterations=1000)

# This exercises common code paths so the JIT
# compiles them before serving requests
```

## Best Practices

### Do's

1. **Use for long-running servers**
   ```bash
   # PyPy shines in server mode
   pypy3 src/cli/runner.py start --port 8000
   ```

2. **Pre-compile expressions**
   ```python
   # Good: Use expression cache (already implemented)
   from runtime.expression_cache import get_expression_cache
   cache = get_expression_cache()
   result = cache.evaluate("x + y * 2", context)
   ```

3. **Use list comprehensions**
   ```python
   # Good: JIT optimizes this well
   result = [x * 2 for x in items]

   # Less optimal
   result = list(map(lambda x: x * 2, items))
   ```

4. **Leverage dictionary performance**
   ```python
   # PyPy has excellent dict performance
   cache = {}
   for item in items:
       cache[item.id] = item
   ```

### Don'ts

1. **Avoid metaclasses in hot paths**
   ```python
   # Avoid in performance-critical code
   class Meta(type):
       pass
   ```

2. **Don't use uvloop**
   ```python
   # Use standard asyncio instead
   import asyncio
   # NOT: import uvloop
   ```

3. **Avoid frequent subprocess calls**
   ```python
   # PyPy has subprocess overhead
   # Prefer Python-native solutions
   ```

## Programmatic Usage

```python
from runtime.pypy_compat import (
    is_pypy,
    get_implementation_info,
    DependencyChecker,
    QuantumPyPyAdapter,
)

# Check runtime
if is_pypy():
    print("Running on PyPy!")

# Get detailed info
info = get_implementation_info()
print(f"Python: {info['implementation']} {info['version']}")

# Check a dependency
result = DependencyChecker.check_dependency('flask')
print(f"{result.name}: {result.message}")

# Get memory usage (works on both)
memory = QuantumPyPyAdapter.get_memory_usage()
print(f"Memory: {memory:.1f} MB")
```

## Testing on PyPy

Run the test suite on PyPy:

```bash
# Activate PyPy environment
source venv-pypy/bin/activate

# Run tests
pypy3 -m pytest tests/ -v

# Run specific performance tests
pypy3 -m pytest tests/test_pypy_compat.py -v
```

## Troubleshooting

### lxml not installing

```bash
# Use cffi version
pip install lxml-cffi

# Or use xml.etree (standard library) as fallback
```

### Slow startup

```bash
# Normal - JIT needs warmup
# First request: 500ms
# Subsequent: 2ms

# Consider preloading common components
```

### Memory usage higher than CPython

```python
# PyPy uses more memory but is faster
# Trade-off is usually worth it for servers

# Monitor with:
from runtime.pypy_compat import QuantumPyPyAdapter
print(f"Memory: {QuantumPyPyAdapter.get_memory_usage():.1f} MB")
```

## Benchmarks

Run PyPy-specific benchmarks:

```bash
# Expression cache benchmark
pypy3 benchmarks/bench_expression_cache.py

# AST cache benchmark
pypy3 benchmarks/bench_ast_cache.py

# Full comparison
pypy3 benchmarks/run_all.py --compare
```

## When to Use PyPy

| Scenario | Recommendation |
|----------|----------------|
| Production server | ✅ Use PyPy |
| Development/debugging | ❌ Use CPython |
| Short CLI scripts | ❌ Use CPython |
| Long-running tasks | ✅ Use PyPy |
| Memory-constrained | ❌ Use CPython |
| CPU-bound processing | ✅ Use PyPy |
