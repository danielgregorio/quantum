---
source: guide/query.md
source_hash: 571d40ef1966
---

# 数据库查询（`q:query`）

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/query)为准。
:::

`q:query` 针对一个数据源运行 SQL，并把行交给你。本页中每个带有 **Output** 的示例，
都在测试套件中针对下面的示例数据库运行。

## 声明数据源 {#declaring-a-datasource}

数据源在 `quantum.config.yaml` 中。SQLite 只需要一个文件：

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
```

PostgreSQL 和 MySQL 接受 `host`、`port`、`database`、`username` 和 `password`。
用 `${DB_PASSWORD}` 把密钥放在环境变量中——参见[安装](/zh/guide/installation)。

### 示例数据库 {#the-example-database}

```sql
create table users (id integer primary key, name text, email text, status text);
insert into users (name, email, status) values
  ('Ana', 'ana@example.com', 'active'),
  ('Bruno', 'bruno@example.com', 'active'),
  ('Carla', 'carla@example.com', 'inactive');
create table products (id integer primary key, name text, price real, stock integer);
insert into products (name, price, stock) values
  ('Notebook', 3500.0, 5), ('Mouse', 80.0, 40), ('Monitor', 1200.0, 0);
create table orders (id integer primary key, user_id integer, total real);
```

## 读取行 {#reading-rows}

```xml
<q:component name="ActiveUsers" xmlns:q="https://quantum.lang/ns">
  <q:query name="users" datasource="db">
    SELECT name, email FROM users
    WHERE status = :status
    ORDER BY name
    <q:param name="status" value="active" type="string" />
  </q:query>

  <q:return value="{users}" />
</q:component>
```

**Output:** `[{"name": "Ana", "email": "ana@example.com"}, {"name": "Bruno", "email": "bruno@example.com"}]`

- `users` 是行的列表，每一行是一条记录：`{users[0].name}`。
- SQL 中的每个 `:name` 都绑定到同名的 `q:param`——值**永远不会**被粘贴进 SQL，
  所以表单输入无法注入 SQL。没有 `q:param` 的 `:name` 是解析错误。
- `q:param` 的 `type` 是 `string`、`integer`、`decimal` 或 `boolean`。

### 遍历行 {#looping-over-the-rows}

```xml
<q:component name="UserList" xmlns:q="https://quantum.lang/ns">
  <q:query name="products" datasource="db">
    SELECT name, stock FROM products ORDER BY id
  </q:query>

  <q:loop query="products">
    <q:return value="{products.name}: {products.stock}" />
  </q:loop>
</q:component>
```

**Output:** `["Notebook: 5", "Mouse: 40", "Monitor: 0"]`

在页面中，同样的循环会渲染 HTML：
`<ul><q:loop query="products"><li>{products.name}</li></q:loop></ul>`。
`<q:loop items="{products}" var="p">` 也可以，配合 `{p.name}` 使用。

### 一行 {#one-row}

当查询恰好返回一行时，它的字段也可以直接使用：

```xml
<q:component name="One" xmlns:q="https://quantum.lang/ns">
  <q:query name="user" datasource="db">
    SELECT name, email FROM users WHERE id = :id
    <q:param name="id" value="2" type="integer" />
  </q:query>

  <q:return value="{user.name} &lt;{user.email}&gt;" />
</q:component>
```

**Output:** `"Bruno <bruno@example.com>"`

## 查询元数据 {#query-metadata}

`<name>_result` 描述这次查询：

| 字段 | 含义 |
|-------|---------|
| `success` | 查询已运行 |
| `recordCount` | 返回的行数 |
| `columnList` | 列名 |
| `executionTime` | 毫秒 |
| `affectedRows` | INSERT / UPDATE / DELETE 修改的行数 |
| `lastInsertId` | INSERT 创建的行的 id |

`result="meta"` 给同一个对象另起一个名字。

```xml
<q:component name="Count" xmlns:q="https://quantum.lang/ns">
  <q:query name="users" datasource="db">SELECT id, name FROM users</q:query>
  <q:return value="{users_result.recordCount} rows, columns {join(users_result.columnList)}" />
</q:component>
```

**Output:** `"3 rows, columns id, name"`

## 写入 {#writing}

```xml
<q:component name="Stock" xmlns:q="https://quantum.lang/ns">
  <q:query name="restock" datasource="db">
    UPDATE products SET stock = stock + :amount WHERE stock &lt; :limit
    <q:param name="amount" value="10" type="integer" />
    <q:param name="limit" value="10" type="integer" />
  </q:query>

  <q:query name="placed" datasource="db">
    INSERT INTO orders (user_id, total) VALUES (:user, :total)
    <q:param name="user" value="1" type="integer" />
    <q:param name="total" value="80.0" type="decimal" />
  </q:query>

  <q:return value="{restock_result.affectedRows} restocked, order {placed_result.lastInsertId}" />
