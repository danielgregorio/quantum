CREATE TABLE sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region TEXT NOT NULL,
    amount INTEGER NOT NULL
);

INSERT INTO sales (region, amount) VALUES
    ('North', 120), ('South', 80), ('North', 200), ('East', 50), ('South', 40);
