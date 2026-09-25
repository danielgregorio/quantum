---
order: 4
title: "条件"
description: "q:if、q:elseif 和 q:else，条件是表达式。"
source: cookbook/basics/conditionals.md
source_hash: 6ed2fdc28533
---

# 条件

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/basics/conditionals)为准。
:::

**任务：** 根据一个值显示这样或那样的内容。

<<< @/../examples/cookbook/basics/conditionals/quantum.config.yaml{yaml}

第一个条件成立的分支会运行；都不成立时运行 `q:else`。
条件是一个表达式，可以用 `and`、`or` 和 `not`。在属性里，`<` 要写成 `&lt;`：
`.q` 文件是 XML。

<<< @/../examples/cookbook/basics/conditionals/components/index.q{xml}

<<< @/../examples/cookbook/basics/conditionals/tests/stock.test.q{xml}

<<< @/../examples/cookbook/basics/conditionals/output/test-report.txt{text}

参见 [IF-1](../../../reference/spec.md#IF-1) 和 [IF-2](../../../reference/spec.md#IF-2)。
