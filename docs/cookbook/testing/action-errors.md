---
order: 3
title: Testing what an action refuses
description: "Test the field errors, the business rule and the success of an action — error=, message=, flash= and the table."
---

# Testing what an action refuses

**Task:** prove that a form refuses what it should — a field that breaks its
rule, a value the business does not allow — and that nothing is written when
it does.

A sign-up with two kinds of refusal: the `q:param` rules (checked before the
action runs) and a business rule in the action itself (the address is
already a member):

<<< @/../examples/cookbook/testing/action-errors/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/testing/action-errors/migrations/V001_members.sql{sql}

<<< @/../examples/cookbook/testing/action-errors/components/index.q{xml}

`error="name"` checks the field the submit was refused on, and `message=` the
text shown next to it. A refusal the action decides itself is a redirect with a
flash, checked with `flash=`. `table=` with `count=` proves nothing was written:

<<< @/../examples/cookbook/testing/action-errors/tests/signup.test.q{xml}

<<< @/../examples/cookbook/testing/action-errors/output/test-report.txt{text}

The rules a `q:param` takes (`required`, `minlength`, `type="email"`, `enum`…)
are in [Actions & Forms](../../guide/actions.md).

*Tested:* this page imports the files of
`examples/cookbook/testing/action-errors/`, and the result above is the report
of running them.
