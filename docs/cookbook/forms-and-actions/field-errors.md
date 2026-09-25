---
order: 1
title: Show each error on its field
description: "Write the rules once on the action's q:param; the form reads them and shows every refusal next to its field."
---

# Show each error on its field

**Task:** refuse a bad form and say, next to each field, what is wrong with it.

<<< @/../examples/cookbook/forms-and-actions/field-errors/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/field-errors/migrations/V001_guests.sql{sql}

The rules are written once, on the action's `q:param`s. The `ui:form` reads
them and puts them on its fields (`required`, `minlength`, `type="number"`,
`min`...), so the browser checks first. The server checks again, every field
at once: when one fails, the action does not run, the page comes back and
each field shows its own message.

<<< @/../examples/cookbook/forms-and-actions/field-errors/components/index.q{xml}

`error="field"` in a test checks that the field was refused, and `message=`
the text shown next to it:

<<< @/../examples/cookbook/forms-and-actions/field-errors/tests/guests.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/field-errors/output/test-report.txt{text}

The rules and their messages: [ACT-2](../../reference/spec.md#ACT-2) and
[UI-9](../../reference/spec.md#UI-9).
