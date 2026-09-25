---
order: 2
title: A table you edit in place
description: "ui:table edit= turns each cell into a small form checked against the table's schema; no action to write."
---

# A table you edit in place

**Task:** let people change a value in a table without opening an edit page.

<<< @/../examples/cookbook/screens/editable-table/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/screens/editable-table/migrations/V001_items.sql{sql}

`edit="items"` makes each cell a small form that saves one column of one
row. The table's schema is the rule: `shelf` must be A, B or C because of
its `CHECK`, and a refused value comes back as an error flash. A column with
`edit="false"` is shown, not edited, and a post that tries anyway answers
`400`. `sort="true"` puts links on the headers.

<<< @/../examples/cookbook/screens/editable-table/components/index.q{xml}

A test edits a cell the way the browser does, with the `__edit` action:

<<< @/../examples/cookbook/screens/editable-table/tests/stock.test.q{xml}

<<< @/../examples/cookbook/screens/editable-table/output/test-report.txt{text}

See [UI-5](../../reference/spec.md#UI-5) and [UI-13](../../reference/spec.md#UI-13).
