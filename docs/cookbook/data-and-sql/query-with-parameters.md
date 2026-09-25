---
order: 1
title: A query with parameters
description: "Filter by a value from the URL, bound as a q:param — the value never becomes SQL."
---

# A query with parameters

**Task:** list the products whose name contains what the URL asks for
(`/?name=mouse`), safely.

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/migrations/V001_products.sql{sql}

Each `:name` in the SQL is bound to the `q:param` of the same name: the value
goes to the database apart from the SQL text, converted by its `type` first.
A `:name` without a `q:param` does not parse, so there is no way to paste a
value into the SQL by accident.

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/components/index.q{xml}

The last test sends SQL in the URL. It is only text to search for: no product
has it in its name, and the table is untouched.

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/tests/products.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/output/test-report.txt{text}

See [DB-1](../../reference/spec.md#DB-1).
