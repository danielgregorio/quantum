CREATE TABLE tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('billing', 'shipping', 'other')),
    urgent INTEGER NOT NULL DEFAULT 0
);
