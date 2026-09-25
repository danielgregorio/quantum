---
source: tools/check.md
source_hash: d23fd88befc7
---

# `quantum check`

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/tools/check).
:::

O `quantum check` lê o projeto como o servidor leria e informa, com arquivo e
linha, o que de outro modo só apareceria quando alguém abrisse a página:

- uma página que não passa pelo parser;
- uma `q:query` cujo SQL não compila contra o seu banco de dados — uma tabela ou
  coluna que não existe, um erro de sintaxe — com a mensagem do próprio banco;
- um `{query.field}` que a página lê e que a consulta não retorna: diretamente
  (`{post.titulo}`), por um `q:loop` sobre ela (`{linha.titulo}`), por um
  `ui:table` / `ui:list` com `source="{query}"`, ou por um `<ui:column key>`.

```bash
quantum migrate up        # the database the pages run against
quantum check
```

```text
components/index.q:42: <q:query name="tarefas">: no such column: titlo
components/index.q:86: {tarefas.titul}: query "tarefas" returns no column "titul" (columns: id, titulo, prioridade, feita)

2 problem(s) — 1 file(s), 5 query(ies) checked against the database.
```

Ele termina com `1` quando há um problema, então cabe no CI depois de
`quantum migrate up`.

## Nada é executado {#nothing-runs}
Cada consulta é **compilada** pelo banco de dados (`EXPLAIN`), nunca executada;
as colunas de um `SELECT` vêm de executá-lo com `LIMIT 0`, que não retorna
nenhuma linha. O banco é aberto somente para leitura. Um `DELETE` numa página é
verificado, e não apaga nada.

## O que ele não verifica {#what-it-does-not-check}
- Uma fonte de dados que ele não consegue abrir vira uma `[NOTE]`, não um OK
  silencioso: um arquivo SQLite que ainda não existe (rode `quantum migrate up`),
  ou um driver que não seja SQLite (ainda não suportado).
- `q:query datasource="knowledge:…"` (RAG) e consultas de consultas não são SQL
  num banco de dados, e são ignoradas.
