---
order: 1
title: "适应屏幕的布局"
description: "ui:hbox 在宽屏上并排、在窄屏上堆叠，配合 grow、width 和 hide-below。"
source: cookbook/screens/responsive-layout.md
source_hash: a5899ccac57b
---

# 适应屏幕的布局

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/screens/responsive-layout)为准。
:::

**任务：** 宽屏上侧边菜单在内容旁边，手机上在内容上方。

<<< @/../examples/cookbook/screens/responsive-layout/quantum.config.yaml{yaml}

`stack-below="md"` 让 `ui:hbox` 中的盒子在宽度小于 `md`（浏览器中 768 px，
终端中 96 列）时上下堆叠。`width` 固定侧边盒子的宽度，`grow="true"` 把剩余空间
给内容，`hide-below="lg"` 让一条提示只在宽屏上显示。

<<< @/../examples/cookbook/screens/responsive-layout/components/index.q{xml}

`quantum test` 读取的是页面的文本，而不是布局，所以它检查的是内容：

<<< @/../examples/cookbook/screens/responsive-layout/tests/layout.test.q{xml}

<<< @/../examples/cookbook/screens/responsive-layout/output/test-report.txt{text}

堆叠本身在终端里检查，那里的测试可以测量它：80 列时 `#main` 是堆叠的，
140 列时是并排的，`#side` 宽 220 / 8 = 27 列
（[`tests/docs/test_cookbook_console.py`](https://github.com/danielgregorio/quantum/blob/main/tests/docs/test_cookbook_console.py)）。规则：
[UI-2](../../../reference/spec.md#UI-2)。
