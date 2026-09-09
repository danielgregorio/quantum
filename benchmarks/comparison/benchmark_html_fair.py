"""
Fair Cross-Language HTML Rendering Benchmark
=============================================

Compares HTML generation performance fairly:
- Quantum TRANSPILED (production mode - pre-compiled to Python)
- Quantum Interpreted (development mode)
- Python (string formatting)
- PHP (string building)
- Ruby (string interpolation)
- Perl (string concatenation)

The key difference: Quantum Transpiled pre-compiles the template,
so only the execution is measured - same as native code in other languages.
"""

import sys
import time
import statistics
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Language interpreters
PHP_PATH = r"C:\Users\danie\AppData\Local\Microsoft\WinGet\Packages\PHP.PHP.8.4_Microsoft.Winget.Source_8wekyb3d8bbwe\php.exe"
RUBY_PATH = r"C:\Ruby33-x64\bin\ruby.exe"
PERL_PATH = r"C:\Strawberry\perl\bin\perl.exe"


@dataclass
class HTMLComparisonResult:
    language: str
    mode: str
    avg_time_ms: float
    renders_per_second: float
    iterations: int


def benchmark_quantum_transpiled(iterations: int = 500) -> HTMLComparisonResult:
    """Benchmark Quantum TRANSPILED (production mode)"""
    from compiler import Transpiler

    source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="TableTest">
    <q:param name="rows" type="array" />
    <table>
        <q:loop items="{rows}" var="row">
            <tr>
                <td>{row.id}</td>
                <td>{row.name}</td>
                <td>{row.email}</td>
            </tr>
        </q:loop>
    </table>
</q:component>'''

    # Transpile once (pre-compilation step)
    transpiler = Transpiler(target='python')
    result = transpiler.compile_string(source)

    if not result.success:
        raise Exception(f"Transpilation failed: {result.errors}")

    # Execute transpiled code to get the class
    exec_globals = {}
    exec(result.code, exec_globals)
    TableTest = exec_globals['TableTest']

    # Prepare data
    rows = [{"id": i, "name": f"User {i}", "email": f"user{i}@test.com"} for i in range(50)]

    # Warmup
    for _ in range(50):
        TableTest(rows=rows).render()

    # Benchmark (only measures render time, NOT transpilation)
    times = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        TableTest(rows=rows).render()
        times.append((time.perf_counter_ns() - start) / 1_000_000)

    avg = statistics.mean(times)
    return HTMLComparisonResult(
        language="Quantum",
        mode="Transpiled",
        avg_time_ms=avg,
        renders_per_second=1000/avg if avg > 0 else 0,
        iterations=iterations
    )


def benchmark_quantum_interpreted(iterations: int = 200) -> HTMLComparisonResult:
    """Benchmark Quantum INTERPRETED (development mode)"""
    from core.parser import QuantumParser
    from runtime.component import ComponentRuntime
    from runtime.renderer import HTMLRenderer

    source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="TableTest">
    <table>
        <q:loop items="{rows}" var="row">
            <tr>
                <td>{row.id}</td>
                <td>{row.name}</td>
                <td>{row.email}</td>
            </tr>
        </q:loop>
    </table>
</q:component>'''

    context = {
        "rows": [{"id": i, "name": f"User {i}", "email": f"user{i}@test.com"} for i in range(50)]
    }

    parser = QuantumParser()
    ast = parser.parse(source)

    # Warmup
    for _ in range(20):
        runtime = ComponentRuntime()
        for k, v in context.items():
            runtime.execution_context.set_variable(k, v, scope="component")
        runtime.execute_component(ast, context.copy())
        renderer = HTMLRenderer(runtime.execution_context)
        renderer.render(ast)

    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        runtime = ComponentRuntime()
        for k, v in context.items():
            runtime.execution_context.set_variable(k, v, scope="component")
        runtime.execute_component(ast, context.copy())
        renderer = HTMLRenderer(runtime.execution_context)
        renderer.render(ast)
        times.append((time.perf_counter_ns() - start) / 1_000_000)

    avg = statistics.mean(times)
    return HTMLComparisonResult(
        language="Quantum",
        mode="Interpreted",
        avg_time_ms=avg,
        renders_per_second=1000/avg if avg > 0 else 0,
        iterations=iterations
    )


