CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    password_hash TEXT NOT NULL
);

-- The password is "correct horse battery"; only its bcrypt hash is stored
-- (made with hashPassword, see the sign-up recipe).
INSERT INTO users (email, name, role, password_hash) VALUES
    ('ana@example.com', 'Ana', 'admin',
     '$2b$12$I4TEFfyLIaWrYBSQnyB1cuE1nkqh3CS4qpXmtZcUPUokfv/cOZNnC');
