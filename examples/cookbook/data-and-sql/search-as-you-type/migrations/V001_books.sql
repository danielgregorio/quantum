CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL
);

INSERT INTO books (title, author) VALUES
    ('Dom Casmurro', 'Machado de Assis'),
    ('Quincas Borba', 'Machado de Assis'),
    ('Vidas Secas', 'Graciliano Ramos'),
    ('Grande Sertão: Veredas', 'João Guimarães Rosa');
