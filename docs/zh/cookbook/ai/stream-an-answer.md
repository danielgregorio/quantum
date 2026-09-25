---
order: 3
title: "流式输出回答"
description: "流式的 q:llm 和 ui:stream：页面立即渲染，回答边生成边出现。"
source: cookbook/ai/stream-an-answer.md
source_hash: 5dbf53d20a59
---

# 流式输出回答

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/ai/stream-an-answer)为准。
:::

**任务：** 模型可能要几秒钟才能回答；立即显示页面，回答到达时逐步显示。

<<< @/../examples/cookbook/ai/stream-an-answer/quantum.config.yaml{yaml}

使用 `stream="true"` 时，`q:llm` 不会等待：检索已经完成，所以来源已经在页面上，
`<ui:stream for="answer">` 随着模型的输出逐步填入回答——通过框架自带的脚本，
不需要编写 JavaScript。没有 JavaScript 时，它是一个链接；`quantum console`
也会显示逐步到达的回答。

<<< @/../examples/cookbook/ai/stream-an-answer/components/index.q{xml}

<<< @/../examples/cookbook/ai/stream-an-answer/tests/stream.test.q{xml}

<<< @/../examples/cookbook/ai/stream-an-answer/output/test-report.txt{text}

这个流属于提问的访问者，只能读取一次，十分钟后过期。

*已测试：* 在 CI 中，这些测试针对一个替身模型服务器运行，它根据收到的第一个来源作答；每次发布前，它们针对真实模型运行（`tests/live_ai/test_cookbook_ai.py`）。因此它们检查的是结构——哪个来源、哪个工具、失败时页面显示什么——而从不检查模型的措辞。

参见 [IA-7](../../../reference/spec.md#IA-7)。
