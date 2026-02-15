#!/usr/bin/env python
"""
Baseline Performance Benchmark
==============================

Captures current Quantum interpreter performance as baseline
for comparing with transpiled code later.

Run: python benchmarks/baseline/run_baseline.py
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


@dataclass
class BenchmarkResult:
    name: str
    iterations: int
    total_time_ms: float
    avg_time_us: float
    ops_per_sec: float
    category: str


def benchmark_expression_cache(iterations: int = 10000) -> BenchmarkResult:
    """Benchmark expression evaluation with cache."""
    from runtime.expression_cache import ExpressionCache

    cache = ExpressionCache(enable_stats=False)
    context = {'total': 0, 'i': 0, 'x': 10, 'y': 20}

    # Warmup
    for _ in range(100):
        cache.evaluate('total + i', context)

    start = time.perf_counter()
    for i in range(iterations):
        context['i'] = i
        context['total'] = cache.evaluate('total + i', context)
    elapsed = (time.perf_counter() - start) * 1000

    return BenchmarkResult(
        name='expression_cache_loop',
        iterations=iterations,
        total_time_ms=elapsed,
        avg_time_us=(elapsed * 1000) / iterations,
        ops_per_sec=iterations / (elapsed / 1000),
        category='expression'
    )


def benchmark_expression_fast(iterations: int = 10000) -> BenchmarkResult:
    """Benchmark expression evaluation with evaluate_fast."""
    from runtime.expression_cache import ExpressionCache

    cache = ExpressionCache(enable_stats=False)
    context = {'total': 0, 'i': 0}

    # Warmup
    cache.evaluate_fast('total + i', context)

    start = time.perf_counter()
    for i in range(iterations):
        context['i'] = i
        context['total'] = cache.evaluate_fast('total + i', context)
    elapsed = (time.perf_counter() - start) * 1000

    return BenchmarkResult(
        name='expression_fast_loop',
        iterations=iterations,
        total_time_ms=elapsed,
        avg_time_us=(elapsed * 1000) / iterations,
        ops_per_sec=iterations / (elapsed / 1000),
        category='expression'
    )


def benchmark_databinding(iterations: int = 10000) -> BenchmarkResult:
    """Benchmark databinding resolution."""
    from runtime.expression_cache import get_databinding_cache

    cache = get_databinding_cache()
    context = {'user': 'John', 'count': 42, 'items': [1, 2, 3]}
    template = "Hello {user}, you have {count} items"

    # Warmup
    for _ in range(100):
        cache.apply(template, context)

    start = time.perf_counter()
    for _ in range(iterations):
        cache.apply(template, context)
    elapsed = (time.perf_counter() - start) * 1000

    return BenchmarkResult(
        name='databinding_simple',
        iterations=iterations,
        total_time_ms=elapsed,
        avg_time_us=(elapsed * 1000) / iterations,
        ops_per_sec=iterations / (elapsed / 1000),
        category='databinding'
    )


def benchmark_parser(iterations: int = 500) -> BenchmarkResult:
    """Benchmark XML parsing."""
    from core.parser import QuantumParser

    parser = QuantumParser()
    source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="TestComponent">
    <q:set name="x" value="10" />
    <q:set name="y" value="20" />
    <q:if condition="{x > 5}">
        <q:set name="result" value="{x + y}" />
    </q:if>
    <q:loop from="1" to="10" var="i">
        <q:set name="total" value="{total + i}" />
    </q:loop>
    <div class="container">
        <h1>{result}</h1>
        <p>Total: {total}</p>
    </div>
</q:component>
'''

    # Warmup
    for _ in range(10):
        parser.parse(source)

    start = time.perf_counter()
    for _ in range(iterations):
        ast = parser.parse(source)
    elapsed = (time.perf_counter() - start) * 1000

    return BenchmarkResult(
        name='parser_component',
        iterations=iterations,
        total_time_ms=elapsed,
        avg_time_us=(elapsed * 1000) / iterations,
        ops_per_sec=iterations / (elapsed / 1000),
        category='parser'
    )


def benchmark_component_execution(iterations: int = 200) -> BenchmarkResult:
    """Benchmark full component execution."""
    from core.parser import QuantumParser
    from runtime.component import ComponentRuntime

    parser = QuantumParser()
    source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="SimpleComponent">
    <q:set name="total" value="0" />
    <q:loop from="1" to="100" var="i">
        <q:set name="total" value="{total + i}" />
    </q:loop>
</q:component>
'''

    ast = parser.parse(source)

    # Warmup
    for _ in range(10):
        runtime = ComponentRuntime()
        runtime.execute_component(ast)

    start = time.perf_counter()
    for _ in range(iterations):
        runtime = ComponentRuntime()
        runtime.execute_component(ast)
    elapsed = (time.perf_counter() - start) * 1000

    return BenchmarkResult(
        name='component_loop_100',
        iterations=iterations,
        total_time_ms=elapsed,
        avg_time_us=(elapsed * 1000) / iterations,
        ops_per_sec=iterations / (elapsed / 1000),
        category='component'
    )


def benchmark_html_rendering(iterations: int = 500) -> BenchmarkResult:
    """Benchmark HTML rendering with databinding."""
    from core.parser import QuantumParser
    from runtime.component import ComponentRuntime

    parser = QuantumParser()
    source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="HTMLComponent">
    <q:set name="title" value="Hello World" />
    <q:set name="items" value="{[1, 2, 3, 4, 5]}" />
    <div class="container">
        <h1>{title}</h1>
        <ul>
            <q:loop collection="{items}" var="item">
                <li>Item {item}</li>
            </q:loop>
        </ul>
    </div>
</q:component>
'''

    ast = parser.parse(source)

    # Warmup
    for _ in range(10):
        runtime = ComponentRuntime()
        runtime.execute_component(ast)

    start = time.perf_counter()
    for _ in range(iterations):
        runtime = ComponentRuntime()
        runtime.execute_component(ast)
    elapsed = (time.perf_counter() - start) * 1000

    return BenchmarkResult(
        name='html_render_loop',
        iterations=iterations,
        total_time_ms=elapsed,
        avg_time_us=(elapsed * 1000) / iterations,
        ops_per_sec=iterations / (elapsed / 1000),
        category='render'
    )


def benchmark_python_baseline(iterations: int = 10000) -> BenchmarkResult:
    """Python native baseline for comparison."""
    start = time.perf_counter()
    total = 0
    for i in range(iterations):
        total += i
    elapsed = (time.perf_counter() - start) * 1000

    return BenchmarkResult(
        name='python_native_loop',
        iterations=iterations,
        total_time_ms=elapsed,
        avg_time_us=(elapsed * 1000) / iterations,
        ops_per_sec=iterations / (elapsed / 1000),
        category='baseline'
    )


def run_all_benchmarks() -> Dict[str, Any]:
    """Run all benchmarks and return results."""
    print("=" * 70)
    print("QUANTUM BASELINE PERFORMANCE BENCHMARK")
    print("=" * 70)
    print(f"Date: {datetime.now().isoformat()}")
    print()

    benchmarks = [
        ('Python Native (baseline)', benchmark_python_baseline),
        ('Expression Cache', benchmark_expression_cache),
        ('Expression Fast', benchmark_expression_fast),
        ('Databinding', benchmark_databinding),
        ('Parser', benchmark_parser),
        ('Component Execution', benchmark_component_execution),
        ('HTML Rendering', benchmark_html_rendering),
    ]

    results: List[BenchmarkResult] = []

    for name, func in benchmarks:
        print(f"Running: {name}...", end=" ", flush=True)
        try:
            result = func()
            results.append(result)
            print(f"{result.total_time_ms:.2f}ms ({result.ops_per_sec:,.0f} ops/s)")
        except Exception as e:
            print(f"ERROR: {e}")

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Benchmark':<30} {'Time (ms)':<12} {'Ops/sec':<15} {'vs Python':<10}")
    print("-" * 70)

    python_baseline = next((r for r in results if r.name == 'python_native_loop'), None)
    baseline_ops = python_baseline.ops_per_sec if python_baseline else 1

    for r in results:
        ratio = baseline_ops / r.ops_per_sec if r.ops_per_sec > 0 else 0
        ratio_str = f"{ratio:.1f}x" if ratio > 1 else "baseline"
        print(f"{r.name:<30} {r.total_time_ms:<12.2f} {r.ops_per_sec:<15,.0f} {ratio_str:<10}")

    # Build output
    output = {
        'timestamp': datetime.now().isoformat(),
        'python_version': sys.version,
        'results': [asdict(r) for r in results],
        'summary': {
            'python_baseline_ops': baseline_ops,
            'expression_cache_ratio': baseline_ops / next((r.ops_per_sec for r in results if r.name == 'expression_cache_loop'), 1),
            'expression_fast_ratio': baseline_ops / next((r.ops_per_sec for r in results if r.name == 'expression_fast_loop'), 1),
            'component_ratio': baseline_ops / next((r.ops_per_sec for r in results if r.name == 'component_loop_100'), 1),
        }
    }

    return output


def save_baseline(output: Dict[str, Any]):
    """Save baseline to file."""
    baseline_dir = Path(__file__).parent
    baseline_dir.mkdir(exist_ok=True)

    # Save timestamped version
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    timestamped_file = baseline_dir / f'baseline_{timestamp}.json'
    with open(timestamped_file, 'w') as f:
        json.dump(output, f, indent=2)

    # Save as latest
    latest_file = baseline_dir / 'baseline_latest.json'
    with open(latest_file, 'w') as f:
        json.dump(output, f, indent=2)

    print()
    print(f"Saved to: {timestamped_file}")
    print(f"Latest:   {latest_file}")


if __name__ == '__main__':
    output = run_all_benchmarks()
    save_baseline(output)
