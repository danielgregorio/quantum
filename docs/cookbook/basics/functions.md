---
order: 5
title: Functions
description: "A q:function with typed, checked params, called from q:set and from the HTML."
---

# Functions

**Task:** write a calculation once and use it wherever the page needs it.

<<< @/../examples/cookbook/basics/functions/quantum.config.yaml{yaml}

A `q:function` takes `q:param`s like an action: each argument is converted
to its type and checked against its rules on every call, and `default` fills
one left out. `returnType` checks what comes back. A function can be called
in any expression of the page, including inside another call.

<<< @/../examples/cookbook/basics/functions/components/index.q{xml}

<<< @/../examples/cookbook/basics/functions/tests/prices.test.q{xml}

<<< @/../examples/cookbook/basics/functions/output/test-report.txt{text}

See [FN-1](../../reference/spec.md#FN-1), [FN-3](../../reference/spec.md#FN-3)
and [FN-4](../../reference/spec.md#FN-4).
