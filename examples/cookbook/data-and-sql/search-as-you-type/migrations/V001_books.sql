CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL
);

INSERT INTO books (title, author) VALUES
    ('Emma', 'Jane Austen'),
    ('Persuasion', 'Jane Austen'),
    ('Middlemarch', 'George Eliot'),
    ('Moby-Dick', 'Herman Melville');
