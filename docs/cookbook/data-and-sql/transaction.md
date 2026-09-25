---
order: 5
title: Writes that happen together
description: "A q:transaction: the debit, the credit and the log line commit together, or none of them does."
---

# Writes that happen together

**Task:** move money between two accounts so that it can never be debited
from one without being credited to the other.

<<< @/../examples/cookbook/data-and-sql/transaction/quantum.config.yaml{yaml}

The log table refuses a transfer above 1000 — which the last test uses to
make the third write fail:

<<< @/../examples/cookbook/data-and-sql/transaction/migrations/V001_accounts.sql{sql}

The page checks what it can explain (not enough money) and says so with a
flash. The three writes go inside `q:transaction`: if any of them fails, the
ones before it are rolled back and the page stops with the error.

<<< @/../examples/cookbook/data-and-sql/transaction/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/transaction/tests/transfer.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/transaction/output/test-report.txt{text}

See [DB-4](../../reference/spec.md#DB-4).
