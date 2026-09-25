CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    stock INTEGER NOT NULL
);

INSERT INTO products (name, stock) VALUES
    ('Mug', 40), ('Monitor', 2), ('Cable', 3), ('Keyboard', 25);
