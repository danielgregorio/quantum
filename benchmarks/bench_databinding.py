#!/usr/bin/env python
"""
Quantum Framework - Databinding Performance Benchmark

Measures the impact of pre-compiled regex patterns and DataBindingCache
on databinding performance.

Run: python benchmarks/bench_databinding.py
"""

import sys
import time
import re
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


def format_time(ms: float) -> str:
    """Format time in appropriate units"""
    if ms < 0.001:
        return f"{ms * 1000000:.1f} ns"
    elif ms < 1:
        return f"{ms * 1000:.2f} µs"
    else:
        return f"{ms:.2f} ms"


class OldDatabindingMethod:
    """Simulates the OLD databinding approach (inline regex compilation)"""

    def apply_databinding(self, text: str, context: Dict[str, Any]) -> Any:
        """OLD: Compiles regex on every call"""
        import re  # Import inside method (old pattern)

        if not text:
            return text

        if context is None:
            context = {}

        # Pattern compiled on EVERY call
        pattern = r'\{([^}]+)\}'

        full_match = re.fullmatch(pattern, text.strip())
        if full_match:
            var_expr = full_match.group(1).strip()
            if var_expr in context:
                return context[var_expr]
            return text

        def replace_variable(match):
            var_expr = match.group(1).strip()
            if var_expr in context:
                return str(context[var_expr])
            return match.group(0)

        return re.sub(pattern, replace_variable, text)


class NewDatabindingMethod:
    """Simulates the NEW databinding approach (pre-compiled regex)"""

    def __init__(self):
        # Pre-compiled pattern (compiled ONCE)
        self._pattern = re.compile(r'\{([^}]+)\}')

    def apply_databinding(self, text: str, context: Dict[str, Any]) -> Any:
        """NEW: Uses pre-compiled regex pattern"""
        if not text:
            return text

        if context is None:
            context = {}

        # Use pre-compiled pattern
        pattern = self._pattern

        full_match = pattern.fullmatch(text.strip())
        if full_match:
            var_expr = full_match.group(1).strip()
            if var_expr in context:
                return context[var_expr]
            return text

        def replace_variable(match):
            var_expr = match.group(1).strip()
            if var_expr in context:
                return str(context[var_expr])
            return match.group(0)

        return pattern.sub(replace_variable, text)


def run_databinding_benchmark():
    """Run databinding performance comparison"""

    print("\n" + "=" * 70)
    print("  DATABINDING PERFORMANCE BENCHMARK")
    print("=" * 70)
    print("  Comparing OLD (inline regex) vs NEW (pre-compiled regex)")
    print("=" * 70)

    old_method = OldDatabindingMethod()
    new_method = NewDatabindingMethod()

    # Test cases
    test_cases = [
        ("Simple variable", "{name}", {"name": "Alice"}),
        ("Pure expression", "{count}", {"count": 42}),
        ("Mixed content", "Hello {name}, you have {count} items", {"name": "Alice", "count": 42}),
        ("Multiple vars", "{a} + {b} = {c}", {"a": 1, "b": 2, "c": 3}),
        ("Nested access", "{user}", {"user": {"name": "Alice", "age": 30}}),
        ("Long template", "User: {name}, Email: {email}, Phone: {phone}, Status: {status}",
         {"name": "Alice", "email": "alice@example.com", "phone": "555-0123", "status": "active"}),
    ]

    iterations = 10000

    print(f"\n  Iterations per test: {iterations:,}")
    print()
    print(f"  {'Test Case':<25} {'Old (inline)':>12} {'New (precomp)':>14} {'Speedup':>10}")
    print(f"  {'-' * 61}")

    total_old = 0
    total_new = 0

    for name, template, context in test_cases:
        # OLD method
        start = time.perf_counter()
        for _ in range(iterations):
            old_method.apply_databinding(template, context)
        old_time = (time.perf_counter() - start) * 1000

        # NEW method
        start = time.perf_counter()
        for _ in range(iterations):
            new_method.apply_databinding(template, context)
        new_time = (time.perf_counter() - start) * 1000

        speedup = old_time / new_time if new_time > 0 else 0

        total_old += old_time
        total_new += new_time

        # Per-operation time
        old_per_op = old_time / iterations
        new_per_op = new_time / iterations

        print(f"  {name:<25} {format_time(old_per_op):>12} {format_time(new_per_op):>14} {speedup:>9.1f}x")

    # Total
    print(f"  {'-' * 61}")
    avg_speedup = total_old / total_new if total_new > 0 else 0
    print(f"  {'TOTAL':<25} {format_time(total_old):>12} {format_time(total_new):>14} {avg_speedup:>9.1f}x")

    print()
    print("  Key improvements:")
    print("    - Regex pattern compiled once at class init, not per call")
    print("    - Removed 'import re' inside method (module already imported)")
    print("    - Pre-compiled patterns stored as instance attributes")
    print()
    print("=" * 70)

    return avg_speedup


