"""
Comparison Benchmarks

Benchmarks comparing Quantum with other platforms:
- Python/Flask equivalents
- FastAPI equivalents
- Raw Python baselines
"""

import sys
import json
import sqlite3
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from framework import Benchmark, benchmark, BenchmarkSuite, BenchmarkResult
from datetime import datetime


# =============================================================================
# Pure Python Baselines
# =============================================================================

@benchmark("baseline_variable_assign", category="baseline", iterations=100000, warmup=10000)
def bench_baseline_variable_assign():
    """Pure Python variable assignment"""
    x = 42
    y = "hello"
    z = [1, 2, 3]


@benchmark("baseline_arithmetic", category="baseline", iterations=100000, warmup=10000)
def bench_baseline_arithmetic():
    """Pure Python arithmetic"""
    a = 10
    b = 20
    c = 30
    result = a + b * c - a / 2


@benchmark("baseline_loop_1000", category="baseline", iterations=1000, warmup=100)
def bench_baseline_loop_1000():
    """Pure Python loop (1000 iterations)"""
    total = 0
    for i in range(1000):
        total += i


@benchmark("baseline_list_comprehension", category="baseline", iterations=5000, warmup=500)
def bench_baseline_list_comprehension():
    """Pure Python list comprehension"""
    squares = [x**2 for x in range(100)]
    total = sum(squares)


@benchmark("baseline_function_call", category="baseline", iterations=50000, warmup=5000)
def bench_baseline_function_call():
    """Pure Python function call"""
    def add(a, b):
        return a + b

    result = add(10, 20)


@benchmark("baseline_dict_operations", category="baseline", iterations=10000, warmup=1000)
def bench_baseline_dict_operations():
    """Pure Python dictionary operations"""
    d = {}
    for i in range(100):
        d[f"key{i}"] = i
    values = [d[f"key{i}"] for i in range(100)]


@benchmark("baseline_json_parse", category="baseline", iterations=5000, warmup=500)
def bench_baseline_json_parse():
    """Pure Python JSON parsing"""
    data = '{"name": "Alice", "age": 30, "items": [1, 2, 3, 4, 5]}'
    result = json.loads(data)


@benchmark("baseline_json_serialize", category="baseline", iterations=5000, warmup=500)
def bench_baseline_json_serialize():
    """Pure Python JSON serialization"""
    data = {"name": "Alice", "age": 30, "items": [1, 2, 3, 4, 5]}
    result = json.dumps(data)


@benchmark("baseline_sqlite_query", category="baseline", iterations=1000, warmup=100)
def bench_baseline_sqlite_query():
    """Pure Python SQLite query"""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test (id INTEGER, value TEXT)")
    cursor.execute("INSERT INTO test VALUES (1, 'test')")
    cursor.execute("SELECT * FROM test")
    result = cursor.fetchall()
    conn.close()


@benchmark("baseline_class_instantiation", category="baseline", iterations=10000, warmup=1000)
def bench_baseline_class_instantiation():
    """Pure Python class instantiation"""
    class User:
        def __init__(self, name, age):
            self.name = name
            self.age = age

        def greet(self):
            return f"Hello, {self.name}"

    user = User("Alice", 30)
    greeting = user.greet()


# =============================================================================
# Flask-style Equivalents
# =============================================================================

class FlaskStyleRequest:
    """Simulates Flask request object"""
    def __init__(self, method="GET", path="/", form=None, args=None, json=None):
        self.method = method
        self.path = path
        self.form = form or {}
        self.args = args or {}
        self.json = json


class FlaskStyleResponse:
    """Simulates Flask response"""
    def __init__(self, data, status=200, content_type="text/html"):
        self.data = data
        self.status = status
        self.content_type = content_type


def flask_style_render_template(template, **context):
    """Simulates Flask template rendering"""
    result = template
    for key, value in context.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


@benchmark("flask_request_handling", category="flask_style", iterations=5000, warmup=500)
def bench_flask_request_handling():
    """Flask-style request handling"""
    request = FlaskStyleRequest(
        method="POST",
        path="/api/users",
        json={"name": "Alice", "age": 30}
    )

    # Simulate route handling
    if request.method == "POST":
        data = request.json
        response = FlaskStyleResponse(
            json.dumps({"status": "created", "id": 1}),
            status=201,
            content_type="application/json"
        )


@benchmark("flask_template_render", category="flask_style", iterations=5000, warmup=500)
def bench_flask_template_render():
    """Flask-style template rendering"""
    template = """
<html>
<head><title>{{title}}</title></head>
<body>
<h1>{{heading}}</h1>
<p>Welcome, {{username}}!</p>
<ul>
{{items}}
</ul>
</body>
</html>
"""
    items_html = "\n".join([f"<li>Item {i}</li>" for i in range(10)])
    result = flask_style_render_template(
        template,
        title="My Page",
        heading="Welcome",
        username="Alice",
        items=items_html
    )


