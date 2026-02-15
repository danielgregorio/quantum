#!/usr/bin/env python
"""
Cross-Language Performance Comparison
======================================

Compares Quantum performance against other interpreted languages:
- Quantum Interpreted
- Quantum Transpiled
- Python Native
- Node.js (JavaScript)

Tests:
1. Loop with accumulation (1M iterations)
2. String/HTML building
3. Fibonacci recursive
4. Object/Dict manipulation
"""

import sys
import os
import time
import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


@dataclass
class BenchmarkResult:
    language: str
    test: str
    time_ms: float
    iterations: int
    ops_per_sec: float


# Paths to interpreters
PHP_PATH = r"C:\Users\danie\AppData\Local\Microsoft\WinGet\Packages\PHP.PHP.8.4_Microsoft.Winget.Source_8wekyb3d8bbwe\php.exe"
RUBY_PATH = r"C:\Ruby33-x64\bin\ruby.exe"
LUA_PATH = r"C:\Users\danie\AppData\Local\Programs\Lua\bin\lua.exe"
PERL_PATH = r"C:\Strawberry\perl\bin\perl.exe"


def run_external_benchmark(cmd: list, code: str, suffix: str) -> float:
    """Run code in external interpreter and return execution time in ms."""
    with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8') as f:
        f.write(code)
        f.flush()
        temp_path = f.name

    try:
        result = subprocess.run(
            cmd + [temp_path],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            print(f"Error: {result.stderr[:200]}")
            return -1

        # Parse time from output
        if result.stdout.strip():
            try:
                return float(result.stdout.strip().split('\n')[-1])
            except ValueError:
                pass

        return -1
    except Exception as e:
        print(f"Exception: {e}")
        return -1
    finally:
        try:
            os.unlink(temp_path)
        except:
            pass


def run_php_benchmark(code: str) -> float:
    """Run PHP code and return execution time in ms."""
    return run_external_benchmark([PHP_PATH], code, '.php')


def run_ruby_benchmark(code: str) -> float:
    """Run Ruby code and return execution time in ms."""
    return run_external_benchmark([RUBY_PATH], code, '.rb')


def run_lua_benchmark(code: str) -> float:
    """Run Lua code and return execution time in ms."""
    return run_external_benchmark([LUA_PATH], code, '.lua')


def run_perl_benchmark(code: str) -> float:
    """Run Perl code and return execution time in ms."""
    return run_external_benchmark([PERL_PATH], code, '.pl')


def benchmark_loop_accumulation(iterations: int = 100) -> List[BenchmarkResult]:
    """Benchmark: Loop with accumulation (sum 1 to N)."""
    results = []
    N = 100000  # Sum 1 to 100k

    # 1. Python Native
    def python_loop():
        total = 0
        for i in range(1, N + 1):
            total += i
        return total

    # Warmup
    for _ in range(3):
        python_loop()

    start = time.perf_counter()
    for _ in range(iterations):
        python_loop()
    python_time = (time.perf_counter() - start) * 1000

    results.append(BenchmarkResult(
        language='Python 3.12',
        test='loop_100k',
        time_ms=python_time,
        iterations=iterations,
        ops_per_sec=(iterations / python_time) * 1000
    ))

    # 2. Quantum Interpreted
    from core.parser import QuantumParser
    from runtime.component import ComponentRuntime

    quantum_source = f'''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="LoopBench">
    <q:set name="total" value="0" />
    <q:loop from="1" to="{N}" var="i">
        <q:set name="total" value="{{total + i}}" />
    </q:loop>
</q:component>'''

    parser = QuantumParser()
    ast = parser.parse(quantum_source)

    # Warmup
    for _ in range(3):
        runtime = ComponentRuntime()
        runtime.execute_component(ast)

    start = time.perf_counter()
    for _ in range(iterations):
        runtime = ComponentRuntime()
        runtime.execute_component(ast)
    quantum_interp_time = (time.perf_counter() - start) * 1000

    results.append(BenchmarkResult(
        language='Quantum Interpreted',
        test='loop_100k',
        time_ms=quantum_interp_time,
        iterations=iterations,
        ops_per_sec=(iterations / quantum_interp_time) * 1000
    ))

    # 3. Quantum Transpiled
    from compiler import Transpiler

    transpiler = Transpiler(target='python')
    compiled = transpiler.compile_string(quantum_source)

    if compiled.success:
        exec_globals = {}
        exec(compiled.code, exec_globals)
        LoopBench = exec_globals['LoopBench']

        # Warmup
        for _ in range(3):
            LoopBench().render()

        start = time.perf_counter()
        for _ in range(iterations):
            LoopBench().render()
        quantum_trans_time = (time.perf_counter() - start) * 1000

        results.append(BenchmarkResult(
            language='Quantum Transpiled',
            test='loop_100k',
            time_ms=quantum_trans_time,
            iterations=iterations,
            ops_per_sec=(iterations / quantum_trans_time) * 1000
        ))

    # 4. Lua
    lua_code = f'''
local start = os.clock()
local iterations = {iterations}

for iter = 1, iterations do
    local total = 0
    for i = 1, {N} do
        total = total + i
    end
end

local elapsed = (os.clock() - start) * 1000
print(elapsed)
'''

    lua_time = run_lua_benchmark(lua_code)
    if lua_time > 0:
        results.append(BenchmarkResult(
            language='Lua 5.4',
            test='loop_100k',
            time_ms=lua_time,
            iterations=iterations,
            ops_per_sec=(iterations / lua_time) * 1000
        ))

    # 5. Perl
    perl_code = f'''
use Time::HiRes qw(time);

my $start = time();
my $iterations = {iterations};

for (my $iter = 0; $iter < $iterations; $iter++) {{
    my $total = 0;
    for (my $i = 1; $i <= {N}; $i++) {{
        $total += $i;
    }}
}}

my $elapsed = (time() - $start) * 1000;
print $elapsed;
'''

    perl_time = run_perl_benchmark(perl_code)
    if perl_time > 0:
        results.append(BenchmarkResult(
            language='Perl 5.42',
            test='loop_100k',
            time_ms=perl_time,
            iterations=iterations,
            ops_per_sec=(iterations / perl_time) * 1000
        ))

    # 6. PHP
    php_code = f'''<?php
$start = hrtime(true);
$iterations = {iterations};

for ($iter = 0; $iter < $iterations; $iter++) {{
    $total = 0;
    for ($i = 1; $i <= {N}; $i++) {{
        $total += $i;
    }}
}}

$end = hrtime(true);
echo ($end - $start) / 1e6;
'''

    php_time = run_php_benchmark(php_code)
    if php_time > 0:
        results.append(BenchmarkResult(
            language='PHP 8.4',
            test='loop_100k',
            time_ms=php_time,
            iterations=iterations,
            ops_per_sec=(iterations / php_time) * 1000
        ))

    # 8. Ruby
    ruby_code = f'''
start = Process.clock_gettime(Process::CLOCK_MONOTONIC)
iterations = {iterations}

iterations.times do
    total = 0
    (1..{N}).each do |i|
        total += i
    end
end

elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - start
puts elapsed * 1000
'''

    ruby_time = run_ruby_benchmark(ruby_code)
    if ruby_time > 0:
        results.append(BenchmarkResult(
            language='Ruby 3.3',
            test='loop_100k',
            time_ms=ruby_time,
            iterations=iterations,
            ops_per_sec=(iterations / ruby_time) * 1000
        ))

    return results


def benchmark_string_building(iterations: int = 100) -> List[BenchmarkResult]:
    """Benchmark: String/HTML building."""
    results = []
    ITEMS = 100

    # 1. Python Native
    def python_strings():
        html = []
        for i in range(ITEMS):
            html.append(f'<li class="item">Item {i}</li>')
        return '\n'.join(html)

    # Warmup
    for _ in range(3):
        python_strings()

    start = time.perf_counter()
    for _ in range(iterations):
        python_strings()
    python_time = (time.perf_counter() - start) * 1000

    results.append(BenchmarkResult(
        language='Python 3.12',
        test='string_build',
        time_ms=python_time,
        iterations=iterations,
        ops_per_sec=(iterations / python_time) * 1000
    ))

    # 2. Quantum Interpreted
    from core.parser import QuantumParser
    from runtime.component import ComponentRuntime

    quantum_source = f'''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="StringBench">
    <q:set name="items" value="{{list(range({ITEMS}))}}" />
    <ul>
        <q:loop collection="{{items}}" var="i">
            <li class="item">Item {{i}}</li>
        </q:loop>
    </ul>
</q:component>'''

    parser = QuantumParser()
    ast = parser.parse(quantum_source)

    # Warmup
    for _ in range(3):
        runtime = ComponentRuntime()
        runtime.execute_component(ast)

    start = time.perf_counter()
    for _ in range(iterations):
        runtime = ComponentRuntime()
        runtime.execute_component(ast)
    quantum_interp_time = (time.perf_counter() - start) * 1000

    results.append(BenchmarkResult(
        language='Quantum Interpreted',
        test='string_build',
        time_ms=quantum_interp_time,
        iterations=iterations,
        ops_per_sec=(iterations / quantum_interp_time) * 1000
    ))

    # 3. Quantum Transpiled
    from compiler import Transpiler

    transpiler = Transpiler(target='python')
    compiled = transpiler.compile_string(quantum_source)

    if compiled.success:
        exec_globals = {}
        exec(compiled.code, exec_globals)
        StringBench = exec_globals['StringBench']

        # Warmup
        for _ in range(3):
            StringBench().render()

        start = time.perf_counter()
        for _ in range(iterations):
            StringBench().render()
        quantum_trans_time = (time.perf_counter() - start) * 1000

        results.append(BenchmarkResult(
            language='Quantum Transpiled',
            test='string_build',
            time_ms=quantum_trans_time,
            iterations=iterations,
            ops_per_sec=(iterations / quantum_trans_time) * 1000
        ))

    # 4. Lua
    lua_code = f'''
local start = os.clock()
local iterations = {iterations}

for iter = 1, iterations do
    local html = {{}}
    for i = 0, {ITEMS - 1} do
        html[#html + 1] = '<li class="item">Item ' .. i .. '</li>'
    end
    table.concat(html, "\\n")
end

local elapsed = (os.clock() - start) * 1000
print(elapsed)
'''

    lua_time = run_lua_benchmark(lua_code)
    if lua_time > 0:
        results.append(BenchmarkResult(
            language='Lua 5.4',
            test='string_build',
            time_ms=lua_time,
            iterations=iterations,
            ops_per_sec=(iterations / lua_time) * 1000
        ))

    # 5. Perl
    perl_code = f'''
use Time::HiRes qw(time);

my $start = time();
my $iterations = {iterations};

for (my $iter = 0; $iter < $iterations; $iter++) {{
    my @html = ();
    for (my $i = 0; $i < {ITEMS}; $i++) {{
        push @html, "<li class=\\"item\\">Item $i</li>";
    }}
    join("\\n", @html);
}}

my $elapsed = (time() - $start) * 1000;
print $elapsed;
'''

    perl_time = run_perl_benchmark(perl_code)
    if perl_time > 0:
        results.append(BenchmarkResult(
            language='Perl 5.42',
            test='string_build',
            time_ms=perl_time,
            iterations=iterations,
            ops_per_sec=(iterations / perl_time) * 1000
        ))

    # 6. PHP
    php_code = f'''<?php
$start = hrtime(true);
$iterations = {iterations};

for ($iter = 0; $iter < $iterations; $iter++) {{
    $html = [];
    for ($i = 0; $i < {ITEMS}; $i++) {{
        $html[] = "<li class=\\"item\\">Item $i</li>";
    }}
    implode("\\n", $html);
}}

$end = hrtime(true);
echo ($end - $start) / 1e6;
'''

    php_time = run_php_benchmark(php_code)
    if php_time > 0:
        results.append(BenchmarkResult(
            language='PHP 8.4',
            test='string_build',
            time_ms=php_time,
            iterations=iterations,
            ops_per_sec=(iterations / php_time) * 1000
        ))

    # 6. Ruby
    ruby_code = f'''
start = Process.clock_gettime(Process::CLOCK_MONOTONIC)
iterations = {iterations}

iterations.times do
    html = []
    {ITEMS}.times do |i|
        html << "<li class=\\"item\\">Item #{{i}}</li>"
    end
    html.join("\\n")
end

elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - start
puts elapsed * 1000
'''

    ruby_time = run_ruby_benchmark(ruby_code)
    if ruby_time > 0:
        results.append(BenchmarkResult(
            language='Ruby 3.3',
            test='string_build',
            time_ms=ruby_time,
            iterations=iterations,
            ops_per_sec=(iterations / ruby_time) * 1000
        ))

    return results


def benchmark_fibonacci(iterations: int = 100) -> List[BenchmarkResult]:
    """Benchmark: Recursive Fibonacci."""
    results = []
    N = 25  # fib(25) = 75025

    # 1. Python Native
    def fib(n):
        if n <= 1:
            return n
        return fib(n - 1) + fib(n - 2)

    # Warmup
    for _ in range(3):
        fib(N)

    start = time.perf_counter()
    for _ in range(iterations):
        fib(N)
    python_time = (time.perf_counter() - start) * 1000

    results.append(BenchmarkResult(
        language='Python 3.12',
        test='fibonacci_25',
        time_ms=python_time,
        iterations=iterations,
        ops_per_sec=(iterations / python_time) * 1000
    ))

    # 2. Lua
    lua_code = f'''
local function fib(n)
    if n <= 1 then return n end
    return fib(n - 1) + fib(n - 2)
end

local start = os.clock()
local iterations = {iterations}

for iter = 1, iterations do
    fib({N})
end

local elapsed = (os.clock() - start) * 1000
print(elapsed)
'''

    lua_time = run_lua_benchmark(lua_code)
    if lua_time > 0:
        results.append(BenchmarkResult(
            language='Lua 5.4',
            test='fibonacci_25',
            time_ms=lua_time,
            iterations=iterations,
            ops_per_sec=(iterations / lua_time) * 1000
        ))

    # 3. Perl
    perl_code = f'''
use Time::HiRes qw(time);

sub fib {{
    my ($n) = @_;
    return $n if $n <= 1;
    return fib($n - 1) + fib($n - 2);
}}

my $start = time();
my $iterations = {iterations};

for (my $iter = 0; $iter < $iterations; $iter++) {{
    fib({N});
}}

my $elapsed = (time() - $start) * 1000;
print $elapsed;
'''

    perl_time = run_perl_benchmark(perl_code)
    if perl_time > 0:
        results.append(BenchmarkResult(
            language='Perl 5.42',
            test='fibonacci_25',
            time_ms=perl_time,
            iterations=iterations,
            ops_per_sec=(iterations / perl_time) * 1000
        ))

    # 4. PHP
    php_code = f'''<?php
function fib($n) {{
    if ($n <= 1) return $n;
    return fib($n - 1) + fib($n - 2);
}}

$start = hrtime(true);
$iterations = {iterations};

for ($iter = 0; $iter < $iterations; $iter++) {{
    fib({N});
}}

$end = hrtime(true);
echo ($end - $start) / 1e6;
'''

    php_time = run_php_benchmark(php_code)
    if php_time > 0:
        results.append(BenchmarkResult(
            language='PHP 8.4',
            test='fibonacci_25',
            time_ms=php_time,
            iterations=iterations,
            ops_per_sec=(iterations / php_time) * 1000
        ))

    # 4. Ruby
    ruby_code = f'''
def fib(n)
    return n if n <= 1
    fib(n - 1) + fib(n - 2)
end

start = Process.clock_gettime(Process::CLOCK_MONOTONIC)
iterations = {iterations}

iterations.times do
    fib({N})
end

elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - start
puts elapsed * 1000
'''

    ruby_time = run_ruby_benchmark(ruby_code)
    if ruby_time > 0:
        results.append(BenchmarkResult(
            language='Ruby 3.3',
            test='fibonacci_25',
            time_ms=ruby_time,
            iterations=iterations,
            ops_per_sec=(iterations / ruby_time) * 1000
        ))

    return results


def benchmark_dict_operations(iterations: int = 100) -> List[BenchmarkResult]:
    """Benchmark: Dictionary/Object operations."""
    results = []
    OPS = 1000

    # 1. Python Native
    def python_dict():
        data = {}
        for i in range(OPS):
            data[f'key_{i}'] = {'value': i, 'name': f'item_{i}'}
        total = sum(d['value'] for d in data.values())
        return total

    # Warmup
    for _ in range(3):
        python_dict()

    start = time.perf_counter()
    for _ in range(iterations):
        python_dict()
    python_time = (time.perf_counter() - start) * 1000

    results.append(BenchmarkResult(
        language='Python 3.12',
        test='dict_ops',
        time_ms=python_time,
        iterations=iterations,
        ops_per_sec=(iterations / python_time) * 1000
    ))

    # 2. Lua
    lua_code = f'''
local start = os.clock()
local iterations = {iterations}

for iter = 1, iterations do
    local data = {{}}
    for i = 0, {OPS - 1} do
        data["key_" .. i] = {{ value = i, name = "item_" .. i }}
    end
    local total = 0
    for _, v in pairs(data) do
        total = total + v.value
    end
end

local elapsed = (os.clock() - start) * 1000
print(elapsed)
'''

    lua_time = run_lua_benchmark(lua_code)
    if lua_time > 0:
        results.append(BenchmarkResult(
            language='Lua 5.4',
            test='dict_ops',
            time_ms=lua_time,
            iterations=iterations,
            ops_per_sec=(iterations / lua_time) * 1000
        ))

    # 3. Perl
    perl_code = f'''
use Time::HiRes qw(time);

my $start = time();
my $iterations = {iterations};

for (my $iter = 0; $iter < $iterations; $iter++) {{
    my %data = ();
    for (my $i = 0; $i < {OPS}; $i++) {{
        $data{{"key_$i"}} = {{ value => $i, name => "item_$i" }};
    }}
    my $total = 0;
    foreach my $key (keys %data) {{
        $total += $data{{$key}}{{value}};
    }}
}}

my $elapsed = (time() - $start) * 1000;
print $elapsed;
'''

    perl_time = run_perl_benchmark(perl_code)
    if perl_time > 0:
        results.append(BenchmarkResult(
            language='Perl 5.42',
            test='dict_ops',
            time_ms=perl_time,
            iterations=iterations,
            ops_per_sec=(iterations / perl_time) * 1000
        ))

    # 4. PHP
    php_code = f'''<?php
$start = hrtime(true);
$iterations = {iterations};

for ($iter = 0; $iter < $iterations; $iter++) {{
    $data = [];
    for ($i = 0; $i < {OPS}; $i++) {{
        $data["key_$i"] = ["value" => $i, "name" => "item_$i"];
    }}
    $total = 0;
    foreach ($data as $item) {{
        $total += $item["value"];
    }}
}}

$end = hrtime(true);
echo ($end - $start) / 1e6;
'''

    php_time = run_php_benchmark(php_code)
    if php_time > 0:
        results.append(BenchmarkResult(
            language='PHP 8.4',
            test='dict_ops',
            time_ms=php_time,
            iterations=iterations,
            ops_per_sec=(iterations / php_time) * 1000
        ))

    # 4. Ruby
    ruby_code = f'''
start = Process.clock_gettime(Process::CLOCK_MONOTONIC)
iterations = {iterations}

iterations.times do
    data = {{}}
    {OPS}.times do |i|
        data["key_#{{i}}"] = {{ value: i, name: "item_#{{i}}" }}
    end
    total = data.values.sum {{ |v| v[:value] }}
end

elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - start
puts elapsed * 1000
'''

    ruby_time = run_ruby_benchmark(ruby_code)
    if ruby_time > 0:
        results.append(BenchmarkResult(
            language='Ruby 3.3',
            test='dict_ops',
            time_ms=ruby_time,
            iterations=iterations,
            ops_per_sec=(iterations / ruby_time) * 1000
        ))

    return results


def run_all_benchmarks():
    """Run all benchmarks and display results."""
    print("=" * 80)
    print("CROSS-LANGUAGE PERFORMANCE COMPARISON")
    print("=" * 80)
    print(f"Date: {datetime.now().isoformat()}")
    print()

    all_results: List[BenchmarkResult] = []
    iterations = 50  # Fewer iterations for faster results

    benchmarks = [
        ('Loop 100k iterations', benchmark_loop_accumulation),
        ('String/HTML Building', benchmark_string_building),
        ('Fibonacci(25) Recursive', benchmark_fibonacci),
        ('Dictionary Operations', benchmark_dict_operations),
    ]

    for name, func in benchmarks:
        print(f"Running: {name}...", flush=True)
        try:
            results = func(iterations)
            all_results.extend(results)
            print(f"  Done ({len(results)} languages)")
        except Exception as e:
            print(f"  ERROR: {e}")

    # Group by test
    tests = {}
    for r in all_results:
        if r.test not in tests:
            tests[r.test] = []
        tests[r.test].append(r)

    # Print results by test
    print()
    print("=" * 80)
    print("RESULTS BY TEST")
    print("=" * 80)

    for test_name, results in tests.items():
        print(f"\n{test_name.upper()}")
        print("-" * 60)

        # Sort by time
        results.sort(key=lambda x: x.time_ms)
        fastest = results[0].time_ms

        print(f"{'Language':<25} {'Time (ms)':<15} {'Ops/sec':<15} {'vs Fastest':<10}")
        print("-" * 60)

        for r in results:
            ratio = r.time_ms / fastest if fastest > 0 else 0
            print(f"{r.language:<25} {r.time_ms:>12.2f}ms {r.ops_per_sec:>12.1f} {ratio:>8.1f}x")

    # Summary table
    print()
    print("=" * 80)
    print("SUMMARY - AVERAGE PERFORMANCE")
    print("=" * 80)

    # Calculate averages by language
    lang_totals: Dict[str, List[float]] = {}
    for r in all_results:
        if r.language not in lang_totals:
            lang_totals[r.language] = []
        lang_totals[r.language].append(r.time_ms)

    lang_averages = [(lang, sum(times) / len(times)) for lang, times in lang_totals.items()]
    lang_averages.sort(key=lambda x: x[1])

    if lang_averages:
        fastest_avg = lang_averages[0][1]

        print(f"\n{'Language':<25} {'Avg Time (ms)':<15} {'Relative Speed':<15}")
        print("-" * 55)

        for lang, avg_time in lang_averages:
            ratio = avg_time / fastest_avg if fastest_avg > 0 else 0
            speed = fastest_avg / avg_time if avg_time > 0 else 0
            bar = "█" * int(min(speed * 10, 50))
            print(f"{lang:<25} {avg_time:>12.2f}ms {ratio:>8.1f}x slower")

    # Save results
    output_dir = Path(__file__).parent
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'language_comparison_{timestamp}.json'

    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': [asdict(r) for r in all_results]
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == '__main__':
    run_all_benchmarks()
