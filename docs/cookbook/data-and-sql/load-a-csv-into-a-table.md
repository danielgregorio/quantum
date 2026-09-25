---
order: 9
title: Load a CSV file into a table
description: "Insert every row of a file in one transaction — a row that fails leaves nothing behind."
---

# Load a CSV file into a table

**Task:** load a product list into the database, all or nothing.

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/migrations/V001_products.sql{sql}

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/import/products.csv{text}

The action reads the file with `q:data`, then inserts each row inside one
`q:transaction`. A query inside a `q:loop` names its datasource, even inside
the transaction.

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/components/index.q{xml}

The second test loads the file when one of its products is already there:
the second row fails, and the first, already inserted, is rolled back.

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/tests/load.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/output/test-report.txt{text}

See [DATA-1](../../reference/spec.md#DATA-1) and [DB-4](../../reference/spec.md#DB-4).
