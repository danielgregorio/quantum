CREATE TABLE members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);
INSERT INTO members (name, email) VALUES ('Ana', 'ana@example.com');
