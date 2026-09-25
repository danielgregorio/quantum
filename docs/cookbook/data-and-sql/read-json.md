---
order: 10
title: Read a JSON file
description: "A JSON array as a list of records, with a computed field on each."
---

# Read a JSON file

**Task:** show a cart from a JSON file, with each line's subtotal, largest
first.

<<< @/../examples/cookbook/data-and-sql/read-json/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/read-json/import/products.json{json}

A JSON array is the list as it is. `q:compute` adds a field to each record;
`{price}` and `{qty}` are the record's own fields.

<<< @/../examples/cookbook/data-and-sql/read-json/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/read-json/tests/cart.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/read-json/output/test-report.txt{text}

See [DATA-1](../../reference/spec.md#DATA-1) and [DATA-3](../../reference/spec.md#DATA-3).
