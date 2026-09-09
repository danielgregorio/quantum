"""
Python Scripting Benchmarks

Benchmarks for Quantum Python scripting features:
- q:python - Python code execution
- Bridge overhead
- Import performance
- Class/Decorator definitions
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from framework import Benchmark, benchmark, BenchmarkSuite
from runtime.python_bridge import QuantumBridge


# =============================================================================
# Bridge Access Benchmarks
# =============================================================================

@benchmark("bridge_create", category="python", iterations=10000, warmup=1000)
def bench_bridge_create():
    """Benchmark creating QuantumBridge"""
    context = {'x': 1, 'y': 2, 'name': 'test'}
    bridge = QuantumBridge(context)


@benchmark("bridge_get_variable", category="python", iterations=50000, warmup=5000)
def bench_bridge_get_variable():
    """Benchmark getting variable via bridge"""
    context = {'x': 42, 'name': 'Alice', 'items': [1, 2, 3]}
    bridge = QuantumBridge(context)
    value = bridge.x


@benchmark("bridge_set_variable", category="python", iterations=50000, warmup=5000)
def bench_bridge_set_variable():
    """Benchmark setting variable via bridge"""
    context = {}
    bridge = QuantumBridge(context)
    bridge.result = 42


@benchmark("bridge_get_nested", category="python", iterations=10000, warmup=1000)
def bench_bridge_get_nested():
    """Benchmark getting nested variable"""
    context = {'user': {'profile': {'name': 'Alice', 'age': 30}}}
    bridge = QuantumBridge(context)
    user = bridge.user


@benchmark("bridge_export", category="python", iterations=10000, warmup=1000)
def bench_bridge_export():
    """Benchmark export method"""
    context = {}
    bridge = QuantumBridge(context)
    bridge.export('result', {'value': 42, 'status': 'ok'})


# =============================================================================
# Python Execution Benchmarks
# =============================================================================

@benchmark("exec_simple", category="python", iterations=10000, warmup=1000)
def bench_exec_simple():
    """Benchmark simple Python execution"""
    context = {}
    bridge = QuantumBridge(context)
    namespace = {'q': bridge, '__builtins__': __builtins__}

    code = "q.result = 1 + 1"
    exec(code, namespace)


@benchmark("exec_arithmetic", category="python", iterations=10000, warmup=1000)
def bench_exec_arithmetic():
    """Benchmark arithmetic operations"""
    context = {'a': 10, 'b': 20, 'c': 30}
    bridge = QuantumBridge(context)
    namespace = {'q': bridge, '__builtins__': __builtins__}

    code = """
x = q.a + q.b * q.c
y = (x - q.a) / q.b
q.result = x + y
"""
    exec(code, namespace)


@benchmark("exec_loop_100", category="python", iterations=1000, warmup=100)
def bench_exec_loop_100():
    """Benchmark loop with 100 iterations"""
    context = {}
    bridge = QuantumBridge(context)
    namespace = {'q': bridge, '__builtins__': __builtins__}

    code = """
total = 0
for i in range(100):
    total += i
q.result = total
"""
    exec(code, namespace)


@benchmark("exec_loop_1000", category="python", iterations=500, warmup=50)
def bench_exec_loop_1000():
    """Benchmark loop with 1000 iterations"""
    context = {}
    bridge = QuantumBridge(context)
    namespace = {'q': bridge, '__builtins__': __builtins__}

    code = """
total = 0
for i in range(1000):
    total += i
q.result = total
"""
    exec(code, namespace)


@benchmark("exec_list_comprehension", category="python", iterations=1000, warmup=100)
def bench_exec_list_comprehension():
    """Benchmark list comprehension"""
    context = {}
    bridge = QuantumBridge(context)
    namespace = {'q': bridge, '__builtins__': __builtins__}

    code = """
squares = [x**2 for x in range(100)]
q.result = sum(squares)
"""
    exec(code, namespace)


@benchmark("exec_function_def", category="python", iterations=5000, warmup=500)
def bench_exec_function_def():
    """Benchmark function definition and call"""
    context = {}
    bridge = QuantumBridge(context)
    namespace = {'q': bridge, '__builtins__': __builtins__}

    code = """
def calculate(x, y):
    return x * y + x - y

q.result = calculate(10, 5)
"""
    exec(code, namespace)


@benchmark("exec_recursive_function", category="python", iterations=1000, warmup=100)
def bench_exec_recursive_function():
    """Benchmark recursive function (factorial of 10)"""
    context = {}
    bridge = QuantumBridge(context)
    namespace = {'q': bridge, '__builtins__': __builtins__}

    code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

q.result = factorial(10)
"""
    exec(code, namespace)


@benchmark("exec_class_def", category="python", iterations=2000, warmup=200)
def bench_exec_class_def():
    """Benchmark class definition and instantiation"""
    context = {}
    bridge = QuantumBridge(context)
    namespace = {'q': bridge, '__builtins__': __builtins__}

    code = """
class Calculator:
    def __init__(self, initial=0):
        self.value = initial

    def add(self, x):
        self.value += x
        return self

    def multiply(self, x):
        self.value *= x
        return self

    def result(self):
        return self.value

calc = Calculator(10)
q.result = calc.add(5).multiply(2).result()
"""
    exec(code, namespace)


@benchmark("exec_exception_handling", category="python", iterations=5000, warmup=500)
def bench_exec_exception_handling():
    """Benchmark try/except handling"""
    context = {}
    bridge = QuantumBridge(context)
    namespace = {'q': bridge, '__builtins__': __builtins__}

    code = """
try:
    result = 10 / 2
except ZeroDivisionError:
    result = 0
finally:
    q.result = result
"""
    exec(code, namespace)


