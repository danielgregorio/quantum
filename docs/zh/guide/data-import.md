---
source: guide/data-import.md
source_hash: d6576ff27031
---
# 数据导入

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/data-import)为准。
:::

`q:data` 把一个 CSV、JSON 或 XML 文件（或 URL）加载到一个变量中——一个记录列表，你可以遍历、过滤、排序和扩展它，不需要数据库。

下面的示例从运行 `quantum` 的位置旁边的 `data/` 文件夹读取这些文件：

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

声明列以得到带类型的值。没有声明的列仍会保留，作为文本。

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

`customers` 保存的是：

```text
[{id: 1, name: "Ana", age: 28, active: true},
 {id: 2, name: "Bruno", age: 35, active: true},
 {id: 3, name: "Carla", age: 42, active: false}]
```

列类型：`string`、`integer`、`decimal`、`boolean`、`json`、`array`。`true`、`1`、`yes` 和 `on` 读作布尔真值。`q:column` 只接受 `name` 和 `type`；要只保留部分行，请使用过滤器（[转换](#transforming)）：

```xml
<q:data name="customers" source="data/customers.csv" type="csv">
  <q:column name="age" type="integer" min="18" />
</q:data>
```

**Error:** `<q:column name="age"> min= is not supported`

读取文件：

| 属性 | 默认值 | 含义 |
|-----------|---------|---------|
| `encoding` | `utf-8` | 文件的编码，例如 `latin-1` |
| `skip_rows` | `0` | 在表头之前、顶部要跳过的行数（一个标题、一条说明） |
| `delimiter` | `,` | 分隔符，例如 `;` |
| `quote` | `"` | 引号字符 |
| `header` | `true` | `false`：第一行是数据，字段名为 `0`、`1`… |

## JSON {#json}

JSON 数组原样成为列表；单个对象成为只有一个元素的列表。

```xml
<q:data name="products" source="data/products.json" type="json" />
```

## XML {#xml}

`q:data` 上的 `xpath` 选择记录；每个 `q:field` 从一条记录中取一个值，路径相对于该记录。

```xml
<q:data name="books" source="data/books.xml" type="xml" xpath=".//book">
  <q:field name="id" xpath="@id" type="integer" />
  <q:field name="title" xpath="title/text()" />
  <q:field name="year" xpath="year/text()" type="integer" />
</q:data>
```

`books` 保存的是 `[{id: 1, title: "Dom Casmurro", year: 1899}, {id: 2, title: "Vidas Secas", year: 1938}]`。

字段路径支持 `@attr`、`child/text()`、`child/@attr` 以及普通的 `child`。

## 转换 {#transforming}

`q:transform` 中的操作按顺序执行：

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

`expensive` 保存的是 `[{name: "T-shirt", price: 80.0, discounted: 72.0}, {name: "Mug", price: 30.0, discounted: 27.0}]`（以及每条记录的 `id`）。

| 操作 | 作用 |
|-----------|------|
| `q:filter condition="…"` | 保留条件为真的记录——语法与 `q:if` 相同，记录的字段作为变量 |
| `q:sort by="field" order="asc\|desc"` | 按一个字段排序 |
| `q:limit value="n"` | 保留前 `n` 条 |
| `q:compute field="new" expression="…" type="…"` | 添加一个根据记录计算出的字段 |

## 导入失败时 {#when-the-import-fails}

文件缺失或内容无效会**停止组件**，错误中会指出这次导入、来源和原因：

```xml
<q:data name="customers" source="data/customers.csv" type="csv" />
```

**Error:** `q:data 'customers' could not read 'data/customers.csv'`

如果失败是预期内的、页面应当处理它，就用 `onerror="continue"` 说明。页面会继续执行，`{name_result}` 说明发生了什么：

```xml
<q:data name="customers" source="data/customers.csv" type="csv" onerror="continue" />

<q:if condition="customers_result.success">
  <p>{customers_result.recordCount} customers</p>
  <q:else><p>Could not read: {customers_result.error.message}</p></q:else>
</q:if>
```
