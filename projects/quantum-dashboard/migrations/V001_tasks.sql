-- Quantum Dashboard - tasks (SQLite)

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done')),
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    created_at TEXT DEFAULT (datetime('now'))
);

INSERT INTO tasks (title, description, priority) VALUES
    ('Read the Quantum guide', 'Start with Pages and Actions.', 'high'),
    ('Write a first page', 'components/index.q is served at /.', 'medium');
INSERT INTO tasks (title, description, priority, status) VALUES
    ('Install Quantum', 'pip install quantum-framework', 'low', 'done');
