CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(120) NOT NULL,
    genre TEXT NOT NULL CHECK (genre IN ('novel', 'poetry', 'essay'))
);

INSERT INTO books (title, genre) VALUES ('Dom Casmurro', 'novel'), ('Libertinagem', 'poetry');
