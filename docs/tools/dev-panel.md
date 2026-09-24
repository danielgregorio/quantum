# The `/_dev` Panel

While you write an app, `/_dev` shows what the last requests did: which
component answered, which `q:action` ran, every query with its parameters,
time and rows, the variables each scope ended with, the redirect and the flash.

Turn it on in `quantum.config.yaml`:

```yaml
server:
  debug: true
  host: 127.0.0.1
```

`quantum start` prints the address (`Dev panel: http://localhost:8080/_dev`).
Use the app, then open `/_dev`: the newest request is shown, and each row of
the list opens its own request (`/_dev/12`).

| Section | What it shows |
|---|---|
| Component, Action | the `.q` file that answered and the action a POST ran |
| Redirect, Flash | where an action sent the browser, and the message for the next page |
| Queries | datasource, SQL, parameters, rows (or the database's error), time |
| action / page | the variables the action or the page ended with |
| session / application | the scopes as they were at the end of the request |

A value longer than 300 characters is cut. Everything is escaped: a variable
holding HTML shows as text.

## It exists only while developing

- With `debug: false` nothing is recorded and `/_dev` is a 404.
- It answers only requests from the machine itself (`127.0.0.1` / `::1`): the
  panel shows sessions and query parameters, so from any other address it does
  not exist — even if the config says `debug: true` behind a public bind.
- It keeps the last 30 requests of the server process, in memory.
