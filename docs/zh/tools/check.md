---
source: tools/check.md
source_hash: d23fd88befc7
---

# `quantum check`

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/tools/check)为准。
:::

`quantum check` 像服务器那样读取项目，并带着文件和行号报告那些原本只会在有人打开页面时才暴露的问题：

- 无法解析的页面；
- SQL 无法针对你的数据库编译的 `q:query`——不存在的表或列、语法错误——并附上数据库自己的消息；
- 页面读取了查询并不返回的 `{query.field}`：直接读取（`{post.titulo}`）、通过对它的 `q:loop`（`{linha.titulo}`）、
  带 `source="{query}"` 的 `ui:table` / `ui:list`，或者 `<ui:column key>`。

```bash
quantum migrate up        # the database the pages run against
quantum check
```

```text
components/index.q:42: <q:query name="tarefas">: no such column: titlo
components/index.q:86: {tarefas.titul}: query "tarefas" returns no column "titul" (columns: id, titulo, prioridade, feita)

2 problem(s) — 1 file(s), 5 query(ies) checked against the database.
```

有问题时它以 `1` 退出，因此适合放在 CI 中 `quantum migrate up` 之后。

## 不运行任何东西 {#nothing-runs}
每个查询都由数据库**编译**（`EXPLAIN`），从不执行；`SELECT` 的列来自以 `LIMIT 0` 运行它，不返回任何行。
数据库以只读方式打开。页面中的 `DELETE` 会被检查，但不会删除任何东西。

## 它不检查的内容 {#what-it-does-not-check}
- 它无法打开的数据源会给出一条 `[NOTE]`，而不是默默地通过：尚不存在的 SQLite 文件（运行 `quantum migrate up`），
  或 SQLite 以外的驱动（尚不支持）。
- `q:query datasource="knowledge:…"`（RAG）和对查询的查询不是数据库上的 SQL，会被跳过。
