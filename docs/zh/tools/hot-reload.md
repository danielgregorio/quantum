---
source: tools/hot-reload.md
source_hash: df2a54054261
---

# 热重载

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/tools/hot-reload)为准。
:::

编写应用时，每当你保存组件或静态文件，`quantum start --hot-reload` 都会重新加载浏览器中打开的页面。你不需要重启服务器，也不需要按 F5。

```bash
quantum start --hot-reload
```

服务器照常打印它的地址。打开一个页面，编辑 `components/` 下的某个 `.q` 文件，保存，页面就会显示改动。

## 改动时发生了什么 {#what-happens-on-a-change}
服务器监视 `quantum.config.yaml` 中的两个文件夹：`paths.components` 和 `paths.static`。它提供的每个页面都会打开一个连接到监视器的 WebSocket。

| 你保存了 | 打开的页面 |
|---|---|
| `.q`、`.html`、`.js`、`.yaml` 或 `.yml` 文件 | 重新加载。表单中已输入的内容会保留 |
| 只有 `.css` 文件 | 重新获取样式表，不重新加载 |
| 不再能解析的 `.q` 文件 | 不重新加载。它们在页面上方显示该文件和解析错误，直到你修正 |

改动会被合并：一次保存多个文件只会触发一次重新加载。

改动后页面会被重新读取，即使打开了 `performance.cache_templates`。Python 代码（服务、`q:python`）不会被重新加载：
为此请设置 `server.reload: true`，它会在 `.py` 文件变化时重启服务器。

## 选项 {#options}
| 参数 | 含义 |
|---|---|
| `--hot-reload` | 监视项目并重新加载打开的页面 |
| `--hot-reload-port N` | 页面连接的 WebSocket 端口。默认 `35729` |

不使用 `--hot-reload` 时，不监视任何内容，也不会向页面添加任何东西。热重载是给你自己的机器用的：页面连接到 `localhost`。

## 故障排除 {#troubleshooting}
**页面不重新加载。** 打开浏览器控制台：客户端连接时会记录 `[Hot Reload] Connected to dev server`。如果它一直尝试重连，
可能有其他程序占用了 35729 端口。用 `--hot-reload-port` 和一个空闲端口启动。

**改动没有被察觉。** 只有 `paths.components` 和 `paths.static` 下的文件会被监视。请在 `quantum.config.yaml` 中检查这两个路径。

本页背后的规则是规范中的 DEV-4。

## 相关 {#related}
- [CLI 命令](/zh/tools/cli) - `quantum start` 和其他命令
- [开发面板](/zh/tools/dev-panel) - 每个请求做了什么（`server.debug: true`）
- [项目结构](/zh/guide/project-structure) - 组件和静态文件放在哪里
