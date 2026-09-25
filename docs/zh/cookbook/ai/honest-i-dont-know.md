---
order: 2
title: "当文档不知道答案时"
description: "minRelevance 挡住不相关的文本块；一个都不剩时，不询问模型，页面如实说明。"
source: cookbook/ai/honest-i-dont-know.md
source_hash: 2f44458e4a17
---

# 当文档不知道答案时

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/ai/honest-i-dont-know)为准。
:::

**任务：** 当文档没有涵盖某个问题时，如实说明——而不是让模型凭记忆回答。

<<< @/../examples/cookbook/ai/honest-i-dont-know/quantum.config.yaml{yaml}

与[带来源的回答](./answer-with-sources.md)中相同的三份文档。没有 `minRelevance` 时，
最接近的文本块总会返回，不管它们与问题是否相关。有了它，相关度低于下限的文本块会被丢弃；
一个都不剩时，`answer_result.found` 为 false，模型根本不会被调用。

<<< @/../examples/cookbook/ai/honest-i-dont-know/components/index.q{xml}

<<< @/../examples/cookbook/ai/honest-i-dont-know/tests/honest.test.q{xml}

<<< @/../examples/cookbook/ai/honest-i-dont-know/output/test-report.txt{text}

下限取决于嵌入模型和文本块大小。对一些你的文档能回答的问题和一些不能回答的问题，
打印 `s.relevance`，然后把下限设在两者之间——正因如此，上面的页面在每个来源旁边都显示了它。

*已测试：* 在 CI 中，这些测试针对一个替身模型服务器运行，它根据收到的第一个来源作答；每次发布前，它们针对真实模型运行（`tests/live_ai/test_cookbook_ai.py`）。因此它们检查的是结构——哪个来源、哪个工具、失败时页面显示什么——而从不检查模型的措辞。

参见 [IA-9](../../../reference/spec.md#IA-9)。
