---
order: 9
title: "把 CSV 文件导入数据表"
description: "在一个事务中插入文件的每一行——任何一行失败都不会留下任何东西。"
source: cookbook/data-and-sql/load-a-csv-into-a-table.md
source_hash: 74e71bd4db57
---

# 把 CSV 文件导入数据表

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/data-and-sql/load-a-csv-into-a-table)为准。
:::

**任务：** 把商品列表导入数据库，要么全部成功，要么全部不导入。

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/migrations/V001_products.sql{sql}

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/import/products.csv{text}

动作用 `q:data` 读取文件，然后在一个 `q:transaction` 中插入每一行；其中的查询，
包括循环里的查询，都使用它的数据源。

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/components/index.q{xml}

第二个测试在文件中的某个商品已经存在时导入它：第二行失败，已经插入的第一行被回滚。

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/tests/load.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/output/test-report.txt{text}

参见 [DATA-1](../../../reference/spec.md#DATA-1) 和 [DB-4](../../../reference/spec.md#DB-4)。
