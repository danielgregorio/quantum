"""
Cross-Language Database Access Benchmark
=========================================

Compares SQLite database performance across:
- Quantum (via DatabaseService)
- Python (native sqlite3)
- PHP
- Ruby
- Lua
- Perl
"""

import sys
import time
import statistics
import subprocess
import tempfile
import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Language interpreters
PHP_PATH = r"C:\Users\danie\AppData\Local\Microsoft\WinGet\Packages\PHP.PHP.8.4_Microsoft.Winget.Source_8wekyb3d8bbwe\php.exe"
RUBY_PATH = r"C:\Ruby33-x64\bin\ruby.exe"
LUA_PATH = r"C:\Users\danie\AppData\Local\Programs\Lua\bin\lua.exe"
PERL_PATH = r"C:\Strawberry\perl\bin\perl.exe"


@dataclass
class DBComparisonResult:
    language: str
    operation: str
    avg_time_ms: float
    ops_per_second: float
    iterations: int


def create_test_database(path: str, num_records: int = 1000):
    """Create test database with sample data"""
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            status INTEGER DEFAULT 1
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_id ON users(id)")

    users = [(i, f"user_{i}", f"user{i}@test.com", i % 2) for i in range(1, num_records + 1)]
    cursor.executemany("INSERT INTO users (id, username, email, status) VALUES (?, ?, ?, ?)", users)
    conn.commit()
    conn.close()


