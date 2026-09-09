"""
Cross-Language HTML/Template Rendering Benchmark
=================================================

Compares template rendering performance across:
- Quantum (interpreted + rendered)
- Python (string formatting + Jinja2-style)
- PHP (native + heredoc)
- Ruby (ERB-style)
- Perl (string interpolation)
- Lua (string concatenation)
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
LUA_PATH = r"C:\Users\danie\AppData\Local\Programs\Lua\bin\lua.exe"
PERL_PATH = r"C:\Strawberry\perl\bin\perl.exe"


@dataclass
class HTMLComparisonResult:
    language: str
    test_name: str
    avg_time_ms: float
    renders_per_second: float
    iterations: int


def benchmark_quantum_html(iterations: int = 200) -> HTMLComparisonResult:
    """Benchmark Quantum HTML rendering"""
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
        test_name="Table (50 rows)",
        avg_time_ms=avg,
        renders_per_second=1000/avg if avg > 0 else 0,
        iterations=iterations
    )


def benchmark_python_html(iterations: int = 200) -> HTMLComparisonResult:
    """Benchmark Python string formatting"""
    rows = [{"id": i, "name": f"User {i}", "email": f"user{i}@test.com"} for i in range(50)]

    def render():
        html = "<table>"
        for row in rows:
            html += f"<tr><td>{row['id']}</td><td>{row['name']}</td><td>{row['email']}</td></tr>"
        html += "</table>"
        return html

    # Warmup
    for _ in range(20):
        render()

    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        render()
        times.append((time.perf_counter_ns() - start) / 1_000_000)

    avg = statistics.mean(times)
    return HTMLComparisonResult(
        language="Python 3.12",
        test_name="Table (50 rows)",
        avg_time_ms=avg,
        renders_per_second=1000/avg if avg > 0 else 0,
        iterations=iterations
    )


def benchmark_php_html(iterations: int = 200) -> HTMLComparisonResult:
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
for ($i = 0; $i < 20; $i++) {{
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
            test_name="Table (50 rows)",
            avg_time_ms=avg,
            renders_per_second=1000/avg if avg > 0 else 0,
            iterations=iterations
        )
    finally:
        Path(php_file).unlink(missing_ok=True)


def benchmark_ruby_html(iterations: int = 200) -> HTMLComparisonResult:
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
20.times {{ render(rows) }}

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
            test_name="Table (50 rows)",
            avg_time_ms=avg,
            renders_per_second=1000/avg if avg > 0 else 0,
            iterations=iterations
        )
    finally:
        Path(ruby_file).unlink(missing_ok=True)


def benchmark_lua_html(iterations: int = 200) -> HTMLComparisonResult:
    """Benchmark Lua HTML generation"""
    lua_code = f'''
local iterations = {iterations}
local rows = {{}}
for i = 0, 49 do
    rows[i+1] = {{id = i, name = "User " .. i, email = "user" .. i .. "@test.com"}}
end

local function render(rows)
    local html = "<table>"
    for _, row in ipairs(rows) do
        html = html .. "<tr><td>" .. row.id .. "</td><td>" .. row.name .. "</td><td>" .. row.email .. "</td></tr>"
    end
    html = html .. "</table>"
    return html
end

-- Warmup
for i = 1, 20 do
    render(rows)
end

-- Benchmark
local socket = require("socket")
local times = {{}}
for i = 1, iterations do
    local start = socket.gettime()
    render(rows)
    times[i] = (socket.gettime() - start) * 1000
end

local sum = 0
for _, t in ipairs(times) do
    sum = sum + t
end
local avg = sum / #times
print(string.format("%.6f", avg))
'''

    with tempfile.NamedTemporaryFile(suffix='.lua', delete=False, mode='w') as f:
        f.write(lua_code)
        lua_file = f.name

    try:
        result = subprocess.run([LUA_PATH, lua_file], capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise Exception(f"Lua error: {result.stderr}")
        avg = float(result.stdout.strip())
        return HTMLComparisonResult(
            language="Lua 5.4",
            test_name="Table (50 rows)",
            avg_time_ms=avg,
            renders_per_second=1000/avg if avg > 0 else 0,
            iterations=iterations
        )
    finally:
        Path(lua_file).unlink(missing_ok=True)


def benchmark_perl_html(iterations: int = 200) -> HTMLComparisonResult:
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
for (1..20) {{
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
            test_name="Table (50 rows)",
            avg_time_ms=avg,
            renders_per_second=1000/avg if avg > 0 else 0,
            iterations=iterations
        )
    finally:
        Path(perl_file).unlink(missing_ok=True)


def run_all_benchmarks():
    """Run all HTML comparison benchmarks"""
    print("=" * 70)
    print("Cross-Language HTML Rendering Benchmark")
    print("=" * 70)
    print("\nTest: Generate HTML table with 50 rows (id, name, email)\n")

    results: List[HTMLComparisonResult] = []

    benchmarks = [
        ("Python 3.12", benchmark_python_html),
        ("Quantum", benchmark_quantum_html),
        ("PHP 8.4", benchmark_php_html),
        ("Ruby 3.3", benchmark_ruby_html),
        ("Lua 5.4", benchmark_lua_html),
        ("Perl 5.42", benchmark_perl_html),
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
    print(f"\n{'Rank':<6} {'Language':<15} {'Avg Time (ms)':<15} {'Renders/sec':<12} {'vs Fastest':<10}")
    print("-" * 70)

    fastest = results[0].avg_time_ms if results else 1
    for i, r in enumerate(results, 1):
        relative = r.avg_time_ms / fastest
        print(f"{i:<6} {r.language:<15} {r.avg_time_ms:<15.4f} {r.renders_per_second:<12.0f} {relative:.1f}x")

    return results


if __name__ == "__main__":
    run_all_benchmarks()
