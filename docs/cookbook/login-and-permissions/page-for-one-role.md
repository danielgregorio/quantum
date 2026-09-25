---
order: 3
title: A page for one role only
description: "require_role keeps a page to the admins: a member gets 403, and a visitor who is not signed in is sent to sign in."
---

# A page for one role only

**Task:** show a page to administrators only.

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/quantum.config.yaml{yaml}

`require_auth="true"` asks for a signed-in session; `require_role` for one of
the listed roles in `session.userRole` (several are separated by commas,
`require_role="admin,editor"`):

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/components/reports.q{xml}

Without a session, the answer redirects to `/login` (change it with
`security.login_url`):

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/components/login.q{xml}

`test:as` signs the test's session in with a role, without a password:

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/tests/reports.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/output/test-report.txt{text}
