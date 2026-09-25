---
source: guide/applications.md
source_hash: 42bbd59d0482
---
# q:application

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/applications)为准。
:::

Quantum 中的 **Web 应用**不是 `q:application`：它是 `components/` 中的一组页面，由 `quantum start` 提供服务。参见[入门](/zh/guide/getting-started)和[快速开始](/zh/guide/quick-start)。

`q:application` 是**不是** Web 页面的程序的根元素。它们都不属于受支持的核心（参见 `SUPPORT_TIERS.md`）：

| `type` | 层级 | `quantum run app.q` 做什么 |
|--------|------|-------------------------------|
| `game` | 实验室 | 构建一个 2D 游戏（`--engine pixi` 或 `--engine godot`） |
| `terminal` | 实验层 | 构建一个终端界面 |
| `ui` | 实验层 | 构建一个界面（`--target html`、`desktop` 或 `mobile`） |
| `testing` | 实验层 | 生成浏览器测试 |

运行实验层或实验室的应用时，会打印一次警告说明这一点。它们的标签和输出可能在任何版本中改变。

## 已移除：`type="html"`、`type="api"`、`type="microservices"` {#removed-type-html-type-api-type-microservices}

早期版本记载了用 `q:application` 加 `q:route` 块声明的 Web 服务器和 JSON API。它们从未真正运行过自己的路由——`html` 启动时就失败，`api` 返回第一个 `q:return` 的字面文本——已在 0.11 中移除。不带 `type` 的 `q:application` 原来表示 `type="html"`，所以同样会被拒绝。

现在解析器会停下并给出指引：

```text
<q:application> type="html" was removed in Quantum 0.11: it never ran its
routes. Build a web app as pages in components/ (components/index.q is /) and
run `quantum start`.
```

每条路由对应成什么：

| 以前 | 现在 |
|--------|-----|
| `<q:route path="/about" method="GET">` | `components/about.q` |
| `<q:route path="/" method="GET">` | `components/index.q` |
| `<q:route path="/users" method="POST">` | `components/users.q` 中的一个 [`q:action`](/zh/guide/actions) |
| JSON API 路由 | 自 0.11 起不可用 |
