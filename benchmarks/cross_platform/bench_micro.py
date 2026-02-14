#!/usr/bin/env python
"""
Cross-Platform Micro-Benchmarks

Compares raw performance of equivalent operations across languages.
This script generates and runs equivalent code in multiple languages.

Run: python benchmarks/cross_platform/bench_micro.py
"""

import sys
import os
import time
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


@dataclass
class BenchmarkResult:
    """Result of a single benchmark"""
    language: str
    test_name: str
    iterations: int
    total_time_ms: float
    avg_time_us: float
    ops_per_sec: float
    success: bool = True
    error: str = ""


@dataclass
class LanguageInfo:
    """Information about a language/runtime"""
    name: str
    command: str
    version_cmd: str
    available: bool = False
    version: str = ""


# =============================================================================
# Language Detection
# =============================================================================

def check_language(cmd: str, version_cmd: str) -> Tuple[bool, str]:
    """Check if a language/runtime is available"""
    try:
        result = subprocess.run(
            version_cmd.split(),
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            return True, version
        return False, ""
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return False, ""


def detect_languages() -> Dict[str, LanguageInfo]:
    """Detect available languages on the system"""
    languages = {
        'python': LanguageInfo('Python', 'python', 'python --version'),
        'node': LanguageInfo('Node.js', 'node', 'node --version'),
        'php': LanguageInfo('PHP', 'php', 'php --version'),
        'ruby': LanguageInfo('Ruby', 'ruby', 'ruby --version'),
        'perl': LanguageInfo('Perl', 'perl', 'perl --version'),
        'java': LanguageInfo('Java', 'java', 'java --version'),
    }

    for key, info in languages.items():
        info.available, info.version = check_language(info.command, info.version_cmd)

    return languages


# =============================================================================
# Benchmark Code Templates
# =============================================================================

# Test 1: Simple Loop
LOOP_BENCHMARKS = {
    'python': '''
import time
iterations = {iterations}
start = time.perf_counter()
total = 0
for i in range(iterations):
    total += i
elapsed = (time.perf_counter() - start) * 1000
print(f"{{elapsed:.6f}}")
''',

    'node': '''
const iterations = {iterations};
const start = process.hrtime.bigint();
let total = 0;
for (let i = 0; i < iterations; i++) {{
    total += i;
}}
const elapsed = Number(process.hrtime.bigint() - start) / 1000000;
console.log(elapsed.toFixed(6));
''',

    'php': '''<?php
$iterations = {iterations};
$start = microtime(true);
$total = 0;
for ($i = 0; $i < $iterations; $i++) {{
    $total += $i;
}}
$elapsed = (microtime(true) - $start) * 1000;
echo number_format($elapsed, 6);
''',

    'ruby': '''
iterations = {iterations}
start = Process.clock_gettime(Process::CLOCK_MONOTONIC)
total = 0
iterations.times do |i|
  total += i
end
elapsed = (Process.clock_gettime(Process::CLOCK_MONOTONIC) - start) * 1000
puts format("%.6f", elapsed)
''',

    'perl': '''
use Time::HiRes qw(time);
my $iterations = {iterations};
my $start = time();
my $total = 0;
for (my $i = 0; $i < $iterations; $i++) {{
    $total += $i;
}}
my $elapsed = (time() - $start) * 1000;
printf("%.6f\\n", $elapsed);
''',

    'java': '''
public class Benchmark {{
    public static void main(String[] args) {{
        int iterations = {iterations};
        long start = System.nanoTime();
        long total = 0;
        for (int i = 0; i < iterations; i++) {{
            total += i;
        }}
        double elapsed = (System.nanoTime() - start) / 1000000.0;
        System.out.printf("%.6f%n", elapsed);
    }}
}}
'''
}

# Test 2: String Concatenation
STRING_BENCHMARKS = {
    'python': '''
import time
iterations = {iterations}
start = time.perf_counter()
result = ""
for i in range(iterations):
    result = f"Item {{i}}: value"
elapsed = (time.perf_counter() - start) * 1000
print(f"{{elapsed:.6f}}")
''',

    'node': '''
const iterations = {iterations};
const start = process.hrtime.bigint();
let result = "";
for (let i = 0; i < iterations; i++) {{
    result = `Item ${{i}}: value`;
}}
const elapsed = Number(process.hrtime.bigint() - start) / 1000000;
console.log(elapsed.toFixed(6));
''',

    'php': '''<?php
$iterations = {iterations};
$start = microtime(true);
$result = "";
for ($i = 0; $i < $iterations; $i++) {{
    $result = "Item $i: value";
}}
$elapsed = (microtime(true) - $start) * 1000;
echo number_format($elapsed, 6);
''',

    'ruby': '''
iterations = {iterations}
start = Process.clock_gettime(Process::CLOCK_MONOTONIC)
result = ""
iterations.times do |i|
  result = "Item #{{i}}: value"
end
elapsed = (Process.clock_gettime(Process::CLOCK_MONOTONIC) - start) * 1000
puts format("%.6f", elapsed)
''',

    'perl': '''
use Time::HiRes qw(time);
my $iterations = {iterations};
my $start = time();
my $result = "";
for (my $i = 0; $i < $iterations; $i++) {{
    $result = "Item $i: value";
}}
my $elapsed = (time() - $start) * 1000;
printf("%.6f\\n", $elapsed);
''',

    'java': '''
public class Benchmark {{
    public static void main(String[] args) {{
        int iterations = {iterations};
        long start = System.nanoTime();
        String result = "";
        for (int i = 0; i < iterations; i++) {{
            result = String.format("Item %d: value", i);
        }}
        double elapsed = (System.nanoTime() - start) / 1000000.0;
        System.out.printf("%.6f%n", elapsed);
    }}
}}
'''
}

# Test 3: Dictionary/Hash Operations
DICT_BENCHMARKS = {
    'python': '''
import time
iterations = {iterations}
start = time.perf_counter()
data = {{}}
for i in range(iterations):
    data[f"key_{{i}}"] = i * 2
    _ = data.get(f"key_{{i // 2}}", 0)
elapsed = (time.perf_counter() - start) * 1000
print(f"{{elapsed:.6f}}")
''',

    'node': '''
const iterations = {iterations};
const start = process.hrtime.bigint();
const data = {{}};
for (let i = 0; i < iterations; i++) {{
    data[`key_${{i}}`] = i * 2;
    const _ = data[`key_${{Math.floor(i / 2)}}`] || 0;
}}
const elapsed = Number(process.hrtime.bigint() - start) / 1000000;
console.log(elapsed.toFixed(6));
''',

    'php': '''<?php
$iterations = {iterations};
$start = microtime(true);
$data = [];
for ($i = 0; $i < $iterations; $i++) {{
    $data["key_$i"] = $i * 2;
    $_ = $data["key_" . intdiv($i, 2)] ?? 0;
}}
$elapsed = (microtime(true) - $start) * 1000;
echo number_format($elapsed, 6);
''',

    'ruby': '''
iterations = {iterations}
start = Process.clock_gettime(Process::CLOCK_MONOTONIC)
data = {{}}
iterations.times do |i|
  data["key_#{{i}}"] = i * 2
  _ = data["key_#{{i / 2}}"] || 0
end
elapsed = (Process.clock_gettime(Process::CLOCK_MONOTONIC) - start) * 1000
puts format("%.6f", elapsed)
''',

    'perl': '''
use Time::HiRes qw(time);
my $iterations = {iterations};
my $start = time();
my %data = ();
for (my $i = 0; $i < $iterations; $i++) {{
    $data{{"key_$i"}} = $i * 2;
    my $_ = $data{{"key_" . int($i / 2)}} // 0;
}}
my $elapsed = (time() - $start) * 1000;
printf("%.6f\\n", $elapsed);
''',

    'java': '''
import java.util.HashMap;
public class Benchmark {{
    public static void main(String[] args) {{
        int iterations = {iterations};
        long start = System.nanoTime();
        HashMap<String, Integer> data = new HashMap<>();
        for (int i = 0; i < iterations; i++) {{
            data.put("key_" + i, i * 2);
            Integer _ = data.getOrDefault("key_" + (i / 2), 0);
        }}
        double elapsed = (System.nanoTime() - start) / 1000000.0;
        System.out.printf("%.6f%n", elapsed);
    }}
}}
'''
}

# Test 4: JSON Operations
JSON_BENCHMARKS = {
    'python': '''
import time
import json
iterations = {iterations}
data = {{"name": "test", "value": 42, "items": [1, 2, 3, 4, 5]}}
start = time.perf_counter()
for i in range(iterations):
    s = json.dumps(data)
    d = json.loads(s)
elapsed = (time.perf_counter() - start) * 1000
print(f"{{elapsed:.6f}}")
''',

    'node': '''
const iterations = {iterations};
const data = {{"name": "test", "value": 42, "items": [1, 2, 3, 4, 5]}};
const start = process.hrtime.bigint();
for (let i = 0; i < iterations; i++) {{
    const s = JSON.stringify(data);
    const d = JSON.parse(s);
}}
const elapsed = Number(process.hrtime.bigint() - start) / 1000000;
console.log(elapsed.toFixed(6));
''',

    'php': '''<?php
$iterations = {iterations};
$data = ["name" => "test", "value" => 42, "items" => [1, 2, 3, 4, 5]];
$start = microtime(true);
for ($i = 0; $i < $iterations; $i++) {{
    $s = json_encode($data);
    $d = json_decode($s, true);
}}
$elapsed = (microtime(true) - $start) * 1000;
echo number_format($elapsed, 6);
''',

    'ruby': '''
require 'json'
iterations = {iterations}
data = {{"name" => "test", "value" => 42, "items" => [1, 2, 3, 4, 5]}}
start = Process.clock_gettime(Process::CLOCK_MONOTONIC)
iterations.times do
  s = JSON.generate(data)
  d = JSON.parse(s)
end
elapsed = (Process.clock_gettime(Process::CLOCK_MONOTONIC) - start) * 1000
puts format("%.6f", elapsed)
''',

    'perl': '''
use Time::HiRes qw(time);
use JSON;
my $iterations = {iterations};
my $data = {{"name" => "test", "value" => 42, "items" => [1, 2, 3, 4, 5]}};
my $json = JSON->new;
my $start = time();
for (my $i = 0; $i < $iterations; $i++) {{
    my $s = $json->encode($data);
    my $d = $json->decode($s);
}}
my $elapsed = (time() - $start) * 1000;
printf("%.6f\\n", $elapsed);
''',

    'java': '''
import com.google.gson.Gson;
import java.util.*;
public class Benchmark {{
    public static void main(String[] args) {{
        int iterations = {iterations};
        Gson gson = new Gson();
        Map<String, Object> data = new HashMap<>();
        data.put("name", "test");
        data.put("value", 42);
        data.put("items", Arrays.asList(1, 2, 3, 4, 5));
        long start = System.nanoTime();
        for (int i = 0; i < iterations; i++) {{
            String s = gson.toJson(data);
            Map d = gson.fromJson(s, Map.class);
        }}
        double elapsed = (System.nanoTime() - start) / 1000000.0;
        System.out.printf("%.6f%n", elapsed);
    }}
}}
'''
}

# Test 5: Conditionals
CONDITIONAL_BENCHMARKS = {
    'python': '''
import time
iterations = {iterations}
start = time.perf_counter()
count = 0
for i in range(iterations):
    if i % 15 == 0:
        count += 3
    elif i % 5 == 0:
        count += 2
    elif i % 3 == 0:
        count += 1
    else:
        count += 0
elapsed = (time.perf_counter() - start) * 1000
print(f"{{elapsed:.6f}}")
''',

    'node': '''
const iterations = {iterations};
const start = process.hrtime.bigint();
let count = 0;
for (let i = 0; i < iterations; i++) {{
    if (i % 15 === 0) {{
        count += 3;
    }} else if (i % 5 === 0) {{
        count += 2;
    }} else if (i % 3 === 0) {{
        count += 1;
    }} else {{
        count += 0;
    }}
}}
const elapsed = Number(process.hrtime.bigint() - start) / 1000000;
console.log(elapsed.toFixed(6));
''',

    'php': '''<?php
$iterations = {iterations};
$start = microtime(true);
$count = 0;
for ($i = 0; $i < $iterations; $i++) {{
    if ($i % 15 == 0) {{
        $count += 3;
    }} elseif ($i % 5 == 0) {{
        $count += 2;
    }} elseif ($i % 3 == 0) {{
        $count += 1;
    }} else {{
        $count += 0;
    }}
}}
$elapsed = (microtime(true) - $start) * 1000;
echo number_format($elapsed, 6);
''',

    'ruby': '''
iterations = {iterations}
start = Process.clock_gettime(Process::CLOCK_MONOTONIC)
count = 0
iterations.times do |i|
  if i % 15 == 0
    count += 3
  elsif i % 5 == 0
    count += 2
  elsif i % 3 == 0
    count += 1
  else
    count += 0
  end
end
elapsed = (Process.clock_gettime(Process::CLOCK_MONOTONIC) - start) * 1000
puts format("%.6f", elapsed)
''',

    'perl': '''
use Time::HiRes qw(time);
my $iterations = {iterations};
my $start = time();
my $count = 0;
for (my $i = 0; $i < $iterations; $i++) {{
    if ($i % 15 == 0) {{
        $count += 3;
    }} elsif ($i % 5 == 0) {{
        $count += 2;
    }} elsif ($i % 3 == 0) {{
        $count += 1;
    }} else {{
        $count += 0;
    }}
}}
my $elapsed = (time() - $start) * 1000;
printf("%.6f\\n", $elapsed);
''',

    'java': '''
public class Benchmark {{
    public static void main(String[] args) {{
        int iterations = {iterations};
        long start = System.nanoTime();
        int count = 0;
        for (int i = 0; i < iterations; i++) {{
            if (i % 15 == 0) {{
                count += 3;
            }} else if (i % 5 == 0) {{
                count += 2;
            }} else if (i % 3 == 0) {{
                count += 1;
            }} else {{
                count += 0;
            }}
        }}
        double elapsed = (System.nanoTime() - start) / 1000000.0;
        System.out.printf("%.6f%n", elapsed);
    }}
}}
'''
}


# =============================================================================
# Quantum Benchmarks (using the actual framework)
# =============================================================================

def run_quantum_benchmark(test_name: str, iterations: int) -> BenchmarkResult:
    """Run benchmark using Quantum Framework"""
    try:
        from runtime.component import ComponentRuntime
        from core.parser import QuantumParser

        parser = QuantumParser()

        if test_name == 'loop':
            # Quantum loop benchmark
            source = f'''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="LoopBench">
    <q:set name="total" value="0" />
    <q:loop from="0" to="{iterations - 1}" var="i">
        <q:set name="total" value="{{total + i}}" />
    </q:loop>
</q:component>
'''
        elif test_name == 'string':
            source = f'''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="StringBench">
    <q:set name="result" value="" />
    <q:loop from="0" to="{iterations - 1}" var="i">
        <q:set name="result" value="Item {{i}}: value" />
    </q:loop>
</q:component>
'''
        elif test_name == 'conditional':
            source = f'''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="CondBench">
    <q:set name="count" value="0" />
    <q:loop from="0" to="{iterations - 1}" var="i">
        <q:if condition="{{i % 15 == 0}}">
            <q:set name="count" value="{{count + 3}}" />
        </q:if>
        <q:elseif condition="{{i % 5 == 0}}">
            <q:set name="count" value="{{count + 2}}" />
        </q:elseif>
        <q:elseif condition="{{i % 3 == 0}}">
            <q:set name="count" value="{{count + 1}}" />
        </q:elseif>
    </q:loop>
</q:component>
'''
        else:
            return BenchmarkResult(
                language='Quantum',
                test_name=test_name,
                iterations=iterations,
                total_time_ms=0,
                avg_time_us=0,
                ops_per_sec=0,
                success=False,
                error=f"Unknown test: {test_name}"
            )

        # Parse and execute
        start = time.perf_counter()
        ast = parser.parse(source)
        runtime = ComponentRuntime()
        runtime.execute_component(ast)
        elapsed_ms = (time.perf_counter() - start) * 1000

        return BenchmarkResult(
            language='Quantum',
            test_name=test_name,
            iterations=iterations,
            total_time_ms=elapsed_ms,
            avg_time_us=(elapsed_ms * 1000) / iterations,
            ops_per_sec=iterations / (elapsed_ms / 1000) if elapsed_ms > 0 else 0,
            success=True
        )

    except Exception as e:
        return BenchmarkResult(
            language='Quantum',
            test_name=test_name,
            iterations=iterations,
            total_time_ms=0,
            avg_time_us=0,
            ops_per_sec=0,
            success=False,
            error=str(e)
        )


# =============================================================================
# Benchmark Runner
# =============================================================================

def run_benchmark(language: str, code: str, lang_info: LanguageInfo) -> Optional[float]:
    """Run a benchmark for a specific language and return time in ms"""
    if not lang_info.available:
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            if language == 'python':
                filepath = os.path.join(tmpdir, 'bench.py')
                with open(filepath, 'w') as f:
                    f.write(code)
                result = subprocess.run(
                    ['python', filepath],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

            elif language == 'node':
                filepath = os.path.join(tmpdir, 'bench.js')
                with open(filepath, 'w') as f:
                    f.write(code)
                result = subprocess.run(
                    ['node', filepath],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

            elif language == 'php':
                filepath = os.path.join(tmpdir, 'bench.php')
                with open(filepath, 'w') as f:
                    f.write(code)
                result = subprocess.run(
                    ['php', filepath],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

            elif language == 'ruby':
                filepath = os.path.join(tmpdir, 'bench.rb')
                with open(filepath, 'w') as f:
                    f.write(code)
                result = subprocess.run(
                    ['ruby', filepath],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

            elif language == 'perl':
                filepath = os.path.join(tmpdir, 'bench.pl')
                with open(filepath, 'w') as f:
                    f.write(code)
                result = subprocess.run(
                    ['perl', filepath],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

            elif language == 'java':
                filepath = os.path.join(tmpdir, 'Benchmark.java')
                with open(filepath, 'w') as f:
                    f.write(code)
                # Compile
                compile_result = subprocess.run(
                    ['javac', filepath],
                    capture_output=True,
                    cwd=tmpdir,
                    timeout=30
                )
                if compile_result.returncode != 0:
                    return None
                # Run
                result = subprocess.run(
                    ['java', 'Benchmark'],
                    capture_output=True,
                    text=True,
                    cwd=tmpdir,
                    timeout=60
                )

            else:
                return None

            if result.returncode == 0:
                return float(result.stdout.strip())
            return None

        except (subprocess.TimeoutExpired, ValueError, Exception):
            return None


def run_benchmark_suite(test_name: str, templates: Dict[str, str], iterations: int,
                        languages: Dict[str, LanguageInfo]) -> List[BenchmarkResult]:
    """Run a benchmark suite across all available languages"""
    results = []

    # Run Quantum benchmark
    quantum_result = run_quantum_benchmark(test_name, iterations)
    results.append(quantum_result)

    # Run other languages
    for lang_key, template in templates.items():
        lang_info = languages.get(lang_key)
        if lang_info and lang_info.available:
            code = template.format(iterations=iterations)
            elapsed_ms = run_benchmark(lang_key, code, lang_info)

            if elapsed_ms is not None:
                results.append(BenchmarkResult(
                    language=lang_info.name,
                    test_name=test_name,
                    iterations=iterations,
                    total_time_ms=elapsed_ms,
                    avg_time_us=(elapsed_ms * 1000) / iterations,
                    ops_per_sec=iterations / (elapsed_ms / 1000) if elapsed_ms > 0 else 0,
                    success=True
                ))
            else:
                results.append(BenchmarkResult(
                    language=lang_info.name,
                    test_name=test_name,
                    iterations=iterations,
                    total_time_ms=0,
                    avg_time_us=0,
                    ops_per_sec=0,
                    success=False,
                    error="Execution failed"
                ))

    return results


# =============================================================================
# Main Execution
# =============================================================================

def format_time(ms: float) -> str:
    """Format time nicely"""
    if ms < 0.001:
        return f"{ms * 1000000:.1f} ns"
    elif ms < 1:
        return f"{ms * 1000:.2f} µs"
    elif ms < 1000:
        return f"{ms:.2f} ms"
    else:
        return f"{ms / 1000:.2f} s"


def print_results_table(results: List[BenchmarkResult], test_name: str):
    """Print results in a formatted table"""
    # Sort by total time
    sorted_results = sorted(
        [r for r in results if r.success],
        key=lambda x: x.total_time_ms
    )

    if not sorted_results:
        print(f"\n  No successful results for {test_name}")
        return

    fastest = sorted_results[0].total_time_ms

    print(f"\n  {'Language':<15} {'Time':>12} {'Ops/sec':>15} {'vs Fastest':>12}")
    print(f"  {'-' * 54}")

    for r in sorted_results:
        ratio = r.total_time_ms / fastest if fastest > 0 else 0
        ratio_str = f"{ratio:.1f}x" if ratio > 1 else "fastest"
        print(f"  {r.language:<15} {format_time(r.total_time_ms):>12} {r.ops_per_sec:>15,.0f} {ratio_str:>12}")

    # Show failed
    failed = [r for r in results if not r.success]
    if failed:
        print(f"\n  Failed: {', '.join(r.language for r in failed)}")


def main():
    print("\n" + "=" * 70)
    print("  QUANTUM FRAMEWORK - CROSS-PLATFORM MICRO-BENCHMARKS")
    print("=" * 70)

    # Detect languages
    print("\n  Detecting available languages...")
    languages = detect_languages()

    available = [f"{info.name} ({info.version})" for info in languages.values() if info.available]
    unavailable = [info.name for info in languages.values() if not info.available]

    print(f"\n  Available: {', '.join(available) if available else 'None'}")
    if unavailable:
        print(f"  Not found: {', '.join(unavailable)}")

    # Always show Quantum
    print(f"  Quantum: Always available (this framework)")

    # Benchmark configurations
    benchmarks = [
        ('Loop (simple addition)', 'loop', LOOP_BENCHMARKS, 100000),
        ('String interpolation', 'string', STRING_BENCHMARKS, 50000),
        ('Dictionary operations', 'dict', DICT_BENCHMARKS, 50000),
        ('Conditionals (FizzBuzz)', 'conditional', CONDITIONAL_BENCHMARKS, 100000),
        ('JSON parse/serialize', 'json', JSON_BENCHMARKS, 10000),
    ]

    all_results = []

    for title, test_name, templates, iterations in benchmarks:
        print("\n" + "-" * 70)
        print(f"  {title} ({iterations:,} iterations)")
        print("-" * 70)

        results = run_benchmark_suite(test_name, templates, iterations, languages)
        all_results.extend(results)
        print_results_table(results, test_name)

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY - AVERAGE PERFORMANCE RATIO")
    print("=" * 70)

    # Calculate average ratios per language
    lang_ratios = {}
    for r in all_results:
        if r.success:
            if r.language not in lang_ratios:
                lang_ratios[r.language] = []
            # Find fastest for this test
            same_test = [x for x in all_results if x.test_name == r.test_name and x.success]
            if same_test:
                fastest = min(x.total_time_ms for x in same_test)
                if fastest > 0:
                    lang_ratios[r.language].append(r.total_time_ms / fastest)

    print(f"\n  {'Language':<15} {'Avg Ratio':>12} {'Interpretation':>25}")
    print(f"  {'-' * 52}")

    sorted_langs = sorted(lang_ratios.items(), key=lambda x: sum(x[1]) / len(x[1]) if x[1] else 999)
    for lang, ratios in sorted_langs:
        if ratios:
            avg_ratio = sum(ratios) / len(ratios)
            interpretation = "fastest" if avg_ratio < 1.1 else f"{avg_ratio:.1f}x slower"
            print(f"  {lang:<15} {avg_ratio:>11.1f}x {interpretation:>25}")

    # Save results
    results_dir = Path(__file__).parent.parent / 'results'
    results_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = results_dir / f'cross_platform_micro_{timestamp}.json'

    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'languages': {k: asdict(v) for k, v in languages.items()},
            'results': [asdict(r) for r in all_results]
        }, f, indent=2)

    print(f"\n  Results saved to: {results_file}")
    print("=" * 70)


if __name__ == '__main__':
    main()
