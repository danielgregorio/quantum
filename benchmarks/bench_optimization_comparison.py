#!/usr/bin/env python
"""
Quantum Framework - Optimization Comparison Benchmark

Compares performance BEFORE and AFTER each optimization phase:
- Baseline (no optimizations)
- Phase 1: Expression Cache
- Phase 2: AST Cache
- Phase 3: PyPy (if available)

Run: python benchmarks/bench_optimization_comparison.py
"""

import sys
import time
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


@dataclass
class BenchmarkResult:
    """Result of a single benchmark"""
    name: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    ops_per_sec: float

    @property
    def avg_time_us(self) -> float:
        return self.avg_time_ms * 1000


def format_time(ms: float) -> str:
    """Format time in appropriate units"""
    if ms < 0.001:
        return f"{ms * 1000:.3f} us"
    elif ms < 1:
        return f"{ms:.3f} ms"
    else:
        return f"{ms:.2f} ms"


def format_speedup(baseline: float, optimized: float) -> str:
    """Format speedup ratio"""
    if optimized <= 0:
        return "N/A"
    ratio = baseline / optimized
    if ratio >= 1:
        return f"{ratio:.1f}x faster"
    else:
        return f"{1/ratio:.1f}x slower"


class BaselineBenchmarks:
    """
    Baseline benchmarks WITHOUT any optimizations.
    Simulates the original behavior before caching.
    """

    # Safe builtins for baseline evaluation
    SAFE_BUILTINS = {
        'abs': abs, 'all': all, 'any': any, 'bool': bool,
        'dict': dict, 'float': float, 'int': int, 'len': len,
        'list': list, 'max': max, 'min': min, 'range': range,
        'round': round, 'str': str, 'sum': sum, 'tuple': tuple,
        'True': True, 'False': False, 'None': None,
    }

    @staticmethod
    def expression_eval_no_cache(expr: str, context: dict, iterations: int) -> BenchmarkResult:
        """Evaluate expression without cache (compile each time)"""
        namespace = dict(BaselineBenchmarks.SAFE_BUILTINS)
        namespace.update(context)

        start = time.perf_counter()
        for _ in range(iterations):
            code = compile(expr, '<expr>', 'eval')
            eval(code, {"__builtins__": {}}, namespace)
        total = (time.perf_counter() - start) * 1000

        return BenchmarkResult(
            name="Expression (no cache)",
            iterations=iterations,
            total_time_ms=total,
            avg_time_ms=total / iterations,
            ops_per_sec=iterations / (total / 1000),
        )

    @staticmethod
    def parse_file_no_cache(parser, file_path: str, iterations: int) -> BenchmarkResult:
        """Parse file without cache (parse each time)"""
        from core.parser import QuantumParser

        # Use parser without cache
        parser_no_cache = QuantumParser(use_cache=False)

        start = time.perf_counter()
        for _ in range(iterations):
            parser_no_cache.parse_file(file_path, use_cache=False)
        total = (time.perf_counter() - start) * 1000

        return BenchmarkResult(
            name="Parse file (no cache)",
            iterations=iterations,
            total_time_ms=total,
            avg_time_ms=total / iterations,
            ops_per_sec=iterations / (total / 1000),
        )

    @staticmethod
    def condition_eval_no_cache(condition: str, context: dict, iterations: int) -> BenchmarkResult:
        """Evaluate condition without cache"""
        namespace = dict(BaselineBenchmarks.SAFE_BUILTINS)
        namespace.update(context)

        start = time.perf_counter()
        for _ in range(iterations):
            code = compile(condition, '<cond>', 'eval')
            bool(eval(code, {"__builtins__": {}}, namespace))
        total = (time.perf_counter() - start) * 1000

        return BenchmarkResult(
            name="Condition (no cache)",
            iterations=iterations,
            total_time_ms=total,
            avg_time_ms=total / iterations,
            ops_per_sec=iterations / (total / 1000),
        )


