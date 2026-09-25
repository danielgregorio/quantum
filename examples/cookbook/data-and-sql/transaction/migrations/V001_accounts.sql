CREATE TABLE accounts (
    id INTEGER PRIMARY KEY,
    owner TEXT NOT NULL,
    balance INTEGER NOT NULL CHECK (balance >= 0)
);

-- Every transfer is logged; one transfer moves at most 1000.
CREATE TABLE transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id INTEGER NOT NULL REFERENCES accounts (id),
    to_id INTEGER NOT NULL REFERENCES accounts (id),
    amount INTEGER NOT NULL CHECK (amount > 0 AND amount <= 1000)
);

INSERT INTO accounts (id, owner, balance) VALUES (1, 'Ana', 1500), (2, 'Bruno', 200);
