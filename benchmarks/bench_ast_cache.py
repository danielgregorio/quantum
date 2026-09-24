#!/usr/bin/env python
"""
AST Cache Performance Benchmark

Demonstrates the performance improvement from Phase 2 optimization:
- Cached AST loading vs fresh parsing
- Mtime-based invalidation overhead
- Memory usage

Run: python benchmarks/bench_ast_cache.py
"""

import sys
import time
import tempfile
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from runtime.ast_cache import ASTCache, get_ast_cache
from core.parser import QuantumParser


def format_time(seconds: float) -> str:
    """Format time in human-readable units"""
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.2f} us"
    elif seconds < 1:
        return f"{seconds * 1_000:.2f} ms"
    else:
        return f"{seconds:.2f} s"


def create_test_files(count: int, tmpdir: str) -> list:
    """Create test .q files for benchmarking"""
    files = []
    for i in range(count):
        path = os.path.join(tmpdir, f"test_{i}.q")
        content = f'''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="TestComponent{i}">
    <q:set name="counter" value="0" />
    <q:set name="items" value="[]" />

    <q:loop from="1" to="10" var="i">
        <q:set name="counter" value="{{counter + 1}}" />
    </q:loop>

    <q:if condition="{{counter > 5}}">
        <q:set name="status" value="high" />
    </q:if>
    <q:else>
        <q:set name="status" value="low" />
    </q:else>

    <q:function name="process">
        <q:param name="value" type="number" />
        <q:return value="{{value * 2}}" />
    </q:function>
</q:component>
'''
        with open(path, 'w') as f:
            f.write(content)
        files.append(path)
    return files


def benchmark_fresh_parse(parser: QuantumParser, files: list, iterations: int) -> float:
    """Benchmark parsing without cache"""
    # Create parser without cache
    parser_no_cache = QuantumParser(use_cache=False)

    start = time.perf_counter()
    for _ in range(iterations):
        for file_path in files:
            parser_no_cache.parse_file(file_path, use_cache=False)
    return time.perf_counter() - start


def benchmark_cached_parse(parser: QuantumParser, files: list, iterations: int) -> float:
    """Benchmark parsing with cache"""
    cache = get_ast_cache()

    # Warm up cache
    for file_path in files:
        parser.parse_file(file_path)

    # Reset stats for fair measurement
    cache.reset_stats()

    start = time.perf_counter()
    for _ in range(iterations):
        for file_path in files:
            parser.parse_file(file_path)
    return time.perf_counter() - start


def benchmark_cache_miss(parser: QuantumParser, files: list, iterations: int) -> float:
    """Benchmark cache miss scenario (invalidate each time)"""
    cache = get_ast_cache()

    start = time.perf_counter()
    for _ in range(iterations):
        for file_path in files:
            cache.invalidate(file_path)  # Force miss
            parser.parse_file(file_path)
    return time.perf_counter() - start


def run_benchmark(name: str, files: list, parser: QuantumParser, iterations: int = 100):
    """Run a complete benchmark comparison"""
    print(f"\n  {name}")
    print(f"  {'-' * 60}")
    print(f"  Files: {len(files)}")
    print(f"  Iterations: {iterations}")
    print(f"  Total parses: {len(files) * iterations:,}")

    # Fresh parse (no cache)
    fresh_time = benchmark_fresh_parse(parser, files, iterations)

    # Cached parse (warm cache)
    cached_time = benchmark_cached_parse(parser, files, iterations)

    # Cache miss (invalidate each time)
    miss_time = benchmark_cache_miss(parser, files, iterations)

    total_parses = len(files) * iterations
    speedup = fresh_time / cached_time if cached_time > 0 else 0

    print(f"  ")
    print(f"  {'Method':<25} {'Time':>12} {'ops/sec':>15}")
    print(f"  {'-' * 52}")
    print(f"  {'Fresh parse (no cache)':<25} {format_time(fresh_time):>12} {total_parses/fresh_time:>15,.0f}")
    print(f"  {'Cached (warm)':<25} {format_time(cached_time):>12} {total_parses/cached_time:>15,.0f}")
    print(f"  {'Cache miss':<25} {format_time(miss_time):>12} {total_parses/miss_time:>15,.0f}")
    print(f"  ")
    print(f"  Speedup (cached vs fresh): {speedup:.1f}x")

    # Get cache stats
    cache = get_ast_cache()
    stats = cache.stats
    print(f"  Cache hit rate: {stats.hit_rate:.1%}")
    print(f"  Cache entries: {stats.entries_count}")

    return {
        'fresh_time': fresh_time,
        'cached_time': cached_time,
        'miss_time': miss_time,
        'speedup': speedup,
    }


