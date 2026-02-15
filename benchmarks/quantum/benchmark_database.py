"""
Quantum Database Access Benchmarks
===================================

Measures database performance including:
- Query execution time (SELECT, INSERT, UPDATE, DELETE)
- Connection pool efficiency
- Bulk operations
- Parameterized vs raw queries
"""

import sys
import time
import statistics
import tempfile
import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from runtime.database_service import DatabaseService, QueryResult


@dataclass
class DBBenchmarkResult:
    """Result of a database benchmark"""
    name: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    ops_per_second: float
    rows_processed: int


def create_test_database(path: str, num_records: int = 10000) -> sqlite3.Connection:
    """Create a test database with sample data"""
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            content TEXT,
            views INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            user_id INTEGER,
            content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id)")

    # Insert sample data
    users_data = [(f"user_{i}", f"user{i}@example.com", i % 2) for i in range(num_records)]
    cursor.executemany(
        "INSERT INTO users (username, email, status) VALUES (?, ?, ?)",
        users_data
    )

    posts_data = [(i % num_records + 1, f"Post Title {i}", f"Content for post {i}", i * 10)
                  for i in range(num_records * 2)]
    cursor.executemany(
        "INSERT INTO posts (user_id, title, content, views) VALUES (?, ?, ?, ?)",
        posts_data
    )

    comments_data = [(i % (num_records * 2) + 1, i % num_records + 1, f"Comment {i}")
                     for i in range(num_records * 5)]
    cursor.executemany(
        "INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)",
        comments_data
    )

    conn.commit()
    return conn


def run_benchmark(name: str, func, iterations: int = 100, warmup: int = 10) -> DBBenchmarkResult:
    """Run a database benchmark"""
    # Warmup
    for _ in range(warmup):
        func()

    # Benchmark
    times_ms = []
    rows = 0
    for _ in range(iterations):
        start = time.perf_counter_ns()
        result = func()
        end = time.perf_counter_ns()
        times_ms.append((end - start) / 1_000_000)
        if isinstance(result, int):
            rows += result
        elif hasattr(result, 'record_count'):
            rows += result.record_count

    total = sum(times_ms)
    avg = statistics.mean(times_ms)

    return DBBenchmarkResult(
        name=name,
        iterations=iterations,
        total_time_ms=total,
        avg_time_ms=avg,
        min_time_ms=min(times_ms),
        max_time_ms=max(times_ms),
        std_dev_ms=statistics.stdev(times_ms) if len(times_ms) > 1 else 0,
        ops_per_second=1000 / avg if avg > 0 else 0,
        rows_processed=rows
    )


def benchmark_simple_select(db_service: DatabaseService, ds_name: str) -> DBBenchmarkResult:
    """Benchmark simple SELECT query"""
    def func():
        result = db_service.execute_query(ds_name, "SELECT * FROM users WHERE id = :id", {"id": 1})
        return result
    return run_benchmark("Simple SELECT (1 row)", func, iterations=500)


def benchmark_select_range(db_service: DatabaseService, ds_name: str) -> DBBenchmarkResult:
    """Benchmark SELECT with range"""
    def func():
        result = db_service.execute_query(ds_name,
            "SELECT * FROM users WHERE id BETWEEN :start AND :end",
            {"start": 1, "end": 100})
        return result
    return run_benchmark("SELECT Range (100 rows)", func, iterations=200)


def benchmark_select_all(db_service: DatabaseService, ds_name: str) -> DBBenchmarkResult:
    """Benchmark SELECT all"""
    def func():
        result = db_service.execute_query(ds_name, "SELECT * FROM users LIMIT 1000")
        return result
    return run_benchmark("SELECT All (1000 rows)", func, iterations=100)


def benchmark_join_query(db_service: DatabaseService, ds_name: str) -> DBBenchmarkResult:
    """Benchmark JOIN query"""
    def func():
        result = db_service.execute_query(ds_name, """
            SELECT u.username, p.title, COUNT(c.id) as comment_count
            FROM users u
            JOIN posts p ON p.user_id = u.id
            LEFT JOIN comments c ON c.post_id = p.id
            WHERE u.id BETWEEN :start AND :end
            GROUP BY u.id, p.id
            LIMIT 100
        """, {"start": 1, "end": 50})
        return result
    return run_benchmark("JOIN Query (3 tables)", func, iterations=100)


