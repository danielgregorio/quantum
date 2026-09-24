# `quantum check`

`quantum check` reads the project the way the server would and reports, with
file and line, what would otherwise surface only when someone opens the page:

- a page that does not parse;
- a `q:query` whose SQL does not compile against your database — a table or
  column that does not exist, a syntax error — with the database's own message;
- a `{query.field}` a page reads that the query does not return: directly
  (`{post.titulo}`), through a `q:loop` over it (`{linha.titulo}`), a
  `ui:table` / `ui:list` with `source="{query}"`, or a `<ui:column key>`.

```bash
quantum migrate up        # the database the pages run against
quantum check
```

```text
components/index.q:42: <q:query name="tarefas">: no such column: titlo
components/index.q:86: {tarefas.titul}: query "tarefas" returns no column "titul" (columns: id, titulo, prioridade, feita)

2 problem(s) — 1 file(s), 5 query(ies) checked against the database.
```

It exits with `1` when there is a problem, so it fits in CI after
`quantum migrate up`.

## Nothing runs

Each query is **compiled** by the database (`EXPLAIN`), never executed; a
`SELECT`'s columns come from running it with `LIMIT 0`, which returns no row.
The database is opened read-only. A `DELETE` in a page is checked, and deletes
nothing.

## What it does not check

- A datasource it cannot open is a `[NOTE]`, not a silent OK: a SQLite file
  that does not exist yet (run `quantum migrate up`), or a driver other than
  SQLite (not supported yet).
- `q:query datasource="knowledge:…"` (RAG) and queries of queries are not SQL
  on a database, and are skipped.
