-- The tables as they should be (M6, SPEC DB-10). Edit this file, then:
--   quantum migrate plan                  # what changes, what loses data
--   quantum migrate plan --write <name>   # save it as the next migration
--   quantum migrate up

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    done INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
