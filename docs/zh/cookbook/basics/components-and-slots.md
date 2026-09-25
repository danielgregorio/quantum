---
order: 8
title: "可复用的组件"
description: "一个带 props 和 slot 的组件，从一个永远不会被当作页面提供的 _ 文件夹导入。"
source: cookbook/basics/components-and-slots.md
source_hash: e3f5b5e42dc9
---

# 可复用的组件

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/basics/components-and-slots)为准。
:::

**任务：** 把一张卡片写一次，在任何页面上以不同的内容使用。

<<< @/../examples/cookbook/basics/components-and-slots/quantum.config.yaml{yaml}

组件也是一个 `.q` 文件。它的 `q:param` 就是它的 props，`q:slot` 是调用者的内容
放进去的地方。把它放在名字以 `_` 开头的文件夹里：它可以被导入，但永远不会响应 URL。

<<< @/../examples/cookbook/basics/components-and-slots/components/_shared/Card.q{xml}

`q:import` 把它引入页面，`<Card>` 使用它。每个属性都是一个 prop，标签之间的内容
填入 slot，用页面的变量计算：

<<< @/../examples/cookbook/basics/components-and-slots/components/index.q{xml}

<<< @/../examples/cookbook/basics/components-and-slots/tests/cards.test.q{xml}

<<< @/../examples/cookbook/basics/components-and-slots/output/test-report.txt{text}

参见 [COMP-1](../../../reference/spec.md#COMP-1)、[COMP-3](../../../reference/spec.md#COMP-3)
和 [ROUTE-3](../../../reference/spec.md#ROUTE-3)。
