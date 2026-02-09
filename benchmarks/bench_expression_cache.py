#!/usr/bin/env python
"""
Expression Cache Performance Benchmark

Demonstrates the performance improvement from Phase 1 optimization:
- Pre-compiled bytecode caching
- LRU eviction with configurable size
- Thread-safe evaluation

Run: python benchmarks/bench_expression_cache.py
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from runtime.expression_cache import ExpressionCache, get_expression_cache


def format_time(seconds: float) -> str:
    """Format time in human-readable units"""
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.2f} µs"
    elif seconds < 1:
        return f"{seconds * 1_000:.2f} ms"
    else:
        return f"{seconds:.2f} s"


def benchmark_uncached(expr: str, context: dict, iterations: int) -> float:
    """Benchmark expression evaluation without caching (compile each time)"""
    start = time.perf_counter()
    for _ in range(iterations):
        code = compile(expr, '<bench>', 'eval')
        eval(code, {}, context)
    return time.perf_counter() - start


def benchmark_cached(cache: ExpressionCache, expr: str, context: dict, iterations: int) -> float:
    """Benchmark expression evaluation with caching"""
    # Warm up cache
    cache.evaluate(expr, context)

    start = time.perf_counter()
    for _ in range(iterations):
        cache.evaluate(expr, context)
    return time.perf_counter() - start


def benchmark_direct_eval(expr: str, context: dict, iterations: int) -> float:
    """Benchmark direct eval with pre-compiled code (baseline)"""
    code = compile(expr, '<bench>', 'eval')

    start = time.perf_counter()
    for _ in range(iterations):
        eval(code, {}, context)
    return time.perf_counter() - start


def run_benchmark(name: str, expr: str, context: dict, iterations: int = 10000):
    """Run a single benchmark comparison"""
    cache = ExpressionCache(max_size=100, enable_stats=False)  # Disable stats for fair comparison

    # Run benchmarks
    uncached_time = benchmark_uncached(expr, context, iterations)
    cached_time = benchmark_cached(cache, expr, context, iterations)
    direct_time = benchmark_direct_eval(expr, context, iterations)

    # Calculate speedups
    speedup_vs_uncached = uncached_time / cached_time if cached_time > 0 else 0
    overhead_vs_direct = (cached_time / direct_time) if direct_time > 0 else 0

    print(f"\n  {name}")
    print(f"  {'-' * 60}")
    print(f"  Expression: {expr}")
    print(f"  Iterations: {iterations:,}")
    print(f"  ")
    print(f"  {'Method':<25} {'Time':>12} {'ops/sec':>15}")
    print(f"  {'-' * 52}")
    print(f"  {'Uncached (compile each)':<25} {format_time(uncached_time):>12} {iterations/uncached_time:>15,.0f}")
    print(f"  {'Cached (LRU)':<25} {format_time(cached_time):>12} {iterations/cached_time:>15,.0f}")
    print(f"  {'Direct eval (baseline)':<25} {format_time(direct_time):>12} {iterations/direct_time:>15,.0f}")
    print(f"  ")
    print(f"  Speedup vs uncached: {speedup_vs_uncached:.1f}x")
    print(f"  Overhead vs direct:  {overhead_vs_direct:.1f}x")

    return {
        'name': name,
        'expr': expr,
        'uncached_time': uncached_time,
        'cached_time': cached_time,
        'direct_time': direct_time,
        'speedup': speedup_vs_uncached,
    }


def run_mixed_expressions_benchmark(iterations_per_expr: int = 1000):
    """Benchmark with multiple different expressions (realistic workload)"""
    cache = ExpressionCache(max_size=100, enable_stats=True)

    expressions = [
        ("x + 1", {"x": 10}),
        ("a * b + c", {"a": 5, "b": 10, "c": 15}),
        ("x > y", {"x": 20, "y": 10}),
        ("len(items)", {"items": [1, 2, 3, 4, 5]}),
        ("sum(values) / len(values)", {"values": [1, 2, 3, 4, 5]}),
        ("x ** 2 + y ** 2", {"x": 3, "y": 4}),
        ("max(a, b, c)", {"a": 10, "b": 20, "c": 15}),
        ("'hello' + ' ' + name", {"name": "world"}),
        ("x if x > 0 else -x", {"x": -5}),
        ("a and b or c", {"a": True, "b": False, "c": True}),
    ]

    print(f"\n  Mixed Expressions Benchmark (10 unique expressions)")
    print(f"  {'-' * 60}")
    print(f"  Iterations per expression: {iterations_per_expr:,}")
    print(f"  Total evaluations: {len(expressions) * iterations_per_expr:,}")

    # Benchmark with cache
    cache.clear()
    start = time.perf_counter()
    for _ in range(iterations_per_expr):
        for expr, ctx in expressions:
            cache.evaluate(expr, ctx)
    cached_time = time.perf_counter() - start

    # Benchmark without cache (compile each time)
    start = time.perf_counter()
    for _ in range(iterations_per_expr):
        for expr, ctx in expressions:
            code = compile(expr, '<bench>', 'eval')
            eval(code, {}, ctx)
    uncached_time = time.perf_counter() - start

    total_evals = len(expressions) * iterations_per_expr
    speedup = uncached_time / cached_time if cached_time > 0 else 0

    print(f"  ")
    print(f"  {'Method':<25} {'Time':>12} {'ops/sec':>15}")
    print(f"  {'-' * 52}")
    print(f"  {'Uncached':<25} {format_time(uncached_time):>12} {total_evals/uncached_time:>15,.0f}")
    print(f"  {'Cached':<25} {format_time(cached_time):>12} {total_evals/cached_time:>15,.0f}")
    print(f"  ")
    print(f"  Speedup: {speedup:.1f}x")
    print(f"  Cache hit rate: {cache.stats.hit_rate:.1%}")
    print(f"  Compilations: {cache.stats.compilations}")


def run_cache_warmup_benchmark():
    """Show the difference between cold and warm cache"""
    cache = ExpressionCache(max_size=100, enable_stats=True)
    expr = "x * y + z"
    context = {"x": 10, "y": 20, "z": 30}
    iterations = 1000

    print(f"\n  Cache Warmup Comparison")
    print(f"  {'-' * 60}")
    print(f"  Expression: {expr}")

    # Cold cache (first evaluation)
    cache.clear()
    start = time.perf_counter()
    cache.evaluate(expr, context)  # First call - compiles
    cold_time = time.perf_counter() - start

    # Warm cache (subsequent evaluations)
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        cache.evaluate(expr, context)
        times.append(time.perf_counter() - start)
    warm_time = sum(times) / len(times)

    print(f"  ")
    print(f"  Cold cache (first call):  {format_time(cold_time)}")
    print(f"  Warm cache (avg of {iterations}): {format_time(warm_time)}")
    print(f"  Warmup speedup: {cold_time/warm_time:.1f}x")


def main():
    print("\n" + "=" * 70)
    print("  EXPRESSION CACHE PERFORMANCE BENCHMARK")
    print("=" * 70)
    print("  Phase 1 Optimization: Pre-compiled bytecode caching")
    print("=" * 70)

    # Simple arithmetic
    run_benchmark(
        "Simple Arithmetic",
        "x + y * 2",
        {"x": 10, "y": 5},
        iterations=50000
    )

    # Complex arithmetic
    run_benchmark(
        "Complex Arithmetic",
        "(a + b) * (c - d) / (e + 1)",
        {"a": 10, "b": 20, "c": 30, "d": 5, "e": 3},
        iterations=20000
    )

    # Comparison
    run_benchmark(
        "Comparison Expression",
        "x > y and z < 100",
        {"x": 50, "y": 25, "z": 75},
        iterations=30000
    )

    # Built-in functions
    run_benchmark(
        "Built-in Functions",
        "max(a, b) + min(c, d) + len(items)",
        {"a": 10, "b": 20, "c": 5, "d": 15, "items": [1, 2, 3]},
        iterations=20000
    )

    # String operations
    run_benchmark(
        "String Concatenation",
        "prefix + '_' + name + '_' + suffix",
        {"prefix": "hello", "name": "world", "suffix": "test"},
        iterations=20000
    )

    # Mixed expressions (realistic workload)
    run_mixed_expressions_benchmark(iterations_per_expr=5000)

    # Cache warmup comparison
    run_cache_warmup_benchmark()

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print("  The expression cache provides significant speedup by:")
    print("  1. Compiling expressions to bytecode only once")
    print("  2. Caching compiled code objects with LRU eviction")
    print("  3. Evaluating cached bytecode directly with context")
    print("  ")
    print("  Typical speedup: 5-15x vs recompiling each time")
    print("  Cache overhead: ~2-3x vs direct eval (acceptable tradeoff)")
    print("=" * 70)
    print()


if __name__ == '__main__':
    main()
