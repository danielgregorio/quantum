#!/usr/bin/env python
"""
Overhead Benchmark - Finding Bottlenecks
========================================

Analyzes where the overhead in ExpressionCache.evaluate() is
"""

import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


def benchmark_overhead():
    """Identifies exactly where the overhead is"""

    iterations = 100000
    context = {'total': 0, 'i': 0}

    print("=" * 70)
    print("OVERHEAD ANALYSIS - ExpressionCache.evaluate()")
    print("=" * 70)

    # 1. Baseline: native Python
    total = 0
    start = time.perf_counter()
    for i in range(iterations):
        total += i
    python_time = (time.perf_counter() - start) * 1000
    print(f"\n1. Native Python:         {python_time:.2f}ms")

    # 2. Only eval() with precompiled code
    code = compile('total + i', '<expr>', 'eval')
    total = 0
    ctx = {'total': 0, 'i': 0}
    start = time.perf_counter()
    for i in range(iterations):
        ctx['i'] = i
        ctx['total'] = eval(code, {"__builtins__": {}}, ctx)
    eval_only = (time.perf_counter() - start) * 1000
    print(f"2. precompiled eval():   {eval_only:.2f}ms ({eval_only/python_time:.1f}x)")

    # 3. Overhead of copying SAFE_BUILTINS
    SAFE_BUILTINS = {
        'abs': abs, 'all': all, 'any': any, 'bool': bool, 'chr': chr,
        'dict': dict, 'divmod': divmod, 'enumerate': enumerate, 'filter': filter,
        'float': float, 'format': format, 'frozenset': frozenset, 'hash': hash,
        'hex': hex, 'int': int, 'isinstance': isinstance, 'issubclass': issubclass,
        'iter': iter, 'len': len, 'list': list, 'map': map, 'max': max, 'min': min,
        'next': next, 'oct': oct, 'ord': ord, 'pow': pow, 'range': range,
        'repr': repr, 'reversed': reversed, 'round': round, 'set': set,
        'slice': slice, 'sorted': sorted, 'str': str, 'sum': sum, 'tuple': tuple,
        'type': type, 'zip': zip, 'upper': str.upper, 'lower': str.lower,
        'strip': str.strip, 'True': True, 'False': False, 'None': None,
    }

    start = time.perf_counter()
    for i in range(iterations):
        namespace = dict(SAFE_BUILTINS)  # This is the problem!
        namespace.update(context)
    copy_time = (time.perf_counter() - start) * 1000
    print(f"3. dict.copy() overhead:  {copy_time:.2f}ms ({copy_time/python_time:.1f}x)")

    # 4. eval() WITH a copy of the namespace (as it does today)
    total = 0
    ctx = {'total': 0, 'i': 0}
    start = time.perf_counter()
    for i in range(iterations):
        ctx['i'] = i
        namespace = dict(SAFE_BUILTINS)
        namespace.update(ctx)
        ctx['total'] = eval(code, {"__builtins__": {}}, namespace)
    eval_with_copy = (time.perf_counter() - start) * 1000
    print(f"4. eval() + dict.copy():  {eval_with_copy:.2f}ms ({eval_with_copy/python_time:.1f}x)")

    # 5. eval() WITHOUT a copy (fixed namespace)
    # Create the namespace once, update the context in it
    namespace = dict(SAFE_BUILTINS)
    namespace['total'] = 0
    namespace['i'] = 0
    start = time.perf_counter()
    for i in range(iterations):
        namespace['i'] = i
        namespace['total'] = eval(code, {"__builtins__": {}}, namespace)
    eval_no_copy = (time.perf_counter() - start) * 1000
    print(f"5. eval() NO dict.copy(): {eval_no_copy:.2f}ms ({eval_no_copy/python_time:.1f}x)")

    # 6. Overhead of lru_cache.cache_info()
    from functools import lru_cache

    @lru_cache(maxsize=1000)
    def cached_compile(expr):
        return compile(expr, '<expr>', 'eval')

    cached_compile('total + i')  # warmup

    start = time.perf_counter()
    for i in range(iterations):
        info = cached_compile.cache_info()
        code = cached_compile('total + i')
        info2 = cached_compile.cache_info()
    cache_info_time = (time.perf_counter() - start) * 1000
    print(f"6. lru_cache overhead:    {cache_info_time:.2f}ms ({cache_info_time/python_time:.1f}x)")

    # 7. Overhead of threading.RLock
    import threading
    lock = threading.RLock()
    counter = 0
    start = time.perf_counter()
    for i in range(iterations):
        with lock:
            counter += 1
    lock_time = (time.perf_counter() - start) * 1000
    print(f"7. RLock overhead:        {lock_time:.2f}ms ({lock_time/python_time:.1f}x)")

    # 8. Overhead of time.perf_counter()
    start = time.perf_counter()
    for i in range(iterations):
        t1 = time.perf_counter()
        t2 = time.perf_counter()
    perf_counter_time = (time.perf_counter() - start) * 1000
    print(f"8. perf_counter() x2:     {perf_counter_time:.2f}ms ({perf_counter_time/python_time:.1f}x)")

    # SUMMARY
    print("\n" + "=" * 70)
    print("SUMMARY - Overhead Components")
    print("=" * 70)

    print(f"""
Current total overhead in ExpressionCache.evaluate():

  Native Python:             {python_time:.2f}ms (baseline)

  Overhead components:
  - dict.copy() x100k:       +{copy_time:.2f}ms ({copy_time/python_time:.0f}x)
  - lru_cache overhead:      +{cache_info_time:.2f}ms ({cache_info_time/python_time:.0f}x)
  - RLock (stats):           +{lock_time:.2f}ms ({lock_time/python_time:.0f}x)
  - time.perf_counter() x2:  +{perf_counter_time:.2f}ms ({perf_counter_time/python_time:.0f}x)

  Expected total:            ~{copy_time + cache_info_time + lock_time + perf_counter_time + eval_only:.0f}ms
  plain eval() (minimum):    {eval_only:.2f}ms ({eval_only/python_time:.0f}x)

SOLUTION:
  1. Remove dict.copy() - use a fixed namespace          ->{copy_time:.0f}ms
  2. Remove the double cache_info()                      ->{cache_info_time/2:.0f}ms
  3. Disable stats in production (flag)                  ->{lock_time + perf_counter_time:.0f}ms

  Potential improvement: {(copy_time + cache_info_time/2 + lock_time + perf_counter_time) / eval_with_copy * 100:.0f}% faster
""")


