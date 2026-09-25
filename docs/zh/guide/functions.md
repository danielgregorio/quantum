---
source: guide/functions.md
source_hash: 7d723be16710
---

# 函数（`q:function`）

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/functions)为准。
:::

`q:function` 是组件中一段有名字的逻辑。它接收参数，运行它的主体，并返回它的
`q:return` 的值。本页中每个带有 **Output** 的示例都由测试套件执行。

## 声明与调用 {#declaring-and-calling}

```xml
<q:component name="Sum" xmlns:q="https://quantum.lang/ns">
  <q:function name="add" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:return value="{a + b}" />
  </q:function>

  <q:return value="Sum: {add(10, 20)}" />
</q:component>
```

**Output:** `"Sum: 30"`

函数可以在它所在组件的任何表达式中调用——`q:` 属性，或页面的 HTML：
`<p>Total: {add(price, tax)}</p>`。

## 参数 {#parameters}

参数可以**按位置**或**按名字**绑定，`default` 补上缺失的参数：

```xml
<q:component name="Name" xmlns:q="https://quantum.lang/ns">
  <q:function name="formatName" returnType="string">
    <q:param name="firstName" type="string" required="true" />
    <q:param name="lastName" type="string" required="true" />
    <q:param name="title" type="string" default="Mr." />
    <q:return value="{title} {firstName} {lastName}" />
  </q:function>

  <q:return value="{formatName('John', 'Doe', 'Dr.')} / {formatName(lastName='Lee', firstName='Ann')}" />
</q:component>
```

**Output:** `"Dr. John Doe / Mr. Ann Lee"`

每次调用时，每个参数都会被转换成它的 `type`，并按它的规则检查——与[动作](/guide/actions)
中的 `q:param` 相同：

| 属性 | 检查 |
|-----------|--------|
| `required="true"` | 提供了这个参数 |
| `type` | `string`、`number`、`integer`、`boolean`、`email`、`url`、`array`、`object` |
| `min` / `max` | 数值范围 |
| `minlength` / `maxlength` / `pattern` | 文本 |
| `enum` | 逗号分隔列表中的一个 |
| `range="1..10"` | 在两者之间，两端都包含 |

```xml
<q:component name="SignUp" xmlns:q="https://quantum.lang/ns">
  <q:function name="register">
    <q:param name="email" type="email" required="true" />
    <q:param name="age" type="number" min="18" max="120" />
    <q:return value="{email} ({age})" />
  </q:function>

  <q:return value="{register('ann@example.com', '30')}" />
</q:component>
```

**Output:** `"ann@example.com (30)"`

没有通过检查的参数会以指明该参数的错误停止调用：

```xml
<q:component name="Smallest" xmlns:q="https://quantum.lang/ns">
  <q:function name="register">
    <q:param name="email" type="email" required="true" />
    <q:param name="age" type="number" min="18" max="120" />
    <q:return value="{email} ({age})" />
  </q:function>

  <q:return value="{register('ann@example.com', 15)}" />
</q:component>
```

**Error:** `Parameter 'age' must be at least 18 (got 15)`

## 返回 {#returning}

第一个运行的 `q:return` 会结束函数，所以检查可以提前返回：

```xml
<q:component name="Grade" xmlns:q="https://quantum.lang/ns">
  <q:function name="grade" returnType="string">
    <q:param name="score" type="number" required="true" />
    <q:if condition="score >= 90"><q:return value="A" /></q:if>
    <q:if condition="score >= 80"><q:return value="B" /></q:if>
    <q:return value="C" />
  </q:function>

  <q:return value="{grade(95)} {grade(85)} {grade(50)}" />
</q:component>
```

**Output:** `"A B C"`

每次返回时都会检查 `returnType`：值会被转换成这个类型（对于 `number`，`"7"` 变成 `7`），
不属于这个类型的值是一个指明函数的错误。`any`（默认）接受任何值；`void` 表示函数不返回任何东西。

## 循环与递归 {#loops-and-recursion}

函数体可以使用组件能用的一切——`q:set`、`q:loop`、`q:query`、其他函数，以及它自己：

```xml
<q:component name="Maths" xmlns:q="https://quantum.lang/ns">
  <q:function name="sumArray" returnType="number">
    <q:param name="numbers" type="array" required="true" />
    <q:set name="total" type="number" value="0" />
    <q:loop type="array" items="{numbers}" var="n">
      <q:set name="total" operation="add" value="{n}" />
    </q:loop>
    <q:return value="{total}" />
  </q:function>

  <q:function name="factorial" returnType="number">
    <q:param name="n" type="number" required="true" />
    <q:if condition="n <= 1"><q:return value="{1}" /></q:if>
    <q:return value="{n * factorial(n - 1)}" />
  </q:function>

  <q:set name="numbers" type="array" value="[10, 20, 30, 40]" />
  <q:return value="{sumArray(numbers)} {factorial(5)}" />
</q:component>
```

**Output:** `"100 120"`

## `q:function` 没有的东西 {#what-q-function-does-not-have}

本页的早期版本描述过 `cache`、`memoize`、`pure`、`async`、`retry`、`timeout`、
`access`、`scope="global"`、REST 端点和一个事件系统。它们曾被接受，却从未起过任何作用，
已在 0.11 中移除：解析器现在会拒绝这些属性并说明原因。

函数属于它所在的组件。要在页面之间共享逻辑，把它放进一个组件，并用
[`q:import`](/zh/guide/components) 使用它。

## 相关内容 {#related}

- [表达式与数据绑定](/guide/databinding)
- [条件](/zh/guide/conditionals) · [循环](/zh/guide/loops)
- [状态管理（`q:set`）](/zh/guide/state-management)
