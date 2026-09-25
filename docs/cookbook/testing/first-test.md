---
order: 1
title: A first test with quantum test
description: "Test a page and its action in Quantum itself — visit, submit, check the flash, the table and the field error."
---

# A first test with `quantum test`

**Task:** check that a page lists what is in the database, that its action
stores a row and says so, and that it refuses bad input — without writing
Python.

A small app: one table, a page that lists it and an action that adds to it.

<<< @/../examples/cookbook/testing/first-test/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/testing/first-test/migrations/V001_notes.sql{sql}

<<< @/../examples/cookbook/testing/first-test/components/index.q{xml}

The tests sit next to it, in `tests/`. Each `q:test` starts from a fresh
database built from `migrations/`, so they do not depend on each other:

<<< @/../examples/cookbook/testing/first-test/tests/notes.test.q{xml}

Run them from the app's folder:

```bash
quantum test
```

<<< @/../examples/cookbook/testing/first-test/output/test-report.txt{text}

`test:visit` opens the page; `test:submit` posts an action with the other
attributes as its fields; `test:expect` checks what happened — the status,
the redirect and the flash, a text on the page, rows in a table, or the field
an input was refused on. The whole vocabulary is in the
[Testing an App](../../guide/testing.md) guide.

*Tested:* this page imports the files of `examples/cookbook/testing/first-test/`,
and the result above is the report of running them.
