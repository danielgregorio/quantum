# Expression Cache - Phase 1 Performance Optimization

The Expression Cache is the first phase of Quantum Framework's performance optimization strategy. It pre-compiles Python expressions into bytecode and caches them for faster repeated evaluation.

## Overview

When evaluating expressions like `x + y * 2` or `count > 0 and active`, the Quantum runtime previously used Python's `eval()` with `compile()` on every evaluation. This is inefficient because:

1. **Parsing overhead**: The expression string must be parsed each time
2. **Compilation overhead**: Python must generate bytecode each time
3. **No reuse**: Previous compilations are discarded

The Expression Cache solves this by:
- Compiling expressions to bytecode once
- Caching compiled code objects using LRU eviction
- Reusing cached bytecode for subsequent evaluations

## Performance Results

| Expression Type | Speedup vs Recompile | Cache Overhead |
|-----------------|---------------------|----------------|
| Simple Arithmetic | 3.7x | 10x vs direct |
| Complex Arithmetic | 6.4x | 8x vs direct |
| Comparisons | 5.2x | 9x vs direct |
| Built-in Functions | 6.9x | 4x vs direct |
| String Operations | 4.5x | 6x vs direct |

**Key metrics:**
- Cache hit rate: 100% for repeated expressions
- Cold to warm cache: 13x speedup
- Memory overhead: ~1KB per cached expression

## Usage

The cache is used automatically by the runtime. No configuration is needed.

### Manual Usage (Advanced)

```python
from runtime.expression_cache import get_expression_cache, ExpressionCache

# Get the global singleton cache
cache = get_expression_cache()

# Evaluate an expression
result = cache.evaluate("x + y * 2", {"x": 10, "y": 5})  # Returns 20

# Evaluate a condition
is_valid = cache.evaluate_condition("x > 0 and y < 100", {"x": 5, "y": 50})

# Check statistics
print(f"Hit rate: {cache.stats.hit_rate:.1%}")
print(f"Compilations: {cache.stats.compilations}")

# Pre-warm the cache with common expressions
cache.precompile([
    "x + 1",
    "count > 0",
    "len(items) > 0",
])
```

### DataBinding Cache

For template expressions like `{x + 1}` or `Hello {name}!`:

```python
from runtime.expression_cache import get_databinding_cache

cache = get_databinding_cache()

# Pure expression - returns actual value
result = cache.apply("{x + y}", {"x": 10, "y": 20})  # Returns 30

# Mixed content - returns string
result = cache.apply("Hello {name}!", {"name": "World"})  # Returns "Hello World!"
```

## Security

The Expression Cache includes security features to prevent code injection:

### Blocked Patterns

The following patterns are blocked and will raise `ValueError`:

- `__import__`, `__builtins__`, `__class__` (dunder attributes)
- `exec`, `eval`, `compile` (code execution)
- `open`, `file`, `input` (file/input operations)
- `globals`, `locals`, `vars`, `dir` (introspection)
- `getattr`, `setattr`, `delattr`, `hasattr` (attribute manipulation)

### Safe Builtins

Only safe built-in functions are available in expressions:

- Math: `abs`, `divmod`, `pow`, `round`, `sum`, `max`, `min`
- Type conversion: `bool`, `int`, `float`, `str`, `list`, `dict`, `set`, `tuple`
- Iteration: `len`, `range`, `enumerate`, `zip`, `map`, `filter`, `sorted`, `reversed`
- Logic: `all`, `any`, `isinstance`, `issubclass`, `type`
- Values: `True`, `False`, `None`

## Configuration

### Cache Size

The default cache size is 1000 expressions. To customize:

```python
from runtime.expression_cache import ExpressionCache

# Create a custom cache with smaller size
cache = ExpressionCache(max_size=100)
```

### Statistics

Enable or disable statistics tracking:

```python
# Disable for maximum performance
cache = ExpressionCache(enable_stats=False)

# With stats enabled (default), access them:
print(cache.stats.to_dict())
# {
#     'hits': 1000,
#     'misses': 10,
#     'hit_rate': '99.0%',
#     'compilations': 10,
#     'evaluations': 1010,
#     'avg_compile_time_ms': '0.0150',
#     'avg_eval_time_ms': '0.0012',
# }
```

## Thread Safety

The Expression Cache is thread-safe:

- Uses `threading.RLock` for statistics updates
- Uses `functools.lru_cache` which is thread-safe in Python 3.2+
- Safe for concurrent evaluation from multiple threads

## Integration

The cache is automatically integrated with:

- `component.py:_evaluate_arithmetic_expression()` - Arithmetic expressions
- `component.py:_evaluate_condition()` - Condition evaluation
- Future: DataBinding and template processing

## Benchmarking

Run the benchmark to see performance on your system:

```bash
python benchmarks/bench_expression_cache.py
```

## Future Optimizations

Phase 2 and beyond will add:

- **AST Cache**: Cache parsed XML/AST structures
- **PyPy Compatibility**: JIT compilation support
- **Code Generation**: Compile Quantum to Python bytecode

See `docs/proposals/performance-optimization-study.md` for the full roadmap.
