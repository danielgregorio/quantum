---
source: guide/query.md
source_hash: 571d40ef1966
---
# Consultas ao banco (`q:query`)

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/query). O código é o mesmo do original.
:::

O `q:query` roda SQL numa fonte de dados e devolve as linhas. Cada exemplo com
uma **Saída** nesta página roda na suíte de testes contra o banco de exemplo
abaixo.

## Declarar uma fonte de dados {#declaring-a-datasource}

As fontes de dados ficam no `quantum.config.yaml`. O SQLite precisa só de um
arquivo:

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
```

PostgreSQL e MySQL recebem `host`, `port`, `database`, `username` e
`password`. Guarde segredos em variáveis de ambiente com `${DB_PASSWORD}` —
veja [Instalação](/pt/guide/installation).

### O banco de exemplo {#the-example-database}

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

## Ler linhas {#reading-rows}

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

**Saída:** `[{"name": "Ana", "email": "ana@example.com"}, {"name": "Bruno", "email": "bruno@example.com"}]`

- `users` é a lista de linhas, cada linha um registro: `{users[0].name}`.
- Cada `:name` no SQL é ligado ao `q:param` de mesmo nome — o valor **nunca**
  é colado no SQL, então uma entrada de formulário não consegue injetar SQL.
  Um `:name` sem `q:param` é um erro de parse.
- O `type` no `q:param` é `string`, `integer`, `decimal` ou `boolean`.

### Percorrer as linhas {#looping-over-the-rows}

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

**Saída:** `["Notebook: 5", "Mouse: 40", "Monitor: 0"]`

Numa página, o mesmo loop renderiza HTML:
`<ul><q:loop query="products"><li>{products.name}</li></q:loop></ul>`.
`<q:loop items="{products}" var="p">` também funciona, com `{p.name}`.

### Uma linha {#one-row}

Quando a consulta devolve exatamente uma linha, os campos dela também ficam
disponíveis diretamente:

```xml
<q:component name="One" xmlns:q="https://quantum.lang/ns">
  <q:query name="user" datasource="db">
    SELECT name, email FROM users WHERE id = :id
    <q:param name="id" value="2" type="integer" />
  </q:query>

  <q:return value="{user.name} &lt;{user.email}&gt;" />
</q:component>
```

**Saída:** `"Bruno <bruno@example.com>"`

## Metadados da consulta {#query-metadata}

`<name>_result` descreve a consulta:

| Campo | Significado |
|-------|---------|
| `success` | a consulta rodou |
| `recordCount` | linhas devolvidas |
| `columnList` | nomes das colunas |
| `executionTime` | milissegundos |
| `affectedRows` | linhas alteradas por INSERT / UPDATE / DELETE |
| `lastInsertId` | o id da linha que um INSERT criou |

`result="meta"` dá outro nome ao mesmo objeto.

```xml
<q:component name="Count" xmlns:q="https://quantum.lang/ns">
  <q:query name="users" datasource="db">SELECT id, name FROM users</q:query>
  <q:return value="{users_result.recordCount} rows, columns {join(users_result.columnList)}" />
</q:component>
```

**Saída:** `"3 rows, columns id, name"`

## Escrever {#writing}

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

**Saída:** `"2 restocked, order 1"`

No SQL dentro de um arquivo `.q`, escreva `<` como `&lt;` — o arquivo é XML.

Uma consulta que falha — SQL errado, uma tabela que falta, uma fonte de dados
que não foi declarada — para o componente com a mensagem do banco:

```xml
<q:component name="Failure" xmlns:q="https://quantum.lang/ns">
  <q:query name="x" datasource="db">SELECT * FROM clients</q:query>
</q:component>
```

**Erro:** `no such table: clients`

## Paginação {#pagination}

```xml
<q:component name="Pages" xmlns:q="https://quantum.lang/ns">
  <q:query name="page" datasource="db" paginate="true" page="2" page_size="2">
    SELECT name FROM products ORDER BY id
  </q:query>

  <q:return value="{page[0].name} (page {page_result.pagination.currentPage} of {page_result.pagination.totalPages})" />
</q:component>
```

**Saída:** `"Monitor (page 2 of 2)"`

`page_result.pagination` também tem `totalRecords`, `pageSize`,
`hasNextPage`, `hasPreviousPage`, `startRecord` e `endRecord`. Numa página,
pegue o número da página da URL: `page="{query.page}"`.

## Consulta de consultas {#query-of-queries}

`source=` roda SQL em memória sobre as linhas de uma consulta anterior, que
aparece como uma tabela com o nome dela:

```xml
<q:component name="Summary" xmlns:q="https://quantum.lang/ns">
  <q:query name="all" datasource="db">SELECT name, status FROM users</q:query>

  <q:query name="byStatus" source="all">
    SELECT status, COUNT(*) AS total FROM all GROUP BY status ORDER BY status
  </q:query>

  <q:return value="{byStatus}" />
</q:component>
```

**Saída:** `[{"status": "active", "total": 2}, {"status": "inactive", "total": 1}]`

## Transações {#transactions}

Dentro de `q:transaction`, as consultas usam a fonte de dados dela. Se
qualquer uma falhar, tudo é desfeito:

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

**Saída:** `4`

## Histórico de mudanças {#change-history}

Ligue por fonte de dados:

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
    history: true
```

Cada escrita que uma ação faz — INSERT, UPDATE, DELETE, e edições numa
[tabela editável](/pt/guide/ui#a-table-that-sorts-and-edits-itself) — é
registrada numa tabela `quantum_history` do mesmo banco: quando, quem (o
`userName` da sessão), qual ação, qual linha, e a linha antes e depois. Ela é
gravada na mesma transação da mudança, então uma escrita desfeita não deixa
rastro.

Mostre o histórico de uma linha em qualquer página com `ui:history`. Uma
página de post com uma ação de renomear. Salve como `components/post.q`:

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

Depois que `ana` (tendo entrado) renomeia o post de `First` para `First!`, a
página mostra:

| When | Who | Action | Change |
|---|---|---|---|
| 2026-09-24 10:02:11 | ana | rename | title: First → First! |

(`tests/docs/test_guide_query_history.py` o renomeia e confere esta linha.)

As instruções da página e as migrações não são registradas — só as ações
mudam registros. Por enquanto, só SQLite.

## Não disponível {#not-available}

Versões antigas desta página descreviam consultas com cache, reativas e em
lote, `maxrows`, `timeout`, stored procedures (`q:storedproc`),
`q:try`/`q:catch`, várias instruções numa consulta e parâmetros de array para
`IN`. Nenhum deles funcionava. Os atributos são recusados pelo parser desde a
0.11, e tags desconhecidas são um erro.

## Relacionados {#related}

- [Ações e formulários](/pt/guide/actions) — gravar o que um formulário envia
- [Loops](/pt/guide/loops) · [Expressões](/pt/guide/databinding)
