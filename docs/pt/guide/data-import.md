---
source: guide/data-import.md
source_hash: d6576ff27031
---
# Importação de dados

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/data-import). O código é o mesmo do original.
:::

O `q:data` carrega um arquivo CSV, JSON ou XML (ou uma URL) numa variável —
uma lista de registros que você pode percorrer, filtrar, ordenar e ampliar,
sem banco de dados.

Os exemplos abaixo leem estes arquivos de uma pasta `data/` ao lado de onde
você roda o `quantum`:

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

Declare as colunas para ter valores tipados. As colunas que você não declara
chegam mesmo assim, como texto.

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

`customers` guarda:

```text
[{id: 1, name: "Ana", age: 28, active: true},
 {id: 2, name: "Bruno", age: 35, active: true},
 {id: 3, name: "Carla", age: 42, active: false}]
```

Tipos de coluna: `string`, `integer`, `decimal`, `boolean`, `json`, `array`.
`true`, `1`, `yes` e `on` são lidos como um boolean verdadeiro. Um
`q:column` aceita só `name` e `type`; para ficar só com algumas linhas, use um
filtro ([Transformar](#transforming)):

```xml
<q:data name="customers" source="data/customers.csv" type="csv">
  <q:column name="age" type="integer" min="18" />
</q:data>
```

**Erro:** `<q:column name="age"> min= is not supported`

Ler o arquivo:

| Atributo | Padrão | Significado |
|-----------|---------|---------|
| `encoding` | `utf-8` | a codificação do arquivo, p. ex. `latin-1` |
| `skip_rows` | `0` | linhas a pular no topo, antes do cabeçalho (um título, uma nota) |
| `delimiter` | `,` | o separador, p. ex. `;` |
| `quote` | `"` | o caractere de aspas |
| `header` | `true` | `false`: a primeira linha é dado, e os campos são `0`, `1`… |

## JSON {#json}

Um array JSON vira a lista como ela é; um objeto único vira uma lista de um.

```xml
<q:data name="products" source="data/products.json" type="json" />
```

## XML {#xml}

`xpath` no `q:data` seleciona os registros; cada `q:field` pega um valor de um
registro, relativo a ele.

```xml
<q:data name="books" source="data/books.xml" type="xml" xpath=".//book">
  <q:field name="id" xpath="@id" type="integer" />
  <q:field name="title" xpath="title/text()" />
  <q:field name="year" xpath="year/text()" type="integer" />
</q:data>
```

`books` guarda `[{id: 1, title: "Dom Casmurro", year: 1899}, {id: 2, title: "Vidas Secas", year: 1938}]`.

Os caminhos dos campos entendem `@attr`, `child/text()`, `child/@attr` e um
`child` simples.

## Transformar {#transforming}

As operações dentro de `q:transform` rodam em ordem:

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

`expensive` guarda `[{name: "T-shirt", price: 80.0, discounted: 72.0}, {name: "Mug", price: 30.0, discounted: 27.0}]`
(e o `id` de cada um).

| Operação | Faz |
|-----------|------|
| `q:filter condition="…"` | mantém os registros em que a condição é verdadeira — a mesma sintaxe do `q:if`, com os campos do registro como variáveis |
| `q:sort by="field" order="asc\|desc"` | ordena por um campo |
| `q:limit value="n"` | mantém os `n` primeiros |
| `q:compute field="new" expression="…" type="…"` | acrescenta um campo calculado a partir do registro |

## Quando a importação falha {#when-the-import-fails}

Um arquivo que falta ou um conteúdo inválido **para o componente** com um
erro que nomeia a importação, a fonte e o motivo:

```xml
<q:data name="customers" source="data/customers.csv" type="csv" />
```

**Erro:** `q:data 'customers' could not read 'data/customers.csv'`

Quando uma falha é esperada e a página deve tratá-la, diga isso com
`onerror="continue"`. A página segue, e `{name_result}` diz o que aconteceu:

```xml
<q:data name="customers" source="data/customers.csv" type="csv" onerror="continue" />

<q:if condition="customers_result.success">
  <p>{customers_result.recordCount} customers</p>
  <q:else><p>Could not read: {customers_result.error.message}</p></q:else>
</q:if>
```
