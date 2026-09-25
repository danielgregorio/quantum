---
source: guide/query.md
source_hash: 571d40ef1966
---

# Consultas a la base de datos (`q:query`)

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/query).
:::

`q:query` ejecuta SQL contra una fuente de datos y te da las filas. Cada ejemplo
de esta página que tiene un **Output** se ejecuta en el conjunto de pruebas
contra la base de datos de ejemplo de más abajo.

## Declarar una fuente de datos {#declaring-a-datasource}

Las fuentes de datos están en `quantum.config.yaml`. SQLite solo necesita un archivo:

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
```

PostgreSQL y MySQL reciben `host`, `port`, `database`, `username` y
`password`. Guarda los secretos en variables de entorno con `${DB_PASSWORD}` — ver
[Instalación](/es/guide/installation).

### La base de datos de ejemplo {#the-example-database}

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

## Leer filas {#reading-rows}

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

- `users` es la lista de filas, y cada fila es un registro: `{users[0].name}`.
- Cada `:name` del SQL se vincula al `q:param` del mismo nombre — el valor
  **nunca** se pega en el SQL, así que lo que llega de un formulario no puede
  inyectar SQL. Un `:name` sin `q:param` es un error de análisis.
- El `type` de un `q:param` es `string`, `integer`, `decimal` o `boolean`.

### Recorrer las filas {#looping-over-the-rows}

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

En una página, el mismo bucle renderiza HTML:
`<ul><q:loop query="products"><li>{products.name}</li></q:loop></ul>`.
`<q:loop items="{products}" var="p">` también funciona, con `{p.name}`.

### Una sola fila {#one-row}

Cuando la consulta devuelve exactamente una fila, sus campos también están
disponibles directamente:

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

## Metadatos de la consulta {#query-metadata}

`<name>_result` describe la consulta:

| Campo | Significado |
|-------|---------|
| `success` | la consulta se ejecutó |
| `recordCount` | filas devueltas |
| `columnList` | nombres de las columnas |
| `executionTime` | milisegundos |
| `affectedRows` | filas cambiadas por INSERT / UPDATE / DELETE |
| `lastInsertId` | id de la fila que creó un INSERT |

`result="meta"` le da otro nombre al mismo objeto.

```xml
<q:component name="Count" xmlns:q="https://quantum.lang/ns">
  <q:query name="users" datasource="db">SELECT id, name FROM users</q:query>
  <q:return value="{users_result.recordCount} rows, columns {join(users_result.columnList)}" />
</q:component>
```

**Output:** `"3 rows, columns id, name"`

## Escribir {#writing}

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

En el SQL dentro de un archivo `.q`, escribe `<` como `&lt;` — el archivo es XML.

Una consulta que falla — un SQL incorrecto, una tabla que no existe, una fuente
de datos que no está declarada — detiene el componente con el mensaje de la base
de datos:

```xml
<q:component name="Failure" xmlns:q="https://quantum.lang/ns">
  <q:query name="x" datasource="db">SELECT * FROM clients</q:query>
</q:component>
```

**Error:** `no such table: clients`

## Paginación {#pagination}

```xml
<q:component name="Pages" xmlns:q="https://quantum.lang/ns">
  <q:query name="page" datasource="db" paginate="true" page="2" page_size="2">
    SELECT name FROM products ORDER BY id
  </q:query>

  <q:return value="{page[0].name} (page {page_result.pagination.currentPage} of {page_result.pagination.totalPages})" />
</q:component>
```

**Output:** `"Monitor (page 2 of 2)"`

`page_result.pagination` también tiene `totalRecords`, `pageSize`, `hasNextPage`,
`hasPreviousPage`, `startRecord` y `endRecord`. En una página, toma el número de
página de la URL: `page="{query.page}"`.

## Consulta de consultas {#query-of-queries}

`source=` ejecuta SQL en memoria sobre las filas de una consulta anterior, que
aparece como una tabla con su nombre:

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

## Transacciones {#transactions}

Dentro de `q:transaction`, las consultas usan su fuente de datos. Si alguna
falla, todo se deshace:

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

## Historial de cambios {#change-history}

Se activa por fuente de datos:

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
    history: true
```

Cada escritura que hace una acción — INSERT, UPDATE, DELETE, y las ediciones en
una [tabla editable](/es/guide/ui#a-table-that-sorts-and-edits-itself) — se registra
en una tabla `quantum_history` de la misma base de datos: cuándo, quién (el
`userName` de la sesión), qué acción, qué fila, y la fila antes y después. Se
escribe en la misma transacción que el cambio, así que una escritura revertida
no deja rastro.

Muestra el historial de una fila en cualquier página con `ui:history`. Una
página de una publicación con una acción para cambiarle el nombre. Guárdala como
`components/post.q`:

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

Después de que `ana` (con sesión iniciada) cambia el título de la publicación de
`First` a `First!`, la página muestra:

| Cuándo | Quién | Acción | Cambio |
|---|---|---|---|
| 2026-09-24 10:02:11 | ana | rename | title: First → First! |

(`tests/docs/test_guide_query_history.py` le cambia el título y verifica esta fila.)

Las sentencias de la página y las migraciones no se registran — solo las
acciones cambian registros. Por ahora, solo SQLite.

## No disponible {#not-available}

Versiones anteriores de esta página describían consultas en caché, reactivas y
por lotes, `maxrows`, `timeout`, procedimientos almacenados (`q:storedproc`),
`q:try`/`q:catch`, varias sentencias en una consulta y parámetros de array para
`IN`. Ninguno funcionaba. El analizador rechaza esos atributos desde la 0.11, y
las etiquetas desconocidas son un error.

## Relacionado {#related}

- [Acciones y formularios](/es/guide/actions) — escribir lo que envía un formulario
- [Bucles](/es/guide/loops) · [Expresiones](/es/guide/databinding)
