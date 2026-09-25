---
order: 4
title: "卡片"
description: "带页眉、正文和页脚的 ui:card，放在 ui:grid 中；或者只有标题的卡片。"
source: cookbook/screens/cards.md
source_hash: fb4a0ba08d55
---

# 卡片

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/screens/cards)为准。
:::

**任务：** 把几项并排显示，每一项在自己的盒子里。

<<< @/../examples/cookbook/screens/cards/quantum.config.yaml{yaml}

`ui:card` 包含 `ui:card-header`、`ui:card-body` 和 `ui:card-footer`，都是可选的。
`ui:grid columns="3"` 把卡片排成三列。只有标题和一些文本的卡片不需要这些部分：
`title=` 就够了。

<<< @/../examples/cookbook/screens/cards/components/index.q{xml}

<<< @/../examples/cookbook/screens/cards/tests/cards.test.q{xml}

<<< @/../examples/cookbook/screens/cards/output/test-report.txt{text}

参见 [UI-7](../../../reference/spec.md#UI-7)。
