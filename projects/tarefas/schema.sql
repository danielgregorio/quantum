-- The tables as they should be (M6, SPEC DB-10). Edit this file, then:
--   quantum migrate plan                  # what changes, what loses data
--   quantum migrate plan --write <name>   # save it as the next migration
--   quantum migrate up

CREATE TABLE tarefas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    prioridade TEXT NOT NULL DEFAULT 'media' CHECK (prioridade IN ('baixa', 'media', 'alta')),
    feita INTEGER NOT NULL DEFAULT 0,
    criada_em TEXT DEFAULT (datetime('now'))
);
