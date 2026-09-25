---
source: guide/databinding.md
source_hash: 68dae0629ce9
---

# 表达式与数据绑定

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/databinding)为准。
:::

花括号之间的任何内容都是表达式：`{total * 2}`。Quantum 用作用域中的变量对它求值，
并把结果放在原处。

本页的每个示例都按所示运行——`tests/docs` 执行每个代码块，并与它下面的 **Output** 比较。

## 一个值，或者带值的文本 {#a-value-or-text-with-values-in-it}

当一个属性**恰好是一个表达式**时，你得到的是带类型的值。周围还有其他内容时，你得到的是文本：

```xml
<q:component name="Order" xmlns:q="https://quantum.lang/ns">
  <q:set name="price" value="9.5" type="number" />
  <q:set name="qty" value="3" type="number" />
  <q:return value="{price * qty}" />
</q:component>
```

**Output:** `28.5`

```xml
<q:component name="Summary" xmlns:q="https://quantum.lang/ns">
  <q:set name="price" value="9.5" type="number" />
  <q:set name="qty" value="3" type="number" />
  <q:return value="{qty} items, total {price * qty}" />
</q:component>
```

**Output:** `"3 items, total 28.5"`

## 运算符 {#operators}

| 类别 | 运算符 |
|------|-----------|
| 算术 | `+` `-` `*` `/` `//`（整除） `%` `**` |
| 比较 | `==` `!=` `<` `<=` `>` `>=` `in` `not in` |
| 逻辑 | `and` `or` `not`——或 `&&` `\|\|` `!` |
| 选择 | `value if condition else other` |

以文本形式到达的值——表单字段、查询参数、LLM 给出的工具参数——看起来像数字时会被当作数字，
所以 `+` 是相加：

```xml
<q:component name="Sum" xmlns:q="https://quantum.lang/ns">
  <q:set name="a" value="17" />
  <q:set name="b" value="25" />
  <q:return value="{a + b}" />
</q:component>
```

**Output:** `42`

```xml
<q:component name="Age" xmlns:q="https://quantum.lang/ns">
  <q:set name="age" value="20" type="number" />
  <q:set name="invited" value="false" type="boolean" />
  <q:return value="{'enters' if age >= 18 && !invited else 'waits'}" />
</q:component>
```

**Output:** `"enters"`

`in` 的比较方式与 `==` 相同，所以以文本形式到达的值仍然能在列表中找到它对应的数字：

```xml
<q:component name="Member" xmlns:q="https://quantum.lang/ns">
  <q:set name="chosen" value="5" />
  <q:set name="allowed" value="[1, 5, 10]" type="array" />
  <q:return value="{chosen in allowed}" />
</q:component>
```

**Output:** `true`

## 读取列表和记录 {#reading-lists-and-records}

```xml
<q:component name="Reading" xmlns:q="https://quantum.lang/ns">
  <q:set name="user" type="object" value='{"name": "Ana", "tags": ["admin", "dev"]}' />
  <q:return value="{user.name} has {user.tags.length} tags, first {user.tags[0]}, last {user.tags[-1]}" />
</q:component>
```

**Output:** `"Ana has 2 tags, first admin, last dev"`

`true`、`false` 和 `null` 是字面量。在双引号属性中，字符串使用单引号：`{status == 'active'}`。

## 函数 {#functions}

| 函数 | 示例 | 结果 |
|----------|---------|--------|
| `upper(s)`、`lower(s)`、`trim(s)` | `upper('ana')` | `ANA` |
| `replace(s, old, new)` | `replace('a-b', '-', '+')` | `a+b` |
| `split(s, sep=',')` | `split('a,b')` | `['a', 'b']` |
| `contains(s, part)` | `contains('quantum', 'ant')` | `true` |
| `len(x)`、`first(x)`、`last(x)` | `len(items)` | 项的数量 |
| `get(x, key, default=null)`——可选的键或索引 | `get(prefs, 'theme', 'light')` | 这个值，缺失时为 `default` |
| `join(list, sep=', ')`、`sort(list)` | `join(sort(tags), ' / ')` | 文本 |
| `round(n, digits=0)`——.5 向远离零的方向取整 | `round(2.5)` | `3` |
| `ceil(n)`、`floor(n)`、`abs`、`min`、`max` | `ceil(7 / 3)` | `3` |
| `int(x)`、`float(x)`、`str(x)` | `int('42')` | `42` |
| `now()` | `now()` | 当前日期和时间 |
| `dateAdd(unit, n, start=now)` | `dateAdd('d', 7)` | 一周之后 |
| `dateDiff(unit, start, end)` | `dateDiff('h', a, b)` | 整小时数 |
| `dateFormat(date, pattern)` | `dateFormat(now(), '%d/%m/%Y')` | `10/09/2026` |
| `hashPassword(s)`、`verifyPassword(s, hash)` | 见[身份认证](/guide/authentication) | |
| `random()`、`random(a, b)` | `random(1, 6)` | 0 到 1 之间的数；`a` 到 `b` 之间的整数 |
| `chance(p)`、`pick(list)` | `pick(tips)` | 以概率 `p` 为真；一个元素 |

