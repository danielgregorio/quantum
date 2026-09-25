---
source: tools/error-pages.md
source_hash: 0611f0033fe0
---

# 错误页面

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/tools/error-pages)为准。
:::

开发时页面出错（`server.debug: true`），错误页面会显示**在哪里**：`.q` 文件、出错那一行周围的几行（并标出该行）、
说明要改什么的消息，以及消息引用的 SPEC 规则的链接（`PARSE-2`、`ACT-9`……）。Python 的 traceback 也在，折叠着，
用于问题出在 Quantum 本身的情况。

行号是出错的最内层那一行：

- 解析错误指向标签（第 3 行的 `<q:sett>`）；
- 运行时错误指向语句——`q:if` 里面的 `q:set`，而不是 `q:if`；
- 你调用的组件内部的错误指向**那个组件的文件**，而不是调用它的 `<Card />`。

解析错误在任何地方都带有行号，不只是在页面上：`quantum run` 和日志会打印 `at line 3: <q:sett name="x" value="1"/>`。

在 `debug: false` 时，页面只说明发生了错误——没有源码，也没有消息细节。错误页面上的一切都经过转义：消息可能带有请求发送的内容。

## 重新加载时保持登录 {#reloading-keeps-you-logged-in}
在 `debug: true` 和 `reload: true` 时，保存文件会重启服务器进程。没有配置 `security.secret_key` 时，每个进程过去都会
自己生成会话密钥，所以每次保存都会让所有人退出登录。在调试模式下，密钥现在保存在 `quantum.config.yaml` 旁边的
`.quantum/dev-secret-key` 中（请把 `.quantum/` 加入 git-ignore），会话可以在重新加载后保留。
在生产环境中，请设置 `QUANTUM_SECRET_KEY` 或 `security.secret_key`——在 `debug: false` 时从不使用该文件。
