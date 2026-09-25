---
order: 2
title: "分页列表"
description: "一次显示长列表的一页，用 ui:pager 画出指向其他页的链接。"
source: cookbook/data-and-sql/paginated-list.md
source_hash: 5d55378336e3
---

# 分页列表

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/data-and-sql/paginated-list)为准。
:::

**任务：** 每页十条地显示 23 篇文章，并带有指向其他页的链接。

<<< @/../examples/cookbook/data-and-sql/paginated-list/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/paginated-list/migrations/V001_posts.sql{sql}

`paginate="true"` 让查询只返回一页——URL 中 `?page=` 指定的页，或者第一页——并在
`posts_result.pagination` 中填入总数。`<ui:pager for="posts">` 画出上一页、页码和下一页，
并保留 URL 的其他参数。

<<< @/../examples/cookbook/data-and-sql/paginated-list/components/index.q{xml}

不是正数的 `page` 就是第 1 页，从不报错：

<<< @/../examples/cookbook/data-and-sql/paginated-list/tests/posts.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/paginated-list/output/test-report.txt{text}

参见 [DB-2](../../../reference/spec.md#DB-2)、[DB-9](../../../reference/spec.md#DB-9)
和 [UI-11](../../../reference/spec.md#UI-11)。