日期函数的单位：`s`、`n`（分钟）、`h`、`d`、`w`。在组件中声明的 `q:function`
也以同样的方式调用：`{twice(price)}`。

函数按名字调用，从不作为方法调用：写 `split(title, ' ')`，而不是 `title.split(' ')`；
写 `ceil(n)`，而不是 `Math.ceil(n)`。出于 JavaScript 习惯写错时，错误会指出应该用的函数。
`.length` 可以用于文本和列表。

```xml
<q:component name="Functions" xmlns:q="https://quantum.lang/ns">
  <q:function name="twice">
    <q:param name="x" type="number" />
    <q:return value="{x * 2}" />
  </q:function>
  <q:set name="tags" value='["dev", "admin"]' type="array" />
  <q:return value="{upper(join(sort(tags), ' / '))} {twice(21)}" />
</q:component>
```

**Output:** `"ADMIN / DEV 42"`

## 带作用域的变量 {#scoped-variables}

`session.`、`application.`、`request.`、`form.`、`query.` 和 `cookie.` 从各自的作用域读取。
页面常常在值存在之前就渲染——比如登录之前——所以读取一个没有设置的值会得到空文本：

```xml
<q:component name="Hello" xmlns:q="https://quantum.lang/ns">
  <q:return value="[{session.name}]" />
</q:component>
```

**Output:** `"[]"`

对没有设置的值做算术是一个错误，而不是空结果。计数器请用 `operation="increment"`，它从零开始：

```xml
<q:component name="Visits" xmlns:q="https://quantum.lang/ns">
  <q:set name="session.visits" operation="increment" />
  <q:return value="{session.visits}" />
</q:component>
```

**Output:** `1`

## 当表达式失败时 {#when-an-expression-fails}

在 `q:` 属性中，无法求值的表达式会以指明它的错误让组件停止——不会悄悄地替换成别的东西：

```xml
<q:component name="Broken" xmlns:q="https://quantum.lang/ns">
  <q:set name="total" value="3" type="number" />
  <q:return value="{totl + 1}" />
</q:component>
```

**Error:** `{totl + 1} could not be evaluated: variable 'totl' is not defined, did you mean 'total'?`

求值失败（`{10 / zero}`）以及对没有设置的作用域值做算术，也是如此。

有两个地方是有意更宽容的：

- **条件检查的是存在性。** 不存在的名字、键或属性会让 `condition` 为假，所以
  `<q:if condition="flash">` 在还没有提示消息时也能工作。其他任何问题——语法错误、
  不存在的函数——仍然是错误。
- **HTML 内容保留原文。** 页面内容中无法解析的表达式会按原样渲染，并记录一次日志。
  页面内容中也会有代码示例和零散的花括号，它们不能让页面崩溃。

```xml
<q:component name="Presence" xmlns:q="https://quantum.lang/ns">
  <q:if condition="flash">
    <q:return value="there is one" />
  </q:if>
  <q:return value="there is none" />
</q:component>
```

**Output:** `"there is none"`

## 不是表达式的花括号 {#braces-that-are-not-expressions}

JSON 对象和正则表达式的量词会保持原样：

```xml
<q:component name="Literals" xmlns:q="https://quantum.lang/ns">
  <q:set name="pattern" value="[0-9]{10,11}" />
  <q:set name="rows" value='[{"a": 1}, {"b": 2}]' type="array" />
  <q:return value="{pattern} {len(rows)}" />
</q:component>
```

**Output:** `"[0-9]{10,11} 2"`

## 参考 {#reference}

本页的规则是 [SPEC.md](https://github.com/danielgregorio/quantum/blob/main/SPEC.md)
中的 `EXPR-1` 到 `EXPR-5`。
