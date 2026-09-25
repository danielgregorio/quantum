---
order: 7
title: Add a column with a migration
description: "Change the schema with a new migration file; the old one stays as it was."
---

# Add a column with a migration

**Task:** products need a stock count, and the database already exists.

<<< @/../examples/cookbook/data-and-sql/add-a-column/quantum.config.yaml{yaml}

The first migration made the table:

<<< @/../examples/cookbook/data-and-sql/add-a-column/migrations/V001_products.sql{sql}

The change is a second file. Migrations run in order, each once, each in its
own transaction; an applied migration is never edited:

<<< @/../examples/cookbook/data-and-sql/add-a-column/migrations/V002_add_stock.sql{sql}

```bash
quantum migrate up
```

<<< @/../examples/cookbook/data-and-sql/add-a-column/components/index.q{xml}

Each test starts from a database built by the migrations, so the test sees
the schema a new install gets:

<<< @/../examples/cookbook/data-and-sql/add-a-column/tests/stock.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/add-a-column/output/test-report.txt{text}

Rather write the schema you want and let Quantum write the migration? See
`quantum migrate plan` in [Project Structure](../../guide/project-structure.md).
See [DB-6](../../reference/spec.md#DB-6) and [DB-8](../../reference/spec.md#DB-8).
