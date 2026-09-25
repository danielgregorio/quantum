---
order: 4
title: Filter and sort a table
description: "Links that filter the rows and headers that sort them — both in SQL, both in the URL."
---

# Filter and sort a table

**Task:** a task table the reader filters (open, done, all) and sorts by
clicking a header.

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/migrations/V001_tasks.sql{sql}

The filter is `?show=`, passed to the query as a parameter. `sortable="true"`
on the query and `sort="true"` on the table turn each header into a link that
orders the query in SQL by `?sort=` and `?dir=` — so it still works on a
paginated query. A column the query does not return is ignored.

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/tests/tasks.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/output/test-report.txt{text}

See [UI-13](../../reference/spec.md#UI-13).
