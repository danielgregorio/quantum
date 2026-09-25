---
source: guide/components.md
source_hash: 1a0d2d913b73
---

# 组件

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/components)为准。
:::

组件是 Quantum 应用的基本构件。它们把逻辑、数据处理和输出生成封装在可复用的模块化单元中。

本页的示例在每次变更时都会运行：带有 **Output:** 的示例按所示运行，其余的——
需要参数的示例，以及使用卡片的页面——由 `tests/docs/test_guide_components.py` 运行。

## 基本结构 {#basic-structure}

每个 Quantum 组件都遵循这种结构：

```xml
<q:component name="ComponentName" xmlns:q="https://quantum.lang/ns">
  <!-- Component logic here -->
  <q:return value="output" />
</q:component>
```

**Output:** `"output"`

### 必需的元素 {#required-elements}

| 元素 | 说明 |
|---------|-------------|
| `q:component` | 根元素 |
| `name` 属性 | 组件的名字（PascalCase） |
| `xmlns:q` | Quantum 命名空间声明 |

## 简单组件 {#simple-components}

### Hello World {#hello-world}

```xml
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello, World!" />
</q:component>
```

**Output:** `"Hello, World!"`

### 提前返回 {#returning-early}

`q:return` 结束组件：第一个运行的 `q:return` 就是结果，它后面的内容不会运行。
在 `q:if` 中，只有当它所在的分支运行时，它才会结束组件。

```xml
<q:component name="Stock" xmlns:q="https://quantum.lang/ns">
  <q:set name="stock" value="0" type="number" />

  <q:if condition="stock == 0">
    <q:return value="Sold out" />
  </q:if>
  <q:return value="{stock} in stock" />
</q:component>
```

**Output:** `"Sold out"`

