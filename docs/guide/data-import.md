# Data Import

`q:data` loads a CSV, JSON or XML file (or URL) into a variable — a list of
records you can loop over, filter, sort and extend, without a database.

The examples below read these files from a `data/` folder next to where you
run `quantum`:

::: code-group

```text [data/clientes.csv]
id,nome,idade,ativo
1,Ana,28,true
2,Bruno,35,true
3,Carla,42,false
```

```json [data/produtos.json]
[
  {"id": 1, "nome": "Caneca", "preco": 30.0},
  {"id": 2, "nome": "Camiseta", "preco": 80.0},
  {"id": 3, "nome": "Adesivo", "preco": 5.0}
]
```

```xml [data/livros.xml]
<livros>
  <livro id="1"><titulo>Dom Casmurro</titulo><ano>1899</ano></livro>
  <livro id="2"><titulo>Vidas Secas</titulo><ano>1938</ano></livro>
</livros>
```

:::

## CSV

Declare the columns to get typed values. Columns you do not declare still come
through, as text.

```xml
<q:data name="clientes" source="data/clientes.csv" type="csv">
  <q:column name="id" type="integer" />
  <q:column name="nome" type="string" />
  <q:column name="idade" type="integer" />
  <q:column name="ativo" type="boolean" />
</q:data>

<q:loop items="{clientes}" var="c">
  <p>{c.nome}, {c.idade}</p>
</q:loop>
```

`clientes` holds:

```text
[{id: 1, nome: "Ana", idade: 28, ativo: true},
 {id: 2, nome: "Bruno", idade: 35, ativo: true},
 {id: 3, nome: "Carla", idade: 42, ativo: false}]
```

Column types: `string`, `integer`, `decimal`, `boolean`, `json`, `array`.
`true`, `1`, `yes` and `on` read as a true boolean.

## JSON

A JSON array becomes the list as it is; a single object becomes a list of one.

```xml
<q:data name="produtos" source="data/produtos.json" type="json" />
```

## XML

`xpath` on `q:data` selects the records; each `q:field` picks a value from one
record, relative to it.

```xml
<q:data name="livros" source="data/livros.xml" type="xml" xpath=".//livro">
  <q:field name="id" xpath="@id" type="integer" />
  <q:field name="titulo" xpath="titulo/text()" />
  <q:field name="ano" xpath="ano/text()" type="integer" />
</q:data>
```

`livros` holds `[{id: 1, titulo: "Dom Casmurro", ano: 1899}, {id: 2, titulo: "Vidas Secas", ano: 1938}]`.

Field paths understand `@attr`, `child/text()`, `child/@attr` and a plain
`child`.

## Transforming

Operations inside `q:transform` run in order:

```xml
<q:data name="caros" source="data/produtos.json" type="json">
  <q:transform>
    <q:compute field="comDesconto" expression="{preco} * 0.9" type="decimal" />
    <q:filter condition="preco > 10" />
    <q:sort by="preco" order="desc" />
    <q:limit value="2" />
  </q:transform>
</q:data>
```

`caros` holds `[{nome: "Camiseta", preco: 80.0, comDesconto: 72.0}, {nome: "Caneca", preco: 30.0, comDesconto: 27.0}]`
(and the `id` of each).

| Operation | Does |
|-----------|------|
| `q:filter condition="…"` | keeps records where the condition is true — same syntax as `q:if`, with the record's fields as variables |
| `q:sort by="campo" order="asc\|desc"` | sorts by one field |
| `q:limit value="n"` | keeps the first `n` |
| `q:compute field="novo" expression="…" type="…"` | adds a field computed from the record |

## When the import fails

A missing file or invalid content does **not** stop the page. The variable is
empty, and `{nome_result}` says what happened:

```xml
<q:data name="clientes" source="data/clientes.csv" type="csv" />

<q:if condition="clientes_result.success">
  <p>{clientes_result.recordCount} clientes</p>
  <q:else><p>Não foi possível ler: {clientes_result.error.message}</p></q:else>
</q:if>
```

::: warning
A failed import is silent unless you check `_result`. Whether it should be an
error by default is an open decision of the language specification (known gap
`G16`).
:::
