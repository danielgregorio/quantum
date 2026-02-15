"""
Quantum HTML Throughput Benchmarks
===================================

Measures HTML generation performance:
- Templates per second
- Component rendering throughput
- Databinding performance
- Complex layout rendering
"""

import sys
import time
import statistics
import gc
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.parser import QuantumParser
from runtime.component import ComponentRuntime
from runtime.renderer import HTMLRenderer


@dataclass
class HTMLBenchmarkResult:
    """Result of an HTML benchmark"""
    name: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    renders_per_second: float
    html_size_bytes: int
    bytes_per_second: float


def run_benchmark(name: str, source: str, context: Dict[str, Any] = None,
                  iterations: int = 100, warmup: int = 10) -> HTMLBenchmarkResult:
    """Run an HTML rendering benchmark"""
    if context is None:
        context = {}

    parser = QuantumParser()

    # Parse once (not part of benchmark)
    ast = parser.parse(source)
    if ast is None:
        raise ValueError("Failed to parse template")

    # Warmup
    for _ in range(warmup):
        runtime = ComponentRuntime()
        # Set context variables
        for key, value in context.items():
            runtime.execution_context.set_variable(key, value, scope="component")
        runtime.execute_component(ast, context.copy())
        renderer = HTMLRenderer(runtime.execution_context)
        renderer.render(ast)

    # Get HTML size from first run
    runtime = ComponentRuntime()
    for key, value in context.items():
        runtime.execution_context.set_variable(key, value, scope="component")
    runtime.execute_component(ast, context.copy())
    renderer = HTMLRenderer(runtime.execution_context)
    html = renderer.render(ast)
    html_size = len(html.encode('utf-8'))

    # Benchmark
    times_ms = []
    gc.disable()
    try:
        for _ in range(iterations):
            start = time.perf_counter_ns()
            runtime = ComponentRuntime()
            for key, value in context.items():
                runtime.execution_context.set_variable(key, value, scope="component")
            runtime.execute_component(ast, context.copy())
            renderer = HTMLRenderer(runtime.execution_context)
            renderer.render(ast)
            end = time.perf_counter_ns()
            times_ms.append((end - start) / 1_000_000)
    finally:
        gc.enable()

    total = sum(times_ms)
    avg = statistics.mean(times_ms)
    renders_per_sec = 1000 / avg if avg > 0 else 0
    bytes_per_sec = (html_size * renders_per_sec)

    return HTMLBenchmarkResult(
        name=name,
        iterations=iterations,
        total_time_ms=total,
        avg_time_ms=avg,
        min_time_ms=min(times_ms),
        max_time_ms=max(times_ms),
        std_dev_ms=statistics.stdev(times_ms) if len(times_ms) > 1 else 0,
        renders_per_second=renders_per_sec,
        html_size_bytes=html_size,
        bytes_per_second=bytes_per_sec
    )


def benchmark_simple_template() -> HTMLBenchmarkResult:
    """Benchmark simple static template"""
    source = """<?xml version="1.0" encoding="UTF-8"?>
<q:component name="SimpleTemplate">
    <div class="container">
        <h1>Welcome</h1>
        <p>This is a simple template.</p>
    </div>
</q:component>"""
    return run_benchmark("Simple Static Template", source, iterations=500)


def benchmark_databinding() -> HTMLBenchmarkResult:
    """Benchmark template with databinding"""
    source = """<?xml version="1.0" encoding="UTF-8"?>
<q:component name="DatabindingTemplate">
    <q:set name="title" value="Welcome" />
    <q:set name="username" value="John Doe" />
    <q:set name="count" value="42" />

    <div class="container">
        <h1>{title}</h1>
        <p>Hello, {username}!</p>
        <p>You have {count} messages.</p>
    </div>
</q:component>"""
    return run_benchmark("Databinding (3 vars)", source, iterations=300)


def benchmark_loop_small() -> HTMLBenchmarkResult:
    """Benchmark small loop (10 items)"""
    source = """<?xml version="1.0" encoding="UTF-8"?>
<q:component name="SmallLoop">
    <q:set name="items" value="[1,2,3,4,5,6,7,8,9,10]" />

    <ul>
        <q:loop items="{items}" var="item">
            <li>Item {item}</li>
        </q:loop>
    </ul>
</q:component>"""
    return run_benchmark("Loop (10 items)", source, iterations=300)


