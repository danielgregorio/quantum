CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    priority INTEGER NOT NULL,
    done INTEGER NOT NULL DEFAULT 0
);

INSERT INTO tasks (title, priority, done) VALUES
    ('Write the report', 2, 0),
    ('Call the bank', 1, 0),
    ('Pay the rent', 3, 1);
