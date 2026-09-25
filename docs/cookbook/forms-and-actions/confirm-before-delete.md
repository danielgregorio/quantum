---
order: 7
title: Confirm before deleting
description: "A page that asks first, reached by a link, and the delete as a POST from its button; no JavaScript."
---

# Confirm before deleting

**Task:** ask "are you sure?" before deleting, without JavaScript.

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/migrations/V001_contacts.sql{sql}

The list has a link, not a button. Opening a link only reads, so it can
only ask:

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/components/index.q{xml}

The question is a page of its own, `components/delete/[id].q`. Its button
posts to the `remove` action, which deletes and goes back to the list. If
the contact is already gone (a second tab, a reload), the page says so
instead of asking.

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/components/delete/[id].q{xml}

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/tests/delete.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/output/test-report.txt{text}