def benchmark_python_native(iterations: int = 500) -> HTMLComparisonResult:
    """Benchmark Python string formatting"""
    rows = [{"id": i, "name": f"User {i}", "email": f"user{i}@test.com"} for i in range(50)]

    def render(rows):
        html = "<table>"
        for row in rows:
            html += f"<tr><td>{row['id']}</td><td>{row['name']}</td><td>{row['email']}</td></tr>"
        html += "</table>"
        return html

    # Warmup
    for _ in range(50):
        render(rows)

    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        render(rows)
        times.append((time.perf_counter_ns() - start) / 1_000_000)

    avg = statistics.mean(times)
    return HTMLComparisonResult(
        language="Python 3.12",
        mode="Native",
        avg_time_ms=avg,
        renders_per_second=1000/avg if avg > 0 else 0,
        iterations=iterations
    )


def benchmark_php(iterations: int = 500) -> HTMLComparisonResult:
    """Benchmark PHP HTML generation"""
    php_code = f'''<?php
$iterations = {iterations};
$rows = [];
for ($i = 0; $i < 50; $i++) {{
    $rows[] = ["id" => $i, "name" => "User $i", "email" => "user$i@test.com"];
}}

function render($rows) {{
    $html = "<table>";
    foreach ($rows as $row) {{
        $html .= "<tr><td>{{$row['id']}}</td><td>{{$row['name']}}</td><td>{{$row['email']}}</td></tr>";
    }}
    $html .= "</table>";
    return $html;
}}

// Warmup
for ($i = 0; $i < 50; $i++) {{
    render($rows);
}}

// Benchmark
$times = [];
for ($i = 0; $i < $iterations; $i++) {{
    $start = hrtime(true);
    render($rows);
    $times[] = (hrtime(true) - $start) / 1000000;
}}

$avg = array_sum($times) / count($times);
echo number_format($avg, 6);
?>'''

    with tempfile.NamedTemporaryFile(suffix='.php', delete=False, mode='w') as f:
        f.write(php_code)
        php_file = f.name

    try:
        result = subprocess.run([PHP_PATH, php_file], capture_output=True, text=True, timeout=60)
        avg = float(result.stdout.strip())
        return HTMLComparisonResult(
            language="PHP 8.4",
            mode="Native",
            avg_time_ms=avg,
            renders_per_second=1000/avg if avg > 0 else 0,
            iterations=iterations
        )
    finally:
        Path(php_file).unlink(missing_ok=True)


