---
order: 8
title: Numbers and dates
description: "type=integer, decimal and date on q:param: the action gets checked numbers and real dates, with min and max."
---

# Numbers and dates

**Task:** take an amount, a count and a date, and do arithmetic with them
without converting anything by hand.

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/migrations/V001_expenses.sql{sql}

A form sends text. `type="decimal"` and `type="integer"` make it a number
before the action runs, so `amount / people` works. `min` and `max` are
checked on that number. `type="date"` takes `YYYY-MM-DD` and a day that
exists, and keeps it as text, ready for the database.

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/components/index.q{xml}

The form gets `type="number"` with the same `min` and `max`, and
`type="date"`, so the browser checks first. The tests post straight to the
server, as a script would:

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/tests/split.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/output/test-report.txt{text}

See [ACT-2](../../reference/spec.md#ACT-2) and [UI-9](../../reference/spec.md#UI-9).
