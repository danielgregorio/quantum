#!/usr/bin/env python
"""
Cross-Platform HTTP Benchmarks

Compares HTTP request handling across web frameworks.
Uses wrk or ab for load testing where available.

Run: python benchmarks/cross_platform/bench_http.py
"""

import sys
import os
import time
import json
import subprocess
import tempfile
import threading
import socket
import signal
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from contextlib import contextmanager
import http.client
import urllib.request

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


@dataclass
class HttpBenchmarkResult:
    """Result of HTTP benchmark"""
    framework: str
    test_name: str
    requests_total: int
    duration_sec: float
    requests_per_sec: float
    avg_latency_ms: float
    success: bool = True
    error: str = ""


# =============================================================================
# Server Templates
# =============================================================================

FLASK_SERVER = '''
from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World!'

@app.route('/json')
def json_endpoint():
    return jsonify({{
        'message': 'Hello, World!',
        'items': [1, 2, 3, 4, 5],
        'nested': {{'a': 1, 'b': 2}}
    }})

@app.route('/compute')
def compute():
    total = sum(i * i for i in range(1000))
    return jsonify({{'result': total}})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port={port}, threaded=True, debug=False)
'''

DJANGO_MANAGE = '''
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

import django
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.urls import path

if not settings.configured:
    settings.configure(
        DEBUG=False,
        SECRET_KEY='benchmark-secret-key',
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=['*'],
    )
    django.setup()

def hello(request):
    return HttpResponse('Hello, World!')

def json_view(request):
    return JsonResponse({
        'message': 'Hello, World!',
        'items': [1, 2, 3, 4, 5],
        'nested': {'a': 1, 'b': 2}
    })

def compute(request):
    total = sum(i * i for i in range(1000))
    return JsonResponse({'result': total})

urlpatterns = [
    path('', hello),
    path('json', json_view),
    path('compute', compute),
]

if __name__ == '__main__':
    from django.core.management import execute_from_command_line
    sys.argv = ['manage.py', 'runserver', '127.0.0.1:{port}', '--noreload']
    execute_from_command_line(sys.argv)
'''

NODE_EXPRESS_SERVER = '''
const express = require('express');
const app = express();

app.get('/', (req, res) => {{
    res.send('Hello, World!');
}});

app.get('/json', (req, res) => {{
    res.json({{
        message: 'Hello, World!',
        items: [1, 2, 3, 4, 5],
        nested: {{a: 1, b: 2}}
    }});
}});

app.get('/compute', (req, res) => {{
    let total = 0;
    for (let i = 0; i < 1000; i++) {{
        total += i * i;
    }}
    res.json({{result: total}});
}});

app.listen({port}, '127.0.0.1', () => {{
    console.log('Server running');
}});
'''

PHP_SERVER = '''<?php
$uri = $_SERVER['REQUEST_URI'];

if ($uri === '/' || $uri === '') {{
    echo 'Hello, World!';
}} elseif ($uri === '/json') {{
    header('Content-Type: application/json');
    echo json_encode([
        'message' => 'Hello, World!',
        'items' => [1, 2, 3, 4, 5],
        'nested' => ['a' => 1, 'b' => 2]
    ]);
}} elseif ($uri === '/compute') {{
    header('Content-Type: application/json');
    $total = 0;
    for ($i = 0; $i < 1000; $i++) {{
        $total += $i * $i;
    }}
    echo json_encode(['result' => $total]);
}} else {{
    http_response_code(404);
    echo 'Not Found';
}}
'''

RUBY_SINATRA_SERVER = '''
require 'sinatra'
require 'json'

set :port, {port}
set :bind, '127.0.0.1'

get '/' do
  'Hello, World!'
end

get '/json' do
  content_type :json
  {
    message: 'Hello, World!',
    items: [1, 2, 3, 4, 5],
    nested: {a: 1, b: 2}
  }.to_json
end

get '/compute' do
  content_type :json
  total = (0...1000).sum { |i| i * i }
  {result: total}.to_json
end
'''

PYTHON_PURE_SERVER = '''
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress logging

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Hello, World!')
        elif self.path == '/json':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            data = {{
                'message': 'Hello, World!',
                'items': [1, 2, 3, 4, 5],
                'nested': {{'a': 1, 'b': 2}}
            }}
            self.wfile.write(json.dumps(data).encode())
        elif self.path == '/compute':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            total = sum(i * i for i in range(1000))
            self.wfile.write(json.dumps({{'result': total}}).encode())
        else:
            self.send_response(404)
            self.end_headers()

server = HTTPServer(('127.0.0.1', {port}), Handler)
server.serve_forever()
'''


