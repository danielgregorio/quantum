---
order: 11
title: "一次查询得出汇总"
description: "在内存中对一个查询的结果执行 SQL——数据库只被询问一次。"
source: cookbook/data-and-sql/query-a-result.md
source_hash: 56c2928ad9cd
---

# 一次查询得出汇总

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/data-and-sql/query-a-result)为准。
:::

**任务：** 按地区显示销售总额，而不必询问数据库两次。

<<< @/../examples/cookbook/data-and-sql/query-a-result/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/query-a-result/migrations/V001_sales.sql{sql}

`q:query source="sales"` 在名为 `sales` 的查询结果上运行它的 SQL，这个结果以同名数据表
的形式出现。测试中的 `queries="1"` 检查数据库只被询问了一次。

<<< @/../examples/cookbook/data-and-sql/query-a-result/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/query-a-result/tests/totals.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/query-a-result/output/test-report.txt{text}

参见 [DB-3](../../../reference/spec.md#DB-3)。