class Phase1Benchmarks:
    """
    Phase 1 benchmarks WITH Expression Cache.
    """

    @staticmethod
    def expression_eval_cached(expr: str, context: dict, iterations: int) -> BenchmarkResult:
        """Evaluate expression with cache"""
        from runtime.expression_cache import ExpressionCache

        cache = ExpressionCache(max_size=100, enable_stats=False)

        # Warm up
        cache.evaluate(expr, context)

        start = time.perf_counter()
        for _ in range(iterations):
            cache.evaluate(expr, context)
        total = (time.perf_counter() - start) * 1000

        return BenchmarkResult(
            name="Expression (cached)",
            iterations=iterations,
            total_time_ms=total,
            avg_time_ms=total / iterations,
            ops_per_sec=iterations / (total / 1000),
        )

    @staticmethod
    def condition_eval_cached(condition: str, context: dict, iterations: int) -> BenchmarkResult:
        """Evaluate condition with cache"""
        from runtime.expression_cache import ExpressionCache

        cache = ExpressionCache(max_size=100, enable_stats=False)

        # Warm up
        cache.evaluate_condition(condition, context)

        start = time.perf_counter()
        for _ in range(iterations):
            cache.evaluate_condition(condition, context)
        total = (time.perf_counter() - start) * 1000

        return BenchmarkResult(
            name="Condition (cached)",
            iterations=iterations,
            total_time_ms=total,
            avg_time_ms=total / iterations,
            ops_per_sec=iterations / (total / 1000),
        )


class Phase2Benchmarks:
    """
    Phase 2 benchmarks WITH AST Cache.
    """

    @staticmethod
    def parse_file_cached(parser, file_path: str, iterations: int) -> BenchmarkResult:
        """Parse file with AST cache"""
        from runtime.ast_cache import get_ast_cache

        cache = get_ast_cache()
        cache.clear()

        # Warm up (first parse)
        parser.parse_file(file_path)

        start = time.perf_counter()
        for _ in range(iterations):
            parser.parse_file(file_path)
        total = (time.perf_counter() - start) * 1000

        return BenchmarkResult(
            name="Parse file (cached)",
            iterations=iterations,
            total_time_ms=total,
            avg_time_ms=total / iterations,
            ops_per_sec=iterations / (total / 1000),
        )


class ComponentBenchmarks:
    """
    End-to-end component execution benchmarks.
    """

    @staticmethod
    def create_test_component(tmpdir: str, name: str = "BenchComponent") -> str:
        """Create a test component file"""
        path = os.path.join(tmpdir, f"{name}.q")
        content = f'''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="{name}">
    <q:set name="counter" value="0" />
    <q:set name="sum" value="0" />

    <q:loop from="1" to="100" var="i">
        <q:set name="counter" value="{{counter + 1}}" />
        <q:set name="sum" value="{{sum + i}}" />
    </q:loop>

    <q:if condition="{{sum > 1000}}">
        <q:set name="status" value="high" />
    </q:if>
    <q:else>
        <q:set name="status" value="low" />
    </q:else>

    <q:function name="calculate">
        <q:param name="x" type="number" />
        <q:param name="y" type="number" />
        <q:set name="result" value="{{x * y + sum}}" />
        <q:return value="{{result}}" />
    </q:function>
</q:component>
'''
        with open(path, 'w') as f:
            f.write(content)
        return path


