---
source: tools/check.md
source_hash: d23fd88befc7
---

# `quantum check`

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/tools/check).
:::

`quantum check` lee el proyecto como lo haría el servidor e informa, con archivo
y línea, lo que de otro modo solo aparecería cuando alguien abriera la página:

- una página que no se analiza;
- una `q:query` cuyo SQL no compila contra tu base de datos — una tabla o
  columna que no existe, un error de sintaxis — con el mensaje de la propia base;
- un `{query.field}` que una página lee y que la consulta no devuelve:
  directamente (`{post.titulo}`), a través de un `q:loop` sobre ella
  (`{linha.titulo}`), un `ui:table` / `ui:list` con `source="{query}"`, o un
  `<ui:column key>`.

```bash
quantum migrate up        # the database the pages run against
quantum check
```

```text
components/index.q:42: <q:query name="tarefas">: no such column: titlo
components/index.q:86: {tarefas.titul}: query "tarefas" returns no column "titul" (columns: id, titulo, prioridade, feita)

2 problem(s) — 1 file(s), 5 query(ies) checked against the database.
```

Termina con `1` cuando hay un problema, así que encaja en CI después de
`quantum migrate up`.

## No se ejecuta nada {#nothing-runs}
Cada consulta la **compila** la base de datos (`EXPLAIN`), nunca se ejecuta; las
columnas de un `SELECT` salen de ejecutarlo con `LIMIT 0`, que no devuelve
ninguna fila. La base de datos se abre en modo de solo lectura. Un `DELETE` en
una página se verifica, y no borra nada.

## Lo que no verifica {#what-it-does-not-check}
- Una fuente de datos que no puede abrir es una `[NOTE]`, no un OK silencioso:
  un archivo SQLite que todavía no existe (ejecuta `quantum migrate up`), o un
  driver que no sea SQLite (todavía no soportado).
- `q:query datasource="knowledge:…"` (RAG) y las consultas de consultas no son
  SQL sobre una base de datos, y se omiten.
