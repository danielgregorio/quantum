---
source: guide/loops.md
source_hash: 0d3575e1e5eb
---

# 循环结构

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/loops)为准。
:::

Quantum 提供强大的循环结构，灵感来自 ColdFusion 的 `cfloop`，但为现代声明式编程而设计。所有循环都支持变量的数据绑定，并且可以嵌套。

## 循环类型 {#loop-types}

Quantum 有四种循环类型——`range`、`array`、`list` 和 `query`——循环中的每个
`q:return` 都会向循环返回的列表中添加一项（LOOP-1）。
每个属性都在[参考手册](/reference/tags#q-loop)中；规则是
[LOOP-1 到 LOOP-6](/reference/spec#LOOP-1)。

### 范围循环（`type="range"`） {#range-loop-type-range}

遍历一个数字范围，步长可选。

```xml
<q:component name="RangeExample" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="5">
    <q:return value="Number {i}" />
  </q:loop>
</q:component>
```

**Output:** `["Number 1", "Number 2", "Number 3", "Number 4", "Number 5"]`

#### 带步长

```xml
<q:loop type="range" var="i" from="1" to="10" step="2">
  <q:return value="Odd: {i}" />
</q:loop>
```

**Output:** `["Odd: 1", "Odd: 3", "Odd: 5", "Odd: 7", "Odd: 9"]`

### 数组循环（`type="array"`） {#array-loop-type-array}

遍历 JSON 数组，可选地跟踪索引。

```xml
<q:component name="ArrayExample" xmlns:q="https://quantum.lang/ns">
  <q:loop type="array" var="fruit" items='["apple", "banana", "orange"]'>
    <q:return value="Fruit: {fruit}" />
  </q:loop>
</q:component>
```

**Output:** `["Fruit: apple", "Fruit: banana", "Fruit: orange"]`

#### 带索引

```xml
<q:loop type="array" var="fruit" index="idx" items='["apple", "banana", "orange"]'>
  <q:return value="{idx}: {fruit}" />
</q:loop>
```

**Output:** `["0: apple", "1: banana", "2: orange"]`

### 列表循环（`type="list"`） {#list-loop-type-list}

遍历带分隔符的字符串。

```xml
<q:component name="ListExample" xmlns:q="https://quantum.lang/ns">
  <q:loop type="list" var="color" items="red,green,blue">
    <q:return value="Color: {color}" />
  </q:loop>
</q:component>
```

**Output:** `["Color: red", "Color: green", "Color: blue"]`

#### 自定义分隔符

```xml
<q:loop type="list" var="name" items="João|Maria|Pedro" delimiter="|">
  <q:return value="Name: {name}" />
</q:loop>
```

**Output:** `["Name: João", "Name: Maria", "Name: Pedro"]`

## 高级功能 {#advanced-features}

### 数据绑定中的算术 {#arithmetic-in-databinding}

所有循环都支持在变量的数据绑定中使用算术表达式：

```xml
<q:loop type="range" var="i" from="1" to="3">
  <q:return value="Item {i}, Next: {i + 1}, Double: {i * 2}" />
</q:loop>
```

**Output:** `["Item 1, Next: 2, Double: 2", "Item 2, Next: 3, Double: 4", "Item 3, Next: 4, Double: 6"]`

### 嵌套循环 {#nested-loops}

循环可以嵌套，用于处理复杂的数据：

```xml
<q:component name="NestedExample" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="x" from="1" to="2">
    <q:loop type="range" var="y" from="1" to="2">
      <q:return value="({x},{y})" />
    </q:loop>
  </q:loop>
</q:component>
```

**Output:** `["(1,1)", "(1,2)", "(2,1)", "(2,2)"]`

### 与条件结合 {#integration-with-conditionals}

```xml
<q:loop type="range" var="i" from="1" to="5">
  <q:if condition="i % 2 == 0">
    <q:return value="{i} is even" />
  <q:else>
    <q:return value="{i} is odd" />
  </q:else>
  </q:if>
</q:loop>
```

**Output:** `["1 is odd", "2 is even", "3 is odd", "4 is even", "5 is odd"]`

## 查询循环（`query="name"`） {#query-loop-query-name}

遍历 `q:query` 的行；每一行通过查询的名字访问。示例数据库就是
[数据库查询](/guide/query)中的那个：

```xml
<q:query name="users" datasource="db">
  SELECT name FROM users WHERE status = 'active' ORDER BY name
</q:query>
<q:loop query="users">
  <q:return value="{users.name}" />
</q:loop>
```

**Output:** `["Ana", "Bruno"]`

没有返回任何行的查询，循环体运行零次（LOOP-4）。

## 细节 {#details}

没有 `type` 的循环，有 `items` 时是数组循环，否则是范围循环（LOOP-5）：

```xml
<q:loop var="x" items="{[10, 20]}">
  <q:return value="{x}" />
</q:loop>
```

**Output:** `[10, 20]`

列表循环会去掉每一项两端的空格：

```xml
<q:loop type="list" var="c" items=" red , green ">
  <q:return value="[{c}]" />
</q:loop>
```

**Output:** `["[red]", "[green]"]`

`from` 大于 `to` 时，范围循环运行零次；没有返回任何内容的循环会让执行继续（LOOP-2）：

```xml
<q:loop type="range" var="i" from="5" to="1">
  <q:return value="{i}" />
</q:loop>
<q:return value="none" />
```

**Output:** `none`

## 错误 {#errors}

对不是列表的东西进行数组循环，会说明它得到的是什么（LOOP-6）：

```xml
<q:set name="n" value="{5}" />
<q:loop type="array" var="x" items="{n}">
  <q:return value="{x}" />
</q:loop>
```

**Error:** `needs a list`

不存在的 `type` 是解析错误（PARSE-5）：

```xml
<q:loop type="while" var="x">
</q:loop>
```

**Error:** `<q:loop type="while"> does not exist`

## 另请参见 {#see-also}

- [参考手册中的 `q:loop`](/reference/tags#q-loop)
- [状态管理（`q:set`）](/zh/guide/state-management)
- [条件（`q:if`）](/zh/guide/conditionals)
