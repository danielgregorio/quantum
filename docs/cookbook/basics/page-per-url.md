---
order: 6
title: A page per URL
description: "components/product/[id].q answers /product/1, /product/2...; the segment is a variable."
---

# A page per URL

**Task:** one file that answers a URL for each item.

<<< @/../examples/cookbook/basics/page-per-url/quantum.config.yaml{yaml}

A `[name]` segment in a file or folder name matches any value, and the page
gets it as the variable `name`. It arrives as text; `type="integer"` on a
`q:set` turns it into a number.

<<< @/../examples/cookbook/basics/page-per-url/components/product/[id].q{xml}

<<< @/../examples/cookbook/basics/page-per-url/tests/product.test.q{xml}

<<< @/../examples/cookbook/basics/page-per-url/output/test-report.txt{text}

With a database, the page reads the row with the id: see
[Edit a row](../forms-and-actions/edit-a-row.md). The rule:
[ROUTE-1](../../reference/spec.md#ROUTE-1).
