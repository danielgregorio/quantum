---
title: Mail in development
description: "Send mail from an action without a mail server while you develop — host: log writes each message to the log."
---

# Mail in development

**Task:** a contact form that e-mails the support team — and that you can
develop and test without a mail server.

With `host: log`, `q:mail` writes each message to the log instead of sending
it. The config reads the host from the environment, so production only sets
`SMTP_HOST`:

<<< @/../examples/cookbook/files-and-mail/mail-in-development/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/files-and-mail/mail-in-development/components/index.q{xml}

The tests submit the form and check what the visitor is told, and that a bad
address is refused on its field before anything is sent:

<<< @/../examples/cookbook/files-and-mail/mail-in-development/tests/contact.test.q{xml}

<<< @/../examples/cookbook/files-and-mail/mail-in-development/output/test-report.txt{text}

And this is the message the first test "sent" — what `host: log` wrote:

<<< @/../examples/cookbook/files-and-mail/mail-in-development/output/mail.txt{text}

Without a `mail:` section, `q:mail` is an error that says so — it never
pretends to send. More in [Files & Mail](../../guide/files-and-mail.md).

*Tested:* this page imports the files of
`examples/cookbook/files-and-mail/mail-in-development/`, and the results above
come from running them.
