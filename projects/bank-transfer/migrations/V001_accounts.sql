-- Bank transfer (SQLite)

CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_name TEXT NOT NULL,
    -- The database refuses an overdrawn account: a debit that would go below
    -- zero fails, and q:transaction rolls back the whole transfer (DB-4).
    balance NUMERIC NOT NULL DEFAULT 0 CHECK (balance >= 0)
);

CREATE TABLE transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_account_id INTEGER NOT NULL REFERENCES accounts(id),
    to_account_id INTEGER NOT NULL REFERENCES accounts(id),
    amount NUMERIC NOT NULL CHECK (amount > 0),
    transfer_date TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO accounts (account_name, balance) VALUES
    ('Alice', 100),
    ('Bob', 50),
    ('Carol', 0);
