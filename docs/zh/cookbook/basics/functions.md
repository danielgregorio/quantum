---
order: 5
title: "函数"
description: "带类型检查参数的 q:function，可以在 q:set 和 HTML 中调用。"
source: cookbook/basics/functions.md
source_hash: ee92d47aaa68
---

# 函数

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/basics/functions)为准。
:::

**任务：** 把一个计算写一次，在页面需要的任何地方使用。

<<< @/../examples/cookbook/basics/functions/quantum.config.yaml{yaml}

`q:function` 像动作一样接收 `q:param`：每次调用时，每个参数都会被转换成它的类型，
并按它的规则检查；`default` 补上省略的参数。`returnType` 检查返回的值。
函数可以在页面的任何表达式中调用，包括在另一个调用里面。

<<< @/../examples/cookbook/basics/functions/components/index.q{xml}

<<< @/../examples/cookbook/basics/functions/tests/prices.test.q{xml}

<<< @/../examples/cookbook/basics/functions/output/test-report.txt{text}

参见 [FN-1](../../../reference/spec.md#FN-1)、[FN-3](../../../reference/spec.md#FN-3)
和 [FN-4](../../../reference/spec.md#FN-4)。
