# Sessions & Scopes

A plain `q:set` lives for one request (SET-2). Three prefixed scopes keep
values longer, or expose the request itself:

| Scope | Lives | Shared with |
|-------|-------|-------------|
| `session.` | across requests, for one visitor | that visitor only |
| `application.` | while the server process runs | every visitor of that process |
| `request.` | one request | — |

`application.` is memory in the server process: it is gone after a restart, and
under `gunicorn --workers 4` each worker has its own. Keep what must last in the
database — see [How a Page Runs](/guide/how-a-page-runs).

Sessions are kept in a signed cookie by the web server, so they work with
`quantum start` out of the box. When you deploy, set `QUANTUM_SECRET_KEY` (or
`security.secret_key` in the config): without it each process signs with a key
of its own, and a restart logs everyone out.

The examples on this page run in CI (`tests/docs/test_guide_sessions.py`).

## Counting visits

Save as `components/visits.q`:

```xml
<q:component name="visits" xmlns:q="https://quantum.lang/ns">
  <q:set name="session.mine" operation="increment" />
  <q:set name="application.everyone" operation="increment" />

  <html><body>
    <p>Your visits: {session.mine}</p>
    <p>Everyone's visits: {application.everyone}</p>
    <p>{request.method} {request.path}</p>
  </body></html>
</q:component>
```

Two visitors opening `/visits` one after the other see:

| Request | `session.mine` | `application.everyone` |
|---------|------------------|---------------------|
| visitor A, 1st | 1 | 1 |
| visitor A, 2nd | 2 | 2 |
| visitor B, 1st | 1 | 3 |

and the last line says `GET /visits`. `operation="increment"` starts from zero
when the variable does not exist yet (SET-3).

## A value that does not exist yet

Arithmetic on a session value that was never set is an error that says so and
points to the fix (EXPR-3):

```xml
<q:set name="session.visits" value="{session.visits + 1}" />
```

**Error:** `session value used in 'session.visits + 1' is not set`

Use `operation="increment"` for a counter, or give the value a `default`
(SET-1):

```xml
<q:set name="session.visits" operation="increment" />
<q:return value="Visits: {session.visits}" />
```

**Output:** `Visits: 1`

The reference alone is not an error: `{session.name}` that does not exist
renders empty (a page renders before login), and in a condition it is false:

```xml
<q:return value="Hello, {session.name}!" />
```

**Output:** `Hello, !`

That makes "is the visitor logged in?" a one-liner. Save as
`components/welcome.q`:

```xml
<q:component name="welcome" xmlns:q="https://quantum.lang/ns">
  <q:if condition="session.authenticated">
    <p>Welcome back!</p>
    <q:else><a href="/login">Sign in</a></q:else>
  </q:if>
</q:component>
```

A new visitor sees **Sign in**; once an action has set
`session.authenticated`, the same page says **Welcome back!**

## Writing from an action

Actions write to `session.` the same way, and the change is saved before the
redirect — see [Actions & Forms](/guide/actions) and
[Authentication](/guide/authentication).

## Request values

| Variable | Contains |
|----------|----------|
| `request.method` | `GET`, `POST`… |
| `request.path` | the path, without the query string |
| `request.url` | the whole URL, with the query string |

The query string itself is in `query.` (`{query.page}`), and a submitted form
in `form.`.
