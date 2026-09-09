"""
Quantum Benchmark Framework

Provides utilities for measuring performance of Quantum features
and comparing with other languages/platforms.
"""

import time
import statistics
import json
import gc
import sys
import platform
import psutil
from dataclasses import dataclass, field, asdict
from typing import Callable, List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from functools import wraps


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run"""
    name: str
    category: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    ops_per_second: float
    memory_before_mb: float
    memory_after_mb: float
    memory_delta_mb: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComparisonResult:
    """Comparison between Quantum and another platform"""
    benchmark_name: str
    quantum_result: BenchmarkResult
    comparison_results: Dict[str, BenchmarkResult]
    speedup_factors: Dict[str, float] = field(default_factory=dict)


class Timer:
    """High-precision timer for benchmarks"""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed_ns = 0

    def start(self):
        gc.disable()  # Disable GC during timing
        self.start_time = time.perf_counter_ns()
        return self

    def stop(self):
        self.end_time = time.perf_counter_ns()
        gc.enable()
        self.elapsed_ns = self.end_time - self.start_time
        return self

    @property
    def elapsed_ms(self) -> float:
        return self.elapsed_ns / 1_000_000

    @property
    def elapsed_us(self) -> float:
        return self.elapsed_ns / 1_000

    @property
    def elapsed_s(self) -> float:
        return self.elapsed_ns / 1_000_000_000


@contextmanager
def timed():
    """Context manager for timing code blocks"""
    timer = Timer()
    timer.start()
    try:
        yield timer
    finally:
        timer.stop()


def get_memory_usage_mb() -> float:
    """Get current memory usage in MB"""
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)


class Benchmark:
    """Decorator and class for defining benchmarks"""

    registry: Dict[str, 'Benchmark'] = {}

    def __init__(
        self,
        name: str,
        category: str = "general",
        iterations: int = 1000,
        warmup: int = 100,
        description: str = ""
    ):
        self.name = name
        self.category = category
        self.iterations = iterations
        self.warmup = warmup
        self.description = description
        self.func = None
        self.setup_func = None
        self.teardown_func = None

        # Register benchmark
        Benchmark.registry[name] = self

    def __call__(self, func: Callable) -> 'Benchmark':
        self.func = func
        return self

    def setup(self, func: Callable) -> Callable:
        """Decorator to register setup function"""
        self.setup_func = func
        return func

    def teardown(self, func: Callable) -> Callable:
        """Decorator to register teardown function"""
        self.teardown_func = func
        return func

    def run(self, **kwargs) -> BenchmarkResult:
        """Execute the benchmark and return results"""
        if self.func is None:
            raise ValueError(f"Benchmark {self.name} has no function defined")

        # Setup
        context = {}
        if self.setup_func:
            context = self.setup_func(**kwargs) or {}

        # Warmup runs
        for _ in range(self.warmup):
            self.func(**context)

        # Force garbage collection before timing
        gc.collect()

        # Measure memory before
        memory_before = get_memory_usage_mb()

        # Benchmark runs
        times_ns = []
        for _ in range(self.iterations):
            start = time.perf_counter_ns()
            self.func(**context)
            end = time.perf_counter_ns()
            times_ns.append(end - start)

        # Measure memory after
        memory_after = get_memory_usage_mb()

        # Teardown
        if self.teardown_func:
            self.teardown_func(**context)

        # Calculate statistics
        times_ms = [t / 1_000_000 for t in times_ns]
        total_time = sum(times_ms)
        avg_time = statistics.mean(times_ms)
        min_time = min(times_ms)
        max_time = max(times_ms)
        std_dev = statistics.stdev(times_ms) if len(times_ms) > 1 else 0
        ops_per_sec = 1000 / avg_time if avg_time > 0 else float('inf')

        return BenchmarkResult(
            name=self.name,
            category=self.category,
            iterations=self.iterations,
            total_time_ms=total_time,
            avg_time_ms=avg_time,
            min_time_ms=min_time,
            max_time_ms=max_time,
            std_dev_ms=std_dev,
            ops_per_second=ops_per_sec,
            memory_before_mb=memory_before,
            memory_after_mb=memory_after,
            memory_delta_mb=memory_after - memory_before,
            metadata=kwargs
        )


class BenchmarkSuite:
    """Collection of benchmarks to run together"""

    def __init__(self, name: str = "Quantum Benchmarks"):
        self.name = name
        self.results: List[BenchmarkResult] = []
        self.comparisons: List[ComparisonResult] = []
        self.system_info = self._get_system_info()

    def _get_system_info(self) -> Dict[str, Any]:
        """Collect system information"""
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "timestamp": datetime.now().isoformat()
        }

    def run_benchmark(self, name: str, **kwargs) -> BenchmarkResult:
        """Run a single benchmark by name"""
        if name not in Benchmark.registry:
            raise ValueError(f"Benchmark '{name}' not found")

        benchmark = Benchmark.registry[name]
        result = benchmark.run(**kwargs)
        self.results.append(result)
        return result

    def run_category(self, category: str, **kwargs) -> List[BenchmarkResult]:
        """Run all benchmarks in a category"""
        results = []
        for name, benchmark in Benchmark.registry.items():
            if benchmark.category == category:
                result = benchmark.run(**kwargs)
                self.results.append(result)
                results.append(result)
        return results

    def run_all(self, **kwargs) -> List[BenchmarkResult]:
        """Run all registered benchmarks"""
        results = []
        for name, benchmark in Benchmark.registry.items():
            print(f"Running: {name}...", end=" ", flush=True)
            result = benchmark.run(**kwargs)
            self.results.append(result)
            results.append(result)
            print(f"{result.avg_time_ms:.3f}ms avg ({result.ops_per_second:.0f} ops/sec)")
        return results

    def add_comparison(
        self,
        benchmark_name: str,
        platform_name: str,
        result: BenchmarkResult
    ):
        """Add a comparison result from another platform"""
        # Find existing comparison or create new
        comparison = None
        for c in self.comparisons:
            if c.benchmark_name == benchmark_name:
                comparison = c
                break

        if comparison is None:
            # Find quantum result
            quantum_result = None
            for r in self.results:
                if r.name == benchmark_name:
                    quantum_result = r
                    break

            if quantum_result is None:
                raise ValueError(f"Run Quantum benchmark '{benchmark_name}' first")

            comparison = ComparisonResult(
                benchmark_name=benchmark_name,
                quantum_result=quantum_result,
                comparison_results={}
            )
            self.comparisons.append(comparison)

        comparison.comparison_results[platform_name] = result

        # Calculate speedup
        if result.avg_time_ms > 0:
            speedup = result.avg_time_ms / comparison.quantum_result.avg_time_ms
            comparison.speedup_factors[platform_name] = speedup

    def save_results(self, path: str = "benchmarks/results"):
        """Save results to JSON file"""
        results_dir = Path(path)
        results_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = results_dir / f"benchmark_{timestamp}.json"

        data = {
            "suite_name": self.name,
            "system_info": self.system_info,
            "results": [asdict(r) for r in self.results],
            "comparisons": [
                {
                    "benchmark_name": c.benchmark_name,
                    "quantum_result": asdict(c.quantum_result),
                    "comparison_results": {
                        k: asdict(v) for k, v in c.comparison_results.items()
                    },
                    "speedup_factors": c.speedup_factors
                }
                for c in self.comparisons
            ]
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Results saved to: {filename}")
        return filename

    def print_summary(self):
        """Print a summary of benchmark results"""
        print("\n" + "=" * 70)
        print(f"  {self.name} - Summary")
        print("=" * 70)

        # Group by category
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)

        for category, results in sorted(categories.items()):
            print(f"\n  [{category.upper()}]")
            print("-" * 70)
            print(f"  {'Benchmark':<30} {'Avg (ms)':<12} {'Ops/sec':<12} {'Mem (MB)':<10}")
            print("-" * 70)

            for r in sorted(results, key=lambda x: x.avg_time_ms):
                print(f"  {r.name:<30} {r.avg_time_ms:<12.3f} {r.ops_per_second:<12.0f} {r.memory_delta_mb:<10.2f}")

        # Print comparisons if any
        if self.comparisons:
            print("\n" + "=" * 70)
            print("  Comparisons (speedup factor: >1 = Quantum faster)")
            print("=" * 70)

            for comp in self.comparisons:
                print(f"\n  {comp.benchmark_name}:")
                for platform, speedup in comp.speedup_factors.items():
                    status = "faster" if speedup > 1 else "slower"
                    print(f"    vs {platform}: {speedup:.2f}x ({status})")

        print("\n" + "=" * 70)


def benchmark(
    name: str,
    category: str = "general",
    iterations: int = 1000,
    warmup: int = 100
):
    """Decorator to create a benchmark from a function"""
    def decorator(func: Callable) -> Benchmark:
        b = Benchmark(name, category, iterations, warmup)
        b.func = func
        return b
    return decorator


# Utility functions for common benchmark patterns

def benchmark_function_call(func: Callable, *args, **kwargs) -> float:
    """Benchmark a single function call, returns time in ms"""
    with timed() as t:
        func(*args, **kwargs)
    return t.elapsed_ms


def benchmark_iterations(func: Callable, iterations: int = 1000) -> Dict[str, float]:
    """Benchmark multiple iterations, returns statistics"""
    times = []
    for _ in range(iterations):
        with timed() as t:
            func()
        times.append(t.elapsed_ms)

    return {
        "total_ms": sum(times),
        "avg_ms": statistics.mean(times),
        "min_ms": min(times),
        "max_ms": max(times),
        "std_dev_ms": statistics.stdev(times) if len(times) > 1 else 0,
        "ops_per_sec": 1000 / statistics.mean(times) if statistics.mean(times) > 0 else 0
    }
