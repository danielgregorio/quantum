---
order: 4
title: "筛选和排序表格"
description: "筛选行的链接和给行排序的表头——都在 SQL 中完成，都体现在 URL 里。"
source: cookbook/data-and-sql/filter-and-sort.md
source_hash: 2fd626dc0a23
---

# 筛选和排序表格

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/data-and-sql/filter-and-sort)为准。
:::

**任务：** 一个任务表格，读者可以筛选（未完成、已完成、全部），并点击表头排序。

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/migrations/V001_tasks.sql{sql}

筛选条件是 `?show=`，作为参数传给查询。查询上的 `sortable="true"` 和表格上的
`sort="true"` 把每个表头变成一个链接，按 `?sort=` 和 `?dir=` 在 SQL 中对查询排序——
所以在分页查询上也有效。查询不返回的列会被忽略。

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/tests/tasks.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/output/test-report.txt{text}

参见 [UI-13](../../../reference/spec.md#UI-13)。