def benchmark_python_sqlite(db_path: str, iterations: int = 500) -> DBComparisonResult:
    """Benchmark Python native SQLite"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Warmup
    for _ in range(50):
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (1,))
        cursor.fetchall()
        cursor.close()

    # Benchmark
    times = []
    for i in range(iterations):
        start = time.perf_counter_ns()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", ((i % 100) + 1,))
        cursor.fetchall()
        cursor.close()
        times.append((time.perf_counter_ns() - start) / 1_000_000)

    conn.close()
    avg = statistics.mean(times)

    return DBComparisonResult(
        language="Python 3.12",
        operation="SELECT (1 row)",
        avg_time_ms=avg,
        ops_per_second=1000/avg if avg > 0 else 0,
        iterations=iterations
    )


def benchmark_quantum_sqlite(db_path: str, iterations: int = 500) -> DBComparisonResult:
    """Benchmark Quantum DatabaseService"""
    from runtime.database_service import DatabaseService

    db_service = DatabaseService(
        admin_api_url="http://localhost:8000",
        local_datasources={"bench_db": {"driver": "sqlite", "database": db_path}}
    )

    # Warmup
    for _ in range(50):
        db_service.execute_query("bench_db", "SELECT * FROM users WHERE id = :id", {"id": 1})

    # Benchmark
    times = []
    for i in range(iterations):
        start = time.perf_counter_ns()
        db_service.execute_query("bench_db", "SELECT * FROM users WHERE id = :id", {"id": (i % 100) + 1})
        times.append((time.perf_counter_ns() - start) / 1_000_000)

    db_service.close_all_connections()
    avg = statistics.mean(times)

    return DBComparisonResult(
        language="Quantum",
        operation="SELECT (1 row)",
        avg_time_ms=avg,
        ops_per_second=1000/avg if avg > 0 else 0,
        iterations=iterations
    )


def benchmark_php_sqlite(db_path: str, iterations: int = 500) -> DBComparisonResult:
    """Benchmark PHP SQLite"""
    php_code = f'''<?php
$db = new SQLite3('{db_path.replace(chr(92), "/")}');
$iterations = {iterations};

// Warmup
for ($i = 0; $i < 50; $i++) {{
    $result = $db->query("SELECT * FROM users WHERE id = 1");
    $result->fetchArray();
}}

// Benchmark
$times = [];
for ($i = 0; $i < $iterations; $i++) {{
    $id = ($i % 100) + 1;
    $start = hrtime(true);
    $result = $db->query("SELECT * FROM users WHERE id = $id");
    $result->fetchArray();
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
        return DBComparisonResult(
            language="PHP 8.4",
            operation="SELECT (1 row)",
            avg_time_ms=avg,
            ops_per_second=1000/avg if avg > 0 else 0,
            iterations=iterations
        )
    finally:
        Path(php_file).unlink(missing_ok=True)


def benchmark_ruby_sqlite(db_path: str, iterations: int = 500) -> DBComparisonResult:
    """Benchmark Ruby SQLite"""
    ruby_code = f'''
require 'sqlite3'

db = SQLite3::Database.new('{db_path.replace(chr(92), "/")}')
iterations = {iterations}

# Warmup
50.times do
  db.execute("SELECT * FROM users WHERE id = ?", [1])
end

# Benchmark
times = []
iterations.times do |i|
  id = (i % 100) + 1
  start = Process.clock_gettime(Process::CLOCK_MONOTONIC, :nanosecond)
  db.execute("SELECT * FROM users WHERE id = ?", [id])
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
        return DBComparisonResult(
            language="Ruby 3.3",
            operation="SELECT (1 row)",
            avg_time_ms=avg,
            ops_per_second=1000/avg if avg > 0 else 0,
            iterations=iterations
        )
    finally:
        Path(ruby_file).unlink(missing_ok=True)


def benchmark_perl_sqlite(db_path: str, iterations: int = 500) -> DBComparisonResult:
    """Benchmark Perl SQLite"""
    perl_code = f'''
use strict;
use warnings;
use DBI;
use Time::HiRes qw(time);

my $db = DBI->connect("dbi:SQLite:dbname={db_path.replace(chr(92), "/")}", "", "");
my $iterations = {iterations};

# Warmup
for (1..50) {{
    my $sth = $db->prepare("SELECT * FROM users WHERE id = ?");
    $sth->execute(1);
    $sth->fetchrow_hashref();
}}

# Benchmark
my @times;
for my $i (0..$iterations-1) {{
    my $id = ($i % 100) + 1;
    my $start = time();
    my $sth = $db->prepare("SELECT * FROM users WHERE id = ?");
    $sth->execute($id);
    $sth->fetchrow_hashref();
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
        return DBComparisonResult(
            language="Perl 5.42",
            operation="SELECT (1 row)",
            avg_time_ms=avg,
            ops_per_second=1000/avg if avg > 0 else 0,
            iterations=iterations
        )
    finally:
        Path(perl_file).unlink(missing_ok=True)


def run_all_benchmarks():
    """Run all database comparison benchmarks"""
    print("=" * 70)
    print("Cross-Language Database Access Benchmark")
    print("=" * 70)

    # Create test database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    print(f"\nCreating test database with 1000 users...")
    create_test_database(db_path, 1000)
    print("Database ready.\n")

    results: List[DBComparisonResult] = []

    benchmarks = [
        ("Python 3.12", lambda: benchmark_python_sqlite(db_path)),
        ("Quantum", lambda: benchmark_quantum_sqlite(db_path)),
        ("PHP 8.4", lambda: benchmark_php_sqlite(db_path)),
        ("Ruby 3.3", lambda: benchmark_ruby_sqlite(db_path)),
        ("Perl 5.42", lambda: benchmark_perl_sqlite(db_path)),
    ]

    print("Running SELECT (1 row) benchmarks...\n")

    for name, bench_func in benchmarks:
        try:
            print(f"  Testing {name}...", end=" ", flush=True)
            result = bench_func()
            results.append(result)
            print(f"{result.avg_time_ms:.4f}ms ({result.ops_per_second:.0f} ops/sec)")
        except Exception as e:
            print(f"ERROR: {e}")

    # Sort by performance
    results.sort(key=lambda r: r.avg_time_ms)

    # Print rankings
    print("\n" + "=" * 70)
    print("Database SELECT Performance Rankings")
    print("=" * 70)
    print(f"\n{'Rank':<6} {'Language':<15} {'Avg Time (ms)':<15} {'Ops/sec':<12} {'vs Fastest':<10}")
    print("-" * 70)

    fastest = results[0].avg_time_ms if results else 1
    for i, r in enumerate(results, 1):
        relative = r.avg_time_ms / fastest
        print(f"{i:<6} {r.language:<15} {r.avg_time_ms:<15.4f} {r.ops_per_second:<12.0f} {relative:.1f}x")

    # Cleanup
    Path(db_path).unlink(missing_ok=True)

    return results


if __name__ == "__main__":
    run_all_benchmarks()
