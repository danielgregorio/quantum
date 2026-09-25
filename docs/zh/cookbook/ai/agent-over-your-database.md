---
order: 4
title: "基于数据库的智能体"
description: "带只读查询工具的 q:agent：模型选择工具和参数，从不编写 SQL。"
source: cookbook/ai/agent-over-your-database.md
source_hash: 144fdb043555
---

# 基于数据库的智能体

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/ai/agent-over-your-database)为准。
:::

**任务：** 让一个助手根据商店的数据库回答"哪些商品快缺货了？"，而从不让模型编写 SQL。

<<< @/../examples/cookbook/ai/agent-over-your-database/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/ai/agent-over-your-database/migrations/V001_products.sql{sql}

工具是你编写的一个函数，里面只有一个只读查询。模型看到它的名字、描述和参数；
它决定是否调用、用什么值调用，这个值会在查询运行之前被转换成参数的类型。
`stock_result.actions` 列出每一次调用的完整写法。

<<< @/../examples/cookbook/ai/agent-over-your-database/components/index.q{xml}

<<< @/../examples/cookbook/ai/agent-over-your-database/tests/agent.test.q{xml}

在 CI 中，替身模型按照一个简短的脚本行事——调用工具，然后结束：

<<< @/../examples/cookbook/ai/agent-over-your-database/tests/fake-model.json{json}

<<< @/../examples/cookbook/ai/agent-over-your-database/output/test-report.txt{text}

工具能做它的函数体所做的一切，而提示词可以引导模型去调用它：只给工具完成任务所需的访问权限。

*已测试：* 在 CI 中，这些测试针对一个替身模型服务器运行，它根据收到的第一个来源作答；每次发布前，它们针对真实模型运行（`tests/live_ai/test_cookbook_ai.py`）。因此它们检查的是结构——哪个来源、哪个工具、失败时页面显示什么——而从不检查模型的措辞。

参见 [IA-4](../../../reference/spec.md#IA-4) 和 [IA-5](../../../reference/spec.md#IA-5)。