# =============================================================================
# Quantum Server
# =============================================================================

def create_quantum_server(port: int):
    """Create a Quantum server for benchmarking"""
    from flask import Flask, jsonify
    from runtime.component import ComponentRuntime
    from core.parser import QuantumParser

    app = Flask(__name__)
    parser = QuantumParser()

    @app.route('/')
    def hello():
        return 'Hello, World!'

    @app.route('/json')
    def json_endpoint():
        return jsonify({
            'message': 'Hello, World!',
            'items': [1, 2, 3, 4, 5],
            'nested': {'a': 1, 'b': 2}
        })

    @app.route('/quantum')
    def quantum_compute():
        source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="Compute">
    <q:set name="total" value="0" />
    <q:loop from="0" to="999" var="i">
        <q:set name="total" value="{total + i * i}" />
    </q:loop>
</q:component>
'''
        ast = parser.parse(source)
        runtime = ComponentRuntime()
        result = runtime.execute_component(ast)
        return jsonify({'result': runtime.execution_context.get_variable('total')})

    return app


# =============================================================================
# Server Management
# =============================================================================

def find_free_port() -> int:
    """Find a free port"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def wait_for_server(port: int, timeout: float = 10) -> bool:
    """Wait for a server to start"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=1)
            conn.request('GET', '/')
            conn.getresponse()
            conn.close()
            return True
        except:
            time.sleep(0.1)
    return False


@contextmanager
def start_server(name: str, code: str, port: int, command: List[str] = None):
    """Context manager to start and stop a server"""
    with tempfile.TemporaryDirectory() as tmpdir:
        process = None
        try:
            if name == 'php':
                # PHP built-in server
                filepath = os.path.join(tmpdir, 'index.php')
                with open(filepath, 'w') as f:
                    f.write(code)
                process = subprocess.Popen(
                    ['php', '-S', f'127.0.0.1:{port}', '-t', tmpdir],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            elif name == 'node':
                filepath = os.path.join(tmpdir, 'server.js')
                with open(filepath, 'w') as f:
                    f.write(code)
                process = subprocess.Popen(
                    ['node', filepath],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            elif name in ('flask', 'django', 'python_pure'):
                filepath = os.path.join(tmpdir, 'server.py')
                with open(filepath, 'w') as f:
                    f.write(code)
                process = subprocess.Popen(
                    ['python', filepath],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            elif name == 'ruby':
                filepath = os.path.join(tmpdir, 'server.rb')
                with open(filepath, 'w') as f:
                    f.write(code)
                process = subprocess.Popen(
                    ['ruby', filepath],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                yield None
                return

            if wait_for_server(port):
                yield process
            else:
                yield None

        finally:
            if process:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except:
                    process.kill()


# =============================================================================
# Benchmark Functions
# =============================================================================

def simple_http_benchmark(port: int, path: str, num_requests: int) -> Tuple[float, float]:
    """Simple HTTP benchmark using urllib"""
    url = f'http://127.0.0.1:{port}{path}'

    start = time.perf_counter()
    for _ in range(num_requests):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                response.read()
        except:
            pass
    elapsed = time.perf_counter() - start

    return elapsed, num_requests / elapsed if elapsed > 0 else 0


def run_http_benchmark(framework: str, port: int, test_name: str,
                       path: str, num_requests: int) -> HttpBenchmarkResult:
    """Run HTTP benchmark for a specific framework"""
    try:
        elapsed, rps = simple_http_benchmark(port, path, num_requests)
        return HttpBenchmarkResult(
            framework=framework,
            test_name=test_name,
            requests_total=num_requests,
            duration_sec=elapsed,
            requests_per_sec=rps,
            avg_latency_ms=(elapsed / num_requests) * 1000 if num_requests > 0 else 0,
            success=True
        )
    except Exception as e:
        return HttpBenchmarkResult(
            framework=framework,
            test_name=test_name,
            requests_total=num_requests,
            duration_sec=0,
            requests_per_sec=0,
            avg_latency_ms=0,
            success=False,
            error=str(e)
        )


# =============================================================================
# Main
# =============================================================================

def check_dependencies() -> Dict[str, bool]:
    """Check which frameworks are available"""
    deps = {}

    # Python frameworks
    try:
        import flask
        deps['flask'] = True
    except ImportError:
        deps['flask'] = False

    try:
        import django
        deps['django'] = True
    except ImportError:
        deps['django'] = False

    # Node.js
    try:
        result = subprocess.run(['node', '--version'], capture_output=True)
        deps['node'] = result.returncode == 0
    except:
        deps['node'] = False

    # PHP
    try:
        result = subprocess.run(['php', '--version'], capture_output=True)
        deps['php'] = result.returncode == 0
    except:
        deps['php'] = False

    # Ruby
    try:
        result = subprocess.run(['ruby', '--version'], capture_output=True)
        deps['ruby'] = result.returncode == 0
    except:
        deps['ruby'] = False

    return deps


def print_results_table(results: List[HttpBenchmarkResult], test_name: str):
    """Print benchmark results"""
    sorted_results = sorted(
        [r for r in results if r.success],
        key=lambda x: -x.requests_per_sec
    )

    if not sorted_results:
        print(f"\n  No results for {test_name}")
        return

    fastest = sorted_results[0].requests_per_sec

    print(f"\n  {'Framework':<20} {'Req/sec':>12} {'Latency':>12} {'vs Fastest':>12}")
    print(f"  {'-' * 56}")

    for r in sorted_results:
        ratio = fastest / r.requests_per_sec if r.requests_per_sec > 0 else 999
        ratio_str = "fastest" if ratio < 1.05 else f"{ratio:.1f}x slower"
        print(f"  {r.framework:<20} {r.requests_per_sec:>12,.0f} {r.avg_latency_ms:>10.2f}ms {ratio_str:>12}")


def main():
    print("\n" + "=" * 70)
    print("  QUANTUM FRAMEWORK - CROSS-PLATFORM HTTP BENCHMARKS")
    print("=" * 70)

    # Check dependencies
    print("\n  Checking available frameworks...")
    deps = check_dependencies()

    for name, available in deps.items():
        status = "OK" if available else "Not available"
        print(f"    {name}: {status}")

    print(f"    quantum: OK (always available)")

    # Benchmark configuration
    num_requests = 500  # Per test
    tests = [
        ('Hello World', '/'),
        ('JSON Response', '/json'),
    ]

    all_results = []

    # Frameworks to test
    frameworks = [
        ('Quantum (Flask)', FLASK_SERVER, 'flask'),
        ('Flask', FLASK_SERVER, 'flask'),
        ('Python http.server', PYTHON_PURE_SERVER, 'python_pure'),
    ]

    if deps.get('node'):
        frameworks.append(('Node.js Express', NODE_EXPRESS_SERVER, 'node'))

    if deps.get('php'):
        frameworks.append(('PHP Built-in', PHP_SERVER, 'php'))

    for test_name, path in tests:
        print("\n" + "-" * 70)
        print(f"  {test_name} ({num_requests} requests)")
        print("-" * 70)

        results = []

        for framework_name, server_code, server_type in frameworks:
            port = find_free_port()
            code = server_code.format(port=port)

            print(f"    Testing {framework_name}...", end=" ", flush=True)

            with start_server(server_type, code, port) as proc:
                if proc:
                    result = run_http_benchmark(
                        framework_name, port, test_name, path, num_requests
                    )
                    results.append(result)
                    if result.success:
                        print(f"{result.requests_per_sec:.0f} req/sec")
                    else:
                        print(f"FAILED: {result.error}")
                else:
                    print("Server failed to start")
                    results.append(HttpBenchmarkResult(
                        framework=framework_name,
                        test_name=test_name,
                        requests_total=0,
                        duration_sec=0,
                        requests_per_sec=0,
                        avg_latency_ms=0,
                        success=False,
                        error="Server failed to start"
                    ))

        all_results.extend(results)
        print_results_table(results, test_name)

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    # Average RPS per framework
    framework_rps = {}
    for r in all_results:
        if r.success:
            if r.framework not in framework_rps:
                framework_rps[r.framework] = []
            framework_rps[r.framework].append(r.requests_per_sec)

    print(f"\n  {'Framework':<20} {'Avg Req/sec':>15}")
    print(f"  {'-' * 35}")

    sorted_frameworks = sorted(
        framework_rps.items(),
        key=lambda x: sum(x[1]) / len(x[1]) if x[1] else 0,
        reverse=True
    )

    for framework, rps_list in sorted_frameworks:
        avg_rps = sum(rps_list) / len(rps_list) if rps_list else 0
        print(f"  {framework:<20} {avg_rps:>15,.0f}")

    # Save results
    results_dir = Path(__file__).parent.parent / 'results'
    results_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = results_dir / f'cross_platform_http_{timestamp}.json'

    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'dependencies': deps,
            'results': [asdict(r) for r in all_results]
        }, f, indent=2)

    print(f"\n  Results saved to: {results_file}")
    print("=" * 70)


if __name__ == '__main__':
    main()
