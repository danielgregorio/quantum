# Sessions & Scopes

A plain `q:set` lives for one page render. Three prefixed scopes keep values
longer, or expose the request itself:

| Scope | Lives | Shared with |
|-------|-------|-------------|
| `session.` | across requests, for one visitor | that visitor only |
| `application.` | while the server process runs | every visitor of that process |
| `request.` | one request | — |

`application.` is memory in the server process: it is gone after a restart, and
under `gunicorn --workers 4` each worker has its own. Keep what must last in the
database — see [How a Page Runs](/guide/how-a-page-runs).

Sessions are kept in a signed cookie by the web server, so they work with
`quantum start` out of the box.

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

Two visitors opening the page one after the other see:

| Request | `session.mine` | `application.everyone` |
|---------|------------------|---------------------|
| visitor A, 1st | 1 | 1 |
| visitor A, 2nd | 2 | 2 |
| visitor B, 1st | 1 | 3 |

`operation="increment"` starts from zero when the variable does not exist yet.

::: warning Arithmetic on a missing session value
`value="{session.mine + 1}"` does **not** work on the first visit: a missing
scope value evaluates to an empty string, and converting that to a number
fails. Use `operation="increment"` (or `operation="add"` with a `value`) for
counters. Known gap `G15`, to be settled by the language specification.
:::

## Reading a scope that was never set

Reading `session.something` or `request.something` that does not exist is not an error:
it renders empty, and in a condition it is false. That makes "is the visitor
logged in?" a one-liner:

```xml
<q:if condition="session.authenticated">
  <p>Welcome back!</p>
  <q:else><a href="/login">Sign in</a></q:else>
</q:if>
```

## Writing from an action

Actions write to `session.` the same way, and the change is saved before the
redirect — see [Actions & Forms](/guide/actions) and
[Authentication](/guide/authentication).

## Request values

| Variable | Contains |
|----------|----------|
| `request.method` | `GET`, `POST`… |
| `request.path` | the path, without the query string |
| `request.user_agent` | the browser's `User-Agent` header |
