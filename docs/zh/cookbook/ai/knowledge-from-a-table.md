---
order: 7
title: "根据数据表回答"
description: "一个作为查询的 q:knowledge 来源：你的常见问题数据表中的行，像文档一样被检索。"
source: cookbook/ai/knowledge-from-a-table.md
source_hash: f7b220a49066
---

# 根据数据表回答

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/ai/knowledge-from-a-table)为准。
:::

**任务：** 根据保存在数据库中的常见问题，回答有关账号的问题。

<<< @/../examples/cookbook/ai/knowledge-from-a-table/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/ai/knowledge-from-a-table/migrations/V001_faq.sql{sql}

`type="query"` 来源把每一行变成一段待索引的文本。其中的所有内容由应用的所有用户共享——
任何问题都可能检索到任何一行——所以只索引每个人都可以读的内容。

<<< @/../examples/cookbook/ai/knowledge-from-a-table/components/index.q{xml}

<<< @/../examples/cookbook/ai/knowledge-from-a-table/tests/faq.test.q{xml}

<<< @/../examples/cookbook/ai/knowledge-from-a-table/output/test-report.txt{text}

*已测试：* 在 CI 中，这些测试针对一个替身模型服务器运行，它根据收到的第一个来源作答；每次发布前，它们针对真实模型运行（`tests/live_ai/test_cookbook_ai.py`）。因此它们检查的是结构——哪个来源、哪个工具、失败时页面显示什么——而从不检查模型的措辞。

参见 [IA-8](../../../reference/spec.md#IA-8) 和 [IA-9](../../../reference/spec.md#IA-9)。