def run_array_index_benchmark():
    """Benchmark array index pattern matching"""

    print("\n" + "=" * 70)
    print("  ARRAY INDEX PARSING BENCHMARK")
    print("=" * 70)

    # Old: compile on every call
    def old_parse(expr: str):
        import re
        match = re.match(r'^(\w+)\[(\d+)\](\.(.+))?$', expr.strip())
        return match

    # New: pre-compiled
    pattern = re.compile(r'^(\w+)\[(\d+)\](\.(.+))?$')
    def new_parse(expr: str):
        return pattern.match(expr.strip())

    test_cases = [
        "result[0]",
        "result[0].id",
        "users[1].name",
        "data[99].nested.value",
        "items[5]",
    ]

    iterations = 10000

    print(f"\n  Iterations per test: {iterations:,}")
    print()
    print(f"  {'Expression':<25} {'Old':>12} {'New':>14} {'Speedup':>10}")
    print(f"  {'-' * 61}")

    total_old = 0
    total_new = 0

    for expr in test_cases:
        # OLD
        start = time.perf_counter()
        for _ in range(iterations):
            old_parse(expr)
        old_time = (time.perf_counter() - start) * 1000

        # NEW
        start = time.perf_counter()
        for _ in range(iterations):
            new_parse(expr)
        new_time = (time.perf_counter() - start) * 1000

        speedup = old_time / new_time if new_time > 0 else 0

        total_old += old_time
        total_new += new_time

        old_per_op = old_time / iterations
        new_per_op = new_time / iterations

        print(f"  {expr:<25} {format_time(old_per_op):>12} {format_time(new_per_op):>14} {speedup:>9.1f}x")

    print(f"  {'-' * 61}")
    avg_speedup = total_old / total_new if total_new > 0 else 0
    print(f"  {'AVERAGE':<25} {'-':>12} {'-':>14} {avg_speedup:>9.1f}x")

    print()
    print("=" * 70)

    return avg_speedup


def run_sql_pattern_benchmark():
    """Benchmark SQL pattern matching for count queries"""

    print("\n" + "=" * 70)
    print("  SQL PATTERN MATCHING BENCHMARK")
    print("=" * 70)

    # Old: compile patterns on every call
    def old_clean_sql(sql: str):
        import re
        sql = re.sub(r'\s+ORDER\s+BY\s+[^;]+?(?=\s+(?:LIMIT|OFFSET|FOR\s+UPDATE)|$)', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\s+LIMIT\s+\d+', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\s+OFFSET\s+\d+', '', sql, flags=re.IGNORECASE)
        return sql

    # New: pre-compiled patterns
    order_pattern = re.compile(r'\s+ORDER\s+BY\s+[^;]+?(?=\s+(?:LIMIT|OFFSET|FOR\s+UPDATE)|$)', re.IGNORECASE)
    limit_pattern = re.compile(r'\s+LIMIT\s+\d+', re.IGNORECASE)
    offset_pattern = re.compile(r'\s+OFFSET\s+\d+', re.IGNORECASE)

    def new_clean_sql(sql: str):
        sql = order_pattern.sub('', sql)
        sql = limit_pattern.sub('', sql)
        sql = offset_pattern.sub('', sql)
        return sql

    test_cases = [
        "SELECT * FROM users ORDER BY name LIMIT 10",
        "SELECT id, name FROM users WHERE status = 'active' ORDER BY created_at DESC LIMIT 20 OFFSET 40",
        "SELECT u.id, u.name, COUNT(o.id) FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id ORDER BY COUNT(o.id) DESC LIMIT 100",
    ]

    iterations = 5000

    print(f"\n  Iterations per test: {iterations:,}")
    print()

    total_old = 0
    total_new = 0

    for i, sql in enumerate(test_cases, 1):
        # OLD
        start = time.perf_counter()
        for _ in range(iterations):
            old_clean_sql(sql)
        old_time = (time.perf_counter() - start) * 1000

        # NEW
        start = time.perf_counter()
        for _ in range(iterations):
            new_clean_sql(sql)
        new_time = (time.perf_counter() - start) * 1000

        speedup = old_time / new_time if new_time > 0 else 0

        total_old += old_time
        total_new += new_time

        old_per_op = old_time / iterations
        new_per_op = new_time / iterations

        print(f"  Query {i}: {format_time(old_per_op):>12} -> {format_time(new_per_op):>12} ({speedup:.1f}x faster)")

    print()
    avg_speedup = total_old / total_new if total_new > 0 else 0
    print(f"  Average Speedup: {avg_speedup:.1f}x")

    print()
    print("=" * 70)

    return avg_speedup


if __name__ == '__main__':
    print("\n" + "#" * 70)
    print("#" + " " * 68 + "#")
    print("#" + "  QUANTUM FRAMEWORK - REGEX OPTIMIZATION BENCHMARK".center(68) + "#")
    print("#" + " " * 68 + "#")
    print("#" * 70)

    db_speedup = run_databinding_benchmark()
    arr_speedup = run_array_index_benchmark()
    sql_speedup = run_sql_pattern_benchmark()

    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print()
    print(f"  Databinding patterns:     {db_speedup:.1f}x faster")
    print(f"  Array index patterns:     {arr_speedup:.1f}x faster")
    print(f"  SQL cleanup patterns:     {sql_speedup:.1f}x faster")
    print()
    print("  These improvements apply to every:")
    print("    - Variable interpolation ({variable})")
    print("    - Array access (result[0].id)")
    print("    - Paginated query execution")
    print()
    print("=" * 70)
