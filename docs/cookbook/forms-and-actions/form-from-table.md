---
order: 5
title: A form from the table
description: "q:action table= takes its params from the schema; a ui:form with no fields draws one field per column."
---

# A form from the table

**Task:** a form for a table without writing each field and each rule again.

<<< @/../examples/cookbook/forms-and-actions/form-from-table/quantum.config.yaml{yaml}

The schema already says what a book needs:

<<< @/../examples/cookbook/forms-and-actions/form-from-table/migrations/V001_library.sql{sql}

`<q:action table="books" datasource="db">` reads it and makes a `q:param` of
each column except the key, in the table's order:

| Column | Becomes |
|---|---|
| `title VARCHAR(120) NOT NULL` | required, at most 120 characters |
| `author_id ... REFERENCES authors(id)` | an integer that must name an existing author |
| `genre ... CHECK (genre IN (...))` | one of the three |
| `pages INTEGER` (accepts NULL) | an integer; left blank, it reaches the action as `None` |
| `lent BOOLEAN` | a box |

A `ui:form` with no fields of its own draws one per param, labelled from the
name (`author_id` becomes "Author"). The author field is a list of the
authors' names. `null="true"` on the query's `pages` param stores a blank as
`NULL`.

<<< @/../examples/cookbook/forms-and-actions/form-from-table/components/index.q{xml}

<<< @/../examples/cookbook/forms-and-actions/form-from-table/tests/books.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/form-from-table/output/test-report.txt{text}

A `q:param` written in the action wins over the schema's, and
`columns="a,b"` keeps only those columns. See
[UI-10](../../reference/spec.md#UI-10).
