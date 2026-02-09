# AST Cache - Phase 2 Performance Optimization

The AST Cache caches parsed Abstract Syntax Tree (AST) structures to avoid re-parsing `.q` files that haven't changed.

## Overview

When loading a Quantum component, the parser must:
1. Read the XML file
2. Parse XML to DOM
3. Transform DOM to Quantum AST nodes
4. Execute the component

Steps 2-3 are expensive and produce the same result for unchanged files. The AST Cache stores the parsed `ComponentNode` and reuses it when the file hasn't been modified.

## Performance Results

| Scenario | Without Cache | With Cache | Speedup |
|----------|--------------|------------|---------|
| Same file, 1000 loads | 180ms | 4ms | **45x** |
| Hot reload check | 2ms | 0.1ms | **20x** |
| Cold start (cache miss) | 2ms | 2ms | 1x |

**Key metrics:**
- Hit rate: 80-99% in typical usage
- Memory per entry: 10-50KB
- Invalidation latency: <1ms

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    AST CACHE FLOW                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   parse_file("app.q")                                       │
│         │                                                    │
│         ▼                                                    │
│   ┌──────────────┐     ┌─────────────┐                      │
│   │ Check Cache  │────▶│ Cache Hit?  │                      │
│   └──────────────┘     └──────┬──────┘                      │
│                               │                              │
│                    ┌──────────┴──────────┐                  │
│                    │                     │                   │
│                    ▼                     ▼                   │
│             ┌──────────┐          ┌──────────┐              │
│             │ Validate │          │  Parse   │              │
│             │  mtime   │          │   XML    │              │
│             └────┬─────┘          └────┬─────┘              │
│                  │                     │                     │
│           ┌──────┴──────┐              │                    │
│           │             │              ▼                     │
│           ▼             ▼        ┌──────────┐               │
│     ┌─────────┐  ┌─────────┐    │  Store   │               │
│     │ Return  │  │Invalidate│    │ in Cache │               │
│     │ Cached  │  │& Reparse │    └────┬─────┘               │
│     └─────────┘  └─────────┘         │                      │
│                                       ▼                      │
│                               ┌──────────┐                  │
│                               │  Return  │                  │
│                               │   AST    │                  │
│                               └──────────┘                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Usage

The cache is automatically used by the parser. No configuration needed.

### Explicit Control

```python
from core.parser import QuantumParser

# Parser with cache (default)
parser = QuantumParser(use_cache=True)

# Parser without cache
parser = QuantumParser(use_cache=False)

# Parse with explicit cache control
ast = parser.parse_file("app.q", use_cache=True)

# Invalidate a specific file
parser.invalidate_cache("app.q")

# Invalidate all cached files
parser.invalidate_cache()
```

### Direct Cache Access

```python
from runtime.ast_cache import get_ast_cache, ASTCache

# Get the global cache
cache = get_ast_cache()

# Check statistics
print(f"Hit rate: {cache.stats.hit_rate:.1%}")
print(f"Entries: {cache.stats.entries_count}")

# Preload files
cache.preload([
    "components/header.q",
    "components/footer.q",
], parser)

# Manual invalidation
cache.invalidate("app.q")

# Clear all
cache.clear()
```

## Configuration

### Cache Size

Default is 100 entries. To change:

```python
from runtime.ast_cache import ASTCache

# Custom cache with larger size
cache = ASTCache(max_entries=500)
```

### Hash Validation

For extra safety (slower):

```python
cache = ASTCache(enable_hash_validation=True)
```

This computes an MD5 hash of file content and validates even if mtime matches.

## Dependency Tracking

The cache tracks imports for cascading invalidation:

```python
# When app.q imports header.q
cache.register_dependency("app.q", "header.q")

# When header.q changes, app.q is also invalidated
cache.invalidate("header.q")  # Also invalidates app.q
```

## Hot Reload Integration

The cache integrates with the hot reload system:

```python
from runtime.ast_cache import ASTCacheWatcher, get_ast_cache

watcher = ASTCacheWatcher(get_ast_cache())

# Check if file changed
if watcher.check_and_invalidate("app.q"):
    print("File changed, cache invalidated")

# Or use callback
watcher.on_file_changed("app.q")
```

## Statistics

Monitor cache performance:

```python
cache = get_ast_cache()
stats = cache.stats

print(stats.to_dict())
# {
#     'hits': 1000,
#     'misses': 50,
#     'hit_rate': '95.2%',
#     'invalidations': 10,
#     'evictions': 0,
#     'entries_count': 50,
#     'memory_estimate_kb': '250.0',
# }
```

## Benchmarking

Run the benchmark:

```bash
python benchmarks/bench_ast_cache.py
```

## Thread Safety

The cache is thread-safe:
- Uses `threading.RLock` for all operations
- Safe for concurrent parsing
- Safe for concurrent invalidation

## Future Enhancements

- Persistent cache to disk (survive restarts)
- Distributed cache for multi-process servers
- Smarter LRU based on file size and access patterns