@benchmark("exec_with_imports", category="python", iterations=500, warmup=50)
def bench_exec_with_imports():
    """Benchmark execution with imports"""
    context = {}
    bridge = QuantumBridge(context)
    namespace = {'q': bridge, '__builtins__': __builtins__}

    code = """
import json
import math

data = {'value': math.pi, 'squared': math.pi ** 2}
q.result = json.dumps(data)
"""
    exec(code, namespace)


# =============================================================================
# Data Processing in Python
# =============================================================================

@benchmark("py_filter_map", category="python_data", iterations=500, warmup=50)
def bench_py_filter_map():
    """Benchmark filter and map operations"""
    context = {}
    bridge = QuantumBridge(context)
    namespace = {'q': bridge, '__builtins__': __builtins__}

    code = """
data = list(range(1000))
filtered = [x for x in data if x % 2 == 0]
mapped = [x * 2 for x in filtered]
q.result = sum(mapped)
"""
    exec(code, namespace)


@benchmark("py_dict_processing", category="python_data", iterations=500, warmup=50)
def bench_py_dict_processing():
    """Benchmark dictionary processing"""
    context = {}
    bridge = QuantumBridge(context)
    namespace = {'q': bridge, '__builtins__': __builtins__}

    code = """
data = [{'id': i, 'value': i * 10, 'category': f'cat{i % 5}'} for i in range(100)]
by_category = {}
for item in data:
    cat = item['category']
    if cat not in by_category:
        by_category[cat] = []
    by_category[cat].append(item)
q.result = {k: len(v) for k, v in by_category.items()}
"""
    exec(code, namespace)


@benchmark("py_json_processing", category="python_data", iterations=500, warmup=50)
def bench_py_json_processing():
    """Benchmark JSON processing in Python"""
    context = {}
    bridge = QuantumBridge(context)
    namespace = {'q': bridge, '__builtins__': __builtins__}

    code = """
import json

raw = '{"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}'
data = json.loads(raw)
names = [u['name'] for u in data['users']]
q.result = json.dumps({'names': names})
"""
    exec(code, namespace)


@benchmark("py_string_processing", category="python_data", iterations=1000, warmup=100)
def bench_py_string_processing():
    """Benchmark string processing"""
    context = {}
    bridge = QuantumBridge(context)
    namespace = {'q': bridge, '__builtins__': __builtins__}

    code = """
text = "Hello World! " * 100
words = text.split()
upper_words = [w.upper() for w in words]
q.result = ' '.join(upper_words)
"""
    exec(code, namespace)


@benchmark("py_regex_processing", category="python_data", iterations=500, warmup=50)
def bench_py_regex_processing():
    """Benchmark regex processing"""
    context = {}
    bridge = QuantumBridge(context)
    namespace = {'q': bridge, '__builtins__': __builtins__}

    code = """
import re

text = "Contact: alice@example.com, bob@test.org, charlie@demo.net"
emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}', text)
q.result = emails
"""
    exec(code, namespace)


# =============================================================================
# Comparison: Pure Python vs Bridge
# =============================================================================

@benchmark("pure_python_loop", category="comparison", iterations=1000, warmup=100)
def bench_pure_python_loop():
    """Pure Python loop (no bridge)"""
    total = 0
    for i in range(1000):
        total += i


@benchmark("pure_python_function", category="comparison", iterations=5000, warmup=500)
def bench_pure_python_function():
    """Pure Python function call (no bridge)"""
    def calculate(x, y):
        return x * y + x - y

    result = calculate(10, 5)


@benchmark("pure_python_class", category="comparison", iterations=2000, warmup=200)
def bench_pure_python_class():
    """Pure Python class (no bridge)"""
    class Calculator:
        def __init__(self, initial=0):
            self.value = initial

        def add(self, x):
            self.value += x
            return self

        def result(self):
            return self.value

    calc = Calculator(10)
    result = calc.add(5).result()


# =============================================================================
# Utilities
# =============================================================================

@benchmark("bridge_log", category="utilities", iterations=10000, warmup=1000)
def bench_bridge_log():
    """Benchmark logging via bridge"""
    context = {}
    bridge = QuantumBridge(context)
    bridge.info("Test log message")


@benchmark("bridge_now", category="utilities", iterations=10000, warmup=1000)
def bench_bridge_now():
    """Benchmark datetime via bridge"""
    context = {}
    bridge = QuantumBridge(context)
    now = bridge.now()


@benchmark("bridge_uuid", category="utilities", iterations=5000, warmup=500)
def bench_bridge_uuid():
    """Benchmark UUID generation via bridge"""
    context = {}
    bridge = QuantumBridge(context)
    uuid = bridge.uuid()


@benchmark("bridge_json", category="utilities", iterations=5000, warmup=500)
def bench_bridge_json():
    """Benchmark JSON serialization via bridge"""
    context = {}
    bridge = QuantumBridge(context)
    result = bridge.json({'name': 'Alice', 'age': 30, 'items': [1, 2, 3]})


# =============================================================================
# Run benchmarks
# =============================================================================

def run_python_benchmarks():
    """Run all Python scripting benchmarks"""
    suite = BenchmarkSuite("Quantum Python Scripting Benchmarks")
    suite.run_category("python")
    suite.run_category("python_data")
    suite.run_category("comparison")
    suite.run_category("utilities")
    suite.print_summary()
    return suite


if __name__ == "__main__":
    run_python_benchmarks()