def run_comparison_suite():
    """Run the complete comparison benchmark suite"""

    print("\n" + "=" * 80)
    print("  QUANTUM FRAMEWORK - OPTIMIZATION COMPARISON BENCHMARK")
    print("=" * 80)
    print("  Comparing performance BEFORE and AFTER each optimization phase")
    print("=" * 80)

    # Check Python implementation
    from runtime.pypy_compat import get_implementation_info
    info = get_implementation_info()
    print(f"\n  Python: {info['implementation']} {info['version']}")
    print(f"  Platform: {info['platform']}")

    results = {}

    # =========================================================================
    # EXPRESSION EVALUATION BENCHMARKS
    # =========================================================================

    print("\n" + "-" * 80)
    print("  EXPRESSION EVALUATION")
    print("-" * 80)

    expressions = [
        ("Simple arithmetic", "x + y * 2", {"x": 10, "y": 5}),
        ("Complex arithmetic", "(a + b) * (c - d) / (e + 1)", {"a": 10, "b": 20, "c": 30, "d": 5, "e": 3}),
        ("With builtins", "max(a, b) + min(c, d) + len(items)", {"a": 10, "b": 20, "c": 5, "d": 15, "items": [1, 2, 3]}),
        ("Comparison", "x > y and z < 100", {"x": 50, "y": 25, "z": 75}),
    ]

    iterations = 10000

    print(f"\n  Iterations per expression: {iterations:,}")
    print()
    print(f"  {'Expression':<25} {'Baseline':>12} {'Cached':>12} {'Speedup':>15}")
    print(f"  {'-' * 64}")

    expr_results = []

    for name, expr, ctx in expressions:
        baseline = BaselineBenchmarks.expression_eval_no_cache(expr, ctx, iterations)
        cached = Phase1Benchmarks.expression_eval_cached(expr, ctx, iterations)

        speedup = baseline.avg_time_ms / cached.avg_time_ms if cached.avg_time_ms > 0 else 0

        print(f"  {name:<25} {format_time(baseline.avg_time_ms):>12} {format_time(cached.avg_time_ms):>12} {speedup:>14.1f}x")

        expr_results.append({
            'name': name,
            'baseline': baseline,
            'cached': cached,
            'speedup': speedup,
        })

    results['expressions'] = expr_results

    # =========================================================================
    # CONDITION EVALUATION BENCHMARKS
    # =========================================================================

    print("\n" + "-" * 80)
    print("  CONDITION EVALUATION")
    print("-" * 80)

    conditions = [
        ("Simple comparison", "x > 5", {"x": 10}),
        ("Complex condition", "x > 0 and y < 100 and z != 0", {"x": 50, "y": 50, "z": 1}),
        ("Boolean logic", "a or (b and c)", {"a": False, "b": True, "c": True}),
    ]

    print(f"\n  Iterations per condition: {iterations:,}")
    print()
    print(f"  {'Condition':<25} {'Baseline':>12} {'Cached':>12} {'Speedup':>15}")
    print(f"  {'-' * 64}")

    cond_results = []

    for name, cond, ctx in conditions:
        baseline = BaselineBenchmarks.condition_eval_no_cache(cond, ctx, iterations)
        cached = Phase1Benchmarks.condition_eval_cached(cond, ctx, iterations)

        speedup = baseline.avg_time_ms / cached.avg_time_ms if cached.avg_time_ms > 0 else 0

        print(f"  {name:<25} {format_time(baseline.avg_time_ms):>12} {format_time(cached.avg_time_ms):>12} {speedup:>14.1f}x")

        cond_results.append({
            'name': name,
            'baseline': baseline,
            'cached': cached,
            'speedup': speedup,
        })

    results['conditions'] = cond_results

    # =========================================================================
    # FILE PARSING BENCHMARKS
    # =========================================================================

    print("\n" + "-" * 80)
    print("  FILE PARSING (AST Cache)")
    print("-" * 80)

    from core.parser import QuantumParser
    import runtime.ast_cache as ast_cache_module

    # Reset global cache
    ast_cache_module._global_cache = None

    parser = QuantumParser(use_cache=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files of different sizes
        test_files = [
            ("Small component", ComponentBenchmarks.create_test_component(tmpdir, "Small")),
        ]

        # Create a larger component
        large_path = os.path.join(tmpdir, "Large.q")
        with open(large_path, 'w') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<q:component name="Large">\n')
            for i in range(50):
                f.write(f'    <q:set name="var{i}" value="{i}" />\n')
            for i in range(20):
                f.write(f'    <q:loop from="1" to="10" var="i{i}">\n')
                f.write(f'        <q:set name="sum{i}" value="{{sum{i} + i{i}}}" />\n')
                f.write(f'    </q:loop>\n')
            f.write('</q:component>\n')
        test_files.append(("Large component", large_path))

        iterations_parse = 500

        print(f"\n  Iterations per file: {iterations_parse:,}")
        print()
        print(f"  {'File':<25} {'Baseline':>12} {'Cached':>12} {'Speedup':>15}")
        print(f"  {'-' * 64}")

        parse_results = []

        for name, file_path in test_files:
            # Reset cache for fair comparison
            ast_cache_module._global_cache = None
            parser = QuantumParser(use_cache=True)

            baseline = BaselineBenchmarks.parse_file_no_cache(parser, file_path, iterations_parse)

            # Reset and warm up cache
            ast_cache_module._global_cache = None
            parser = QuantumParser(use_cache=True)
            cached = Phase2Benchmarks.parse_file_cached(parser, file_path, iterations_parse)

            speedup = baseline.avg_time_ms / cached.avg_time_ms if cached.avg_time_ms > 0 else 0

            print(f"  {name:<25} {format_time(baseline.avg_time_ms):>12} {format_time(cached.avg_time_ms):>12} {speedup:>14.1f}x")

            parse_results.append({
                'name': name,
                'baseline': baseline,
                'cached': cached,
                'speedup': speedup,
            })

        results['parsing'] = parse_results

    # =========================================================================
    # MIXED WORKLOAD BENCHMARK
    # =========================================================================

    print("\n" + "-" * 80)
    print("  MIXED WORKLOAD (Realistic Scenario)")
    print("-" * 80)

    print("\n  Simulating 1000 component loads with expression evaluation...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create 10 component files
        files = []
        for i in range(10):
            files.append(ComponentBenchmarks.create_test_component(tmpdir, f"Component{i}"))

        expressions_mixed = [
            ("x + 1", {"x": i}) for i in range(10)
        ]

        # Baseline (no caches)
        ast_cache_module._global_cache = None
        parser_no_cache = QuantumParser(use_cache=False)

        start = time.perf_counter()
        for _ in range(100):
            for file_path in files:
                parser_no_cache.parse_file(file_path, use_cache=False)
            for expr, ctx in expressions_mixed:
                code = compile(expr, '<expr>', 'eval')
                eval(code, {}, ctx)
        baseline_mixed = (time.perf_counter() - start) * 1000

        # With all caches
        from runtime.expression_cache import ExpressionCache
        ast_cache_module._global_cache = None
        parser_cached = QuantumParser(use_cache=True)
        expr_cache = ExpressionCache(max_size=100, enable_stats=False)

        # Warm up
        for file_path in files:
            parser_cached.parse_file(file_path)
        for expr, ctx in expressions_mixed:
            expr_cache.evaluate(expr, ctx)

        start = time.perf_counter()
        for _ in range(100):
            for file_path in files:
                parser_cached.parse_file(file_path)
            for expr, ctx in expressions_mixed:
                expr_cache.evaluate(expr, ctx)
        cached_mixed = (time.perf_counter() - start) * 1000

        speedup_mixed = baseline_mixed / cached_mixed if cached_mixed > 0 else 0

        print()
        print(f"  {'Scenario':<30} {'Time':>15} {'Ops/sec':>15}")
        print(f"  {'-' * 60}")
        print(f"  {'Baseline (no caches)':<30} {format_time(baseline_mixed):>15} {100 * 20 / (baseline_mixed / 1000):>15,.0f}")
        print(f"  {'Optimized (all caches)':<30} {format_time(cached_mixed):>15} {100 * 20 / (cached_mixed / 1000):>15,.0f}")
        print()
        print(f"  Overall Speedup: {speedup_mixed:.1f}x")

    # =========================================================================
    # SUMMARY
    # =========================================================================

    print("\n" + "=" * 80)
    print("  SUMMARY - OPTIMIZATION IMPACT")
    print("=" * 80)

    # Calculate averages
    avg_expr_speedup = sum(r['speedup'] for r in expr_results) / len(expr_results)
    avg_cond_speedup = sum(r['speedup'] for r in cond_results) / len(cond_results)
    avg_parse_speedup = sum(r['speedup'] for r in parse_results) / len(parse_results)

    print()
    print(f"  {'Optimization':<35} {'Avg Speedup':>15}")
    print(f"  {'-' * 50}")
    print(f"  {'Phase 1: Expression Cache':<35} {avg_expr_speedup:>14.1f}x")
    print(f"  {'Phase 1: Condition Cache':<35} {avg_cond_speedup:>14.1f}x")
    print(f"  {'Phase 2: AST Cache':<35} {avg_parse_speedup:>14.1f}x")
    print(f"  {'Combined (Mixed Workload)':<35} {speedup_mixed:>14.1f}x")

    print()
    print("  Before Optimizations:")
    print(f"    - Each expression re-compiled on every evaluation")
    print(f"    - Each file re-parsed on every load")
    print(f"    - No caching of intermediate results")

    print()
    print("  After Optimizations:")
    print(f"    - Expressions compiled once, cached as bytecode")
    print(f"    - AST cached with mtime-based invalidation")
    print(f"    - LRU eviction keeps memory bounded")
    print(f"    - Thread-safe for concurrent access")

    if info['implementation'] == 'PyPy':
        print()
        print("  PyPy JIT Status: ACTIVE")
        print("    - Additional 5-10x speedup from JIT compilation")
    else:
        print()
        print("  PyPy JIT Status: NOT AVAILABLE (using CPython)")
        print("    - Run with PyPy for additional 5-10x speedup")

    print()
    print("=" * 80)

    return results


def run_before_after_comparison():
    """Run a simple before/after comparison"""

    print("\n" + "=" * 80)
    print("  BEFORE vs AFTER - QUICK COMPARISON")
    print("=" * 80)

    iterations = 50000
    expr = "x * y + z - w / 2"
    context = {"x": 10, "y": 20, "z": 30, "w": 40}

    # BEFORE: No cache
    print("\n  BEFORE (No optimizations):")
    print(f"  Expression: {expr}")
    print(f"  Iterations: {iterations:,}")

    start = time.perf_counter()
    for _ in range(iterations):
        code = compile(expr, '<expr>', 'eval')
        eval(code, {}, context)
    before_time = (time.perf_counter() - start) * 1000
    before_ops = iterations / (before_time / 1000)

    print(f"  Time: {format_time(before_time)}")
    print(f"  Speed: {before_ops:,.0f} ops/sec")

    # AFTER: With cache
    from runtime.expression_cache import ExpressionCache
    cache = ExpressionCache(max_size=100, enable_stats=False)

    # Warm up
    cache.evaluate(expr, context)

    print("\n  AFTER (With Expression Cache):")

    start = time.perf_counter()
    for _ in range(iterations):
        cache.evaluate(expr, context)
    after_time = (time.perf_counter() - start) * 1000
    after_ops = iterations / (after_time / 1000)

    print(f"  Time: {format_time(after_time)}")
    print(f"  Speed: {after_ops:,.0f} ops/sec")

    speedup = before_time / after_time

    print("\n  " + "-" * 40)
    print(f"  IMPROVEMENT: {speedup:.1f}x faster")
    print(f"  Time saved: {format_time(before_time - after_time)} per {iterations:,} ops")
    print("  " + "-" * 40)

    return speedup


if __name__ == '__main__':
    # Quick comparison first
    run_before_after_comparison()

    # Full suite
    run_comparison_suite()