</q:component>
```

**Output:** `"2 restocked, order 1"`

在 `.q` 文件的 SQL 中，把 `<` 写成 `&lt;`——这个文件是 XML。

失败的查询——错误的 SQL、不存在的数据表、没有声明的数据源——会带着数据库给出的消息让组件停止：

```xml
<q:component name="Failure" xmlns:q="https://quantum.lang/ns">
  <q:query name="x" datasource="db">SELECT * FROM clients</q:query>
</q:component>
```

**Error:** `no such table: clients`

## 分页 {#pagination}

```xml
<q:component name="Pages" xmlns:q="https://quantum.lang/ns">
  <q:query name="page" datasource="db" paginate="true" page="2" page_size="2">
    SELECT name FROM products ORDER BY id
  </q:query>

  <q:return value="{page[0].name} (page {page_result.pagination.currentPage} of {page_result.pagination.totalPages})" />
</q:component>
```

**Output:** `"Monitor (page 2 of 2)"`

`page_result.pagination` 还有 `totalRecords`、`pageSize`、`hasNextPage`、
`hasPreviousPage`、`startRecord` 和 `endRecord`。在页面中，从 URL 获取页码：
`page="{query.page}"`。

## 查询的查询 {#query-of-queries}

`source=` 在内存中对之前某个查询的行运行 SQL，这个查询结果以同名数据表的形式出现：

```xml
<q:component name="Summary" xmlns:q="https://quantum.lang/ns">
  <q:query name="all" datasource="db">SELECT name, status FROM users</q:query>

  <q:query name="byStatus" source="all">
    SELECT status, COUNT(*) AS total FROM all GROUP BY status ORDER BY status
  </q:query>

  <q:return value="{byStatus}" />
</q:component>
```

**Output:** `[{"status": "active", "total": 2}, {"status": "inactive", "total": 1}]`

## 事务 {#transactions}

在 `q:transaction` 中，查询使用它的数据源。其中任何一个失败，所有操作都会撤销：

```xml
<q:component name="Order" xmlns:q="https://quantum.lang/ns">
  <q:transaction datasource="db">
    <q:query name="order">
      INSERT INTO orders (user_id, total) VALUES (1, 3500.0)
    </q:query>
    <q:query name="stock">
      UPDATE products SET stock = stock - 1 WHERE name = 'Notebook'
    </q:query>
  </q:transaction>

  <q:query name="left" datasource="db">SELECT stock FROM products WHERE name = 'Notebook'</q:query>
  <q:return value="{left.stock}" />
</q:component>
```

**Output:** `4`

## 变更历史 {#change-history}

按数据源开启：

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
    history: true
```

动作的每一次写入——INSERT、UPDATE、DELETE，以及[可编辑表格](/zh/guide/ui#a-table-that-sorts-and-edits-itself)
中的编辑——都会记录到同一个数据库的 `quantum_history` 数据表中：时间、谁（会话的 `userName`）、
哪个动作、哪一行，以及修改前后的这一行。它与修改在同一个事务中写入，所以回滚的写入不会留下痕迹。

在任何页面上用 `ui:history` 显示一行的历史。一个带有改名动作的文章页面。保存为
`components/post.q`：

```xml
<q:component name="post">
  <q:action name="rename" method="POST">
    <q:param name="title" required="true" />
    <q:query name="renamed" datasource="db">
      UPDATE posts SET title = :title WHERE id = 1
      <q:param name="title" value="{title}" type="string" />
    </q:query>
    <q:redirect url="/post" />
  </q:action>

  <q:query name="post" datasource="db">SELECT id, title FROM posts WHERE id = 1</q:query>

  <ui:window title="{post.title}">
    <ui:form on-submit="rename" submit="Rename" />
    <ui:history table="posts" key="{post.id}" datasource="db" />
  </ui:window>
</q:component>
```

`ana`（已登录）把文章从 `First` 改名为 `First!` 之后，页面显示：

| 时间 | 谁 | 动作 | 变更 |
|---|---|---|---|
| 2026-09-24 10:02:11 | ana | rename | title: First → First! |

（`tests/docs/test_guide_query_history.py` 会执行这次改名并检查这一行。）

页面语句和迁移不会被记录——只有动作会修改记录。目前只支持 SQLite。

## 不可用的功能 {#not-available}

本页的早期版本描述过带缓存的查询、响应式查询和批量查询、`maxrows`、`timeout`、
存储过程（`q:storedproc`）、`q:try`/`q:catch`、一个查询中的多条语句，以及用于 `IN`
的数组参数。它们都不能用。自 0.11 起，解析器会拒绝这些属性，未知的标签是错误。

## 相关内容 {#related}

- [动作与表单](/zh/guide/actions)——写入表单发送的内容
- [循环](/zh/guide/loops) · [表达式](/zh/guide/databinding)
