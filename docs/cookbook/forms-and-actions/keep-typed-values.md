---
order: 2
title: A refused form keeps what was typed
description: "After a refusal, the form comes back filled with the values sent, once, so nobody types a long message twice."
---

# A refused form keeps what was typed

**Task:** when the server refuses a form, bring it back with what the person
typed, not empty.

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/migrations/V001_messages.sql{sql}

There is nothing to write for it. After a refusal, the next render of a
`ui:form` fills each field with the value sent, once, like the flash. A
password or file field never comes back. `rows="6"` makes the message a
multi-line field.

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/components/index.q{xml}

The first test sends a bad address with a good message: the address is
refused and the message is still in its field. The second opens the page
again: the values are gone.

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/tests/contact.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/output/test-report.txt{text}

See [UI-9](../../reference/spec.md#UI-9) and, for the multi-line field,
[UI-14](../../reference/spec.md#UI-14).
