---
order: 6
title: Change history
description: "history: true records who changed which row, and how; ui:history shows it on the page."
---

# Change history

**Task:** know who changed a page of a wiki, when, and what they changed.

`history: true` on the datasource is the whole setup:

<<< @/../examples/cookbook/data-and-sql/change-history/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/change-history/migrations/V001_pages.sql{sql}

Every write an action makes is recorded in a `quantum_history` table of the
same database, in the same transaction: when, the session's user, the action,
the row, and the row before and after. `ui:history` lists a row's changes,
newest first, with each changed column as `old → new`.

<<< @/../examples/cookbook/data-and-sql/change-history/components/index.q{xml}

`test:as` signs the test in; `history=` checks what was recorded. A write
that is refused, or rolled back, leaves no history:

<<< @/../examples/cookbook/data-and-sql/change-history/tests/history.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/change-history/output/test-report.txt{text}

See [DB-11](../../reference/spec.md#DB-11).
