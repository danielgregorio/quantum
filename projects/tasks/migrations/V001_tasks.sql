-- Tasks (SQLite)

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    done INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

INSERT INTO tasks (title, priority) VALUES
    ('Read the Quantum guide', 'high'),
    ('Write the first page', 'medium');
INSERT INTO tasks (title, priority, done) VALUES
    ('Install Quantum', 'low', 1);
