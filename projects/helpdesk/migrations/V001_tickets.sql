-- Helpdesk (SQLite)

CREATE TABLE tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    email TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    attachment TEXT,             -- the stored file name, under paths.uploads
    attachment_name TEXT,        -- the name it was sent with
    opened_on TEXT NOT NULL DEFAULT (datetime('now'))
);