def benchmark_loop_medium() -> HTMLBenchmarkResult:
    """Benchmark medium loop (100 items)"""
    items_str = ",".join(str(i) for i in range(1, 101))
    source = f"""<?xml version="1.0" encoding="UTF-8"?>
<q:component name="MediumLoop">
    <q:set name="items" value="[{items_str}]" />

    <ul>
        <q:loop items="{{items}}" var="item">
            <li>Item {{item}}</li>
        </q:loop>
    </ul>
</q:component>"""
    return run_benchmark("Loop (100 items)", source, iterations=100)


def benchmark_loop_large() -> HTMLBenchmarkResult:
    """Benchmark large loop (500 items)"""
    items_str = ",".join(str(i) for i in range(1, 501))
    source = f"""<?xml version="1.0" encoding="UTF-8"?>
<q:component name="LargeLoop">
    <q:set name="items" value="[{items_str}]" />

    <ul>
        <q:loop items="{{items}}" var="item">
            <li>Item {{item}}</li>
        </q:loop>
    </ul>
</q:component>"""
    return run_benchmark("Loop (500 items)", source, iterations=30)


def benchmark_conditionals() -> HTMLBenchmarkResult:
    """Benchmark conditional rendering"""
    # Note: Using &gt; and &lt; for XML entity encoding
    source = """<?xml version="1.0" encoding="UTF-8"?>
<q:component name="ConditionalTemplate">
    <q:set name="showHeader" value="true" />
    <q:set name="isAdmin" value="false" />
    <q:set name="hasItems" value="true" />

    <div>
        <q:if condition="{showHeader}">
            <header>Site Header</header>
        </q:if>

        <q:if condition="{isAdmin}">
            <div class="admin-panel">Admin Only</div>
        </q:if>
        <q:else>
            <div class="user-panel">User Panel</div>
        </q:else>

        <q:if condition="{hasItems}">
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </q:if>
    </div>
</q:component>"""
    return run_benchmark("Conditionals (3 branches)", source, iterations=300)


def benchmark_nested_components() -> HTMLBenchmarkResult:
    """Benchmark nested structure"""
    source = """<?xml version="1.0" encoding="UTF-8"?>
<q:component name="NestedTemplate">
    <div class="container">
        <header class="header">
            <nav class="nav">
                <ul class="nav-list">
                    <li class="nav-item"><a href="#">Home</a></li>
                    <li class="nav-item"><a href="#">About</a></li>
                    <li class="nav-item"><a href="#">Contact</a></li>
                </ul>
            </nav>
        </header>

        <main class="main">
            <article class="article">
                <h1 class="title">Article Title</h1>
                <div class="content">
                    <p>First paragraph with some text.</p>
                    <p>Second paragraph with more text.</p>
                    <blockquote>A quote here.</blockquote>
                </div>
            </article>

            <aside class="sidebar">
                <div class="widget">
                    <h3>Widget Title</h3>
                    <ul>
                        <li>Link 1</li>
                        <li>Link 2</li>
                    </ul>
                </div>
            </aside>
        </main>

        <footer class="footer">
            <p>Copyright 2025</p>
        </footer>
    </div>
</q:component>"""
    return run_benchmark("Nested Structure (deep)", source, iterations=300)


def benchmark_table_render() -> HTMLBenchmarkResult:
    """Benchmark table rendering with context data"""
    source = """<?xml version="1.0" encoding="UTF-8"?>
<q:component name="TableTemplate">
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Email</th>
            </tr>
        </thead>
        <tbody>
            <q:loop items="{rows}" var="row">
                <tr>
                    <td>{row.id}</td>
                    <td>{row.name}</td>
                    <td>{row.email}</td>
                </tr>
            </q:loop>
        </tbody>
    </table>
</q:component>"""
    context = {
        "rows": [{"id": i, "name": f"User {i}", "email": f"user{i}@test.com"} for i in range(50)]
    }
    return run_benchmark("Table (50 rows x 3 cols)", source, context, iterations=50)