def benchmark_optimized_version():
    """Shows what an optimized version would look like"""

    print("\n" + "=" * 70)
    print("OPTIMIZED VERSION (Prototype)")
    print("=" * 70)

    iterations = 100000

    # Optimized version
    SAFE_BUILTINS = {
        'abs': abs, 'len': len, 'int': int, 'str': str, 'float': float,
        'bool': bool, 'list': list, 'dict': dict, 'range': range, 'sum': sum,
        'min': min, 'max': max, 'True': True, 'False': False, 'None': None,
    }

    class OptimizedExpressionCache:
        def __init__(self):
            from functools import lru_cache
            self._compile = lru_cache(maxsize=1000)(self._do_compile)
            self._base_namespace = dict(SAFE_BUILTINS)

        def _do_compile(self, expr):
            return compile(expr, '<expr>', 'eval')

        def evaluate_fast(self, expr, context):
            """Optimized version - no unnecessary overhead"""
            code = self._compile(expr)
            # Reuse the base namespace, only update the context
            ns = self._base_namespace
            ns.update(context)
            return eval(code, {"__builtins__": {}}, ns)

    cache = OptimizedExpressionCache()

    # Warmup
    cache.evaluate_fast('total + i', {'total': 0, 'i': 0})

    # Benchmark
    ctx = {'total': 0, 'i': 0}
    start = time.perf_counter()
    for i in range(iterations):
        ctx['i'] = i
        ctx['total'] = cache.evaluate_fast('total + i', ctx)
    optimized_time = (time.perf_counter() - start) * 1000

    # Native Python
    total = 0
    start = time.perf_counter()
    for i in range(iterations):
        total += i
    python_time = (time.perf_counter() - start) * 1000

    # Current version
    from runtime.expression_cache import get_expression_cache
    current_cache = get_expression_cache()
    ctx = {'total': 0, 'i': 0}
    for _ in range(100):  # warmup
        current_cache.evaluate('total + i', ctx)

    ctx = {'total': 0, 'i': 0}
    start = time.perf_counter()
    for i in range(iterations):
        ctx['i'] = i
        ctx['total'] = current_cache.evaluate('total + i', ctx)
    current_time = (time.perf_counter() - start) * 1000

    print(f"\n{iterations:,} iterations:")
    print(f"  Native Python:      {python_time:.2f}ms (baseline)")
    print(f"  Current cache:      {current_time:.2f}ms ({current_time/python_time:.1f}x)")
    print(f"  Optimized cache:    {optimized_time:.2f}ms ({optimized_time/python_time:.1f}x)")
    print(f"\n  Potential improvement: {current_time/optimized_time:.1f}x faster")


if __name__ == '__main__':
    benchmark_overhead()
    benchmark_optimized_version()
