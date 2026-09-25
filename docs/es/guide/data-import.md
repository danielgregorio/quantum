---
source: guide/data-import.md
source_hash: d6576ff27031
---

# Importación de datos

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/data-import).
:::

`q:data` carga un archivo (o una URL) CSV, JSON o XML en una variable — una
lista de registros que puedes recorrer, filtrar, ordenar y ampliar, sin una
base de datos.

Los ejemplos de abajo leen estos archivos de una carpeta `data/` junto al lugar
donde ejecutas `quantum`:

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

## CSV {#csv}

Declara las columnas para obtener valores con tipo. Las columnas que no declaras
igual llegan, como texto.

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

`customers` contiene:

```text
[{id: 1, name: "Ana", age: 28, active: true},
 {id: 2, name: "Bruno", age: 35, active: true},
 {id: 3, name: "Carla", age: 42, active: false}]
```

Tipos de columna: `string`, `integer`, `decimal`, `boolean`, `json`, `array`.
`true`, `1`, `yes` y `on` se leen como un booleano verdadero. Un `q:column` solo
acepta `name` y `type`; para quedarte solo con algunas filas, usa un filtro
([Transformar](#transforming)):

```xml
<q:data name="customers" source="data/customers.csv" type="csv">
  <q:column name="age" type="integer" min="18" />
</q:data>
```

**Error:** `<q:column name="age"> min= is not supported`

Leer el archivo:

| Atributo | Por defecto | Significado |
|-----------|---------|---------|
| `encoding` | `utf-8` | la codificación del archivo, p. ej. `latin-1` |
| `skip_rows` | `0` | líneas a saltar al principio, antes del encabezado (un título, una nota) |
| `delimiter` | `,` | el separador, p. ej. `;` |
| `quote` | `"` | el carácter de comillas |
| `header` | `true` | `false`: la primera línea son datos, y los campos son `0`, `1`… |

## JSON {#json}

Un array JSON se convierte en la lista tal como está; un solo objeto se convierte
en una lista de uno.

```xml
<q:data name="products" source="data/products.json" type="json" />
```

## XML {#xml}

`xpath` en `q:data` selecciona los registros; cada `q:field` toma un valor de un
registro, relativo a él.

```xml
<q:data name="books" source="data/books.xml" type="xml" xpath=".//book">
  <q:field name="id" xpath="@id" type="integer" />
  <q:field name="title" xpath="title/text()" />
  <q:field name="year" xpath="year/text()" type="integer" />
</q:data>
```

`books` contiene `[{id: 1, title: "Dom Casmurro", year: 1899}, {id: 2, title: "Vidas Secas", year: 1938}]`.

Las rutas de los campos entienden `@attr`, `child/text()`, `child/@attr` y un
`child` simple.

## Transformar {#transforming}

Las operaciones dentro de `q:transform` se ejecutan en orden:

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

`expensive` contiene `[{name: "T-shirt", price: 80.0, discounted: 72.0}, {name: "Mug", price: 30.0, discounted: 27.0}]`
(y el `id` de cada uno).

| Operación | Hace |
|-----------|------|
| `q:filter condition="…"` | conserva los registros donde la condición es verdadera — la misma sintaxis que `q:if`, con los campos del registro como variables |
| `q:sort by="field" order="asc\|desc"` | ordena por un campo |
| `q:limit value="n"` | conserva los primeros `n` |
| `q:compute field="new" expression="…" type="…"` | agrega un campo calculado a partir del registro |

## Cuando la importación falla {#when-the-import-fails}

Un archivo que no existe o un contenido inválido **detiene el componente** con un
error que nombra la importación, el origen y el motivo:

```xml
<q:data name="customers" source="data/customers.csv" type="csv" />
```

**Error:** `q:data 'customers' could not read 'data/customers.csv'`

Cuando un fallo es esperable y la página debe manejarlo, dilo con
`onerror="continue"`. La página sigue, y `{name_result}` dice lo que pasó:

```xml
<q:data name="customers" source="data/customers.csv" type="csv" onerror="continue" />

<q:if condition="customers_result.success">
  <p>{customers_result.recordCount} customers</p>
  <q:else><p>Could not read: {customers_result.error.message}</p></q:else>
</q:if>
```
