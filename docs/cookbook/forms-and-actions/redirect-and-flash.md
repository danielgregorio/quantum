---
order: 3
title: Redirect and say what happened
description: "End an action with q:redirect and a flash; q:flash for a warning; the message shows once on the next page."
---

# Redirect and say what happened

**Task:** after a form is sent, take the browser to a page and tell it what
happened, once.

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/migrations/V001_notes.sql{sql}

`q:redirect` ends the action. Its `flash` takes expressions and becomes
`flash` on the next page rendered, with `flashType` set to `success`. For
another kind of message, `q:flash type="warning"` sets both before the
redirect. The URL can be any page of the app.

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/components/index.q{xml}

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/components/done.q{xml}

The second test opens the page again after the redirect: the flash is gone,
and `flash` is `''`.

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/tests/notes.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/output/test-report.txt{text}

See [ACT-3](../../reference/spec.md#ACT-3).
