"""
Cross-Language JSON Processing Benchmark
=========================================

Compares JSON parsing and serialization across:
- Python (native json)
- PHP (json_encode/decode)
- Ruby (JSON module)
- Perl (JSON module)
- Lua (cjson/dkjson)
"""

import sys
import time
import statistics
import subprocess
import tempfile
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List

# Language interpreters
PHP_PATH = r"C:\Users\danie\AppData\Local\Microsoft\WinGet\Packages\PHP.PHP.8.4_Microsoft.Winget.Source_8wekyb3d8bbwe\php.exe"
RUBY_PATH = r"C:\Ruby33-x64\bin\ruby.exe"
LUA_PATH = r"C:\Users\danie\AppData\Local\Programs\Lua\bin\lua.exe"
PERL_PATH = r"C:\Strawberry\perl\bin\perl.exe"


@dataclass
class JSONComparisonResult:
    language: str
    operation: str
    avg_time_ms: float
    ops_per_second: float
    iterations: int


def benchmark_python_json_parse(iterations: int = 1000) -> JSONComparisonResult:
    """Benchmark Python JSON parsing"""
    data = json.dumps({"users": [{"id": i, "name": f"User {i}", "email": f"user{i}@test.com"} for i in range(100)]})

    # Warmup
    for _ in range(100):
        json.loads(data)

    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        json.loads(data)
        times.append((time.perf_counter_ns() - start) / 1_000_000)

    avg = statistics.mean(times)
    return JSONComparisonResult(
        language="Python 3.12",
        operation="JSON Parse (100 objects)",
        avg_time_ms=avg,
        ops_per_second=1000/avg if avg > 0 else 0,
        iterations=iterations
    )


def benchmark_python_json_serialize(iterations: int = 1000) -> JSONComparisonResult:
    """Benchmark Python JSON serialization"""
    data = {"users": [{"id": i, "name": f"User {i}", "email": f"user{i}@test.com"} for i in range(100)]}

    # Warmup
    for _ in range(100):
        json.dumps(data)

    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        json.dumps(data)
        times.append((time.perf_counter_ns() - start) / 1_000_000)

    avg = statistics.mean(times)
    return JSONComparisonResult(
        language="Python 3.12",
        operation="JSON Serialize (100 objects)",
        avg_time_ms=avg,
        ops_per_second=1000/avg if avg > 0 else 0,
        iterations=iterations
    )


def benchmark_php_json_parse(iterations: int = 1000) -> JSONComparisonResult:
    """Benchmark PHP JSON parsing"""
    php_code = f'''<?php
$iterations = {iterations};
$users = [];
for ($i = 0; $i < 100; $i++) {{
    $users[] = ["id" => $i, "name" => "User $i", "email" => "user$i@test.com"];
}}
$json = json_encode(["users" => $users]);

// Warmup
for ($i = 0; $i < 100; $i++) {{
    json_decode($json, true);
}}

// Benchmark
$times = [];
for ($i = 0; $i < $iterations; $i++) {{
    $start = hrtime(true);
    json_decode($json, true);
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
        return JSONComparisonResult(
            language="PHP 8.4",
            operation="JSON Parse (100 objects)",
            avg_time_ms=avg,
            ops_per_second=1000/avg if avg > 0 else 0,
            iterations=iterations
        )
    finally:
        Path(php_file).unlink(missing_ok=True)


def benchmark_php_json_serialize(iterations: int = 1000) -> JSONComparisonResult:
    """Benchmark PHP JSON serialization"""
    php_code = f'''<?php
$iterations = {iterations};
$users = [];
for ($i = 0; $i < 100; $i++) {{
    $users[] = ["id" => $i, "name" => "User $i", "email" => "user$i@test.com"];
}}
$data = ["users" => $users];

// Warmup
for ($i = 0; $i < 100; $i++) {{
    json_encode($data);
}}

