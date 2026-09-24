-- A small shop (SQLite)

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER NOT NULL
);

CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    city TEXT NOT NULL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open', 'shipped', 'cancelled')),
    ordered_on TEXT NOT NULL
);

INSERT INTO products (name, category, price, stock) VALUES
    ('Espresso beans 1kg', 'coffee', 24.90, 40),
    ('Decaf beans 500g', 'coffee', 14.50, 3),
    ('Ceramic mug', 'kitchen', 9.90, 120),
    ('Pour-over kettle', 'kitchen', 49.00, 2),
    ('Paper filters (100)', 'coffee', 4.20, 0),
    ('Hand grinder', 'kitchen', 65.00, 7);

INSERT INTO customers (name, city) VALUES
    ('Ana Souza', 'Recife'),
    ('Bruno Lima', 'Porto Alegre'),
    ('Carla Mendes', 'Recife');

INSERT INTO orders (customer_id, product_id, quantity, status, ordered_on) VALUES
    (1, 1, 2, 'shipped', '2026-09-01'),
    (1, 3, 4, 'open', '2026-09-20'),
    (2, 4, 1, 'open', '2026-09-18'),
    (2, 6, 1, 'cancelled', '2026-09-10'),
    (3, 2, 3, 'shipped', '2026-09-05'),
    (3, 5, 2, 'open', '2026-09-22');
