-- Kanban (SQLite): boards of columns of cards, and who may see and change them.

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member', 'viewer')),
    password_hash TEXT NOT NULL
);

CREATE TABLE boards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    webhook_url TEXT,                                   -- told when a card reaches the done column
    issues_api TEXT NOT NULL DEFAULT 'https://api.github.com',   -- GitHub, or a Gitea or Forgejo of its API
    created_on TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE members (
    board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (board_id, user_id)
);

CREATE TABLE columns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    position INTEGER NOT NULL,
    wip_limit INTEGER,                                  -- cards in progress it may hold; none: no limit
    is_done INTEGER NOT NULL DEFAULT 0                  -- the column a card is finished in
);

CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    column_id INTEGER NOT NULL REFERENCES columns(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    assignee_id INTEGER REFERENCES users(id),
    due_on TEXT,                                        -- a date, YYYY-MM-DD
    labels TEXT NOT NULL DEFAULT '',                    -- comma-separated
    archived INTEGER NOT NULL DEFAULT 0,
    source TEXT,                                        -- where it came from: an issue's URL
    created_on TEXT NOT NULL DEFAULT (datetime('now')),
    started_on TEXT,                                    -- when it left the first column
    done_on TEXT                                        -- when it reached the done column
);

-- The demo: three people, password kanban-demo, and a board to start from.
INSERT INTO users (email, name, role, password_hash) VALUES
    ('ana@example.com', 'Ana', 'admin', '$2b$10$.rB6GAf6cv06/gKV9NWaxeJyqoSJi5lXdB7PRawEfTxAlhgZYwUIa'),
    ('bruno@example.com', 'Bruno', 'member', '$2b$10$.rB6GAf6cv06/gKV9NWaxeJyqoSJi5lXdB7PRawEfTxAlhgZYwUIa'),
    ('carla@example.com', 'Carla', 'viewer', '$2b$10$.rB6GAf6cv06/gKV9NWaxeJyqoSJi5lXdB7PRawEfTxAlhgZYwUIa');

INSERT INTO boards (name, description) VALUES ('Website launch', 'Everything the new site needs before it goes live.');
INSERT INTO members (board_id, user_id) VALUES (1, 1), (1, 2), (1, 3);
INSERT INTO columns (board_id, name, position, wip_limit, is_done) VALUES
    (1, 'To do', 1, NULL, 0), (1, 'Doing', 2, 3, 0), (1, 'Review', 3, 2, 0), (1, 'Done', 4, NULL, 1);
INSERT INTO cards (board_id, column_id, title, description, assignee_id, due_on, labels, started_on, done_on) VALUES
    (1, 1, 'Write the about page', 'Who we are, in two paragraphs, with the team''s photo.', 2, '2026-11-02', 'content', NULL, NULL),
    (1, 1, 'Choose the fonts', 'One for the titles, one for the text; both free.', NULL, NULL, 'design', NULL, NULL),
    (1, 2, 'Set up the domain', 'Point the DNS at the server and renew the certificate.', 1, '2026-10-20', 'ops', '2026-10-15 09:00:00', NULL),
    (1, 2, 'Contact form', 'Name, e-mail and message, sent to the support inbox.', 2, '2026-10-30', 'code', '2026-10-18 14:00:00', NULL),
    (1, 3, 'Home page copy', 'The headline and the three blocks below it.', 3, '2026-10-25', 'content', '2026-10-12 10:00:00', NULL),
    (1, 4, 'Logo', 'The panda, in two sizes and a monochrome version.', 2, '2026-10-10', 'design', '2026-10-01 10:00:00', '2026-10-08 17:00:00');
