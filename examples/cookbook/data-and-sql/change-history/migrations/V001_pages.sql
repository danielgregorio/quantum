CREATE TABLE pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT ''
);

INSERT INTO pages (title, body) VALUES ('Welcome', 'First draft.');
