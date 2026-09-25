CREATE TABLE cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT NOT NULL,
    quantity INTEGER NOT NULL
);

INSERT INTO cart (item, quantity) VALUES ('Coffee', 1), ('Bread', 2);
