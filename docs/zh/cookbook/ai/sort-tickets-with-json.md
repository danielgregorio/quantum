---
order: 6
title: "用 JSON 回答给消息分类"
description: "responseFormat json：模型的回答是一个对象，你检查并保存它的字段。"
source: cookbook/ai/sort-tickets-with-json.md
source_hash: 77e549b1b79e
---

# 用 JSON 回答给消息分类

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/ai/sort-tickets-with-json)为准。
:::

**任务：** 把每条支持消息归入一个由模型决定的类别，保存在数据表中。

<<< @/../examples/cookbook/ai/sort-tickets-with-json/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/ai/sort-tickets-with-json/migrations/V001_tickets.sql{sql}

`responseFormat="json"` 要求模型返回 JSON 并解析它：`ticket` 是一个对象。
它的字段和其他输入一样——页面在保存之前检查类别，而动作自身的 `q:param`
规则在调用模型之前就会运行。

<<< @/../examples/cookbook/ai/sort-tickets-with-json/components/index.q{xml}

<<< @/../examples/cookbook/ai/sort-tickets-with-json/tests/tickets.test.q{xml}

<<< @/../examples/cookbook/ai/sort-tickets-with-json/tests/fake-model.json{json}

<<< @/../examples/cookbook/ai/sort-tickets-with-json/output/test-report.txt{text}

*已测试：* 在 CI 中，这些测试针对一个替身模型服务器运行，它根据收到的第一个来源作答；每次发布前，它们针对真实模型运行（`tests/live_ai/test_cookbook_ai.py`）。因此它们检查的是结构——哪个来源、哪个工具、失败时页面显示什么——而从不检查模型的措辞。

参见 [IA-1](../../../reference/spec.md#IA-1)。
