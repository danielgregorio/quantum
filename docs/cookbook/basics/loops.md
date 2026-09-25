---
order: 3
title: Loops
description: "q:loop over a list (with its position), a range of numbers and comma-separated text."
---

# Loops

**Task:** repeat part of a page for each item of a list or each number of a range.

<<< @/../examples/cookbook/basics/loops/quantum.config.yaml{yaml}

`type="array"` goes over a list, with `index=` naming the position from 0.
`type="range"` counts from `from` to `to`, both included, by `step`.
`type="list"` splits text by commas and trims each item.

<<< @/../examples/cookbook/basics/loops/components/index.q{xml}

<<< @/../examples/cookbook/basics/loops/tests/loops.test.q{xml}

<<< @/../examples/cookbook/basics/loops/output/test-report.txt{text}

To loop over the rows of a query, see [Several forms on one page](../forms-and-actions/several-actions.md).
The rules: [LOOP-5](../../reference/spec.md#LOOP-5) and [LOOP-6](../../reference/spec.md#LOOP-6).
