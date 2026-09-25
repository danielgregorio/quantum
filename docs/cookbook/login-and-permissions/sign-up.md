---
order: 2
title: Sign up and store a password hash
description: "Create an account with hashPassword, so the database never holds the password, with rules on each field."
---

# Sign up and store a password hash

**Task:** create an account without ever storing the password itself.

<<< @/../examples/cookbook/login-and-permissions/sign-up/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/login-and-permissions/sign-up/migrations/V001_users.sql{sql}

`hashPassword(password)` returns a bcrypt hash with a new salt every time; the
`INSERT` stores that. The `q:param` rules run before anything else: a password
under 12 characters never reaches the query.

<<< @/../examples/cookbook/login-and-permissions/sign-up/components/index.q{xml}

The tests look in the table: the row has a bcrypt hash (it starts with `$2b$`)
and no row holds the password as typed:

<<< @/../examples/cookbook/login-and-permissions/sign-up/tests/signup.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/sign-up/output/test-report.txt{text}

To sign in with that hash, see [Log in with a hashed password](./login-with-hashed-password.md).
