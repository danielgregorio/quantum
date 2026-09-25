---
order: 8
title: Reusable components
description: "A component with props and a slot, imported from a _ folder that is never served."
---

# Reusable components

**Task:** write a card once and use it on any page, with different content.

<<< @/../examples/cookbook/basics/components-and-slots/quantum.config.yaml{yaml}

A component is a `.q` file too. Its `q:param`s are its props, and
`q:slot` is where the caller's content goes. Keep it in a folder whose name
starts with `_`: it can be imported, and it never answers a URL.

<<< @/../examples/cookbook/basics/components-and-slots/components/_shared/Card.q{xml}

`q:import` brings it into the page, and `<Card>` uses it. Each attribute is
a prop, and the content between the tags fills the slot, computed with the
page's variables:

<<< @/../examples/cookbook/basics/components-and-slots/components/index.q{xml}

<<< @/../examples/cookbook/basics/components-and-slots/tests/cards.test.q{xml}

<<< @/../examples/cookbook/basics/components-and-slots/output/test-report.txt{text}

See [COMP-1](../../reference/spec.md#COMP-1), [COMP-3](../../reference/spec.md#COMP-3)
and [ROUTE-3](../../reference/spec.md#ROUTE-3).