def benchmark_ruby(iterations: int = 500) -> HTMLComparisonResult:
    """Benchmark Ruby HTML generation"""
    ruby_code = f'''
iterations = {iterations}
rows = (0...50).map {{ |i| {{id: i, name: "User #{{i}}", email: "user#{{i}}@test.com"}} }}

def render(rows)
  html = "<table>"
  rows.each do |row|
    html += "<tr><td>#{{row[:id]}}</td><td>#{{row[:name]}}</td><td>#{{row[:email]}}</td></tr>"
  end
  html += "</table>"
  html
end

# Warmup
50.times {{ render(rows) }}

# Benchmark
times = []
iterations.times do
  start = Process.clock_gettime(Process::CLOCK_MONOTONIC, :nanosecond)
  render(rows)
  times << (Process.clock_gettime(Process::CLOCK_MONOTONIC, :nanosecond) - start) / 1_000_000.0
end

avg = times.sum / times.length
puts format("%.6f", avg)
'''

    with tempfile.NamedTemporaryFile(suffix='.rb', delete=False, mode='w') as f:
        f.write(ruby_code)
        ruby_file = f.name

    try:
        result = subprocess.run([RUBY_PATH, ruby_file], capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise Exception(f"Ruby error: {result.stderr}")
        avg = float(result.stdout.strip())
        return HTMLComparisonResult(
            language="Ruby 3.3",
            mode="Native",
            avg_time_ms=avg,
            renders_per_second=1000/avg if avg > 0 else 0,
            iterations=iterations
        )
    finally:
        Path(ruby_file).unlink(missing_ok=True)


def benchmark_perl(iterations: int = 500) -> HTMLComparisonResult:
    """Benchmark Perl HTML generation"""
    perl_code = f'''
use strict;
use warnings;
use Time::HiRes qw(time);

my $iterations = {iterations};
my @rows;
for my $i (0..49) {{
    push @rows, {{id => $i, name => "User $i", email => "user$i\\@test.com"}};
}}

sub render {{
    my @rows = @_;
    my $html = "<table>";
    for my $row (@rows) {{
        $html .= "<tr><td>$row->{{id}}</td><td>$row->{{name}}</td><td>$row->{{email}}</td></tr>";
    }}
    $html .= "</table>";
    return $html;
}}

# Warmup
for (1..50) {{
    render(@rows);
}}

# Benchmark
my @times;
for (1..$iterations) {{
    my $start = time();
    render(@rows);
    push @times, (time() - $start) * 1000;
}}

my $sum = 0;
$sum += $_ for @times;
my $avg = $sum / scalar(@times);
printf("%.6f\\n", $avg);
'''

    with tempfile.NamedTemporaryFile(suffix='.pl', delete=False, mode='w') as f:
        f.write(perl_code)
        perl_file = f.name

    try:
        result = subprocess.run([PERL_PATH, perl_file], capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise Exception(f"Perl error: {result.stderr}")
        avg = float(result.stdout.strip())
        return HTMLComparisonResult(
            language="Perl 5.42",
            mode="Native",
            avg_time_ms=avg,
            renders_per_second=1000/avg if avg > 0 else 0,
            iterations=iterations
        )
    finally:
        Path(perl_file).unlink(missing_ok=True)


def run_all_benchmarks():
    """Run all HTML comparison benchmarks"""
    print("=" * 70)
    print("Fair Cross-Language HTML Rendering Benchmark")
    print("=" * 70)
    print("\nTest: Generate HTML table with 50 rows (id, name, email)")
    print("Note: Quantum Transpiled = pre-compiled, only runtime measured\n")

    results: List[HTMLComparisonResult] = []

    benchmarks = [
        ("Quantum Transpiled", benchmark_quantum_transpiled),
        ("Quantum Interpreted", benchmark_quantum_interpreted),
        ("Python Native", benchmark_python_native),
        ("PHP Native", benchmark_php),
        ("Ruby Native", benchmark_ruby),
        ("Perl Native", benchmark_perl),
    ]

    for name, bench_func in benchmarks:
        try:
            print(f"  Testing {name}...", end=" ", flush=True)
            result = bench_func()
            results.append(result)
            print(f"{result.avg_time_ms:.4f}ms ({result.renders_per_second:.0f} renders/sec)")
        except Exception as e:
            print(f"ERROR: {e}")

    # Sort by performance
    results.sort(key=lambda r: r.avg_time_ms)

    # Print rankings
    print("\n" + "=" * 70)
    print("HTML Rendering Performance Rankings")
    print("=" * 70)
    print(f"\n{'Rank':<6} {'Language':<20} {'Mode':<12} {'Avg (ms)':<12} {'Renders/s':<12} {'vs Fast':<8}")
    print("-" * 70)

    fastest = results[0].avg_time_ms if results else 1
    for i, r in enumerate(results, 1):
        relative = r.avg_time_ms / fastest
        lang_mode = f"{r.language}"
        print(f"{i:<6} {lang_mode:<20} {r.mode:<12} {r.avg_time_ms:<12.4f} {r.renders_per_second:<12.0f} {relative:.1f}x")

    # Print key insights
    print("\n" + "=" * 70)
    print("Key Insights")
    print("=" * 70)

    transpiled = next((r for r in results if r.mode == "Transpiled"), None)
    interpreted = next((r for r in results if r.mode == "Interpreted"), None)

    if transpiled and interpreted:
        speedup = interpreted.avg_time_ms / transpiled.avg_time_ms
        print(f"\n- Quantum Transpiled is {speedup:.0f}x faster than Interpreted")

    if transpiled:
        python_native = next((r for r in results if r.language == "Python 3.12"), None)
        if python_native:
            overhead = transpiled.avg_time_ms / python_native.avg_time_ms
            print(f"- Quantum Transpiled has {overhead:.1f}x overhead vs native Python")

    return results


if __name__ == "__main__":
    run_all_benchmarks()
