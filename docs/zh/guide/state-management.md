---
source: guide/state-management.md
source_hash: abd4da66d07f
---

# 状态管理（`q:set`）

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/state-management)为准。
:::

`q:set` 保存一个变量：它把值转换为某个 `type`，检查它，并通过 `operation` 就地修改它。
每个属性及其取值和默认值都在[参考手册](/reference/tags#q-set)中；规则是
[SET-1 到 SET-5](/reference/spec#SET-1)。

本页的每个示例都在 CI 中运行，并显示它返回的结果。

## 保存一个值 {#storing-a-value}

```xml
<q:set name="counter" type="number" value="10" />
<q:return value="{counter}" />
```

**Output:** `10`

### 类型 {#types}

`type` 转换值：`string`、`number`、`decimal`、`boolean`、`array`、`object`、`json`
（以及参考手册中列出的别名）。

```xml
<q:set name="message" type="string" value="Hello World" />
<q:set name="age" type="number" value="25" />
<q:set name="price" type="decimal" value="19.99" />
<q:set name="isActive" type="boolean" value="true" />
<q:return value="{[message, age, price, isActive]}" />
```

**Output:** `["Hello World", 25, 19.99, true]`

```xml
<q:set name="fruits" type="array" value='["apple", "banana", "orange"]' />
<q:set name="user" type="object" value='{"name": "Daniel", "age": 30}' />
<q:set name="config" type="json" value='{"debug": true, "port": 8080}' />
<q:return value="{[fruits, user, config]}" />
```

**Output:** `[["apple", "banana", "orange"], {"name": "Daniel", "age": 30}, {"debug": true, "port": 8080}]`

### 不写 `type` {#without-type}

恰好是一个表达式的 `value` 会保留它计算结果的类型，和 `q:return` 以及组件的 props
一样；其他任何内容都是文本（SET-5）：

```xml
<q:set name="tags" value="{['new', 'sale']}" />
<q:set name="count" value="{len(tags)}" />
<q:set name="label" value="{count} tags" />
<q:set name="code" value="007" />
<q:return value="{[tags, count, label, code]}" />
```

**Output:** `[["new", "sale"], 2, "2 tags", "007"]`

`tags` 是列表，`count` 是数字 2，`label` 和 `code` 是文本。在 1.0 之前，每个没有 `type`
的 `q:set` 都保存文本，所以 `len(tags)` 数的是 `['new', 'sale']` 的字符数。
需要文本的地方请写 `type="string"`。

### 默认值 {#a-default}

当 `value` 什么都得不到时——缺失、`null` 或空文本——保存的是 `default`（SET-1）。
第一次访问时，`session.clicks` 还不存在：

```xml
<q:set name="clicks" value="{session.clicks}" default="0" />
<q:return value="Visits: {clicks}" />
```

**Output:** `Visits: 0`

## 操作 {#operations}

`operation` 就地修改变量（SET-3）。默认是 `assign`。

### 数字 {#numbers}

```xml
<q:set name="counter" type="number" value="0" />
<q:set name="counter" operation="increment" />
<q:set name="counter" operation="increment" />
<q:set name="counter" operation="increment" step="5" />
<q:return value="Counter: {counter}" />
```

**Output:** `Counter: 7`

```xml
<q:set name="total" type="number" value="10" />
<q:set name="total" operation="add" value="5" />
<q:set name="total" operation="multiply" value="2" />
<q:return value="Total: {total}" />
```

**Output:** `Total: 30`

`decrement` 和 `increment` 的用法一样。不存在的变量从 0 开始，对不存在的变量
`append` 会新建一个列表：

```xml
<q:set name="hits" operation="increment" />
<q:set name="items" operation="append" value="first" />
<q:return value="{[hits, items]}" />
```

**Output:** `[1, ["first"]]`

### 列表 {#lists}

```xml
<q:set name="list" type="array" value="[]" />
<q:set name="list" operation="append" value="apple" />
<q:set name="list" operation="append" value="banana" />
<q:set name="list" operation="prepend" value="orange" />
<q:return value="{list}" />
```

**Output:** `["orange", "apple", "banana"]`

`remove` 删除第一个等于 `value` 的项；`removeAt` 删除 `index` 位置的项，从 0 开始计数：

```xml
<q:set name="list" type="array" value='["a", "b", "c", "d"]' />
<q:set name="list" operation="remove" value="b" />
<q:set name="list" operation="removeAt" index="2" />
<q:return value="{list}" />
```

**Output:** `["a", "c"]`

```xml
<q:set name="list" type="array" value='["pear", "apple", "pear", "fig"]' />
<q:set name="list" operation="unique" />
<q:set name="list" operation="sort" />
<q:set name="list" operation="reverse" />
<q:return value="{list}" />
```

**Output:** `["pear", "fig", "apple"]`

```xml
<q:set name="list" type="array" value='["a", "b"]' />
<q:set name="list" operation="clear" />
<q:return value="{list}" />
```

**Output:** `[]`

### 对象 {#objects}

```xml
<q:set name="user" type="object" value="{}" />
<q:set name="user" operation="merge" value='{"name": "Daniel"}' />
<q:set name="user" operation="merge" value='{"age": 30}' />
<q:return value="{user}" />
```

**Output:** `{"name": "Daniel", "age": 30}`

`setProperty` 和 `deleteProperty` 接受一个 `key`。字面文本的 `value` 保持为文本：

```xml
<q:set name="config" type="object" value="{}" />
<q:set name="config" operation="setProperty" key="debug" value="true" />
<q:set name="config" operation="setProperty" key="port" value="8080" />
<q:set name="config" operation="deleteProperty" key="debug" />
<q:return value="{config}" />
```

**Output:** `{"port": "8080"}`

`clone` 保存 `source` 所指变量的一份副本；修改副本不会影响原件：

```xml
<q:set name="original" type="object" value='{"x": 1}' />
<q:set name="copy" operation="clone" source="original" />
<q:set name="copy" operation="setProperty" key="x" value="2" />
<q:return value="{[original, copy]}" />
```

**Output:** `[{"x": 1}, {"x": "2"}]`

### 文本 {#text}

```xml
<q:set name="text" value="  Hello World  " />
<q:set name="text" operation="trim" />
<q:set name="upper" value="{text}" />
<q:set name="upper" operation="uppercase" />
<q:set name="lower" value="{text}" />
<q:set name="lower" operation="lowercase" />
<q:return value="{[text, upper, lower]}" />
```

**Output:** `["Hello World", "HELLO WORLD", "hello world"]`

`format` 保存填入了表达式结果的 `value`：

```xml
<q:set name="name" value="Ana" />
<q:set name="greeting" operation="format" value="Hello, {name}!" />
<q:return value="{greeting}" />
```

**Output:** `Hello, Ana!`

### 类型不对的值 {#the-wrong-kind-of-value}

对类型不对的值执行操作是一个指明变量的错误：

```xml
<q:set name="x" value="1" />
<q:set name="x" operation="append" value="2" />
```

**Error:** `Set execution error for 'x': Cannot perform array operation on non-array`

不存在的操作是解析错误（PARSE-5）：

```xml
<q:set name="x" value="1" operation="explode" />
```

**Error:** `operation="explode" does not exist`

## 配合循环 {#with-loops}

```xml
<q:set name="total" type="number" value="0" />
<q:loop type="range" var="i" from="1" to="5">
  <q:set name="total" operation="add" value="{i}" />
</q:loop>
<q:return value="Total: {total}" />
```

**Output:** `Total: 15`

```xml
<q:set name="results" type="array" value="[]" />
<q:loop type="range" var="i" from="1" to="3">
  <q:set name="results" operation="append" value="{i * 2}" />
</q:loop>
<q:return value="{results}" />
```

**Output:** `[2, 4, 6]`

## 校验 {#validation}

`q:set` 检查它保存的值（SET-4）。通过检查的值会被保存：

```xml
<q:set name="code" type="string" value="ABC1234" pattern="^[A-Z]{3}\d{4}$" />
<q:set name="status" type="string" value="active" enum="pending,active,inactive" />
<q:set name="score" type="number" value="87" min="0" max="100" />
<q:set name="age" type="number" value="25" range="18..120" />
<q:set name="username" type="string" value="ana" minlength="3" maxlength="20" />
<q:return value="{[code, status, score, age, username]}" />
```

**Output:** `["ABC1234", "active", 87, 25, "ana"]`

没有通过检查的值是一个指明变量并说明原因的错误：

```xml
<q:set name="email" type="string" value="" required="true" />
```

**Error:** `Set execution error for 'email': This field cannot be empty`

```xml
<q:set name="age" type="number" value="{null}" nullable="false" />
```

**Error:** `Set execution error for 'age': Variable 'age' cannot be null`

```xml
<q:set name="status" type="string" value="archived" enum="pending,active,inactive" />
```

**Error:** `Set execution error for 'status': Value must be one of: pending, active, inactive`

```xml
<q:set name="age" type="number" value="15" range="18..120" />
```

**Error:** `Set execution error for 'age': Value must be between 18 and 120`

```xml
<q:set name="score" type="number" value="120" min="0" max="100" />
```

**Error:** `Set execution error for 'score': Value must be at most 100`

```xml
<q:set name="username" type="string" value="al" minlength="3" maxlength="20" />
```

**Error:** `Set execution error for 'username': Value must be at least 3 characters`

### 具名校验器 {#named-validators}

`validate` 接受 `email`、`url`、`phone`、`cep`、`cpf`、`cnpj`、`uuid`、`creditcard`、
`ipv4` 或 `ipv6`——或者一个以 `^` 开头的正则表达式：

```xml
<q:set name="website" type="string" value="https://quantumframework.net" validate="url" />
<q:set name="id" type="string" value="7c9e6679-7425-40de-944b-e07fc1f90ae7" validate="uuid" />
<q:set name="ip" type="string" value="192.168.0.1" validate="ipv4" />
<q:return value="valid" />
```

**Output:** `valid`

```xml
<q:set name="email" value="invalid" validate="email" />
```

**Error:** `Set execution error for 'email': Invalid email format`

`cpf` 和 `cnpj`（巴西的税号）会检查校验位，而不只是格式：

```xml
<q:set name="cpf" type="string" value="123.456.789-00" validate="cpf" />
```

**Error:** `Set execution error for 'cpf': Invalid CPF check digit`

## 作用域 {#scopes}

变量存在于 `scope` 指定的地方：`local`（默认）、`function`、`component`、`session`、
`application` 或 `request`（SET-3）。名字本身也可以说明：`session.cart` 就是用户会话中的
`cart`。页面的变量存在于服务器上，持续一次请求（SET-2）；必须比请求存活更久的东西放在
`session` 或数据库中。会话见[会话](/guide/sessions)。

```xml
<q:function name="calculate">
  <q:set name="result" type="number" value="0" scope="function" />
  <q:set name="result" operation="add" value="42" />
  <q:return value="{result}" />
</q:function>
<q:return value="{calculate()}" />
```

**Output:** `42`

## 完整示例 {#a-complete-example}

```xml
<q:component name="ShoppingCart" xmlns:q="https://quantum.lang/ns">
  <q:param name="price" type="number" default="10" />
  <q:param name="quantity" type="number" default="2" />

  <q:set name="subtotal" type="number" value="{price * quantity}" />
  <q:set name="tax" type="number" value="{subtotal * 0.1}" />
  <q:set name="total" type="number" value="{subtotal + tax}" />

  <q:return value="Total: {total}" />
</q:component>
```

**Output:** `Total: 22.0`

## 另请参见 {#see-also}

- [循环（`q:loop`）](/guide/loops)
- [数据绑定](/guide/databinding)
- [组件（`q:component`）](/zh/guide/components)
- [参考手册中的 `q:set`](/reference/tags#q-set)
