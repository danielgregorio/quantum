---
order: 1
title: Log in with a hashed password
description: "Check a password against its bcrypt hash with verifyPassword, open the session, and keep a page for signed-in users."
---

# Log in with a hashed password

**Task:** let a user sign in with an e-mail and a password, where the database
keeps only a hash of the password, and show a page only to signed-in users.

The table stores a bcrypt hash (made with `hashPassword`, as in the
[sign-up recipe](./sign-up.md)), never the password:

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/migrations/V001_users.sql{sql}

The sign-in action looks the user up and checks the password with
`verifyPassword`. It is false, never an error, for a wrong password, a missing
user or an empty field. On success it sets the session variables that
`require_auth` and `require_role` read. `session.sessionExpiry` is required: a
session without it counts as expired.

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/components/login.q{xml}

The home page asks for a signed-in session with `require_auth="true"`:

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/components/index.q{xml}

A wrong address and a wrong password get the same message, so the form does
not tell a stranger which addresses have an account:

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/tests/login.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/output/test-report.txt{text}

More in the [Authentication](../../guide/authentication.md) guide.
