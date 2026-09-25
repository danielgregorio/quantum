# Database Queries (`q:query`)

`q:query` runs SQL against a datasource and gives you the rows. Every example
with an **Output** on this page runs in the test suite against the example
database below.

## Declaring a datasource

Datasources live in `quantum.config.yaml`. SQLite needs only a file:

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
```

PostgreSQL and MySQL take `host`, `port`, `database`, `username` and
`password`. Keep secrets in environment variables with `${DB_PASSWORD}` — see
[Installation](/guide/installation).

### The example database

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

## Reading rows

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

- `users` is the list of rows, each row a record: `{users[0].name}`.
- Every `:name` in the SQL is bound to the `q:param` of the same name — the
  value is **never** pasted into the SQL, so form input cannot inject SQL. A
  `:name` without a `q:param` is a parse error.
- `type` on `q:param` is `string`, `integer`, `decimal` or `boolean`.

### Looping over the rows

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

In a page, the same loop renders HTML:
`<ul><q:loop query="products"><li>{products.name}</li></q:loop></ul>`.
`<q:loop items="{products}" var="p">` works too, with `{p.name}`.

### One row

When the query returns exactly one row, its fields are also available directly:

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

## Query metadata

`<name>_result` describes the query:

| Field | Meaning |
|-------|---------|
| `success` | the query ran |
| `recordCount` | rows returned |
| `columnList` | column names |
| `executionTime` | milliseconds |
| `affectedRows` | rows changed by INSERT / UPDATE / DELETE |
| `lastInsertId` | id of the row an INSERT created |

`result="meta"` gives the same object another name.

```xml
<q:component name="Count" xmlns:q="https://quantum.lang/ns">
  <q:query name="users" datasource="db">SELECT id, name FROM users</q:query>
  <q:return value="{users_result.recordCount} rows, columns {join(users_result.columnList)}" />
</q:component>
```

**Output:** `"3 rows, columns id, name"`

## Writing

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

In SQL inside a `.q` file, write `<` as `&lt;` — the file is XML.

A query that fails — bad SQL, a missing table, a datasource that is not
declared — stops the component with the database's message:

```xml
<q:component name="Failure" xmlns:q="https://quantum.lang/ns">
  <q:query name="x" datasource="db">SELECT * FROM clients</q:query>
</q:component>
```

**Error:** `no such table: clients`

## Pagination

```xml
<q:component name="Pages" xmlns:q="https://quantum.lang/ns">
  <q:query name="page" datasource="db" paginate="true" page="2" page_size="2">
    SELECT name FROM products ORDER BY id
  </q:query>

  <q:return value="{page[0].name} (page {page_result.pagination.currentPage} of {page_result.pagination.totalPages})" />
</q:component>
```

**Output:** `"Monitor (page 2 of 2)"`

`page_result.pagination` also has `totalRecords`, `pageSize`, `hasNextPage`,
`hasPreviousPage`, `startRecord` and `endRecord`. In a page, take the page
number from the URL: `page="{query.page}"`.

## Query of queries

`source=` runs SQL in memory over the rows of an earlier query, which appears
as a table with its name:

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

## Transactions

Inside `q:transaction`, the queries use its datasource. If any of them fails,
everything is undone:

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

## Change history

Turn it on per datasource:

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
    history: true
```

Every write an action makes — INSERT, UPDATE, DELETE, and edits in an
[editable table](/guide/ui#a-table-that-sorts-and-edits-itself) — is recorded
in a `quantum_history` table of the same database: when, who (the session's
`userName`), which action, which row, and the row before and after. It is
written in the same transaction as the change, so a rolled-back write leaves
no trace.

Show a row's history on any page with `ui:history`. A post page with a
rename action. Save as `components/post.q`:

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

After `ana` (signed in) renames the post from `First` to `First!`, the page
shows:

| When | Who | Action | Change |
|---|---|---|---|
| 2026-09-24 10:02:11 | ana | rename | title: First → First! |

(`tests/docs/test_guide_query_history.py` renames it and checks this row.)

Page statements and migrations are not recorded — only actions change
records. SQLite for now.

## Not available

Earlier versions of this page described cached, reactive and batch queries,
`maxrows`, `timeout`, stored procedures (`q:storedproc`), `q:try`/`q:catch`,
several statements in one query and array parameters for `IN`. None of them
worked. The attributes are refused by the parser since 0.11, and unknown tags
are an error.

## Related

- [Actions & Forms](/guide/actions) — writing what a form sends
- [Loops](/guide/loops) · [Expressions](/guide/databinding)
