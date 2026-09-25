---
order: 6
title: Edit a row
description: "A page per row with [id].q, a form opened with the row's values, and the table's rules on save."
---

# Edit a row

**Task:** a page that edits one book, reached from the list.

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/migrations/V001_books.sql{sql}

The list links each book to `/book/{id}`:

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/components/index.q{xml}

`components/book/[id].q` answers `/book/2` with `id = 2`. The action takes
`title` and `genre` from the table ([A form from the table](./form-from-table.md))
and `values="{book}"` opens the form with the row's values. A one-row query
is enough.

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/components/book/[id].q{xml}

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/tests/edit.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/output/test-report.txt{text}

See [UI-10](../../reference/spec.md#UI-10).
