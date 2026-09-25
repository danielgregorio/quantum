---
order: 4
title: Conditionals
description: "q:if, q:elseif and q:else, with conditions that are expressions."
---

# Conditionals

**Task:** show one thing or another depending on a value.

<<< @/../examples/cookbook/basics/conditionals/quantum.config.yaml{yaml}

The first branch whose condition holds runs; `q:else` runs when none does.
A condition is an expression, with `and`, `or` and `not`. Inside an
attribute, `<` is written `&lt;`: a `.q` file is XML.

<<< @/../examples/cookbook/basics/conditionals/components/index.q{xml}

<<< @/../examples/cookbook/basics/conditionals/tests/stock.test.q{xml}

<<< @/../examples/cookbook/basics/conditionals/output/test-report.txt{text}

See [IF-1](../../reference/spec.md#IF-1) and [IF-2](../../reference/spec.md#IF-2).
