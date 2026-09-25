---
order: 2
title: A paginated list
description: "One page of a long list at a time, with ui:pager drawing the links to the others."
---

# A paginated list

**Task:** show 23 posts ten at a time, with links to the other pages.

<<< @/../examples/cookbook/data-and-sql/paginated-list/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/paginated-list/migrations/V001_posts.sql{sql}

`paginate="true"` makes the query return one page — the URL's `?page=`, or
the first — and fills `posts_result.pagination` with the totals.
`<ui:pager for="posts">` draws previous, the page numbers and next, keeping
the URL's other parameters.

<<< @/../examples/cookbook/data-and-sql/paginated-list/components/index.q{xml}

A `page` that is not a positive number is page 1, never an error:

<<< @/../examples/cookbook/data-and-sql/paginated-list/tests/posts.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/paginated-list/output/test-report.txt{text}

See [DB-2](../../reference/spec.md#DB-2), [DB-9](../../reference/spec.md#DB-9)
and [UI-11](../../reference/spec.md#UI-11).