@benchmark("flask_json_api", category="flask_style", iterations=5000, warmup=500)
def bench_flask_json_api():
    """Flask-style JSON API endpoint"""
    request = FlaskStyleRequest(
        method="GET",
        path="/api/users",
        args={"limit": "10", "offset": "0"}
    )

    # Simulate database query
    users = [
        {"id": i, "name": f"User{i}", "email": f"user{i}@example.com"}
        for i in range(10)
    ]

    response = FlaskStyleResponse(
        json.dumps({"users": users, "total": 100}),
        status=200,
        content_type="application/json"
    )


@benchmark("flask_form_processing", category="flask_style", iterations=5000, warmup=500)
def bench_flask_form_processing():
    """Flask-style form processing"""
    request = FlaskStyleRequest(
        method="POST",
        path="/register",
        form={
            "username": "alice",
            "email": "alice@example.com",
            "password": "secret123"
        }
    )

    # Simulate form validation
    errors = []
    if len(request.form.get("username", "")) < 3:
        errors.append("Username too short")
    if "@" not in request.form.get("email", ""):
        errors.append("Invalid email")
    if len(request.form.get("password", "")) < 6:
        errors.append("Password too short")

    if not errors:
        # Simulate user creation
        user = {
            "id": 1,
            "username": request.form["username"],
            "email": request.form["email"]
        }


# =============================================================================
# FastAPI-style Equivalents
# =============================================================================

from dataclasses import dataclass


@dataclass
class FastAPIStyleUser:
    """Pydantic-style model"""
    id: int
    name: str
    email: str
    age: int = 0


def fastapi_style_validate(data: dict, model_class) -> object:
    """Simulates Pydantic validation"""
    return model_class(**data)


@benchmark("fastapi_model_validation", category="fastapi_style", iterations=5000, warmup=500)
def bench_fastapi_model_validation():
    """FastAPI-style model validation"""
    data = {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 30}
    user = fastapi_style_validate(data, FastAPIStyleUser)


@benchmark("fastapi_json_response", category="fastapi_style", iterations=5000, warmup=500)
def bench_fastapi_json_response():
    """FastAPI-style JSON response"""
    users = [
        FastAPIStyleUser(id=i, name=f"User{i}", email=f"user{i}@example.com", age=20+i)
        for i in range(10)
    ]

    # Simulate JSON serialization
    response = json.dumps([
        {"id": u.id, "name": u.name, "email": u.email, "age": u.age}
        for u in users
    ])


@benchmark("fastapi_dependency_injection", category="fastapi_style", iterations=5000, warmup=500)
def bench_fastapi_dependency_injection():
    """FastAPI-style dependency injection"""
    def get_db():
        return {"connection": "sqlite:///:memory:"}

    def get_current_user(db):
        return {"id": 1, "name": "Alice"}

    # Simulate DI resolution
    db = get_db()
    user = get_current_user(db)

    # Simulate endpoint execution
    result = {"user": user, "db_status": "connected"}


# =============================================================================
# ORM-style Equivalents
# =============================================================================

class ORMStyleModel:
    """Simulates SQLAlchemy-style ORM model"""
    _table = "users"
    _fields = ["id", "name", "email", "age"]

    def __init__(self, **kwargs):
        for field in self._fields:
            setattr(self, field, kwargs.get(field))

    @classmethod
    def query(cls):
        return ORMStyleQuery(cls)

    def save(self):
        # Simulate save
        pass


class ORMStyleQuery:
    """Simulates SQLAlchemy-style query builder"""
    def __init__(self, model):
        self.model = model
        self._filters = []
        self._limit = None
        self._offset = None

    def filter(self, **kwargs):
        self._filters.append(kwargs)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def offset(self, n):
        self._offset = n
        return self

    def all(self):
        # Simulate query execution
        return [
            self.model(id=i, name=f"User{i}", email=f"user{i}@example.com", age=20+i)
            for i in range(self._limit or 10)
        ]

    def first(self):
        results = self.all()
        return results[0] if results else None


@benchmark("orm_query_simple", category="orm_style", iterations=2000, warmup=200)
def bench_orm_query_simple():
    """ORM-style simple query"""
    users = ORMStyleModel.query().limit(10).all()


@benchmark("orm_query_filtered", category="orm_style", iterations=2000, warmup=200)
def bench_orm_query_filtered():
    """ORM-style filtered query"""
    users = (
        ORMStyleModel.query()
        .filter(age__gte=25)
        .filter(active=True)
        .limit(10)
        .all()
    )


@benchmark("orm_model_create", category="orm_style", iterations=5000, warmup=500)
def bench_orm_model_create():
    """ORM-style model creation"""
    user = ORMStyleModel(
        id=1,
        name="Alice",
        email="alice@example.com",
        age=30
    )
    user.save()


# =============================================================================
# Run benchmarks
# =============================================================================

def run_comparison_benchmarks():
    """Run all comparison benchmarks"""
    suite = BenchmarkSuite("Quantum Comparison Benchmarks")
    suite.run_category("baseline")
    suite.run_category("flask_style")
    suite.run_category("fastapi_style")
    suite.run_category("orm_style")
    suite.print_summary()
    return suite


if __name__ == "__main__":
    run_comparison_benchmarks()
