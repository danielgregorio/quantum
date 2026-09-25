---
source: guide/how-a-page-runs.md
source_hash: ac6cc77dd1e5
---

# 页面如何运行

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/how-a-page-runs)为准。
:::

一个 `.q` 页面有两类部分：做事情的**语句**（`q:set`、`q:query`、`q:invoke`、
`q:action`……），以及显示内容的**标记**（HTML、`ui:*` 元素、`{expressions}`）。
了解它们的运行顺序，就能理解每一条起初看起来令人意外的规则——这些规则的错误消息
都链接到这里。

## 一次 GET 请求，按顺序 {#a-get-in-order}

1. **路由**选择组件：`components/index.q` 是 `/`，`components/loja/[id].q` 是 `/loja/41`。
2. `require_auth` / `require_role` 决定它是否能打开。
3. 运行**守卫**：分支中带有 `q:redirect` 的顶层 `q:if`。
4. 从上到下运行页面的**语句**。
5. 用语句留下的变量渲染**标记**：`{expressions}`、标记中的 `q:loop` 和 `q:if`、`ui:*` 元素，
   以及从中调用的组件。

```xml
<q:component name="InOrder">
  <q:set name="items" type="array" value='["a", "b", "c"]' />
  <q:set name="total" value="{len(items)}" type="number" />
  <p>Total: {total}</p>
  <q:loop type="array" items="{items}" var="i">
    <p>Item {i}</p>
  </q:loop>
</q:component>
```

**Shows:** `Total: 3` · `Item a` · `Item c`

标记只负责**渲染**。它从不运行语句——所以放在标记里的语句永远不会运行，Quantum
会拒绝它，而不是忽略它：

```xml
<q:component name="Wrong">
  <div>
    <q:set name="x" value="1" />
  </div>
</q:component>
```

**Error:** `never runs (PARSE-2): statements run before the page is rendered`

把 `q:set` 移到标记之上。出于同样的原因，在标记的 `q:loop` 中、其值被各行读取的
`q:set` 是一个错误：循环会在画出任何一行之前先为每一项运行一遍，所以每一行都会显示
最后一个值。请改为在表达式中计算：`{item.price * item.qty}`。

页面的 `q:function` 无论写在哪里，在整个页面以及它的动作中都可以使用：

```xml
<q:set name="doubled" value="{double_it(21)}" type="number" />
<q:function name="double_it">
  <q:param name="n" type="number" />
  <q:return value="{n * 2}" />
</q:function>
<q:return value="{doubled}" />
```

**Output:** `42`

## 一次 POST 请求：先运行动作，然后重定向 {#a-post-the-action-then-a-redirect}

表单向页面提交一个名为 `action` 的字段，它指明页面的某个 `q:action`。第 1–3 步和 GET
一样运行；然后**只运行这个动作**——不运行页面的语句。它校验自己的 `q:param`，
完成它的工作，并以 `q:redirect` 结束：浏览器随后用 GET 请求这个页面，按上面的方式运行。

由于页面的语句不会在动作中运行，页面设置的变量在那里并不存在：

```xml
<q:component name="Order">
  <q:set name="total" value="42" type="number" />

  <q:action name="pay" method="POST">
    <!-- {total} does not exist here: the page's q:set did not run. -->
    <q:redirect url="/order" flash="Paid {total}." />
  </q:action>

  <p>Total: {total}</p>
</q:component>
```

页面显示 `Total: 42`；提交 `pay` 是一个错误，它的消息说的正是这一点：

```text
q:action 'pay' failed: {total} could not be evaluated: variable 'total' is not defined (in scope: form). A q:action does not run the page's statements (ACT-9): query or compute what it needs inside the action.
```

动作自己去查询或计算它需要的东西。

守卫是例外：它们在页面之前运行，**也**在页面的每个动作之前运行，所以会重定向的守卫
也会拦下动作。这也是守卫不能读取页面所设置变量的原因——在动作中这个变量不存在，
守卫就会让提交通过。守卫直接读取作用域（`session.x`）；常见的情况由 `require_auth`
和 `require_role` 替你处理。

不以 `q:redirect` 结束的动作会用页面本身作为响应（它的语句在动作之后运行，和 GET 一样）。
这样得到的是对 POST 的 200 响应，刷新时会再次提交表单——请用 `q:redirect` 结束动作。

## 各种东西存活多久 {#how-long-things-live}

| 什么 | 存活 | 谁能看到 |
|---|---|---|
| 页面变量（`q:set name="x"`） | 一次请求 | 这次请求 |
| `flash` | 下一个页面，一次 | 这个访问者 |
| `session.x` | 跨请求，保存在签名的会话 cookie 中 | 一个访问者 |
| `application.x` | 服务器进程运行期间 | 该进程的所有访问者 |

每个请求都在自己的运行时中运行，所以两个请求永远看不到彼此的变量。`application.x`
是服务器进程中的内存：重启后就没有了；在 `gunicorn --workers 4` 下，每个 worker
都有自己的一份。任何必须持久或共享的东西都要放在数据库中。
