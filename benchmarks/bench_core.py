"""
Core Language Benchmarks

Benchmarks for Quantum core language features using parsing and execution.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from framework import Benchmark, benchmark, BenchmarkSuite
from core.parser import QuantumParser


# =============================================================================
# Parsing Benchmarks
# =============================================================================

@benchmark("parse_minimal", category="parsing", iterations=2000, warmup=200)
def bench_parse_minimal():
    """Benchmark parsing minimal component"""
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="Minimal">
    <q:set name="x" value="1" />
</q:component>
'''
    parser = QuantumParser()
    parser.parse(xml)


@benchmark("parse_simple", category="parsing", iterations=1000, warmup=100)
def bench_parse_simple():
    """Benchmark parsing simple component"""
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="Simple">
    <q:set name="x" value="42" />
    <q:set name="y" value="{x * 2}" />
    <q:set name="message" value="Hello World" />
</q:component>
'''
    parser = QuantumParser()
    parser.parse(xml)


@benchmark("parse_with_loop", category="parsing", iterations=500, warmup=50)
def bench_parse_with_loop():
    """Benchmark parsing component with loop"""
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="LoopTest">
    <q:set name="items" value="[1, 2, 3, 4, 5]" />
    <q:set name="sum" value="0" />
    <q:loop items="{items}" var="item">
        <q:set name="sum" value="{sum + item}" />
    </q:loop>
</q:component>
'''
    parser = QuantumParser()
    parser.parse(xml)


@benchmark("parse_with_conditionals", category="parsing", iterations=500, warmup=50)
def bench_parse_with_conditionals():
    """Benchmark parsing component with conditionals"""
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="CondTest">
    <q:set name="score" value="85" />
    <q:if condition="{score >= 90}">
        <q:set name="grade" value="A" />
    </q:if>
    <q:if condition="{score >= 80}">
        <q:set name="grade" value="B" />
    </q:if>
    <q:if condition="{score &lt; 80}">
        <q:set name="grade" value="C" />
    </q:if>
</q:component>
'''
    parser = QuantumParser()
    parser.parse(xml)


@benchmark("parse_with_function", category="parsing", iterations=500, warmup=50)
def bench_parse_with_function():
    """Benchmark parsing component with function"""
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="FuncTest">
    <q:function name="calculate">
        <q:param name="a" type="number" />
        <q:param name="b" type="number" />
        <q:return value="{a + b}" />
    </q:function>
</q:component>
'''
    parser = QuantumParser()
    parser.parse(xml)


@benchmark("parse_with_html", category="parsing", iterations=500, warmup=50)
def bench_parse_with_html():
    """Benchmark parsing component with HTML"""
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="HtmlTest">
    <q:set name="title" value="My Page" />
    <div class="container">
        <h1>{title}</h1>
        <p>Welcome to the page</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </ul>
    </div>
</q:component>
'''
    parser = QuantumParser()
    parser.parse(xml)


@benchmark("parse_complex", category="parsing", iterations=200, warmup=20)
def bench_parse_complex():
    """Benchmark parsing complex component"""
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="Complex">
    <q:set name="users" value='[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]' />
    <q:set name="total" value="0" />
    <q:set name="count" value="0" />

    <q:function name="processUser">
        <q:param name="user" type="object" />
        <q:if condition="{user.age > 20}">
            <q:set name="total" value="{total + user.age}" />
            <q:set name="count" value="{count + 1}" />
        </q:if>
    </q:function>

    <q:loop items="{users}" var="user">
        <q:if condition="{user.age >= 18}">
            <div class="user-card">
                <h3>{user.name}</h3>
                <p>Age: {user.age}</p>
            </div>
        </q:if>
    </q:loop>

    <div class="summary">
        <p>Total users: {count}</p>
        <p>Average age: {total / count}</p>
    </div>
</q:component>
'''
    parser = QuantumParser()
    parser.parse(xml)


@benchmark("parse_ui_component", category="parsing", iterations=300, warmup=30)
def bench_parse_ui_component():
    """Benchmark parsing UI component"""
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="UITest">
    <ui:window title="Dashboard">
        <ui:vbox padding="lg" gap="md">
            <ui:text size="2xl" weight="bold">Dashboard</ui:text>
            <ui:grid cols="3" gap="md">
                <ui:card>
                    <ui:card-header>
                        <ui:text weight="semibold">Users</ui:text>
                    </ui:card-header>
                    <ui:card-body>
                        <ui:text size="3xl">1,234</ui:text>
                    </ui:card-body>
                </ui:card>
                <ui:card>
                    <ui:card-header>
                        <ui:text weight="semibold">Revenue</ui:text>
                    </ui:card-header>
                    <ui:card-body>
                        <ui:text size="3xl">$56,789</ui:text>
                    </ui:card-body>
                </ui:card>
                <ui:card>
                    <ui:card-header>
                        <ui:text weight="semibold">Orders</ui:text>
                    </ui:card-header>
                    <ui:card-body>
                        <ui:text size="3xl">456</ui:text>
                    </ui:card-body>
                </ui:card>
            </ui:grid>
            <ui:table>
                <ui:thead>
                    <ui:tr>
                        <ui:th>Name</ui:th>
                        <ui:th>Email</ui:th>
                        <ui:th>Status</ui:th>
                    </ui:tr>
                </ui:thead>
            </ui:table>
        </ui:vbox>
    </ui:window>
</q:component>
'''
    parser = QuantumParser()
    parser.parse(xml)


@benchmark("parse_python_scripting", category="parsing", iterations=500, warmup=50)
def bench_parse_python_scripting():
    """Benchmark parsing component with Python scripting"""
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="PythonTest">
    <q:pyimport module="json" />
    <q:pyimport module="datetime" as="dt" />

    <q:class name="Calculator">
        def add(self, a, b):
            return a + b
        def multiply(self, a, b):
            return a * b
    </q:class>

    <q:python>
        calc = Calculator()
        result = calc.add(10, 20)
        q.result = result
    </q:python>
</q:component>
'''
    parser = QuantumParser()
    parser.parse(xml)


# =============================================================================
# Expression Evaluation Benchmarks
# =============================================================================

@benchmark("eval_simple_expression", category="expression", iterations=10000, warmup=1000)
def bench_eval_simple_expression():
    """Benchmark simple expression evaluation"""
    from runtime.component import ComponentRuntime
    runtime = ComponentRuntime()
    context = {'x': 10, 'y': 20}
    runtime.context = context
    result = runtime._evaluate_simple_expression("{x + y}", context)


@benchmark("eval_complex_expression", category="expression", iterations=5000, warmup=500)
def bench_eval_complex_expression():
    """Benchmark complex expression evaluation"""
    from runtime.component import ComponentRuntime
    runtime = ComponentRuntime()
    context = {'a': 10, 'b': 20, 'c': 30, 'd': 40}
    runtime.context = context
    result = runtime._evaluate_simple_expression("{(a + b) * (c - d) / (a + 1)}", context)


@benchmark("eval_string_expression", category="expression", iterations=10000, warmup=1000)
def bench_eval_string_expression():
    """Benchmark string expression evaluation"""
    from runtime.component import ComponentRuntime
    runtime = ComponentRuntime()
    context = {'name': 'Alice', 'age': 30}
    runtime.context = context
    result = runtime._evaluate_simple_expression("{name}", context)


@benchmark("eval_list_expression", category="expression", iterations=5000, warmup=500)
def bench_eval_list_expression():
    """Benchmark list expression evaluation"""
    from runtime.component import ComponentRuntime
    runtime = ComponentRuntime()
    context = {'items': [1, 2, 3, 4, 5]}
    runtime.context = context
    result = runtime._evaluate_simple_expression("{items}", context)


@benchmark("eval_dict_expression", category="expression", iterations=5000, warmup=500)
def bench_eval_dict_expression():
    """Benchmark dictionary expression evaluation"""
    from runtime.component import ComponentRuntime
    runtime = ComponentRuntime()
    context = {'user': {'name': 'Alice', 'age': 30, 'city': 'NYC'}}
    runtime.context = context
    result = runtime._evaluate_simple_expression("{user}", context)


@benchmark("eval_conditional_expression", category="expression", iterations=10000, warmup=1000)
def bench_eval_conditional_expression():
    """Benchmark conditional expression evaluation"""
    from runtime.component import ComponentRuntime
    runtime = ComponentRuntime()
    context = {'x': 50, 'min_val': 0, 'max_val': 100}
    runtime.context = context
    result = runtime._evaluate_condition("x >= min_val", context)


# =============================================================================
# Pure Python Comparisons (baseline)
# =============================================================================

@benchmark("pure_python_assign", category="baseline_python", iterations=100000, warmup=10000)
def bench_pure_python_assign():
    """Pure Python variable assignment"""
    x = 42
    y = "hello"
    z = [1, 2, 3]


@benchmark("pure_python_expression", category="baseline_python", iterations=100000, warmup=10000)
def bench_pure_python_expression():
    """Pure Python expression evaluation"""
    a, b, c, d = 10, 20, 30, 40
    result = (a + b) * (c - d) / (a + 1)


@benchmark("pure_python_loop", category="baseline_python", iterations=1000, warmup=100)
def bench_pure_python_loop():
    """Pure Python loop"""
    total = 0
    for i in range(1000):
        total += i


@benchmark("pure_python_conditional", category="baseline_python", iterations=100000, warmup=10000)
def bench_pure_python_conditional():
    """Pure Python conditional"""
    x = 50
    if x > 40:
        result = "high"
    elif x > 20:
        result = "medium"
    else:
        result = "low"


@benchmark("pure_python_function", category="baseline_python", iterations=50000, warmup=5000)
def bench_pure_python_function():
    """Pure Python function call"""
    def add(a, b):
        return a + b
    result = add(10, 20)


@benchmark("pure_python_list_comp", category="baseline_python", iterations=5000, warmup=500)
def bench_pure_python_list_comp():
    """Pure Python list comprehension"""
    squares = [x ** 2 for x in range(100)]


# =============================================================================
# Run benchmarks
# =============================================================================

def run_core_benchmarks():
    """Run all core benchmarks"""
    suite = BenchmarkSuite("Quantum Core Benchmarks")
    suite.run_category("parsing")
    suite.run_category("expression")
    suite.run_category("baseline_python")
    suite.print_summary()
    return suite


if __name__ == "__main__":
    run_core_benchmarks()
