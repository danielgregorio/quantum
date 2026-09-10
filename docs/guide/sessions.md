# Sessions & Scopes

A plain `q:set` lives for one page render. Three prefixed scopes keep values
longer, or expose the request itself:

| Scope | Lives | Shared with |
|-------|-------|-------------|
| `session.` | across requests, for one visitor | that visitor only |
| `application.` | while the server runs | every visitor |
| `request.` | one request | — |

Sessions are kept in a signed cookie by the web server, so they work with
`quantum start` out of the box.

## Counting visits

Save as `components/visitas.q`:

```xml
<q:component name="visitas" xmlns:q="https://quantum.lang/ns">
  <q:set name="session.minhas" operation="increment" />
  <q:set name="application.todas" operation="increment" />

  <html><body>
    <p>Suas visitas: {session.minhas}</p>
    <p>Visitas de todo mundo: {application.todas}</p>
    <p>{request.method} {request.path}</p>
  </body></html>
</q:component>
```

Two visitors opening the page one after the other see:

| Request | `session.minhas` | `application.todas` |
|---------|------------------|---------------------|
| visitor A, 1st | 1 | 1 |
| visitor A, 2nd | 2 | 2 |
| visitor B, 1st | 1 | 3 |

`operation="increment"` starts from zero when the variable does not exist yet.

::: warning Arithmetic on a missing session value
`value="{session.minhas + 1}"` does **not** work on the first visit: a missing
scope value evaluates to an empty string, and converting that to a number
fails. Use `operation="increment"` (or `operation="add"` with a `value`) for
counters. Known gap `G15`, to be settled by the language specification.
:::

## Reading a scope that was never set

Reading `session.algo` or `request.algo` that does not exist is not an error:
it renders empty, and in a condition it is false. That makes "is the visitor
logged in?" a one-liner:

```xml
<q:if condition="session.authenticated">
  <p>Bem-vindo de volta!</p>
  <q:else><a href="/login">Entrar</a></q:else>
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