def benchmark_aggregation(db_service: DatabaseService, ds_name: str) -> DBBenchmarkResult:
    """Benchmark aggregation query"""
    def func():
        result = db_service.execute_query(ds_name, """
            SELECT status, COUNT(*) as count, AVG(id) as avg_id
            FROM users
            GROUP BY status
        """)
        return result
    return run_benchmark("Aggregation (GROUP BY)", func, iterations=200)


def benchmark_insert(db_service: DatabaseService, ds_name: str) -> DBBenchmarkResult:
    """Benchmark INSERT operation"""
    counter = [0]
    def func():
        counter[0] += 1
        result = db_service.execute_query(ds_name,
            "INSERT INTO users (username, email, status) VALUES (:username, :email, :status)",
            {"username": f"bench_user_{counter[0]}", "email": f"bench{counter[0]}@test.com", "status": 1})
        return result
    return run_benchmark("INSERT (1 row)", func, iterations=200)


def benchmark_update(db_service: DatabaseService, ds_name: str) -> DBBenchmarkResult:
    """Benchmark UPDATE operation"""
    def func():
        result = db_service.execute_query(ds_name,
            "UPDATE users SET status = :status WHERE id = :id",
            {"status": 1, "id": 1})
        return result
    return run_benchmark("UPDATE (1 row)", func, iterations=200)


def benchmark_bulk_select(db_service: DatabaseService, ds_name: str) -> DBBenchmarkResult:
    """Benchmark multiple SELECTs in sequence"""
    def func():
        total = 0
        for i in range(10):
            result = db_service.execute_query(ds_name,
                "SELECT * FROM users WHERE id = :id", {"id": i + 1})
            total += result.record_count
        return total
    return run_benchmark("Bulk SELECT (10 queries)", func, iterations=50)


def run_all_benchmarks():
    """Run all database benchmarks"""
    print("=" * 70)
    print("Quantum Database Access Benchmarks")
    print("=" * 70)

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    print(f"\nCreating test database at: {db_path}")
    print("Inserting 10,000 users, 20,000 posts, 50,000 comments...")

    start = time.time()
    conn = create_test_database(db_path, num_records=10000)
    conn.close()
    setup_time = time.time() - start
    print(f"Setup completed in {setup_time:.2f}s")

    # Create database service with local datasource
    db_service = DatabaseService(
        admin_api_url="http://localhost:8000",
        local_datasources={
            "benchmark_db": {
                "driver": "sqlite",
                "database": db_path
            }
        }
    )
    ds_name = "benchmark_db"

    print("\n" + "-" * 70)
    print("Running benchmarks...")
    print("-" * 70)

    results: List[DBBenchmarkResult] = []

    # Run all benchmarks
    benchmarks = [
        ("SELECT Operations", [
            lambda: benchmark_simple_select(db_service, ds_name),
            lambda: benchmark_select_range(db_service, ds_name),
            lambda: benchmark_select_all(db_service, ds_name),
        ]),
        ("Complex Queries", [
            lambda: benchmark_join_query(db_service, ds_name),
            lambda: benchmark_aggregation(db_service, ds_name),
        ]),
        ("Write Operations", [
            lambda: benchmark_insert(db_service, ds_name),
            lambda: benchmark_update(db_service, ds_name),
        ]),
        ("Bulk Operations", [
            lambda: benchmark_bulk_select(db_service, ds_name),
        ]),
    ]

    for category, bench_funcs in benchmarks:
        print(f"\n[{category}]")
        for bench_func in bench_funcs:
            result = bench_func()
            results.append(result)
            print(f"  {result.name:<30} {result.avg_time_ms:>8.3f}ms avg | {result.ops_per_second:>8.0f} ops/sec")

    # Print summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"\n{'Benchmark':<35} {'Avg (ms)':<12} {'Min (ms)':<12} {'Ops/sec':<12}")
    print("-" * 70)

    for r in results:
        print(f"{r.name:<35} {r.avg_time_ms:<12.3f} {r.min_time_ms:<12.3f} {r.ops_per_second:<12.0f}")

    # Calculate overall metrics
    total_ops = sum(r.iterations for r in results)
    total_time = sum(r.total_time_ms for r in results)
    overall_ops_sec = (total_ops / total_time) * 1000 if total_time > 0 else 0

    print("-" * 70)
    print(f"Total: {total_ops} operations in {total_time:.0f}ms ({overall_ops_sec:.0f} ops/sec overall)")

    # Cleanup
    db_service.close_all_connections()
    Path(db_path).unlink(missing_ok=True)

    return results


if __name__ == "__main__":
    run_all_benchmarks()
