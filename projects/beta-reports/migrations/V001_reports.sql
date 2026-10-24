-- The beta's reports, as the games send them (POST /api/reports), and where they are told.
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game TEXT NOT NULL,
    version TEXT NOT NULL,
    kind TEXT NOT NULL,              -- bug, suggestion or other
    text TEXT NOT NULL,
    screen TEXT NOT NULL DEFAULT '',
    option TEXT NOT NULL DEFAULT '',  -- the option the cursor was on
    context TEXT NOT NULL DEFAULT '', -- where the game was: the world, the season, the club...
    player TEXT NOT NULL DEFAULT '',
    save TEXT NOT NULL DEFAULT '',    -- the game's save, when the player attached it
    created TEXT NOT NULL DEFAULT (datetime('now')),
    issue INTEGER                     -- the issue opened for it (null: not yet)
);

-- Where the reports are told: an issue in a repository of the forge, and the save in a file of it.
CREATE TABLE settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    forge TEXT NOT NULL,              -- the forge's API
    repo TEXT NOT NULL,               -- owner/name
    branch TEXT NOT NULL              -- the branch the saves go to
);
INSERT INTO settings (id, forge, repo, branch)
VALUES (1, 'https://api.github.com', 'danielgregorio/pandafoot', 'beta-reports');