在循环中则不同：每个 `q:return` 都会向列表中添加一项（参见[组件中的循环](#loops-in-components)）。

## 组件参数 {#component-parameters}

用 `q:param` 接收输入：

```xml
<q:component name="Greeting" xmlns:q="https://quantum.lang/ns">
  <q:param name="name" type="string" required="true" />
  <q:param name="formal" type="boolean" default="false" />

  <q:if condition="formal">
    <q:return value="Good day, {name}." />
  </q:if>
  <q:else>
    <q:return value="Hey {name}!" />
  </q:else>
</q:component>
```

`name` = `Ana` 时返回 `"Hey Ana!"`；再加上 `formal` = `true` 时返回
`"Good day, Ana."`。没有 `name` 则是一个错误：
`Required parameter 'name' is missing`。

### 参数的属性 {#parameter-attributes}

| 属性 | 说明 | 示例 |
|-----------|-------------|---------|
| `name` | 参数名 | `name="userId"` |
| `type` | 数据类型 | `type="string"` |
| `required` | 必需参数 | `required="true"` |
| `default` | 默认值 | `default="10"` |

### 类型 {#types}

`q:param` 的 `type` 是 `string`、`integer`、`number`、`decimal`、`boolean`、
`array`、`object`、`json`、`email`、`url`、`date`、`file` 或 `any` 之一
（以及别名 `text`、`int`、`long`、`numeric`、`float`、`double`、`binary`、`upload`）。
其他任何名字都是解析错误。

不符合的值是一个指明参数的错误：类型为 `number` 的 `age` 收到 `abc` 时，组件以
`Parameter 'age' must be a number, got 'abc'` 停止；`email` 收到 `not-an-email` 时，以
`Parameter 'email' must be a valid email` 停止。

## 组件状态 {#component-state}

用 `q:set` 定义内部变量。之后同名的 `q:set` 会替换这个值：

```xml
<q:component name="Counter" xmlns:q="https://quantum.lang/ns">
  <q:set name="count" value="0" type="number" />
  <q:set name="step" value="1" type="number" />
  <q:set name="count" value="{count + step}" />

  <q:return value="Count: {count}" />
</q:component>
```

**Output:** `"Count: 1"`

### 变量校验 {#variable-validation}

`q:set` 可以检查它保存的值——`validate`（`email`、`url`……）、`range` 和 `enum`：

```xml
<q:set name="email"
       value="user@example.com"
       validate="email" />

<q:set name="status"
       type="string"
       value="active"
       enum="active,inactive,pending" />

<q:set name="age"
       type="number"
       value="200"
       range="0..150" />
```

**Error:** `Value must be between 0 and 150`

前两个通过；第三个让组件停止。不在列表中的 `status` 会以
`Value must be one of: active, inactive, pending` 让它停止，不是电子邮件的地址则以
`Invalid email format` 让它停止。

## 组件函数 {#component-functions}

用 `q:function` 定义可复用的逻辑，并在表达式中调用它：

```xml
<q:component name="Calculator" xmlns:q="https://quantum.lang/ns">
  <q:function name="add" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:return value="{a + b}" />
  </q:function>

  <q:function name="multiply" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:return value="{a * b}" />
  </q:function>

  <q:set name="sum" value="{add(5, 3)}" />
  <q:set name="product" value="{multiply(4, 7)}" />

  <q:return value="5 + 3 = {sum}, 4 * 7 = {product}" />
</q:component>
```

**Output:** `"5 + 3 = 8, 4 * 7 = 28"`

更多内容见[函数](/guide/functions)。

## 组件中的循环 {#loops-in-components}

循环中的 `q:return` 不会结束循环：每一个都会添加一项，组件返回这个列表。

### 范围循环 {#range-loop}

```xml
<q:component name="Numbers" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="5">
    <q:return value="Number {i}" />
  </q:loop>
</q:component>
```

**Output:** `["Number 1", "Number 2", "Number 3", "Number 4", "Number 5"]`

### 数组循环 {#array-loop}

```xml
<q:component name="Fruits" xmlns:q="https://quantum.lang/ns">
  <q:set name="fruits" value='["Apple", "Banana", "Cherry"]' />

  <q:loop type="array" var="fruit" items="{fruits}">
    <q:return value="I like {fruit}" />
  </q:loop>
</q:component>
```

**Output:** `["I like Apple", "I like Banana", "I like Cherry"]`

### 列表循环 {#list-loop}

```xml
<q:component name="Colors" xmlns:q="https://quantum.lang/ns">
  <q:loop type="list" var="color" items="red,green,blue" delimiter=",">
    <q:return value="Color: {color}" />
  </q:loop>
</q:component>
```

**Output:** `["Color: red", "Color: green", "Color: blue"]`

### 带索引的循环 {#loop-with-index}

`index` 给位置命名，从 0 开始计数：

```xml
<q:component name="IndexedList" xmlns:q="https://quantum.lang/ns">
  <q:set name="items" value='["First", "Second", "Third"]' />

  <q:loop type="array" var="item" items="{items}" index="i">
    <q:return value="{i + 1}. {item}" />
  </q:loop>
</q:component>
```

**Output:** `["1. First", "2. Second", "3. Third"]`

## 条件 {#conditionals}

### 基本的 If/Else {#basic-if-else}

```xml
<q:component name="AgeCheck" xmlns:q="https://quantum.lang/ns">
  <q:param name="age" type="number" required="true" />

  <q:if condition="age >= 18">
    <q:return value="Adult" />
  </q:if>
  <q:else>
    <q:return value="Minor" />
  </q:else>
</q:component>
```

`age` = `20` 时返回 `"Adult"`；`15` 时返回 `"Minor"`。

### 多个条件 {#multiple-conditions}

```xml
<q:component name="Grade" xmlns:q="https://quantum.lang/ns">
  <q:param name="score" type="number" required="true" />

  <q:if condition="score >= 90">
    <q:return value="A" />
  </q:if>
  <q:elseif condition="score >= 80">
    <q:return value="B" />
  </q:elseif>
  <q:elseif condition="score >= 70">
    <q:return value="C" />
  </q:elseif>
  <q:elseif condition="score >= 60">
    <q:return value="D" />
  </q:elseif>
  <q:else>
    <q:return value="F" />
  </q:else>
</q:component>
```

`score` = `85` 时返回 `"B"`；`42` 时返回 `"F"`。

## 数据绑定 {#data-binding}

用 `{expression}` 表示动态值：

### 简单变量 {#simple-variables}

```xml
<q:set name="name" value="Alice" />
<q:return value="Hello, {name}!" />
```

**Output:** `"Hello, Alice!"`

### 对象属性 {#object-properties}

```xml
<q:set name="user" type="object" value='{"name": "Bob", "age": 30}' />
<q:return value="{user.name} is {user.age} years old" />
```

**Output:** `"Bob is 30 years old"`

### 表达式 {#expressions}

```xml
<q:set name="price" value="100" />
<q:set name="quantity" value="5" />
<q:return value="Total: ${price * quantity}" />
```

**Output:** `"Total: $500"`

### 字符串函数 {#string-functions}

函数以值作为参数来调用——参见[函数列表](/guide/databinding#functions)：

```xml
<q:set name="text" value="hello world" />
<q:return value="{upper(text)}" />
```

**Output:** `"HELLO WORLD"`

## 嵌套循环 {#nested-loops}

内层循环的项会按顺序逐一放进外层循环的列表：

```xml
<q:component name="Report" xmlns:q="https://quantum.lang/ns">
  <q:set name="categories" value='[
    {"name": "Electronics", "items": ["Phone", "Laptop"]},
    {"name": "Clothing", "items": ["Shirt", "Pants"]}
  ]' />

  <q:loop type="array" var="category" items="{categories}">
    <q:return value="Category: {category.name}" />

    <q:loop type="array" var="item" items="{category.items}">
      <q:return value="  - {item}" />
    </q:loop>
  </q:loop>
</q:component>
```

**Output:** `["Category: Electronics", "  - Phone", "  - Laptop", "Category: Clothing", "  - Shirt", "  - Pants"]`

## 在一个组件中使用另一个组件 {#using-one-component-inside-another}

页面通过导入另一个组件——卡片、布局——并把它写成标签来使用它。保存为
`components/_parts/Card.q`：

```xml
<q:component name="Card" xmlns:q="https://quantum.lang/ns">
  <q:param name="title" required="true" />
  <section class="card">
    <h2>{title}</h2>
    <q:slot />
  </section>
</q:component>
```

保存为 `components/index.q`：

```xml
<q:component name="Home" xmlns:q="https://quantum.lang/ns">
  <q:import component="Card" from="_parts" />
  <q:set name="open" value="3" type="number" />

  <Card title="Open tickets: {open}">
    <p>The oldest is from {'Monday'}.</p>
  </Card>
</q:component>
```

打开 `/` 会显示标题为 **Open tickets: 3** 的卡片，卡片里面是
**The oldest is from Monday.**

- `q:import` 在 `quantum.config.yaml` 的 `paths.components` 中查找组件，声明了
  `from` 时在该文件夹中查找。名字以 `_` 开头的文件夹不会被当作页面提供，适合放这类部件。
- 标签的每个属性都是组件的一个 `q:param`，在页面中求值：`title="Open tickets: {open}"`
  能看到页面的 `open`。缺少必需参数是一个错误。
- `<Card>` 和 `</Card>` 之间的内容在页面的作用域中绘制，并放到组件中 `<q:slot />` 的位置。
- 组件使用页面的数据源和服务，并看到同样的 `session`、`application` 和 `request`。
- 找不到的组件或失败的组件是页面的错误——绝不会是一个悄悄消失的区块。

## 错误 {#errors}

一个无法完成它所声明的事情的组件，会以说明原因的错误停止。

### 缺少参数 {#a-missing-parameter}

```xml
<q:component name="Ticket" xmlns:q="https://quantum.lang/ns">
  <q:param name="id" type="integer" required="true" />
  <q:return value="Ticket {id}" />
</q:component>
```

**Error:** `Required parameter 'id' is missing`

### 不存在的变量 {#a-variable-that-does-not-exist}

```xml
<q:component name="ErrorExample" xmlns:q="https://quantum.lang/ns">
  <q:return value="{undefined_variable}" />
</q:component>
```

**Error:** `variable 'undefined_variable' is not defined`

## 最佳实践 {#best-practices}

### 1. 单一职责 {#_1-single-responsibility}

每个组件都应该有一个明确的用途：

```xml
<!-- Good: Focused component -->
<q:component name="UserEmail" xmlns:q="https://quantum.lang/ns">
  <q:param name="email" type="email" required="true" />
  <q:return value="{email}" />
</q:component>
```

### 2. 使用描述性的名字 {#_2-use-descriptive-names}

优先使用 `<q:component name="ProductPriceFormatter">` 而不是
`<q:component name="PF">`：名字就是使用它的页面所读到的内容。

### 3. 为参数写文档 {#_3-document-parameters}

```xml
<!--
  Formats a price with a currency code.

  @param amount - The price amount (required)
  @param currency - Currency code (default: USD)
-->
<q:component name="PriceFormatter" xmlns:q="https://quantum.lang/ns">
  <q:param name="amount" type="decimal" required="true" />
  <q:param name="currency" type="string" default="USD" />
  <q:return value="{currency} {round(amount, 2)}" />
</q:component>
```

`amount` = `19.999` 时返回 `"USD 20.0"`。

### 4. 校验输入 {#_4-validate-input}

```xml
<q:component name="SafeComponent" xmlns:q="https://quantum.lang/ns">
  <q:param name="count" type="integer" required="true" />

  <q:if condition="count < 1">
    <q:return value="Error: count must be at least 1" />
  </q:if>

  <q:return value="{count} item(s)" />
</q:component>
```

`count` = `3` 时返回 `"3 item(s)"`；`-1` 时返回
`"Error: count must be at least 1"`；`abc` 时是错误
`Parameter 'count' must be an integer, got 'abc'`。

## 下一步 {#next-steps}

- [状态管理](/zh/guide/state-management) - 更进一步的变量处理
- [函数](/guide/functions) - 创建可复用的逻辑
- [循环](/guide/loops) - 迭代模式
- [条件](/guide/conditionals) - 控制流
