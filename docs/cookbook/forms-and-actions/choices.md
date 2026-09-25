---
order: 9
title: A choice from a list
description: "enum on q:param gives ui:select and ui:radio their options and refuses anything else; a box is a boolean."
---

# A choice from a list

**Task:** a field that takes one value from a list, and a yes/no box.

<<< @/../examples/cookbook/forms-and-actions/choices/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/choices/migrations/V001_orders.sql{sql}

The list is written once, as `enum` on the action's `q:param`. A
`ui:select` or `ui:radio` with no options of its own takes them from it,
and the server refuses a value that is not on it. `default` fills a field
left out. A box sends a value only when checked, so `type="boolean"`
`default="false"` makes it `true` or `false`.

<<< @/../examples/cookbook/forms-and-actions/choices/components/index.q{xml}

<<< @/../examples/cookbook/forms-and-actions/choices/tests/order.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/choices/output/test-report.txt{text}

See [ACT-2](../../reference/spec.md#ACT-2) and [UI-9](../../reference/spec.md#UI-9).
