---
order: 3
title: "标签页"
description: "ui:tabpanel，页面的每个部分一个 ui:tab。"
source: cookbook/screens/tabs.md
source_hash: d1171ed5c0b9
---

# 标签页

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/screens/tabs)为准。
:::

**任务：** 把页面分成几个部分，一次只显示一个。

<<< @/../examples/cookbook/screens/tabs/quantum.config.yaml{yaml}

每个 `ui:tab` 是一个带 `title` 的部分；第一个随页面一起打开。
所有标签页的内容都在页面上，所以隐藏的标签页对搜索和测试来说仍然存在。

<<< @/../examples/cookbook/screens/tabs/components/index.q{xml}

<<< @/../examples/cookbook/screens/tabs/tests/tabs.test.q{xml}

<<< @/../examples/cookbook/screens/tabs/output/test-report.txt{text}

`ui:tabpanel` 属于浏览器、终端和桌面窗口都会绘制的核心层组件集：
[UI-7](../../../reference/spec.md#UI-7)。
