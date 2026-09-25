---
order: 2
title: When the mail server says no
description: "Keep an order even when its confirmation e-mail cannot be sent — onerror=continue, and tell the visitor."
---

# When the mail server says no

**Task:** an order must be saved even when the confirmation e-mail cannot be
sent — and the visitor should hear about it, not get an error page.

By default a `q:mail` the server does not take stops the action with the
server's reason. `onerror="continue"` lets the action go on and puts the
outcome in `<name>_result`: `success`, and `error.message` when it failed.

This recipe points at a mail server that is not there, so every message fails
— as it does when the real server is down:

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/migrations/V001_orders.sql{sql}

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/components/index.q{xml}

The order is inserted before the mail, and the flash says which way it went.
The test checks both — the row is there, and the visitor was told:

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/tests/order.test.q{xml}

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/output/test-report.txt{text}

In development, [`host: log`](./mail-in-development.md) avoids the failure
altogether; `onerror="continue"` is for the day the real server is down.
More in [Files & Mail](../../guide/files-and-mail.md).

*Tested:* this page imports the files of
`examples/cookbook/files-and-mail/mail-server-refuses/`, and the result above
comes from running them.
