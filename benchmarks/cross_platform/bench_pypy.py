#!/usr/bin/env python3
"""
Benchmark: CPython vs PyPy para Quantum
========================================

Uso:
    python benchmarks/cross_platform/bench_pypy.py   # CPython
    pypy3 benchmarks/cross_platform/bench_pypy.py    # PyPy
"""

import sys
import os
import time
import platform

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def get_runtime_info():
    """Retorna informacoes do runtime Python."""
    impl = platform.python_implementation()
    version = platform.python_version()

    if impl == 'PyPy':
        import pypyinterface
        jit_info = "JIT Enabled"
    else:
        jit_info = "No JIT"

    return f"{impl} {version} ({jit_info})"

def benchmark_expression_eval(iterations: int = 10000):
    """Benchmark de avaliacao de expressoes."""
    from runtime.expression_cache import get_expression_cache

    cache = get_expression_cache()
    context = {'x': 10, 'y': 20, 'items': [1, 2, 3, 4, 5]}

    expressions = [
        "x + y",
        "x * y + 100",
        "len(items)",
        "sum(items)",
        "x > 5 and y < 30",
        "[i * 2 for i in items]",
    ]

    start = time.perf_counter()

    for _ in range(iterations):
        for expr in expressions:
            cache.evaluate(expr, context)

    elapsed = time.perf_counter() - start
    ops = iterations * len(expressions)

    return {
        'name': 'Expression Evaluation',
        'iterations': iterations,
        'total_ops': ops,
        'time_ms': elapsed * 1000,
        'ops_per_sec': ops / elapsed,
    }

def benchmark_databinding(iterations: int = 10000):
    """Benchmark de databinding."""
    from runtime.expression_cache import get_databinding_cache

    cache = get_databinding_cache()
    context = {
        'user': 'John',
        'count': 42,
        'items': ['a', 'b', 'c'],
        'nested': {'value': 100},
    }

    templates = [
        "Hello, {user}!",
        "Count: {count}",
        "Items: {items}",
        "Value is {count} and user is {user}",
        "Nested: {nested}",
    ]

    start = time.perf_counter()

    for _ in range(iterations):
        for template in templates:
            cache.apply(template, context)

    elapsed = time.perf_counter() - start
    ops = iterations * len(templates)

    return {
        'name': 'Databinding Resolution',
        'iterations': iterations,
        'total_ops': ops,
        'time_ms': elapsed * 1000,
        'ops_per_sec': ops / elapsed,
    }

def benchmark_loop_quantum(iterations: int = 1000):
    """Benchmark de avaliacao de expressoes em loop (simula loop Quantum)."""
    from runtime.expression_cache import get_expression_cache

    cache = get_expression_cache()

    start = time.perf_counter()

    for _ in range(iterations):
        context = {'total': 0}
        for i in range(100):
            # Simula o que o Quantum faz internamente em cada iteracao
            context['i'] = i
            context['total'] = cache.evaluate('total + i', context)

    elapsed = time.perf_counter() - start

    return {
        'name': 'Simulated Quantum Loop',
        'iterations': iterations,
        'total_ops': iterations * 100,
        'time_ms': elapsed * 1000,
        'ops_per_sec': (iterations * 100) / elapsed,
    }

def benchmark_parse_only(iterations: int = 1000):
    """Benchmark apenas do parser."""
    from core.parser import QuantumParser

    quantum_code = '''
<q:component name="ParseBench">
    <q:set name="x" value="10" />
    <q:set name="y" value="20" />
    <q:if test="{x > 5}">
        <q:set name="result" value="{x + y}" />
    </q:if>
    <q:loop from="1" to="10" var="i">
        <q:set name="total" value="{total + i}" />
    </q:loop>
</q:component>
'''

    parser = QuantumParser()

    start = time.perf_counter()

    for _ in range(iterations):
        ast = parser.parse(quantum_code)

    elapsed = time.perf_counter() - start

    return {
        'name': 'Parser Only',
        'iterations': iterations,
        'total_ops': iterations,
        'time_ms': elapsed * 1000,
        'ops_per_sec': iterations / elapsed,
    }

def run_all_benchmarks():
    """Executa todos os benchmarks."""
    impl = platform.python_implementation()
    version = platform.python_version()

    print("=" * 60)
    print(f"Quantum JIT Benchmark - {impl} {version}")
    print("=" * 60)

    if impl == 'PyPy':
        print("JIT Status: ENABLED (PyPy)")
        print("Warming up JIT...")
        # Warmup para o JIT compilar
        for _ in range(100):
            benchmark_expression_eval(10)
        print("Warmup complete.\n")
    else:
        print("JIT Status: DISABLED (CPython)")
        print("Tip: Run with 'pypy3' for JIT compilation\n")

    benchmarks = [
        ('Expression Eval', lambda: benchmark_expression_eval(10000)),
        ('Databinding', lambda: benchmark_databinding(10000)),
        ('Parser', lambda: benchmark_parse_only(500)),
        ('Quantum Loop', lambda: benchmark_loop_quantum(200)),
    ]

    results = []

    for name, bench_func in benchmarks:
        print(f"Running: {name}...")
        try:
            result = bench_func()
            results.append(result)
            print(f"  Time: {result['time_ms']:.2f}ms")
            print(f"  Ops/sec: {result['ops_per_sec']:,.0f}")
        except Exception as e:
            print(f"  ERROR: {e}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Benchmark':<30} {'Time (ms)':<15} {'Ops/sec':<15}")
    print("-" * 60)

    for r in results:
        print(f"{r['name']:<30} {r['time_ms']:<15.2f} {r['ops_per_sec']:<15,.0f}")

    # Salvar resultado para comparacao
    output_file = f"bench_result_{impl.lower()}.txt"
    with open(output_file, 'w') as f:
        f.write(f"Runtime: {impl} {version}\n")
        for r in results:
            f.write(f"{r['name']}: {r['ops_per_sec']:.0f} ops/sec\n")

    print(f"\nResults saved to: {output_file}")
    print("\nTo compare CPython vs PyPy:")
    print("  1. python benchmarks/cross_platform/bench_pypy.py")
    print("  2. pypy3 benchmarks/cross_platform/bench_pypy.py")
    print("  3. Compare bench_result_cpython.txt vs bench_result_pypy.txt")

if __name__ == '__main__':
    run_all_benchmarks()
