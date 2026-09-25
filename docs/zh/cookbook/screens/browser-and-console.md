---
order: 6
title: "终端里的同一个页面"
description: "一个 ui:* 页面，由 quantum start 提供给浏览器，由 quantum console 在终端中绘制。"
source: cookbook/screens/browser-and-console.md
source_hash: 0ceede109e4d
---

# 终端里的同一个页面

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/screens/browser-and-console)为准。
:::

**任务：** 在浏览器和终端中使用同一个页面。

<<< @/../examples/cookbook/screens/browser-and-console/quantum.config.yaml{yaml}

由核心层 `ui:*` 标签构成的页面并不绑定于 HTML。`quantum start` 把它提供给浏览器；
`quantum console` 在终端中绘制它，`quantum desktop` 则在本地窗口中绘制。
终端向同一个服务器请求页面的视图树，并提交同样的动作：`name` 的规则、提示消息
（flash）和会话的工作方式都一样，没有任何转换。

<<< @/../examples/cookbook/screens/browser-and-console/components/index.q{xml}

在浏览器中，用 `quantum test`：

<<< @/../examples/cookbook/screens/browser-and-console/tests/guests.test.q{xml}

<<< @/../examples/cookbook/screens/browser-and-console/output/test-report.txt{text}

在终端中，
[`tests/docs/test_cookbook_console.py`](https://github.com/danielgregorio/quantum/blob/main/tests/docs/test_cookbook_console.py) 在终端渲染器中打开同一个应用。
它检查这个测试套件在普通访问时期望的每段文本都出现在终端屏幕上，然后输入一个太短的名字
和一个合适的名字，并按下 **Sign**：终端先显示字段的错误，然后显示提示消息和新名字。

```bash
quantum start      # http://localhost:8080
quantum console    # the same page in this terminal
```

参见 [UI-3](../../../reference/spec.md#UI-3) 和 [UI-7](../../../reference/spec.md#UI-7)。
