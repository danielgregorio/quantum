---
order: 11
title: Totals from one query
description: "SQL over a query's result, in memory — the database is asked once."
---

# Totals from one query

**Task:** show sales totals by region without asking the database twice.

<<< @/../examples/cookbook/data-and-sql/query-a-result/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/query-a-result/migrations/V001_sales.sql{sql}

`q:query source="sales"` runs its SQL over the result of the query named
`sales`, which appears as a table of that name. `queries="1"` in the test
checks that the database was asked only once.

<<< @/../examples/cookbook/data-and-sql/query-a-result/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/query-a-result/tests/totals.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/query-a-result/output/test-report.txt{text}

See [DB-3](../../reference/spec.md#DB-3).
