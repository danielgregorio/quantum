"""
Data Processing Benchmarks

Benchmarks for Quantum data processing features:
- q:query - Database queries
- q:data - Data transformations
- JSON processing
- List/Dict operations
"""

import sys
import sqlite3
import tempfile
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from framework import Benchmark, benchmark, BenchmarkSuite


# =============================================================================
# Database Setup
# =============================================================================

def create_test_database(num_records: int = 1000):
    """Create a test SQLite database with sample data"""
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    conn = sqlite3.connect(db_file.name)
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            age INTEGER,
            city TEXT,
            active INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            product TEXT,
            price REAL,
            quantity INTEGER,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Insert sample data
    cities = ['NYC', 'LA', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia']
    products = ['Laptop', 'Phone', 'Tablet', 'Monitor', 'Keyboard', 'Mouse']

    for i in range(num_records):
        cursor.execute('''
            INSERT INTO users (name, email, age, city, active)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            f'User{i}',
            f'user{i}@example.com',
            20 + (i % 50),
            cities[i % len(cities)],
            1 if i % 3 != 0 else 0
        ))

        # Each user has 1-5 orders
        for j in range(1 + (i % 5)):
            cursor.execute('''
                INSERT INTO orders (user_id, product, price, quantity, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                i + 1,
                products[j % len(products)],
                99.99 + (j * 100),
                1 + (j % 3),
                f'2024-01-{(j % 28) + 1:02d}'
            ))

    conn.commit()
    conn.close()
    return db_file.name


# Global test database
TEST_DB = None


def get_test_db():
    """Get or create test database"""
    global TEST_DB
    if TEST_DB is None:
        TEST_DB = create_test_database(1000)
    return TEST_DB


# =============================================================================
# Database Query Benchmarks
# =============================================================================

@benchmark("query_simple_select", category="database", iterations=500, warmup=50)
def bench_query_simple_select():
    """Benchmark simple SELECT query"""
    conn = sqlite3.connect(get_test_db())
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users LIMIT 10")
    results = cursor.fetchall()
    conn.close()


@benchmark("query_with_where", category="database", iterations=500, warmup=50)
def bench_query_with_where():
    """Benchmark SELECT with WHERE clause"""
    conn = sqlite3.connect(get_test_db())
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE age > 30 AND active = 1")
    results = cursor.fetchall()
    conn.close()


@benchmark("query_with_join", category="database", iterations=200, warmup=20)
def bench_query_with_join():
    """Benchmark SELECT with JOIN"""
    conn = sqlite3.connect(get_test_db())
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.name, o.product, o.price
        FROM users u
        JOIN orders o ON u.id = o.user_id
        WHERE u.active = 1
        LIMIT 100
    ''')
    results = cursor.fetchall()
    conn.close()


@benchmark("query_aggregate", category="database", iterations=500, warmup=50)
def bench_query_aggregate():
    """Benchmark aggregate query"""
    conn = sqlite3.connect(get_test_db())
    cursor = conn.cursor()
    cursor.execute('''
        SELECT city, COUNT(*) as count, AVG(age) as avg_age
        FROM users
        GROUP BY city
    ''')
    results = cursor.fetchall()
    conn.close()


@benchmark("query_subquery", category="database", iterations=200, warmup=20)
def bench_query_subquery():
    """Benchmark query with subquery"""
    conn = sqlite3.connect(get_test_db())
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM users
        WHERE id IN (
            SELECT user_id FROM orders
            WHERE price > 200
        )
    ''')
    results = cursor.fetchall()
    conn.close()


@benchmark("query_insert", category="database", iterations=500, warmup=50)
def bench_query_insert():
    """Benchmark INSERT query"""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)
    ''')
    cursor.execute("INSERT INTO test (value) VALUES (?)", ("test_value",))
    conn.commit()
    conn.close()


@benchmark("query_update", category="database", iterations=500, warmup=50)
def bench_query_update():
    """Benchmark UPDATE query"""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)
    ''')
    cursor.execute("INSERT INTO test (value) VALUES (?)", ("test_value",))
    cursor.execute("UPDATE test SET value = ? WHERE id = 1", ("new_value",))
    conn.commit()
    conn.close()


# =============================================================================
# JSON Processing Benchmarks
# =============================================================================

SAMPLE_JSON_SMALL = json.dumps({
    "name": "Alice",
    "age": 30,
    "email": "alice@example.com"
})

SAMPLE_JSON_MEDIUM = json.dumps({
    "users": [
        {"id": i, "name": f"User{i}", "email": f"user{i}@example.com", "active": i % 2 == 0}
        for i in range(100)
    ]
})

SAMPLE_JSON_LARGE = json.dumps({
    "data": [
        {
            "id": i,
            "name": f"Item{i}",
            "attributes": {
                "color": ["red", "green", "blue"][i % 3],
                "size": ["S", "M", "L", "XL"][i % 4],
                "price": 9.99 + i,
                "tags": [f"tag{j}" for j in range(5)]
            }
        }
        for i in range(1000)
    ]
})


@benchmark("json_parse_small", category="json", iterations=10000, warmup=1000)
def bench_json_parse_small():
    """Benchmark parsing small JSON"""
    data = json.loads(SAMPLE_JSON_SMALL)


@benchmark("json_parse_medium", category="json", iterations=1000, warmup=100)
def bench_json_parse_medium():
    """Benchmark parsing medium JSON (100 items)"""
    data = json.loads(SAMPLE_JSON_MEDIUM)