// Benchmark
$times = [];
for ($i = 0; $i < $iterations; $i++) {{
    $start = hrtime(true);
    json_encode($data);
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
        return JSONComparisonResult(
            language="PHP 8.4",
            operation="JSON Serialize (100 objects)",
            avg_time_ms=avg,
            ops_per_second=1000/avg if avg > 0 else 0,
            iterations=iterations
        )
    finally:
        Path(php_file).unlink(missing_ok=True)


def benchmark_ruby_json_parse(iterations: int = 1000) -> JSONComparisonResult:
    """Benchmark Ruby JSON parsing"""
    ruby_code = f'''
require 'json'

iterations = {iterations}
users = (0...100).map {{ |i| {{id: i, name: "User #{{i}}", email: "user#{{i}}@test.com"}} }}
json = JSON.generate({{users: users}})

# Warmup
100.times {{ JSON.parse(json) }}

# Benchmark
times = []
iterations.times do
  start = Process.clock_gettime(Process::CLOCK_MONOTONIC, :nanosecond)
  JSON.parse(json)
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
        return JSONComparisonResult(
            language="Ruby 3.3",
            operation="JSON Parse (100 objects)",
            avg_time_ms=avg,
            ops_per_second=1000/avg if avg > 0 else 0,
            iterations=iterations
        )
    finally:
        Path(ruby_file).unlink(missing_ok=True)


def benchmark_ruby_json_serialize(iterations: int = 1000) -> JSONComparisonResult:
    """Benchmark Ruby JSON serialization"""
    ruby_code = f'''
require 'json'

iterations = {iterations}
users = (0...100).map {{ |i| {{id: i, name: "User #{{i}}", email: "user#{{i}}@test.com"}} }}
data = {{users: users}}

# Warmup
100.times {{ JSON.generate(data) }}

# Benchmark
times = []
iterations.times do
  start = Process.clock_gettime(Process::CLOCK_MONOTONIC, :nanosecond)
  JSON.generate(data)
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
        return JSONComparisonResult(
            language="Ruby 3.3",
            operation="JSON Serialize (100 objects)",
            avg_time_ms=avg,
            ops_per_second=1000/avg if avg > 0 else 0,
            iterations=iterations
        )
    finally:
        Path(ruby_file).unlink(missing_ok=True)


def benchmark_perl_json_parse(iterations: int = 1000) -> JSONComparisonResult:
    """Benchmark Perl JSON parsing"""
    perl_code = f'''
use strict;
use warnings;
use JSON;
use Time::HiRes qw(time);

my $iterations = {iterations};
my @users;
for my $i (0..99) {{
    push @users, {{id => $i, name => "User $i", email => "user$i\\@test.com"}};
}}
my $json = encode_json({{users => \\@users}});

# Warmup
for (1..100) {{
    decode_json($json);
}}

# Benchmark
my @times;
for (1..$iterations) {{
    my $start = time();
    decode_json($json);
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
        return JSONComparisonResult(
            language="Perl 5.42",
            operation="JSON Parse (100 objects)",
            avg_time_ms=avg,
            ops_per_second=1000/avg if avg > 0 else 0,
            iterations=iterations
        )
    finally:
        Path(perl_file).unlink(missing_ok=True)


def benchmark_perl_json_serialize(iterations: int = 1000) -> JSONComparisonResult:
    """Benchmark Perl JSON serialization"""
    perl_code = f'''
use strict;
use warnings;
use JSON;
use Time::HiRes qw(time);

my $iterations = {iterations};
my @users;
for my $i (0..99) {{
    push @users, {{id => $i, name => "User $i", email => "user$i\\@test.com"}};
}}
my $data = {{users => \\@users}};

# Warmup
for (1..100) {{
    encode_json($data);
}}

# Benchmark
my @times;
for (1..$iterations) {{
    my $start = time();
    encode_json($data);
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
        return JSONComparisonResult(
            language="Perl 5.42",
            operation="JSON Serialize (100 objects)",
            avg_time_ms=avg,
            ops_per_second=1000/avg if avg > 0 else 0,
            iterations=iterations
        )
    finally:
        Path(perl_file).unlink(missing_ok=True)


def run_all_benchmarks():
    """Run all JSON comparison benchmarks"""
    print("=" * 70)
    print("Cross-Language JSON Processing Benchmark")
    print("=" * 70)
    print("\nTest: Parse and serialize JSON with 100 user objects\n")

    parse_results: List[JSONComparisonResult] = []
    serialize_results: List[JSONComparisonResult] = []

    # JSON Parse benchmarks
    print("[JSON Parsing]")
    parse_benchmarks = [
        ("Python 3.12", benchmark_python_json_parse),
        ("PHP 8.4", benchmark_php_json_parse),
        ("Ruby 3.3", benchmark_ruby_json_parse),
        ("Perl 5.42", benchmark_perl_json_parse),
    ]

    for name, bench_func in parse_benchmarks:
        try:
            print(f"  Testing {name}...", end=" ", flush=True)
            result = bench_func()
            parse_results.append(result)
            print(f"{result.avg_time_ms:.4f}ms ({result.ops_per_second:.0f} ops/sec)")
        except Exception as e:
            print(f"ERROR: {e}")

    # JSON Serialize benchmarks
    print("\n[JSON Serialization]")
    serialize_benchmarks = [
        ("Python 3.12", benchmark_python_json_serialize),
        ("PHP 8.4", benchmark_php_json_serialize),
        ("Ruby 3.3", benchmark_ruby_json_serialize),
        ("Perl 5.42", benchmark_perl_json_serialize),
    ]

    for name, bench_func in serialize_benchmarks:
        try:
            print(f"  Testing {name}...", end=" ", flush=True)
            result = bench_func()
            serialize_results.append(result)
            print(f"{result.avg_time_ms:.4f}ms ({result.ops_per_second:.0f} ops/sec)")
        except Exception as e:
            print(f"ERROR: {e}")

    # Sort by performance
    parse_results.sort(key=lambda r: r.avg_time_ms)
    serialize_results.sort(key=lambda r: r.avg_time_ms)

    # Print rankings
    print("\n" + "=" * 70)
    print("JSON Parse Rankings (100 objects)")
    print("=" * 70)
    print(f"\n{'Rank':<6} {'Language':<15} {'Avg Time (ms)':<15} {'Ops/sec':<12} {'vs Fastest':<10}")
    print("-" * 70)

    fastest = parse_results[0].avg_time_ms if parse_results else 1
    for i, r in enumerate(parse_results, 1):
        relative = r.avg_time_ms / fastest
        print(f"{i:<6} {r.language:<15} {r.avg_time_ms:<15.4f} {r.ops_per_second:<12.0f} {relative:.1f}x")

    print("\n" + "=" * 70)
    print("JSON Serialize Rankings (100 objects)")
    print("=" * 70)
    print(f"\n{'Rank':<6} {'Language':<15} {'Avg Time (ms)':<15} {'Ops/sec':<12} {'vs Fastest':<10}")
    print("-" * 70)

    fastest = serialize_results[0].avg_time_ms if serialize_results else 1
    for i, r in enumerate(serialize_results, 1):
        relative = r.avg_time_ms / fastest
        print(f"{i:<6} {r.language:<15} {r.avg_time_ms:<15.4f} {r.ops_per_second:<12.0f} {relative:.1f}x")

    return parse_results, serialize_results


if __name__ == "__main__":
    run_all_benchmarks()
