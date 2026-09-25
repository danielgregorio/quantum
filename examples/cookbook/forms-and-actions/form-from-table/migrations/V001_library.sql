CREATE TABLE authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(120) NOT NULL,
    author_id INTEGER NOT NULL REFERENCES authors(id),
    genre TEXT NOT NULL CHECK (genre IN ('novel', 'poetry', 'essay')),
    pages INTEGER,
    lent BOOLEAN NOT NULL DEFAULT 0
);

INSERT INTO authors (name) VALUES ('Clarice Lispector'), ('Machado de Assis');
