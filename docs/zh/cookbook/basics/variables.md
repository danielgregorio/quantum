---
order: 2
title: "变量与表达式"
description: "q:set 保存一个值，花括号用它计算，default 补上缺失的值。"
source: cookbook/basics/variables.md
source_hash: 103530a1b6f1
---

# 变量与表达式

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/basics/variables)为准。
:::

**任务：** 把值保存在变量里，并用它们计算。

<<< @/../examples/cookbook/basics/variables/quantum.config.yaml{yaml}

`q:set` 以一个名字保存一个值。花括号用它计算：在 `q:` 属性里和 HTML 里都可以。
`type="number"` 把文本变成数字，而只有一个表达式的值会保留它的类型，所以 `total`
是一个数字。`operation="increment"` 就地修改变量，页面从上到下运行：`total` 是在
`quantity` 增加之前计算的。当值为空或不存在时（例如普通访问时的 `?note=`），
保存的是 `default`。

<<< @/../examples/cookbook/basics/variables/components/index.q{xml}

<<< @/../examples/cookbook/basics/variables/tests/receipt.test.q{xml}

<<< @/../examples/cookbook/basics/variables/output/test-report.txt{text}

参见 [SET-1](../../../reference/spec.md#SET-1)、[SET-3](../../../reference/spec.md#SET-3)
和 [SET-5](../../../reference/spec.md#SET-5)。
