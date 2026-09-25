CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL
);

INSERT INTO products (name, price) VALUES
    ('Notebook', 3500.0), ('Mouse', 80.0), ('Monitor', 1200.0), ('Mousepad', 25.0);
