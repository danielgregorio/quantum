---
order: 2
title: Variables and expressions
description: "q:set stores a value, braces compute with it, and default fills in what is missing."
---

# Variables and expressions

**Task:** keep values in variables and compute with them.

<<< @/../examples/cookbook/basics/variables/quantum.config.yaml{yaml}

`q:set` stores a value under a name. Braces compute with it: in a `q:`
attribute and in the HTML. `type="number"` makes text a number, and a value
that is a single expression keeps its type, so `total` is a number.
`operation="increment"` changes a variable in place, and the page runs top
to bottom: `total` was computed before `quantity` grew. `default` is
stored when the value is empty or missing, as `?note=` is on a plain visit.

<<< @/../examples/cookbook/basics/variables/components/index.q{xml}

<<< @/../examples/cookbook/basics/variables/tests/receipt.test.q{xml}

<<< @/../examples/cookbook/basics/variables/output/test-report.txt{text}

See [SET-1](../../reference/spec.md#SET-1), [SET-3](../../reference/spec.md#SET-3)
and [SET-5](../../reference/spec.md#SET-5).