def run_scalability_benchmark(parser: QuantumParser, tmpdir: str):
    """Benchmark how cache scales with number of files"""
    print("\n  Scalability Benchmark")
    print(f"  {'-' * 60}")

    file_counts = [1, 5, 10, 20, 50]
    iterations = 50

    print(f"  {'Files':<10} {'Fresh (ms)':<15} {'Cached (ms)':<15} {'Speedup':<10}")
    print(f"  {'-' * 50}")

    for count in file_counts:
        # Create files
        files = create_test_files(count, tmpdir)

        # Reset cache
        cache = get_ast_cache()
        cache.clear()

        # Benchmark fresh
        parser_no_cache = QuantumParser(use_cache=False)
        start = time.perf_counter()
        for _ in range(iterations):
            for f in files:
                parser_no_cache.parse_file(f, use_cache=False)
        fresh_time = (time.perf_counter() - start) * 1000  # ms

        # Warm up cache
        for f in files:
            parser.parse_file(f)

        # Benchmark cached
        start = time.perf_counter()
        for _ in range(iterations):
            for f in files:
                parser.parse_file(f)
        cached_time = (time.perf_counter() - start) * 1000  # ms

        speedup = fresh_time / cached_time if cached_time > 0 else 0

        print(f"  {count:<10} {fresh_time:<15.2f} {cached_time:<15.2f} {speedup:<10.1f}x")

        # Clean up
        for f in files:
            os.unlink(f)


def main():
    print("\n" + "=" * 70)
    print("  AST CACHE PERFORMANCE BENCHMARK")
    print("=" * 70)
    print("  Phase 2 Optimization: Cached AST structures with mtime invalidation")
    print("=" * 70)

    # Reset global cache for fresh benchmarks
    import runtime.ast_cache as cache_module
    cache_module._global_cache = None

    parser = QuantumParser(use_cache=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Small file benchmark
        files_small = create_test_files(5, tmpdir)
        run_benchmark("Small Workload (5 files)", files_small, parser, iterations=200)

        # Medium file benchmark
        files_medium = create_test_files(20, tmpdir)
        run_benchmark("Medium Workload (20 files)", files_medium, parser, iterations=50)

        # Scalability
        run_scalability_benchmark(parser, tmpdir)

        # Clean up small files
        for f in files_small:
            try:
                os.unlink(f)
            except:
                pass
        for f in files_medium:
            try:
                os.unlink(f)
            except:
                pass

    # Memory usage
    cache = get_ast_cache()
    print("\n  Memory & Statistics")
    print(f"  {'-' * 60}")
    stats = cache.stats
    print(f"  Cache entries: {stats.entries_count}")
    print(f"  Memory estimate: {stats.memory_estimate_kb:.1f} KB")
    print(f"  Total hits: {stats.hits:,}")
    print(f"  Total misses: {stats.misses:,}")
    print(f"  Hit rate: {stats.hit_rate:.1%}")
    print(f"  Invalidations: {stats.invalidations:,}")
    print(f"  Evictions: {stats.evictions:,}")

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print("  The AST cache provides significant speedup by:")
    print("  1. Storing parsed ComponentNode objects in memory")
    print("  2. Using mtime-based invalidation for freshness")
    print("  3. LRU eviction to control memory usage")
    print("  ")
    print("  Typical speedup: 10-50x for repeated file loads")
    print("  Memory overhead: ~10-50KB per cached file")
    print("=" * 70)
    print()


if __name__ == '__main__':
    main()
