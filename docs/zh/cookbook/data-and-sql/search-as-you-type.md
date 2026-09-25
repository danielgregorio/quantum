---
order: 3
title: "边输入边搜索"
description: "一个在每次输入停顿后刷新结果的字段——搜索由页面自己的查询完成。"
source: cookbook/data-and-sql/search-as-you-type.md
source_hash: d5ee5239d914
---

# 边输入边搜索

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/data-and-sql/search-as-you-type)为准。
:::

**任务：** 一个图书搜索字段，在你输入时更新列表，而且没有 JavaScript 也能用。

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/migrations/V001_books.sql{sql}

搜索是一个 GET 参数（`?q=`），由页面自己的查询读取。字段上的 `search="results"`
在每次输入停顿后请求同一个页面，只替换 `id="results"` 的元素；URL 也随之更新，
所以结果可以分享或刷新。

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/tests/search.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/output/test-report.txt{text}

参见 [UI-12](../../../reference/spec.md#UI-12)。
