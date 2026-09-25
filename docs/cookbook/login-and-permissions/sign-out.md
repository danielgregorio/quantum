---
order: 5
title: Sign out
description: "A logout page that clears the session and redirects; the protected pages are closed again."
---

# Sign out

**Task:** end the user's session.

<<< @/../examples/cookbook/login-and-permissions/sign-out/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/login-and-permissions/sign-out/components/index.q{xml}

A page can change the session and then redirect: what it wrote to the session
before `q:redirect` stays written.

<<< @/../examples/cookbook/login-and-permissions/sign-out/components/logout.q{xml}

<<< @/../examples/cookbook/login-and-permissions/sign-out/components/login.q{xml}

The test signs in, signs out, and checks that the home page asks to sign in
again:

<<< @/../examples/cookbook/login-and-permissions/sign-out/tests/logout.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/sign-out/output/test-report.txt{text}
