---
source: guide/conditionals.md
source_hash: f186a35fba5d
---

# 条件（q:if、q:elseif、q:else）

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/conditionals)为准。
:::

`q:if` 在它的 `condition` 为真时运行它的主体。`q:elseif` 和 `q:else` 增加其他分支。
本页中每个带有 **Output** 的示例都由测试套件执行。

## If、elseif、else {#if-elseif-else}

```xml
<q:component name="Grade" xmlns:q="https://quantum.lang/ns">
  <q:param name="score" type="number" default="85" />

  <q:if condition="score >= 90">
    <q:return value="A" />
  </q:if>
  <q:elseif condition="score >= 80">
    <q:return value="B" />
  </q:elseif>
  <q:else>
    <q:return value="C" />
  </q:else>
</q:component>
```

**Output:** `"B"`

`q:elseif` 和 `q:else` 也可以写在 `q:if` **内部**、它的主体之后。两种写法在任何地方
含义都相同——在组件、循环、函数、动作或 HTML 模板中：

```xml
<q:component name="EvenOdd" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="4">
    <q:if condition="i % 2 == 0">
      <q:return value="{i} even" />
      <q:else>
        <q:return value="{i} odd" />
      </q:else>
    </q:if>
  </q:loop>
</q:component>
```

**Output:** `["1 odd", "2 even", "3 odd", "4 even"]`

前面没有紧跟 `q:if` 的 `q:else` 或 `q:elseif` 是解析错误。

## 编写条件 {#writing-conditions}

条件是一个[表达式](/zh/guide/databinding)，带不带花括号都可以：
`condition="age >= 18"` 和 `condition="{age >= 18}"` 是一样的。

| | |
|---|---|
| 比较 | `==` `!=` `<` `<=` `>` `>=` `in` |
| 逻辑 | `and` `or` `not`，或 `&&` `\|\|` `!` |
| 文本 | `status == 'active'`——在属性中使用单引号 |

```xml
<q:component name="Filter" xmlns:q="https://quantum.lang/ns">
  <q:set name="items" type="array" value='[
    {"name": "Apple", "type": "fruit", "price": 1.50},
    {"name": "Carrot", "type": "vegetable", "price": 0.75},
    {"name": "Banana", "type": "fruit", "price": 0.45}
  ]' />

  <q:loop type="array" var="item" items="{items}">
    <q:if condition="item.type == 'fruit' && item.price < 1.00">
      <q:return value="{item.name}: {item.price}" />
    </q:if>
  </q:loop>
</q:component>
```

**Output:** `["Banana: 0.45"]`

### 真与假 {#true-and-false}

`false`、`0`、空文本、空列表和 `null` 为假；其他一切为真。**文本** `"false"`
不是空的，所以它为真——请用 `type="boolean"` 声明布尔值：

```xml
<q:component name="Booleans" xmlns:q="https://quantum.lang/ns">
  <q:set name="as_text" value="false" />
  <q:set name="as_boolean" value="false" type="boolean" />
  <q:set name="r" value="" />
  <q:if condition="as_text"><q:set name="r" value="{r}text " /></q:if>
  <q:if condition="as_boolean"><q:set name="r" value="{r}boolean" /></q:if>
  <q:return value="[{r}]" />
</q:component>
```

**Output:** `"[text ]"`

### 条件是一种存在性检查 {#a-condition-is-a-presence-test}

不存在的名字、键或属性会让条件为**假**——正是这一点让页面可以检查一个只是有时存在的值，
比如提示消息（flash）：

```xml
<q:component name="Notice" xmlns:q="https://quantum.lang/ns">
  <q:if condition="flash">
    <q:return value="{flash}" />
  </q:if>
  <q:return value="no message" />
</q:component>
```

**Output:** `"no message"`

其他任何失败都是错误，绝不会悄悄变成假——一个没写完的条件会让组件停止：

```xml
<q:component name="Unfinished" xmlns:q="https://quantum.lang/ns">
  <q:set name="age" value="20" type="number" />
  <q:if condition="age >">
    <q:return value="adult" />
  </q:if>
</q:component>
```

**Error:** `condition 'age >' could not be evaluated`

## 提前返回 {#returning-early}

第一个运行的 `q:return` 会结束组件或函数，所以一连串的检查不需要嵌套：

```xml
<q:component name="Order" xmlns:q="https://quantum.lang/ns">
  <q:function name="process">
    <q:param name="order_id" type="string" default="" />
    <q:if condition="!order_id">
      <q:return value="order id required" />
    </q:if>
    <q:return value="order {order_id} processed" />
  </q:function>

  <q:return value="{process()} / {process('A7')}" />
</q:component>
```

**Output:** `"order id required / order A7 processed"`

## 在页面中 {#in-a-page}

在 HTML 中，`q:if` 决定渲染什么：

```xml
<q:component name="menu" xmlns:q="https://quantum.lang/ns">
  <nav>
    <q:if condition="session.authenticated">
      <span>Hello, {session.userName}</span>
      <a href="/logout">Logout</a>
    </q:if>
    <q:else>
      <a href="/login">Login</a>
    </q:else>
  </nav>
</q:component>
```

**Shows:** `Login`

登录之前，`session.authenticated` 不存在，所以页面显示 Login 链接。登录本身见
[身份认证](/zh/guide/authentication)。

## 相关内容 {#related}

- [表达式与数据绑定](/zh/guide/databinding)——条件可以使用的一切
- [循环](/zh/guide/loops)
- [函数](/zh/guide/functions)
