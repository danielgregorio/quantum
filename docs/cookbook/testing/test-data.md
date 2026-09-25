---
order: 2
title: Test data with test:given
description: "Put the rows a test needs in its fresh database with test:given, and sign a user in with test:as."
---

# Test data with `test:given`

**Task:** test a page that depends on data and on who is looking — without a
fixtures file and without a password.

The page lists the signed-in user's open tasks:

<<< @/../examples/cookbook/testing/test-data/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/testing/test-data/migrations/V001_tasks.sql{sql}

<<< @/../examples/cookbook/testing/test-data/components/index.q{xml}

Each test starts from an empty database built by `migrations/`.
`test:given` puts in the rows the test needs — through the schema's rules, so
a row the app could never have written (a `done` outside `CHECK (… IN …)`, a
missing required column it cannot fill) fails the step instead of slipping in.
`test:as` signs a user in the way a login does:

<<< @/../examples/cookbook/testing/test-data/tests/tasks.test.q{xml}

<<< @/../examples/cookbook/testing/test-data/output/test-report.txt{text}

`no-text` checks what must *not* be on the page — here, another user's task
and a finished one. The whole vocabulary is in the
[Testing an App](../../guide/testing.md) guide.

*Tested:* this page imports the files of `examples/cookbook/testing/test-data/`,
and the result above is the report of running them.
