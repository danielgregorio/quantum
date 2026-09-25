---
order: 8
title: Read a CSV file
description: "q:data turns a CSV file into typed records, filtered and sorted — no database needed."
---

# Read a CSV file

**Task:** show the active customers of a CSV file, oldest first.

<<< @/../examples/cookbook/data-and-sql/read-a-csv/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/read-a-csv/import/customers.csv{text}

Declared columns are typed (`true`, `1`, `yes` and `on` are a true boolean);
the others come as text. `q:transform` runs its operations in order.

<<< @/../examples/cookbook/data-and-sql/read-a-csv/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/read-a-csv/tests/customers.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/read-a-csv/output/test-report.txt{text}

See [DATA-1](../../reference/spec.md#DATA-1) and
[DATA-3](../../reference/spec.md#DATA-3), and [Data Import](../../guide/data-import.md).
