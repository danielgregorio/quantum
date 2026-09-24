#!/usr/bin/env python
"""
Transpiled vs Interpreted Performance Benchmark
================================================

Compares performance of:
1. Interpreted Quantum (current runtime)
2. Transpiled Python (generated code)
3. Native Python (baseline)
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


@dataclass
class BenchmarkResult:
    name: str
    interpreted_ms: float
    transpiled_ms: float
    native_ms: float
    speedup_vs_interpreted: float
    speedup_vs_native: float


def benchmark_loop(iterations: int = 100) -> BenchmarkResult:
    """Benchmark loop performance."""

    # Source code
    source = f'''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="LoopBench">
    <q:set name="total" value="0" />
    <q:loop from="1" to="1000" var="i">
        <q:set name="total" value="{{total + i}}" />
    </q:loop>
</q:component>
'''

    # 1. Interpreted
    from core.parser import QuantumParser
    from runtime.component import ComponentRuntime

    parser = QuantumParser()
    ast = parser.parse(source)

    # Warmup
    for _ in range(5):
        runtime = ComponentRuntime()
        runtime.execute_component(ast)

    start = time.perf_counter()
    for _ in range(iterations):
        runtime = ComponentRuntime()
        runtime.execute_component(ast)
    interpreted_ms = (time.perf_counter() - start) * 1000

    # 2. Transpiled
    from compiler import Transpiler

    transpiler = Transpiler(target='python')
    result = transpiler.compile_string(source)

    if not result.success:
        print(f"Transpilation failed: {result.errors}")
        return None

    # Execute transpiled code
    exec_globals = {}
    exec(result.code, exec_globals)
    LoopBench = exec_globals['LoopBench']

    # Warmup
    for _ in range(5):
        LoopBench().render()

    start = time.perf_counter()
    for _ in range(iterations):
        LoopBench().render()
    transpiled_ms = (time.perf_counter() - start) * 1000

    # 3. Native Python
    def native_loop():
        total = 0
        for i in range(1, 1001):
            total = total + i
        return total

    # Warmup
    for _ in range(5):
        native_loop()

    start = time.perf_counter()
    for _ in range(iterations):
        native_loop()
    native_ms = (time.perf_counter() - start) * 1000

    return BenchmarkResult(
        name='loop_1000',
        interpreted_ms=interpreted_ms,
        transpiled_ms=transpiled_ms,
        native_ms=native_ms,
        speedup_vs_interpreted=interpreted_ms / transpiled_ms if transpiled_ms > 0 else 0,
        speedup_vs_native=native_ms / transpiled_ms if transpiled_ms > 0 else 0
    )


def benchmark_html_render(iterations: int = 100) -> BenchmarkResult:
    """Benchmark HTML rendering."""

    source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="HTMLBench">
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

    # 1. Interpreted
    from core.parser import QuantumParser
    from runtime.component import ComponentRuntime

    parser = QuantumParser()
    ast = parser.parse(source)

    # Warmup
    for _ in range(5):
        runtime = ComponentRuntime()
        runtime.execute_component(ast)

    start = time.perf_counter()
    for _ in range(iterations):
        runtime = ComponentRuntime()
        runtime.execute_component(ast)
    interpreted_ms = (time.perf_counter() - start) * 1000

    # 2. Transpiled
    from compiler import Transpiler

    transpiler = Transpiler(target='python')
    result = transpiler.compile_string(source)

    if not result.success:
        print(f"Transpilation failed: {result.errors}")
        return None

    exec_globals = {}
    exec(result.code, exec_globals)
    HTMLBench = exec_globals['HTMLBench']

    # Warmup
    for _ in range(5):
        HTMLBench().render()

    start = time.perf_counter()
    for _ in range(iterations):
        HTMLBench().render()
    transpiled_ms = (time.perf_counter() - start) * 1000

    # 3. Native Python
    def native_render():
        title = "Hello World"
        items = [1, 2, 3, 4, 5]
        html = []
        html.append('<div class="container">')
        html.append(f'<h1>{title}</h1>')
        html.append('<ul>')
        for item in items:
            html.append(f'<li>Item {item}</li>')
        html.append('</ul>')
        html.append('</div>')
        return '\n'.join(html)

    # Warmup
    for _ in range(5):
        native_render()

    start = time.perf_counter()
    for _ in range(iterations):
        native_render()
    native_ms = (time.perf_counter() - start) * 1000

    return BenchmarkResult(
        name='html_render',
        interpreted_ms=interpreted_ms,
        transpiled_ms=transpiled_ms,
        native_ms=native_ms,
        speedup_vs_interpreted=interpreted_ms / transpiled_ms if transpiled_ms > 0 else 0,
        speedup_vs_native=native_ms / transpiled_ms if transpiled_ms > 0 else 0
    )


def benchmark_expression(iterations: int = 100) -> BenchmarkResult:
    """Benchmark expression evaluation."""

    source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="ExprBench">
    <q:set name="a" value="10" />
    <q:set name="b" value="20" />
    <q:set name="c" value="{a + b}" />
    <q:set name="d" value="{c * 2}" />
    <q:set name="e" value="{d - a}" />
    <q:set name="f" value="{e / 2}" />
    <q:set name="result" value="{a + b + c + d + e + f}" />
</q:component>
'''

    # 1. Interpreted
    from core.parser import QuantumParser
    from runtime.component import ComponentRuntime

    parser = QuantumParser()
    ast = parser.parse(source)

    # Warmup
    for _ in range(5):
        runtime = ComponentRuntime()
        runtime.execute_component(ast)

    start = time.perf_counter()
    for _ in range(iterations):
        runtime = ComponentRuntime()
        runtime.execute_component(ast)
    interpreted_ms = (time.perf_counter() - start) * 1000

    # 2. Transpiled
    from compiler import Transpiler

    transpiler = Transpiler(target='python')
    result = transpiler.compile_string(source)

    if not result.success:
        print(f"Transpilation failed: {result.errors}")
        return None

    exec_globals = {}
    exec(result.code, exec_globals)
    ExprBench = exec_globals['ExprBench']

    # Warmup
    for _ in range(5):
        ExprBench().render()

    start = time.perf_counter()
    for _ in range(iterations):
        ExprBench().render()
    transpiled_ms = (time.perf_counter() - start) * 1000

    # 3. Native Python
    def native_expr():
        a = 10
        b = 20
        c = a + b
        d = c * 2
        e = d - a
        f = e / 2
        result = a + b + c + d + e + f
        return result

    # Warmup
    for _ in range(5):
        native_expr()

    start = time.perf_counter()
    for _ in range(iterations):
        native_expr()
    native_ms = (time.perf_counter() - start) * 1000

    return BenchmarkResult(
        name='expression_chain',
        interpreted_ms=interpreted_ms,
        transpiled_ms=transpiled_ms,
        native_ms=native_ms,
        speedup_vs_interpreted=interpreted_ms / transpiled_ms if transpiled_ms > 0 else 0,
        speedup_vs_native=native_ms / transpiled_ms if transpiled_ms > 0 else 0
    )


def run_all_benchmarks():
    """Run all benchmarks and print results."""
    print("=" * 70)
    print("TRANSPILED VS INTERPRETED PERFORMANCE BENCHMARK")
    print("=" * 70)
    print(f"Date: {datetime.now().isoformat()}")
    print()

    benchmarks = [
        ('Loop 1000 iterations', benchmark_loop),
        ('HTML Rendering', benchmark_html_render),
        ('Expression Chain', benchmark_expression),
    ]

    results: List[BenchmarkResult] = []
    iterations = 200

    for name, func in benchmarks:
        print(f"Running: {name}...", end=" ", flush=True)
        try:
            result = func(iterations)
            if result:
                results.append(result)
                print(f"OK (speedup: {result.speedup_vs_interpreted:.1f}x)")
            else:
                print("FAILED")
        except Exception as e:
            print(f"ERROR: {e}")

    # Summary
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"{'Benchmark':<20} {'Interpreted':<12} {'Transpiled':<12} {'Native':<12} {'Speedup':<10}")
    print("-" * 70)

    for r in results:
        print(f"{r.name:<20} {r.interpreted_ms:>10.2f}ms {r.transpiled_ms:>10.2f}ms {r.native_ms:>10.2f}ms {r.speedup_vs_interpreted:>8.1f}x")

    # Average speedup
    if results:
        avg_speedup = sum(r.speedup_vs_interpreted for r in results) / len(results)
        avg_vs_native = sum(r.speedup_vs_native for r in results) / len(results)
        print("-" * 70)
        print(f"{'AVERAGE':<20} {'':<12} {'':<12} {'':<12} {avg_speedup:>8.1f}x")
        print()
        print(f"Average speedup vs interpreted: {avg_speedup:.1f}x")
        print(f"Average overhead vs native:     {1/avg_vs_native:.1f}x")

    # Save results
    output_dir = Path(__file__).parent
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'transpiled_benchmark_{timestamp}.json'

    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'iterations': iterations,
            'results': [asdict(r) for r in results]
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == '__main__':
    run_all_benchmarks()