def benchmark_dashboard() -> HTMLBenchmarkResult:
    """Benchmark realistic dashboard with context data"""
    source = """<?xml version="1.0" encoding="UTF-8"?>
<q:component name="Dashboard">
    <div class="dashboard">
        <header class="dashboard-header">
            <h1>{title}</h1>
            <span class="user">Welcome, {user}</span>
        </header>

        <div class="dashboard-grid">
            <q:loop items="{cards}" var="card">
                <div class="card">
                    <h3 class="card-title">{card.title}</h3>
                    <div class="card-value">{card.value}</div>
                    <span class="card-status">{card.status}</span>
                </div>
            </q:loop>
        </div>

        <footer class="dashboard-footer">
            <p>Last updated: now</p>
        </footer>
    </div>
</q:component>"""
    context = {
        "title": "Dashboard",
        "user": "Admin",
        "cards": [
            {"title": f"Card {i}", "value": i * 100, "status": "active" if i % 2 == 0 else "pending"}
            for i in range(12)
        ]
    }
    return run_benchmark("Dashboard (12 cards)", source, context, iterations=50)


def benchmark_form() -> HTMLBenchmarkResult:
    """Benchmark form rendering with context data"""
    source = """<?xml version="1.0" encoding="UTF-8"?>
<q:component name="FormTemplate">
    <form class="form" method="POST">
        <q:loop items="{fields}" var="field">
            <div class="form-group">
                <label for="{field.name}">{field.label}</label>
                <input type="{field.type}" name="{field.name}" id="{field.name}" />
            </div>
        </q:loop>
        <button type="submit">Submit</button>
    </form>
</q:component>"""
    context = {
        "fields": [
            {"name": "username", "type": "text", "label": "Username"},
            {"name": "email", "type": "email", "label": "Email"},
            {"name": "password", "type": "password", "label": "Password"},
            {"name": "bio", "type": "textarea", "label": "Bio"},
            {"name": "country", "type": "select", "label": "Country"},
        ]
    }
    return run_benchmark("Form (5 fields)", source, context, iterations=200)


def run_all_benchmarks():
    """Run all HTML throughput benchmarks"""
    print("=" * 70)
    print("Quantum HTML Throughput Benchmarks")
    print("=" * 70)

    results: List[HTMLBenchmarkResult] = []

    benchmarks = [
        ("Basic Templates", [
            benchmark_simple_template,
            benchmark_databinding,
        ]),
        ("Loop Performance", [
            benchmark_loop_small,
            benchmark_loop_medium,
            benchmark_loop_large,
        ]),
        ("Control Flow", [
            benchmark_conditionals,
        ]),
        ("Complex Templates", [
            benchmark_nested_components,
            benchmark_table_render,
            benchmark_dashboard,
            benchmark_form,
        ]),
    ]

    for category, bench_funcs in benchmarks:
        print(f"\n[{category}]")
        for bench_func in bench_funcs:
            try:
                result = bench_func()
                results.append(result)
                print(f"  {result.name:<30} {result.avg_time_ms:>8.3f}ms | "
                      f"{result.renders_per_second:>8.0f} renders/sec | "
                      f"{result.html_size_bytes:>6} bytes")
            except Exception as e:
                print(f"  {bench_func.__name__:<30} ERROR: {e}")

    # Print summary
    if not results:
        print("\nNo benchmarks completed successfully.")
        return results

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"\n{'Benchmark':<35} {'Avg (ms)':<10} {'Renders/s':<12} {'MB/s':<10}")
    print("-" * 70)

    for r in results:
        mb_per_sec = r.bytes_per_second / (1024 * 1024)
        print(f"{r.name:<35} {r.avg_time_ms:<10.3f} {r.renders_per_second:<12.0f} {mb_per_sec:<10.2f}")

    # Overall stats
    total_renders = sum(r.iterations for r in results)
    total_time = sum(r.total_time_ms for r in results)
    total_bytes = sum(r.html_size_bytes * r.iterations for r in results)

    print("-" * 70)
    if total_time > 0:
        print(f"Total: {total_renders:,} renders in {total_time:.0f}ms")
        print(f"Overall: {(total_renders / total_time) * 1000:.0f} renders/sec")
        print(f"Throughput: {(total_bytes / total_time) * 1000 / (1024*1024):.2f} MB/sec")

    return results


if __name__ == "__main__":
    run_all_benchmarks()
