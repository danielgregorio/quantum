---
order: 5
title: Every kind of field
description: "ui:form with ui:formitem labels: text, number, a select with options, a switch, radios and a multi-line field."
---

# Every kind of field

**Task:** a form that uses each kind of field, with labels.

<<< @/../examples/cookbook/screens/form-fields/quantum.config.yaml{yaml}

`ui:formitem label="…"` puts a label next to its field. `ui:select` takes
its choices from `ui:option`s with their own texts, and `ui:radio` takes
them from the `enum` of the action's `q:param`. A `ui:switch` is a
boolean box, and `rows` makes a multi-line field. The rules of each field
come from the action ([Show each error on its field](../forms-and-actions/field-errors.md)).

<<< @/../examples/cookbook/screens/form-fields/components/index.q{xml}

<<< @/../examples/cookbook/screens/form-fields/tests/booking.test.q{xml}

<<< @/../examples/cookbook/screens/form-fields/output/test-report.txt{text}

See [UI-9](../../reference/spec.md#UI-9) and [UI-14](../../reference/spec.md#UI-14).
