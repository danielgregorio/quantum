---
source: guide/sessions.md
source_hash: 51e837228e46
---
# 会话与作用域

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/sessions)为准。
:::

普通的 `q:set` 只在一次请求内有效（SET-2）。三个带前缀的作用域可以把值保留得更久，或者暴露请求本身：

| 作用域 | 存活时间 | 共享范围 |
|-------|-------|-------------|
| `session.` | 跨请求，针对一个访问者 | 只有该访问者 |
| `application.` | 服务器进程运行期间 | 该进程的所有访问者 |
| `request.` | 一次请求 | — |

`application.` 是服务器进程中的内存：重启后就会消失，而在 `gunicorn --workers 4` 下每个 worker 各有一份。需要持久保存的内容请放进数据库——参见[页面如何运行](/zh/guide/how-a-page-runs)。

会话由 Web 服务器保存在签名的 cookie 中，所以用 `quantum start` 时开箱即用。部署时请设置 `QUANTUM_SECRET_KEY`（或配置中的 `security.secret_key`）：否则每个进程用各自的密钥签名，一次重启就会让所有人退出登录。

本页的示例在 CI 中运行（`tests/docs/test_guide_sessions.py`）。

## 统计访问次数 {#counting-visits}

保存为 `components/visits.q`：

```xml
<q:component name="visits" xmlns:q="https://quantum.lang/ns">
  <q:set name="session.mine" operation="increment" />
  <q:set name="application.everyone" operation="increment" />

  <html><body>
    <p>Your visits: {session.mine}</p>
    <p>Everyone's visits: {application.everyone}</p>
    <p>{request.method} {request.path}</p>
  </body></html>
</q:component>
```

两个访问者先后打开 `/visits`，看到的是：

| 请求 | `session.mine` | `application.everyone` |
|---------|------------------|---------------------|
| 访问者 A，第 1 次 | 1 | 1 |
| 访问者 A，第 2 次 | 2 | 2 |
| 访问者 B，第 1 次 | 1 | 3 |

最后一行显示 `GET /visits`。变量还不存在时，`operation="increment"` 从零开始（SET-3）。

## 一个还不存在的值 {#a-value-that-does-not-exist-yet}

对从未设置过的会话值做算术是一个错误，错误信息会说明并指出修正方法（EXPR-3）：

```xml
<q:set name="session.visits" value="{session.visits + 1}" />
```

**Error:** `session value used in 'session.visits + 1' is not set`

计数器请使用 `operation="increment"`，或者给这个值一个 `default`（SET-1）：

```xml
<q:set name="session.visits" operation="increment" />
<q:return value="Visits: {session.visits}" />
```

**Output:** `Visits: 1`

单纯的引用不是错误：不存在的 `{session.name}` 渲染为空（页面在登录之前就会渲染），在条件中则为假：

```xml
<q:return value="Hello, {session.name}!" />
```

**Output:** `Hello, !`

这让"访问者是否已登录？"只需要一行。保存为 `components/welcome.q`：

```xml
<q:component name="welcome" xmlns:q="https://quantum.lang/ns">
  <q:if condition="session.authenticated">
    <p>Welcome back!</p>
    <q:else><a href="/login">Sign in</a></q:else>
  </q:if>
</q:component>
```

新访问者看到 **Sign in**；当某个动作设置了 `session.authenticated` 之后，同一个页面会显示 **Welcome back!**

## 在动作中写入 {#writing-from-an-action}

动作以同样的方式写入 `session.`，并且修改会在重定向之前保存——参见[动作与表单](/zh/guide/actions)和[身份认证](/zh/guide/authentication)。

## 请求的值 {#request-values}

| 变量 | 内容 |
|----------|----------|
| `request.method` | `GET`、`POST`… |
| `request.path` | 路径，不含查询字符串 |
| `request.url` | 完整的 URL，含查询字符串 |

查询字符串本身在 `query.` 中（`{query.page}`），提交的表单在 `form.` 中。
