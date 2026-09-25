---
source: guide/actions.md
source_hash: 2e221351f1c5
---

# 动作与表单

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/actions)为准。
:::

表单向页面提交数据，页面中的 `q:action` 处理这次提交。动作声明它接受的字段，校验它们，
完成它的工作，然后重定向——经典的 *post / redirect / get* 循环，不需要 JavaScript。

## 一个表单及其动作 {#a-form-and-its-action}

保存为 `components/contact.q`，然后打开 `http://localhost:8080/contact`：

```xml
<q:component name="contact" xmlns:q="https://quantum.lang/ns">
  <q:action name="send" method="POST">
    <q:param name="name" type="string" required="true" minlength="2" />
    <q:set name="session.lastContact" value="{name}" />
    <q:redirect url="/contact" flash="Thank you, {name}!" />
  </q:action>

  <html><body>
    <q:if condition="flash"><p class="{flashType}">{flash}</p></q:if>
    <p>Last contact: {session.lastContact}</p>
    <form method="POST" action="/contact">
      <input name="name" />
      <button>Send</button>
    </form>
  </body></html>
</q:component>
```

发生了什么：

1. **GET** 渲染页面。动作不会运行。
2. 带 `name=Ana` 的 **POST** 运行动作：`name` 被校验并保存到会话中，浏览器被重定向到 `/contact`。
3. 重定向之后的页面显示一次 `Thank you, Ana!`。`flash` 保存消息，`flashType` 保存它的类型
   （除非你另外指定，否则为 `success`）。

## 用 `q:param` 声明字段 {#declaring-fields-with-q-param}

每个用 `q:param` 声明的字段都会成为动作中的一个变量，并且已经校验过、转换成了声明的类型。规则：

| 属性 | 检查 |
|-----------|--------|
| `required="true"` | 字段存在且不为空 |
| `type` | `string`、`number`、`integer`、`boolean`、`email`、`url` |
| `minlength` / `maxlength` | 文本长度 |
| `min` / `max` | 数值范围 |
| `pattern` | 正则表达式 |
| `enum` | 逗号分隔列表中的一个 |
| `range="1..10"` | 在两者之间，两端都包含 |
| `accept`（配合 `type="file"`） | 上传文件的类型：`image/*`、`.pdf`、`application/pdf`——既检查文件名，也检查浏览器声明的类型 |

当某条规则失败时，动作**不会**运行：浏览器回到它来的页面，`flash` 带着原因，
`flashType="error"`——例如 `Parameter 'name' must be at least 2 characters`。

原样提交的值也可以通过 `form.<field>` 获取——是文本，没有经过校验。用它们来显示；
凡是要保存或计算的，都用 `q:param`。

## 一个页面上的多个动作 {#several-actions-on-one-page}

有多个动作时，表单在名为 `action` 的字段中说明它要哪一个：

```xml
<q:component name="tasks" xmlns:q="https://quantum.lang/ns">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" />
    <q:redirect url="/tasks" flash="Created: {title}" />
  </q:action>

  <q:action name="clear" method="POST">
    <q:redirect url="/tasks" flash="List cleared" />
  </q:action>

  <html><body>
    <q:if condition="flash"><p>{flash}</p></q:if>
    <form method="POST" action="/tasks">
      <input type="hidden" name="action" value="create" />
      <input name="title" />
      <button>Create</button>
    </form>
    <form method="POST" action="/tasks">
      <input type="hidden" name="action" value="clear" />
      <button>Clear</button>
    </form>
  </body></html>
</q:component>
```

如果缺少 `action`，或者它不对应页面上的任何动作，请求会以 `400 Bad Request` 被拒绝，
并指明请求的是什么以及存在哪些动作——不会有其他动作代替它运行。

## 重定向与提示消息 {#redirects-and-flash-messages}

`q:redirect` 结束动作。`flash` 是可选的，并且支持数据绑定。要显示其他类型的提示消息，
在重定向之前使用 `q:flash`：

```xml fragment=action
<q:flash type="error" message="Invalid credentials" />
<q:redirect url="/login" />
```

`q:flash` 在 `q:action` 内部有效，由下一个页面显示。在其他任何地方它都不会起作用，
所以无法通过解析：

```xml
<q:flash type="warning" message="Read the terms first" />
```

**Error:** `is outside a q:action`

## 保护一个动作 {#protecting-an-action}

动作通过它所在的页面来保护：`q:component` 上的 `require_auth` / `require_role`，
或者一个守卫（带 `q:redirect` 的顶层 `q:if`），它会在页面的每个动作之前运行。
`q:action` 本身不接受任何保护属性：

```xml
<q:action name="save" method="POST" require_auth="true">
  <q:redirect url="/" />
</q:action>
```

**Error:** `require_auth= is not supported`

## 下一步 {#next-steps}

- [会话与作用域](/guide/sessions)——`session.` 在请求之间保存了什么
- [身份认证](/zh/guide/authentication)——用登录保护页面
