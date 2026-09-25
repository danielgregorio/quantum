CREATE TABLE items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(40) NOT NULL,
    shelf TEXT NOT NULL CHECK (shelf IN ('A', 'B', 'C')),
    quantity INTEGER NOT NULL DEFAULT 0
);

INSERT INTO items (name, shelf, quantity) VALUES ('Bolts', 'A', 120), ('Nuts', 'B', 80), ('Washers', 'A', 45);
