"""
Quantum Concurrent Transactions Benchmarks
============================================

Measures concurrent/parallel performance:
- Concurrent database operations
- Parallel template rendering
- Thread pool efficiency
- Lock contention
"""

import sys
import time
import statistics
import tempfile
import sqlite3
import threading
import queue
import gc
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.parser import QuantumParser
from runtime.component import ComponentRuntime


@dataclass
class ConcurrencyBenchmarkResult:
    """Result of a concurrency benchmark"""
    name: str
    workers: int
    total_operations: int
    total_time_ms: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    std_dev_ms: float
    throughput_ops_sec: float
    speedup_vs_single: float = 1.0


def create_test_database(path: str, num_records: int = 1000) -> sqlite3.Connection:
    """Create a test database for concurrent access"""
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 1000.0,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_account INTEGER,
            to_account INTEGER,
            amount REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create accounts
    accounts = [(i,) for i in range(1, num_records + 1)]
    cursor.executemany("INSERT OR IGNORE INTO accounts (id) VALUES (?)", accounts)
    conn.commit()

    return conn


def benchmark_single_thread_db(db_path: str, operations: int = 100) -> ConcurrencyBenchmarkResult:
    """Baseline: single-threaded database operations"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Warmup
    for _ in range(10):
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accounts WHERE id = ?", (1,))
        cursor.fetchall()
        cursor.close()

    # Benchmark
    times = []
    for i in range(operations):
        start = time.perf_counter_ns()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accounts WHERE id = ?", ((i % 100) + 1,))
        cursor.fetchall()
        cursor.close()
        end = time.perf_counter_ns()
        times.append((end - start) / 1_000_000)

    conn.close()

    total = sum(times)
    avg = statistics.mean(times)

    return ConcurrencyBenchmarkResult(
        name="DB Single Thread",
        workers=1,
        total_operations=operations,
        total_time_ms=total,
        avg_latency_ms=avg,
        min_latency_ms=min(times),
        max_latency_ms=max(times),
        std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0,
        throughput_ops_sec=(operations / total) * 1000,
        speedup_vs_single=1.0
    )


def benchmark_concurrent_db(db_path: str, workers: int = 4, operations_per_worker: int = 25) -> ConcurrencyBenchmarkResult:
    """Concurrent database operations"""
    results_queue = queue.Queue()

    def worker(worker_id: int):
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        times = []

        for i in range(operations_per_worker):
            account_id = (worker_id * operations_per_worker + i) % 100 + 1
            start = time.perf_counter_ns()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
            cursor.fetchall()
            cursor.close()
            end = time.perf_counter_ns()
            times.append((end - start) / 1_000_000)

        conn.close()
        results_queue.put(times)

    # Warmup
    conn = sqlite3.connect(db_path)
    for _ in range(10):
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accounts WHERE id = ?", (1,))
        cursor.fetchall()
        cursor.close()
    conn.close()

    # Run concurrent workers
    start_time = time.perf_counter_ns()
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total_time = (time.perf_counter_ns() - start_time) / 1_000_000

    # Collect results
    all_times = []
    while not results_queue.empty():
        all_times.extend(results_queue.get())

    total_ops = len(all_times)
    avg = statistics.mean(all_times)

    return ConcurrencyBenchmarkResult(
        name=f"DB Concurrent ({workers} workers)",
        workers=workers,
        total_operations=total_ops,
        total_time_ms=total_time,
        avg_latency_ms=avg,
        min_latency_ms=min(all_times),
        max_latency_ms=max(all_times),
        std_dev_ms=statistics.stdev(all_times) if len(all_times) > 1 else 0,
        throughput_ops_sec=(total_ops / total_time) * 1000
    )


def benchmark_single_thread_render(template: str, iterations: int = 100) -> ConcurrencyBenchmarkResult:
    """Baseline: single-threaded template rendering"""
    parser = QuantumParser()
    executor = ComponentRuntime()
    ast = parser.parse(template)

    # Warmup
    for _ in range(10):
        executor.execute_component(ast, {})

    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        executor.execute_component(ast, {})
        end = time.perf_counter_ns()
        times.append((end - start) / 1_000_000)

    total = sum(times)
    avg = statistics.mean(times)

    return ConcurrencyBenchmarkResult(
        name="Render Single Thread",
        workers=1,
        total_operations=iterations,
        total_time_ms=total,
        avg_latency_ms=avg,
        min_latency_ms=min(times),
        max_latency_ms=max(times),
        std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0,
        throughput_ops_sec=(iterations / total) * 1000,
        speedup_vs_single=1.0
    )


def benchmark_concurrent_render(template: str, workers: int = 4, ops_per_worker: int = 25) -> ConcurrencyBenchmarkResult:
    """Concurrent template rendering"""
    parser = QuantumParser()
    ast = parser.parse(template)
    results_queue = queue.Queue()

    def worker():
        executor = ComponentRuntime()  # Each worker has own executor
        times = []
        for _ in range(ops_per_worker):
            start = time.perf_counter_ns()
            executor.execute_component(ast, {})
            end = time.perf_counter_ns()
            times.append((end - start) / 1_000_000)
        results_queue.put(times)

    # Warmup
    executor = ComponentRuntime()
    for _ in range(10):
        executor.execute_component(ast, {})

    # Run concurrent workers
    start_time = time.perf_counter_ns()
    threads = [threading.Thread(target=worker) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total_time = (time.perf_counter_ns() - start_time) / 1_000_000

    # Collect results
    all_times = []
    while not results_queue.empty():
        all_times.extend(results_queue.get())

    total_ops = len(all_times)
    avg = statistics.mean(all_times)

    return ConcurrencyBenchmarkResult(
        name=f"Render Concurrent ({workers} workers)",
        workers=workers,
        total_operations=total_ops,
        total_time_ms=total_time,
        avg_latency_ms=avg,
        min_latency_ms=min(all_times),
        max_latency_ms=max(all_times),
        std_dev_ms=statistics.stdev(all_times) if len(all_times) > 1 else 0,
        throughput_ops_sec=(total_ops / total_time) * 1000
    )


def benchmark_thread_pool(workers: int = 4, tasks: int = 100) -> ConcurrencyBenchmarkResult:
    """Benchmark ThreadPoolExecutor efficiency"""
    def cpu_task(n: int) -> int:
        # Simple CPU-bound task
        result = 0
        for i in range(1000):
            result += i * n
        return result

    times = []

    # Warmup
    with ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(cpu_task, range(10)))

    # Benchmark
    start_time = time.perf_counter_ns()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(cpu_task, i) for i in range(tasks)]
        for future in as_completed(futures):
            future.result()
    total_time = (time.perf_counter_ns() - start_time) / 1_000_000

    # Measure individual task times
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for i in range(tasks):
            start = time.perf_counter_ns()
            future = executor.submit(cpu_task, i)
            future.result()
            end = time.perf_counter_ns()
            times.append((end - start) / 1_000_000)

    avg = statistics.mean(times)

    return ConcurrencyBenchmarkResult(
        name=f"ThreadPool ({workers} workers)",
        workers=workers,
        total_operations=tasks,
        total_time_ms=total_time,
        avg_latency_ms=avg,
        min_latency_ms=min(times),
        max_latency_ms=max(times),
        std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0,
        throughput_ops_sec=(tasks / total_time) * 1000
    )


def benchmark_mixed_workload(db_path: str, template: str, workers: int = 4) -> ConcurrencyBenchmarkResult:
    """Mixed workload: DB + rendering interleaved"""
    parser = QuantumParser()
    ast = parser.parse(template)
    results_queue = queue.Queue()

    def worker(worker_id: int):
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        executor = ComponentRuntime()
        times = []

        for i in range(25):
            start = time.perf_counter_ns()

            # DB operation
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts WHERE id = ?", ((i % 100) + 1,))
            data = cursor.fetchall()
            cursor.close()

            # Render with data
            executor.execute_component(ast, {"data": data})

            end = time.perf_counter_ns()
            times.append((end - start) / 1_000_000)

        conn.close()
        results_queue.put(times)

    # Run concurrent workers
    start_time = time.perf_counter_ns()
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total_time = (time.perf_counter_ns() - start_time) / 1_000_000

    # Collect results
    all_times = []
    while not results_queue.empty():
        all_times.extend(results_queue.get())

    total_ops = len(all_times)
    avg = statistics.mean(all_times)

    return ConcurrencyBenchmarkResult(
        name=f"Mixed Workload ({workers} workers)",
        workers=workers,
        total_operations=total_ops,
        total_time_ms=total_time,
        avg_latency_ms=avg,
        min_latency_ms=min(all_times),
        max_latency_ms=max(all_times),
        std_dev_ms=statistics.stdev(all_times) if len(all_times) > 1 else 0,
        throughput_ops_sec=(total_ops / total_time) * 1000
    )


def run_all_benchmarks():
    """Run all concurrency benchmarks"""
    print("=" * 70)
    print("Quantum Concurrent Transactions Benchmarks")
    print("=" * 70)

    # Create test database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    print(f"\nCreating test database at: {db_path}")
    conn = create_test_database(db_path, num_records=1000)
    conn.close()
    print("Database created with 1000 accounts")

    # Test template
    template = """
    <q:component name="DataView">
        <q:set name="items" value="[1,2,3,4,5,6,7,8,9,10]" />
        <div class="container">
            <h1>Data View</h1>
            <q:loop items="{items}" var="item">
                <div class="item">Item {item}</div>
            </q:loop>
        </div>
    </q:component>
    """

    results: List[ConcurrencyBenchmarkResult] = []

    # Database concurrency
    print("\n[Database Concurrency]")
    db_single = benchmark_single_thread_db(db_path, 100)
    results.append(db_single)
    print(f"  {db_single.name:<35} {db_single.throughput_ops_sec:>8.0f} ops/sec (baseline)")

    for workers in [2, 4, 8]:
        result = benchmark_concurrent_db(db_path, workers, 25)
        result.speedup_vs_single = result.throughput_ops_sec / db_single.throughput_ops_sec
        results.append(result)
        print(f"  {result.name:<35} {result.throughput_ops_sec:>8.0f} ops/sec ({result.speedup_vs_single:.2f}x)")

    # Render concurrency
    print("\n[Render Concurrency]")
    try:
        render_single = benchmark_single_thread_render(template, 100)
        results.append(render_single)
        print(f"  {render_single.name:<35} {render_single.throughput_ops_sec:>8.0f} ops/sec (baseline)")

        for workers in [2, 4, 8]:
            result = benchmark_concurrent_render(template, workers, 25)
            result.speedup_vs_single = result.throughput_ops_sec / render_single.throughput_ops_sec
            results.append(result)
            print(f"  {result.name:<35} {result.throughput_ops_sec:>8.0f} ops/sec ({result.speedup_vs_single:.2f}x)")
    except Exception as e:
        print(f"  Render benchmarks skipped: {e}")

    # ThreadPool efficiency
    print("\n[ThreadPool Efficiency]")
    for workers in [2, 4, 8]:
        result = benchmark_thread_pool(workers, 100)
        results.append(result)
        print(f"  {result.name:<35} {result.throughput_ops_sec:>8.0f} ops/sec")

    # Mixed workload
    print("\n[Mixed Workload (DB + Render)]")
    try:
        for workers in [2, 4, 8]:
            result = benchmark_mixed_workload(db_path, template, workers)
            results.append(result)
            print(f"  {result.name:<35} {result.throughput_ops_sec:>8.0f} ops/sec | {result.avg_latency_ms:.2f}ms latency")
    except Exception as e:
        print(f"  Mixed workload skipped: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"\n{'Benchmark':<40} {'Workers':<8} {'Throughput':<15} {'Speedup':<10}")
    print("-" * 70)

    for r in results:
        speedup = f"{r.speedup_vs_single:.2f}x" if r.speedup_vs_single > 1.0 else "-"
        print(f"{r.name:<40} {r.workers:<8} {r.throughput_ops_sec:>8.0f} ops/sec {speedup:>10}")

    # Cleanup
    Path(db_path).unlink(missing_ok=True)

    return results


if __name__ == "__main__":
    run_all_benchmarks()
