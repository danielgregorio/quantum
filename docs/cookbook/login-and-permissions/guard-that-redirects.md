---
order: 4
title: A guard that redirects
description: "A top-level q:if with q:redirect protects a page and every action on it: a post without a session writes nothing."
---

# A guard that redirects

**Task:** send visitors who are not signed in to the sign-in page with a
message, and make sure they cannot post to the page's actions either.

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/migrations/V001_notes.sql{sql}

A `q:if` at the top of the page whose branch has a `q:redirect` is a
**guard**. It runs before the page and before each of its actions, so a post
sent straight to `add` is stopped too:

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/components/index.q{xml}

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/components/login.q{xml}

The second test posts to the action without a session and checks that no row
was written:

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/tests/guard.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/output/test-report.txt{text}

A guard can check anything the session holds. To only ask for a signed-in
user or a role, `require_auth` and `require_role` say it in one attribute
([A page for one role only](./page-for-one-role.md)).
