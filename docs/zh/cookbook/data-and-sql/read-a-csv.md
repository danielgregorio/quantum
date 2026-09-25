---
order: 8
title: "读取 CSV 文件"
description: "q:data 把 CSV 文件变成带类型的记录，并筛选和排序——不需要数据库。"
source: cookbook/data-and-sql/read-a-csv.md
source_hash: 6de028735194
---

# 读取 CSV 文件

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/data-and-sql/read-a-csv)为准。
:::

**任务：** 显示一个 CSV 文件中的活跃客户，从最早的开始。

<<< @/../examples/cookbook/data-and-sql/read-a-csv/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/read-a-csv/import/customers.csv{text}

声明过的列带有类型（`true`、`1`、`yes` 和 `on` 都是布尔值真）；其余的列以文本形式到达。
`q:transform` 按顺序执行它的操作。

<<< @/../examples/cookbook/data-and-sql/read-a-csv/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/read-a-csv/tests/customers.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/read-a-csv/output/test-report.txt{text}

参见 [DATA-1](../../../reference/spec.md#DATA-1) 和
[DATA-3](../../../reference/spec.md#DATA-3)，以及 [Data Import](../../../guide/data-import.md)（英文）。
