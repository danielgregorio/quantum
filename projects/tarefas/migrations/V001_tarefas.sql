-- Tarefas (SQLite)

CREATE TABLE tarefas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    prioridade TEXT NOT NULL DEFAULT 'media' CHECK (prioridade IN ('baixa', 'media', 'alta')),
    feita INTEGER NOT NULL DEFAULT 0,
    criada_em TEXT DEFAULT (datetime('now'))
);

INSERT INTO tarefas (titulo, prioridade) VALUES
    ('Ler o guia do Quantum', 'alta'),
    ('Escrever a primeira página', 'media');
INSERT INTO tarefas (titulo, prioridade, feita) VALUES
    ('Instalar o Quantum', 'baixa', 1);
