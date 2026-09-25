---
order: 1
title: "带来源的回答"
description: "用 q:knowledge 和 q:llm knowledge= 根据你自己的文档回答问题，并列出来源。"
source: cookbook/ai/answer-with-sources.md
source_hash: f578e2c9daff
---

# 带来源的回答

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/ai/answer-with-sources)为准。
:::

**任务：** 一个根据商店的政策文档回答问题的页面，并显示每个回答来自哪份文档。

<<< @/../examples/cookbook/ai/answer-with-sources/quantum.config.yaml{yaml}

`knowledge/` 中的三个 Markdown 文件：

<<< @/../examples/cookbook/ai/answer-with-sources/knowledge/returns.md{md}

`q:knowledge` 读取这个文件夹，把它拆分成文本块并计算嵌入。`q:llm knowledge="docs"`
检索与问题最接近的文本块，编号后发送给模型，并指示它只根据这些文本块回答、像 `[1]`
这样引用它们。`answer_result.sources` 列出检索到的内容；`answer_result.grounded`
说明回答是否引用了其中任何一项。

<<< @/../examples/cookbook/ai/answer-with-sources/components/index.q{xml}

<<< @/../examples/cookbook/ai/answer-with-sources/tests/ask.test.q{xml}

<<< @/../examples/cookbook/ai/answer-with-sources/output/test-report.txt{text}

*已测试：* 在 CI 中，这些测试针对一个替身模型服务器运行，它根据收到的第一个来源作答；每次发布前，它们针对真实模型运行（`tests/live_ai/test_cookbook_ai.py`）。因此它们检查的是结构——哪个来源、哪个工具、失败时页面显示什么——而从不检查模型的措辞。

参见 [IA-2](../../../reference/spec.md#IA-2)、[IA-6](../../../reference/spec.md#IA-6)
和 [AI 指南](../../../guide/ai.md#answers-that-cite-their-sources)（英文）。
