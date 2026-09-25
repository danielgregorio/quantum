---
order: 7
title: Read the query string
description: "query.name reads ?name= from the address; default covers a missing one; urlencode builds a link."
---

# Read the query string

**Task:** filter and sort a list from values in the address.

<<< @/../examples/cookbook/basics/query-string/quantum.config.yaml{yaml}

`query.q` is the value of `?q=` in the address, and is empty when the
address has none, so `default` gives it a value. A GET form fills the
address for you. `urlencode()` makes a typed value safe inside a link.

<<< @/../examples/cookbook/basics/query-string/components/index.q{xml}

<<< @/../examples/cookbook/basics/query-string/tests/search.test.q{xml}

<<< @/../examples/cookbook/basics/query-string/output/test-report.txt{text}

See [SET-1](../../reference/spec.md#SET-1) and [EXPR-12](../../reference/spec.md#EXPR-12).
