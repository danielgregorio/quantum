"""
Quantum API Access Time Benchmarks
===================================

Measures HTTP/API performance:
- HTTP request latency
- JSON parsing speed
- API endpoint response times
- Request handling overhead
"""

import sys
import time
import statistics
import json
import gc
import threading
import http.server
import socketserver
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any
from urllib.request import urlopen, Request
from urllib.error import URLError

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@dataclass
class APIBenchmarkResult:
    """Result of an API benchmark"""
    name: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    requests_per_second: float
    avg_latency_ms: float


class MockAPIHandler(http.server.BaseHTTPRequestHandler):
    """Simple HTTP handler for benchmarking"""

    def log_message(self, format, *args):
        pass  # Suppress logging

    def do_GET(self):
        if self.path == '/api/simple':
            self._respond_json({"status": "ok"})
        elif self.path == '/api/data':
            data = {"users": [{"id": i, "name": f"User {i}"} for i in range(10)]}
            self._respond_json(data)
        elif self.path == '/api/large':
            data = {"items": [{"id": i, "value": f"Item {i}" * 10} for i in range(100)]}
            self._respond_json(data)
        elif self.path == '/api/slow':
            time.sleep(0.01)  # 10ms simulated delay
            self._respond_json({"status": "delayed"})
        else:
            self.send_error(404)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        data = json.loads(body) if body else {}
        self._respond_json({"received": len(body), "echo": data.get("message", "")})

    def _respond_json(self, data: Dict[str, Any]):
        response = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Threaded HTTP server for concurrent benchmark requests"""
    daemon_threads = True


def start_mock_server(port: int = 8765) -> ThreadedHTTPServer:
    """Start a mock API server"""
    server = ThreadedHTTPServer(('127.0.0.1', port), MockAPIHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server


def run_benchmark(name: str, func, iterations: int = 100, warmup: int = 10) -> APIBenchmarkResult:
    """Run an API benchmark"""
    # Warmup
    for _ in range(warmup):
        try:
            func()
        except:
            pass

    # Benchmark
    times_ms = []
    gc.disable()
    try:
        for _ in range(iterations):
            start = time.perf_counter_ns()
            func()
            end = time.perf_counter_ns()
            times_ms.append((end - start) / 1_000_000)
    finally:
        gc.enable()

    total = sum(times_ms)
    avg = statistics.mean(times_ms)

    return APIBenchmarkResult(
        name=name,
        iterations=iterations,
        total_time_ms=total,
        avg_time_ms=avg,
        min_time_ms=min(times_ms),
        max_time_ms=max(times_ms),
        std_dev_ms=statistics.stdev(times_ms) if len(times_ms) > 1 else 0,
        requests_per_second=1000 / avg if avg > 0 else 0,
        avg_latency_ms=avg
    )


def benchmark_simple_get(base_url: str) -> APIBenchmarkResult:
    """Benchmark simple GET request"""
    url = f"{base_url}/api/simple"
    def func():
        with urlopen(url, timeout=5) as response:
            return response.read()
    return run_benchmark("GET /api/simple", func, iterations=200)


def benchmark_json_response(base_url: str) -> APIBenchmarkResult:
    """Benchmark GET with JSON parsing"""
    url = f"{base_url}/api/data"
    def func():
        with urlopen(url, timeout=5) as response:
            data = json.loads(response.read())
            return data
    return run_benchmark("GET /api/data (10 items)", func, iterations=200)


def benchmark_large_response(base_url: str) -> APIBenchmarkResult:
    """Benchmark large JSON response"""
    url = f"{base_url}/api/large"
    def func():
        with urlopen(url, timeout=5) as response:
            data = json.loads(response.read())
            return data
    return run_benchmark("GET /api/large (100 items)", func, iterations=100)


def benchmark_post_request(base_url: str) -> APIBenchmarkResult:
    """Benchmark POST request"""
    url = f"{base_url}/api/echo"
    payload = json.dumps({"message": "Hello, World!"}).encode('utf-8')
    def func():
        req = Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urlopen(req, timeout=5) as response:
            return response.read()
    return run_benchmark("POST /api/echo", func, iterations=200)


def benchmark_json_parsing_small() -> APIBenchmarkResult:
    """Benchmark JSON parsing (small)"""
    data = '{"status": "ok", "code": 200, "message": "Success"}'
    def func():
        return json.loads(data)
    return run_benchmark("JSON Parse (small)", func, iterations=5000)


def benchmark_json_parsing_medium() -> APIBenchmarkResult:
    """Benchmark JSON parsing (medium)"""
    data = json.dumps({"users": [{"id": i, "name": f"User {i}", "email": f"user{i}@test.com"} for i in range(50)]})
    def func():
        return json.loads(data)
    return run_benchmark("JSON Parse (50 objects)", func, iterations=1000)


def benchmark_json_parsing_large() -> APIBenchmarkResult:
    """Benchmark JSON parsing (large)"""
    data = json.dumps({"items": [{"id": i, "data": f"Content {i}" * 20} for i in range(500)]})
    def func():
        return json.loads(data)
    return run_benchmark("JSON Parse (500 objects)", func, iterations=200)


def benchmark_json_serialization() -> APIBenchmarkResult:
    """Benchmark JSON serialization"""
    data = {"users": [{"id": i, "name": f"User {i}", "email": f"user{i}@test.com"} for i in range(100)]}
    def func():
        return json.dumps(data)
    return run_benchmark("JSON Serialize (100 objects)", func, iterations=1000)


def benchmark_concurrent_requests(base_url: str, num_workers: int = 4) -> APIBenchmarkResult:
    """Benchmark concurrent requests"""
    url = f"{base_url}/api/simple"
    results = []

    def worker():
        times = []
        for _ in range(25):
            start = time.perf_counter_ns()
            with urlopen(url, timeout=5) as response:
                response.read()
            end = time.perf_counter_ns()
            times.append((end - start) / 1_000_000)
        results.extend(times)

    # Warmup
    for _ in range(10):
        with urlopen(url, timeout=5) as response:
            response.read()

    # Run concurrent workers
    start = time.perf_counter_ns()
    threads = [threading.Thread(target=worker) for _ in range(num_workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total_time = (time.perf_counter_ns() - start) / 1_000_000

    avg = statistics.mean(results)
    total_requests = len(results)

    return APIBenchmarkResult(
        name=f"Concurrent ({num_workers} workers)",
        iterations=total_requests,
        total_time_ms=total_time,
        avg_time_ms=avg,
        min_time_ms=min(results),
        max_time_ms=max(results),
        std_dev_ms=statistics.stdev(results) if len(results) > 1 else 0,
        requests_per_second=(total_requests / total_time) * 1000,
        avg_latency_ms=avg
    )


def run_all_benchmarks():
    """Run all API benchmarks"""
    print("=" * 70)
    print("Quantum API Access Time Benchmarks")
    print("=" * 70)

    # Start mock server
    port = 8765
    print(f"\nStarting mock API server on port {port}...")
    server = start_mock_server(port)
    base_url = f"http://127.0.0.1:{port}"

    # Wait for server to start
    time.sleep(0.5)

    results: List[APIBenchmarkResult] = []

    # JSON Processing (no network)
    print("\n[JSON Processing]")
    json_benchmarks = [
        benchmark_json_parsing_small,
        benchmark_json_parsing_medium,
        benchmark_json_parsing_large,
        benchmark_json_serialization,
    ]

    for bench_func in json_benchmarks:
        result = bench_func()
        results.append(result)
        print(f"  {result.name:<35} {result.avg_time_ms:>8.4f}ms | {result.requests_per_second:>10.0f} ops/sec")

    # HTTP Requests
    print("\n[HTTP Requests]")
    http_benchmarks = [
        lambda: benchmark_simple_get(base_url),
        lambda: benchmark_json_response(base_url),
        lambda: benchmark_large_response(base_url),
    ]

    for bench_func in http_benchmarks:
        try:
            result = bench_func()
            results.append(result)
            print(f"  {result.name:<35} {result.avg_time_ms:>8.3f}ms | {result.requests_per_second:>10.0f} req/sec")
        except Exception as e:
            print(f"  ERROR: {e}")

    # Concurrency
    print("\n[Concurrency]")
    for workers in [2, 4, 8]:
        try:
            result = benchmark_concurrent_requests(base_url, workers)
            results.append(result)
            print(f"  {result.name:<35} {result.avg_time_ms:>8.3f}ms latency | {result.requests_per_second:>8.0f} req/sec")
        except Exception as e:
            print(f"  {workers} workers ERROR: {e}")

    # Shutdown server
    server.shutdown()

    # Print summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"\n{'Benchmark':<40} {'Avg (ms)':<12} {'Throughput':<15}")
    print("-" * 70)

    for r in results:
        throughput = f"{r.requests_per_second:.0f} ops/sec"
        print(f"{r.name:<40} {r.avg_time_ms:<12.4f} {throughput:<15}")

    return results


if __name__ == "__main__":
    run_all_benchmarks()
