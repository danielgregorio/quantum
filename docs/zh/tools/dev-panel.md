---
source: tools/dev-panel.md
source_hash: aba77ca68e49
---

# `/_dev` 面板

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/tools/dev-panel)为准。
:::

在编写应用时，`/_dev` 显示最近的请求做了什么：哪个组件做出了响应、运行了哪个 `q:action`、每个查询及其参数、耗时和行数、
每个作用域结束时的变量、重定向以及提示消息（flash）。

在 `quantum.config.yaml` 中打开它：

```yaml
server:
  debug: true
  host: 127.0.0.1
```

`quantum start` 会打印地址（`Dev panel: http://localhost:8080/_dev`）。使用应用，然后打开 `/_dev`：
显示最新的请求，列表中的每一行打开各自的请求（`/_dev/12`）。

| 区域 | 显示内容 |
|---|---|
| Component, Action | 做出响应的 `.q` 文件，以及 POST 运行的动作 |
| Redirect, Flash | 动作把浏览器送到了哪里，以及给下一个页面的消息 |
| Queries | 数据源、SQL、参数、行数（或数据库的错误）、耗时 |
| action / page | 动作或页面结束时的变量 |
| session / application | 请求结束时各作用域的状态 |

超过 300 个字符的值会被截断。所有内容都经过转义：包含 HTML 的变量会显示为文本。

## 它只在开发时存在 {#it-exists-only-while-developing}
- 在 `debug: false` 时不记录任何内容，`/_dev` 返回 404。
- 它只响应来自本机（`127.0.0.1` / `::1`）的请求：面板会显示会话和查询参数，因此从任何其他地址访问它都不存在——
  即使配置在公开绑定之后写着 `debug: true`。
- 它在内存中保存服务器进程的最近 30 个请求。
