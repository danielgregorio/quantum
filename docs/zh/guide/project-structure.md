---
source: guide/project-structure.md
source_hash: 47f6949064e6
---
# 项目结构

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/project-structure)为准。
:::

一个 Quantum Web 应用就是一个文件夹。在其中运行 `quantum start` 即可提供服务。

```text
my-app/
├── quantum.config.yaml     datasources and server settings
├── components/             one .q file per page (and reusable components)
│   ├── index.q             /
│   ├── about.q             /about
│   └── shop/
│       ├── index.q         /shop
│       └── [id].q          /shop/41  (id = 41)
├── static/                 served as-is under /static/
├── migrations/             V001_create_users.sql, applied by `quantum migrate up`
└── data/                   your SQLite files, CSV/JSON for q:data
```

只有 `components/` 是必需的。规则是 [ROUTE-1](../../reference/spec#ROUTE-1)、[DB-6](../../reference/spec#DB-6) 和 [CFG-1](../../reference/spec#CFG-1)；下面的页面在 CI 中实际提供服务（`tests/docs/test_guide_project_structure.py`）。

## 页面与 URL {#pages-and-urls}

`components/` 中的每个 `.q` 文件都按其路径提供服务：

| 文件 | URL |
|------|-----|
| `components/index.q` | `/` |
| `components/about.q` | `/about` |
| `components/shop/index.q` | `/shop` |
| `components/shop/[id].q` | `/shop/<任意值>` |

`[name]` 段匹配任意值，并把它作为参数 `name` 交给页面。保存为 `components/shop/[id].q`：

```xml
<q:component name="product" xmlns:q="https://quantum.lang/ns">
  <q:param name="id" type="integer" />
  <q:query name="product" datasource="db">
    SELECT name, price FROM products WHERE id = :id
    <q:param name="id" value="{id}" type="integer" />
  </q:query>
  <h1>{product.name}</h1>
</q:component>
```

使用[示例数据库](./query#the-example-database)中的产品，`/shop/2` 显示 **Mouse**。没有匹配文件的 URL 返回 `404`。

## quantum.config.yaml {#quantum-config-yaml}

```yaml
server:
  port: 8080
  host: 127.0.0.1

datasources:
  db:
    driver: sqlite
    database: ./data/app.db
```

值可以来自环境变量：`password: ${DB_PASSWORD}`。参见[安装](/zh/guide/installation)和[数据库查询](/zh/guide/query)。

## 迁移 {#migrations}

```bash
quantum migrate create create_users   # writes migrations/V001_create_users.sql and .down.sql
quantum migrate up                    # applies pending migrations
quantum migrate status
quantum migrate down                  # rolls back the last one
```

迁移作用于 `quantum.config.yaml` 中声明的数据源——也就是页面查询的同一个数据库。有多个数据源时，请指定：`quantum migrate --datasource db up`。

### 或者：编写模式，让 Quantum 编写迁移 {#or-write-the-schema-let-quantum-write-the-migration}

维护一个 `schema.sql`，写下数据表**应有的样子**，让 `quantum migrate plan` 推算出迁移：

```bash
quantum migrate plan                     # what changes; what loses data is marked !!
quantum migrate plan --write add_tags    # saves migrations/V00N_add_tags.sql (+ .down.sql), after asking
quantum migrate up
```

```text
Plan: schema.sql vs. the migrations in migrations/

  + add table tags
  ~ rebuild posts (+ slug; status: CHECK)
  + add index posts_slug
```

- 它把 `schema.sql` 与**迁移所产生的**模式（在内存中构建）比较，而不是与你本地的数据库比较——在每台机器上得到相同的答案。
- 新增一个可为空（或有默认值）的列是 `ADD COLUMN`；其他任何变更都会重建数据表并复制各行（SQLite 无法修改列）。
- 删除数据表或列，或修改列的类型，会丢失数据：计划会说明这一点，没有 `--allow-data-loss` 时 `--write` 会拒绝。没有默认值的新 `NOT NULL` 列会被标出：已有的行没有值。
- 回滚迁移会写在旁边。写入之前会检查计划：把它应用到迁移的模式上，必须恰好得到 `schema.sql` 的模式。
- 目前仅支持 SQLite。`projects/tarefas` 维护着一个 `schema.sql`。

## 可复用组件 {#reusable-components}

在页面中使用的组件同样是一个 `.q` 文件：页面用 `q:import` 导入它，并把它当作标签使用。名字以 `_` 开头的文件或文件夹（`components/_parts/Card.q`）永远不会作为页面提供（ROUTE-3）。[组件](/zh/guide/components)中的示例在 CI 中运行。

## 下一步 {#next-steps}

- [快速开始](/zh/guide/quick-start)——一个带数据库和表单的页面
- [动作与表单](/zh/guide/actions)
