# Data Import

`q:data` loads a CSV, JSON or XML file (or URL) into a variable — a list of
records you can loop over, filter, sort and extend, without a database.

The examples below read these files from a `data/` folder next to where you
run `quantum`:

::: code-group

```text [data/customers.csv]
id,name,age,active
1,Ana,28,true
2,Bruno,35,true
3,Carla,42,false
```

```json [data/products.json]
[
  {"id": 1, "name": "Mug", "price": 30.0},
  {"id": 2, "name": "T-shirt", "price": 80.0},
  {"id": 3, "name": "Sticker", "price": 5.0}
]
```

```xml [data/books.xml]
<books>
  <book id="1"><title>Dom Casmurro</title><year>1899</year></book>
  <book id="2"><title>Vidas Secas</title><year>1938</year></book>
</books>
```

:::

## CSV

Declare the columns to get typed values. Columns you do not declare still come
through, as text.

```xml
<q:data name="customers" source="data/customers.csv" type="csv">
  <q:column name="id" type="integer" />
  <q:column name="name" type="string" />
  <q:column name="age" type="integer" />
  <q:column name="active" type="boolean" />
</q:data>

<q:loop items="{customers}" var="c">
  <p>{c.name}, {c.age}</p>
</q:loop>
```

`customers` holds:

```text
[{id: 1, name: "Ana", age: 28, active: true},
 {id: 2, name: "Bruno", age: 35, active: true},
 {id: 3, name: "Carla", age: 42, active: false}]
```

Column types: `string`, `integer`, `decimal`, `boolean`, `json`, `array`.
`true`, `1`, `yes` and `on` read as a true boolean. A `q:column` takes only
`name` and `type`; to keep only some rows, use a filter ([Transforming](#transforming)):

```xml
<q:data name="customers" source="data/customers.csv" type="csv">
  <q:column name="age" type="integer" min="18" />
</q:data>
```

**Error:** `<q:column name="age"> min= is not supported`

Reading the file:

| Attribute | Default | Meaning |
|-----------|---------|---------|
| `encoding` | `utf-8` | the file's encoding, e.g. `latin-1` |
| `skip_rows` | `0` | lines to skip at the top, before the header (a title, a note) |
| `delimiter` | `,` | the separator, e.g. `;` |
| `quote` | `"` | the quote character |
| `header` | `true` | `false`: the first line is data, and the fields are `0`, `1`… |

## JSON

A JSON array becomes the list as it is; a single object becomes a list of one.

```xml
<q:data name="products" source="data/products.json" type="json" />
```

## XML

`xpath` on `q:data` selects the records; each `q:field` picks a value from one
record, relative to it.

```xml
<q:data name="books" source="data/books.xml" type="xml" xpath=".//book">
  <q:field name="id" xpath="@id" type="integer" />
  <q:field name="title" xpath="title/text()" />
  <q:field name="year" xpath="year/text()" type="integer" />
</q:data>
```

`books` holds `[{id: 1, title: "Dom Casmurro", year: 1899}, {id: 2, title: "Vidas Secas", year: 1938}]`.

Field paths understand `@attr`, `child/text()`, `child/@attr` and a plain
`child`.

## Transforming

Operations inside `q:transform` run in order:

```xml
<q:data name="expensive" source="data/products.json" type="json">
  <q:transform>
    <q:compute field="discounted" expression="{price} * 0.9" type="decimal" />
    <q:filter condition="price > 10" />
    <q:sort by="price" order="desc" />
    <q:limit value="2" />
  </q:transform>
</q:data>
```

`expensive` holds `[{name: "T-shirt", price: 80.0, discounted: 72.0}, {name: "Mug", price: 30.0, discounted: 27.0}]`
(and the `id` of each).

| Operation | Does |
|-----------|------|
| `q:filter condition="…"` | keeps records where the condition is true — same syntax as `q:if`, with the record's fields as variables |
| `q:sort by="field" order="asc\|desc"` | sorts by one field |
| `q:limit value="n"` | keeps the first `n` |
| `q:compute field="new" expression="…" type="…"` | adds a field computed from the record |

## When the import fails

A missing file or invalid content **stops the component** with an error that
names the import, the source and the reason:

```xml
<q:data name="customers" source="data/customers.csv" type="csv" />
```

**Error:** `q:data 'customers' could not read 'data/customers.csv'`

When a failure is expected and the page should handle it, say so with
`onerror="continue"`. The page goes on, and `{name_result}` says what happened:

```xml
<q:data name="customers" source="data/customers.csv" type="csv" onerror="continue" />

<q:if condition="customers_result.success">
  <p>{customers_result.recordCount} customers</p>
  <q:else><p>Could not read: {customers_result.error.message}</p></q:else>
</q:if>
```
