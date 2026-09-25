---
order: 10
title: "读取 JSON 文件"
description: "把 JSON 数组作为记录列表，并给每条记录加一个计算字段。"
source: cookbook/data-and-sql/read-json.md
source_hash: 19816ee3c86a
---

# 读取 JSON 文件

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/data-and-sql/read-json)为准。
:::

**任务：** 根据一个 JSON 文件显示购物车，带每一行的小计，从大到小排列。

<<< @/../examples/cookbook/data-and-sql/read-json/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/read-json/import/products.json{json}

JSON 数组就是原样的列表。`q:compute` 给每条记录添加一个字段；`{price}` 和 `{qty}`
是记录自己的字段。

<<< @/../examples/cookbook/data-and-sql/read-json/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/read-json/tests/cart.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/read-json/output/test-report.txt{text}

参见 [DATA-1](../../../reference/spec.md#DATA-1) 和 [DATA-3](../../../reference/spec.md#DATA-3)。
