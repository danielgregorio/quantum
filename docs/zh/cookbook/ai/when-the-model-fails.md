---
order: 5
title: "当模型失败时"
description: "q:llm 上的 onerror：宕机或太慢的模型不会连带页面一起崩溃。"
source: cookbook/ai/when-the-model-fails.md
source_hash: 2fc39501021e
---

# 当模型失败时

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/ai/when-the-model-fails)为准。
:::

**任务：** 使用模型的页面在模型服务器宕机、变慢或缺少模型时，仍然应该能工作——并说明发生了什么。

<<< @/../examples/cookbook/ai/when-the-model-fails/quantum.config.yaml{yaml}

没有 `onerror` 时，AI 失败会停止页面，并给出指明服务器和原因的错误。有了
`onerror="continue"`，页面会继续：`summary_result.success` 为 false，
`summary_result.error.message` 说明原因，`summary` 为空。这个示例把 `endpoint=`
指向一个没有运行的服务器，所以它在任何地方都以同样的方式失败。

<<< @/../examples/cookbook/ai/when-the-model-fails/components/index.q{xml}

<<< @/../examples/cookbook/ai/when-the-model-fails/tests/failure.test.q{xml}

<<< @/../examples/cookbook/ai/when-the-model-fails/output/test-report.txt{text}

`onerror` 在 `q:llm`、`q:knowledge`、`q:agent` 和 `q:query` 上的作用相同。

参见 [IA-5](../../../reference/spec.md#IA-5)。
