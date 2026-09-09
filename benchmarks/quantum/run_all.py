"""
Run All Quantum-Specific Benchmarks
====================================

Executes all Quantum performance benchmarks and generates a report.
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def run_all_benchmarks():
    """Run all Quantum benchmarks"""
    print("=" * 80)
    print("  QUANTUM PERFORMANCE BENCHMARK SUITE")
    print("=" * 80)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version.split()[0]}")
    print("-" * 80)

    results = {}
    start_time = time.time()

    # 1. Database benchmarks
    print("\n\n" + "=" * 80)
    print("  1. DATABASE ACCESS BENCHMARKS")
    print("=" * 80)
    try:
        from benchmark_database import run_all_benchmarks as run_db
        db_results = run_db()
        results['database'] = [
            {'name': r.name, 'avg_ms': r.avg_time_ms, 'ops_sec': r.ops_per_second}
            for r in db_results
        ]
    except Exception as e:
        print(f"\nDatabase benchmarks failed: {e}")
        results['database'] = {'error': str(e)}

    # 2. HTML Throughput benchmarks
    print("\n\n" + "=" * 80)
    print("  2. HTML THROUGHPUT BENCHMARKS")
    print("=" * 80)
    try:
        from benchmark_html_throughput import run_all_benchmarks as run_html
        html_results = run_html()
        results['html_throughput'] = [
            {'name': r.name, 'avg_ms': r.avg_time_ms, 'renders_sec': r.renders_per_second,
             'bytes_sec': r.bytes_per_second}
            for r in html_results
        ]
    except Exception as e:
        print(f"\nHTML throughput benchmarks failed: {e}")
        results['html_throughput'] = {'error': str(e)}

    # 3. API benchmarks
    print("\n\n" + "=" * 80)
    print("  3. API ACCESS TIME BENCHMARKS")
    print("=" * 80)
    try:
        from benchmark_api import run_all_benchmarks as run_api
        api_results = run_api()
        results['api'] = [
            {'name': r.name, 'avg_ms': r.avg_time_ms, 'requests_sec': r.requests_per_second}
            for r in api_results
        ]
    except Exception as e:
        print(f"\nAPI benchmarks failed: {e}")
        results['api'] = {'error': str(e)}

    # 4. Concurrency benchmarks
    print("\n\n" + "=" * 80)
    print("  4. CONCURRENT TRANSACTIONS BENCHMARKS")
    print("=" * 80)
    try:
        from benchmark_concurrent import run_all_benchmarks as run_concurrent
        concurrent_results = run_concurrent()
        results['concurrency'] = [
            {'name': r.name, 'workers': r.workers, 'throughput': r.throughput_ops_sec,
             'speedup': r.speedup_vs_single}
            for r in concurrent_results
        ]
    except Exception as e:
        print(f"\nConcurrency benchmarks failed: {e}")
        results['concurrency'] = {'error': str(e)}

    # Final summary
    total_time = time.time() - start_time
    print("\n\n" + "=" * 80)
    print("  BENCHMARK SUITE COMPLETE")
    print("=" * 80)
    print(f"\nTotal execution time: {total_time:.1f}s")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Save results
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"quantum_benchmarks_{timestamp}.json"

    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'total_time_seconds': total_time,
            'results': results
        }, f, indent=2)

    print(f"\nResults saved to: {results_file}")

    return results


if __name__ == "__main__":
    run_all_benchmarks()
