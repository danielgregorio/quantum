---
order: 4
title: Several forms on one page
description: "Each form and button posts the name of its action; a name the page does not have answers 400."
---

# Several forms on one page

**Task:** add, remove and empty from one page, each with its own action.

<<< @/../examples/cookbook/forms-and-actions/several-actions/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/several-actions/migrations/V001_cart.sql{sql}

Each `ui:form on-submit` and each `ui:button on-click` sends the name of its
action in a field called `action`; the page runs that action and no other.
`with="id={cart.id}"` sends the row's id with the button.

<<< @/../examples/cookbook/forms-and-actions/several-actions/components/index.q{xml}

On a page with more than one action, a post whose `action` is missing or
names none of them answers `400` and lists the actions there are. Nothing
runs in its place, as the last test checks:

<<< @/../examples/cookbook/forms-and-actions/several-actions/tests/cart.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/several-actions/output/test-report.txt{text}

See [ACT-5](../../reference/spec.md#ACT-5).