@benchmark("json_parse_large", category="json", iterations=100, warmup=10)
def bench_json_parse_large():
    """Benchmark parsing large JSON (1000 items)"""
    data = json.loads(SAMPLE_JSON_LARGE)


@benchmark("json_serialize_small", category="json", iterations=10000, warmup=1000)
def bench_json_serialize_small():
    """Benchmark serializing small object to JSON"""
    data = {"name": "Alice", "age": 30, "email": "alice@example.com"}
    result = json.dumps(data)


@benchmark("json_serialize_medium", category="json", iterations=1000, warmup=100)
def bench_json_serialize_medium():
    """Benchmark serializing medium object to JSON"""
    data = {
        "users": [
            {"id": i, "name": f"User{i}", "email": f"user{i}@example.com"}
            for i in range(100)
        ]
    }
    result = json.dumps(data)


@benchmark("json_serialize_large", category="json", iterations=100, warmup=10)
def bench_json_serialize_large():
    """Benchmark serializing large object to JSON"""
    data = {
        "data": [
            {"id": i, "name": f"Item{i}", "value": i * 1.5}
            for i in range(1000)
        ]
    }
    result = json.dumps(data)


# =============================================================================
# List/Dict Operation Benchmarks
# =============================================================================

@benchmark("list_create_100", category="collections", iterations=10000, warmup=1000)
def bench_list_create_100():
    """Benchmark creating list with 100 items"""
    items = [i for i in range(100)]


@benchmark("list_create_1000", category="collections", iterations=1000, warmup=100)
def bench_list_create_1000():
    """Benchmark creating list with 1000 items"""
    items = [i for i in range(1000)]


@benchmark("list_filter", category="collections", iterations=5000, warmup=500)
def bench_list_filter():
    """Benchmark filtering list"""
    items = list(range(1000))
    filtered = [x for x in items if x % 2 == 0]


@benchmark("list_map", category="collections", iterations=5000, warmup=500)
def bench_list_map():
    """Benchmark mapping over list"""
    items = list(range(1000))
    mapped = [x * 2 for x in items]


@benchmark("list_reduce", category="collections", iterations=5000, warmup=500)
def bench_list_reduce():
    """Benchmark reducing list"""
    items = list(range(1000))
    total = sum(items)


@benchmark("list_sort", category="collections", iterations=1000, warmup=100)
def bench_list_sort():
    """Benchmark sorting list"""
    import random
    items = [random.randint(0, 10000) for _ in range(1000)]
    sorted_items = sorted(items)


@benchmark("dict_create", category="collections", iterations=5000, warmup=500)
def bench_dict_create():
    """Benchmark creating dictionary"""
    d = {f"key{i}": i for i in range(100)}


@benchmark("dict_access", category="collections", iterations=10000, warmup=1000)
def bench_dict_access():
    """Benchmark dictionary access"""
    d = {f"key{i}": i for i in range(100)}
    values = [d[f"key{i}"] for i in range(100)]


@benchmark("dict_update", category="collections", iterations=5000, warmup=500)
def bench_dict_update():
    """Benchmark dictionary update"""
    d = {f"key{i}": i for i in range(100)}
    for i in range(100):
        d[f"key{i}"] = i * 2


# =============================================================================
# Data Transformation Benchmarks
# =============================================================================

@benchmark("transform_normalize", category="transform", iterations=1000, warmup=100)
def bench_transform_normalize():
    """Benchmark data normalization"""
    data = [
        {"name": "  Alice  ", "email": "ALICE@EXAMPLE.COM"},
        {"name": "  Bob  ", "email": "BOB@EXAMPLE.COM"},
        {"name": "  Charlie  ", "email": "CHARLIE@EXAMPLE.COM"},
    ] * 100

    normalized = [
        {
            "name": item["name"].strip().title(),
            "email": item["email"].lower()
        }
        for item in data
    ]


@benchmark("transform_aggregate", category="transform", iterations=500, warmup=50)
def bench_transform_aggregate():
    """Benchmark data aggregation"""
    from collections import defaultdict

    data = [
        {"category": f"cat{i % 10}", "value": i * 1.5}
        for i in range(1000)
    ]

    aggregated = defaultdict(lambda: {"count": 0, "sum": 0})
    for item in data:
        cat = item["category"]
        aggregated[cat]["count"] += 1
        aggregated[cat]["sum"] += item["value"]


@benchmark("transform_flatten", category="transform", iterations=1000, warmup=100)
def bench_transform_flatten():
    """Benchmark nested structure flattening"""
    nested = [
        {"items": [{"value": i + j} for j in range(10)]}
        for i in range(100)
    ]

    flattened = [
        item
        for record in nested
        for item in record["items"]
    ]


@benchmark("transform_join", category="transform", iterations=500, warmup=50)
def bench_transform_join():
    """Benchmark joining two datasets"""
    users = [{"id": i, "name": f"User{i}"} for i in range(100)]
    orders = [{"user_id": i % 100, "amount": i * 10} for i in range(500)]

    user_map = {u["id"]: u for u in users}
    joined = [
        {**order, "user_name": user_map[order["user_id"]]["name"]}
        for order in orders
    ]


# =============================================================================
# Run benchmarks
# =============================================================================

def run_data_benchmarks():
    """Run all data processing benchmarks"""
    suite = BenchmarkSuite("Quantum Data Processing Benchmarks")
    suite.run_category("database")
    suite.run_category("json")
    suite.run_category("collections")
    suite.run_category("transform")
    suite.print_summary()
    return suite


if __name__ == "__main__":
    run_data_benchmarks()
