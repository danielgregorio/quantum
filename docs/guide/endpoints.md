# APIs (q:endpoint)

A page answers a browser with HTML; a `q:endpoint` answers anyone with JSON: a game that posts a report, a
script, another site's page. A component with `q:endpoint` is an API: each HTTP method it has an endpoint for
runs that endpoint, its `q:param`s come from the JSON body and are checked as an
[action's](/guide/actions) are, and `q:respond` says what it answers. Everything it answers is JSON, its
refusals and its failures included (API-1 to API-6), and `/api/openapi.json` describes them (API-7).

The examples on this page run in CI (`tests/docs/test_guide_endpoints.py`).

## Notes, listed and added

With a datasource `db` and a table `notes (id INTEGER PRIMARY KEY, text TEXT, stars INTEGER)`, save as
`components/api/notes.q`:

```xml
<q:component name="notes" xmlns:q="https://quantum.lang/ns">
  <q:endpoint method="GET">
    <q:query name="rows" datasource="db">SELECT id, text, stars FROM notes ORDER BY id</q:query>
    <q:respond json="{rows}" />
  </q:endpoint>

  <q:endpoint method="POST" origins="https://game.example" limit="10/minute" maxsize="16kb">
    <q:param name="text" type="string" required="true" maxlength="200" />
    <q:param name="stars" type="integer" min="1" max="5" default="3" />
    <q:query name="added" datasource="db">
      INSERT INTO notes (text, stars) VALUES (:text, :stars) RETURNING id
      <q:param name="text" value="{text}" type="string" />
      <q:param name="stars" value="{stars}" type="integer" />
    </q:query>
    <q:respond status="201" json="{ {'id': added[0].id, 'text': text, 'stars': stars} }" />
  </q:endpoint>
</q:component>
```

It answers `/api/notes`:

| Request | Answer |
|---------|--------|
| `POST /api/notes` `{"text": "Great game", "stars": 5}` | `201` `{"id": 1, "text": "Great game", "stars": 5}` |
| `POST /api/notes` `{"text": "Short"}` | `201` `{"id": 2, "text": "Short", "stars": 3}` |
| `GET /api/notes` | `200` `[{"id": 1, "text": "Great game", "stars": 5}, {"id": 2, "text": "Short", "stars": 3}]` |
| `POST /api/notes` `{"stars": 9}` | `422` `{"error": "invalid", "message": "Parameter 'text' is required", "fields": {"text": "Required", "stars": "Must be at most 5 (got 9)"}}` |
| `PUT /api/notes` `{}` | `405` `{"error": "method", "message": "PUT is not an endpoint of /api/notes.", "allowed": ["GET", "POST"]}` |

- `json=` is one expression, and it may be a dictionary written in place: `{ {'id': 1} }` (EXPR-17).
- `q:respond` ends the endpoint, as a return does; it may sit in a `q:if`. An endpoint that ends without one
  answers `204`, and `q:respond` without `json=` answers its status with no body.
- What was sent, as it was sent, is `body`; for `GET` and `DELETE` the `q:param`s come from the query string
  (`GET /api/notes?since=3`).
- A component's endpoints are its own statements, one for each method. A component with endpoints has no
  `q:action` (put the form in a page), and an endpoint neither redirects nor sets a flash: these are parse
  errors that say so.

## Who may call it

An endpoint is protected as the page around it would be: the component's `require_auth`, `require_role` and
guards (AUTH-6), and the endpoint's own `require_role=`. A browser that is signed in sends its session; the
refusals are JSON: `401` when no one is signed in, `403` when the one who is may not (API-3).

```xml
<q:endpoint method="DELETE" require_role="admin">
  <q:param name="id" type="integer" required="true" />
  ...
</q:endpoint>
```

## From another site's page

A page on another site may call the endpoint only if `origins=` names that site (`origins="*"` lets any). A
browser asks first (an `OPTIONS` preflight) and is told yes only for an allowed site; any other site's call
is refused with `403` before anything runs. A game on the desktop, a script, and this server's own pages send no
other site's `Origin` and are never refused for it. Cookies never cross sites, so an endpoint for other sites
takes no `require_role` (API-4).

## Limits

`limit="10/minute"` (per `second`, `minute`, `hour` or `day`) lets one address call so many times: one more
is `429` with `Retry-After`. `maxsize="16kb"` refuses a larger body with `413` before reading it (API-5).
Behind a reverse proxy (nginx, Caddy, a host's), tell the server so, or every caller is the proxy:

```yaml
server:
  proxies: 1
```

## A secret for a call it makes

An endpoint can pass what it received on: to a webhook, a forge, a mail service. Its credential stays out of
the program: in `q:invoke`'s `authToken` (and `authUsername`, `authPassword`, a `q:header`'s value),
`${NAME}` is the environment variable `NAME`, read when the call is made and never put in a variable, so no
page can show it. A variable that is not set is an error that names it, never an empty token (INV-3).

```xml
<q:invoke name="issue" url="https://api.github.com/repos/{owner}/{repo}/issues" method="POST"
          authType="bearer" authToken="${GITHUB_TOKEN}">
  <q:body>{ {'title': title, 'body': text} }</q:body>
</q:invoke>
```

## Described for whoever calls it

`/api/openapi.json` describes the application's endpoints as an [OpenAPI 3.1](https://spec.openapis.org/oas/v3.1.0)
document, read from the components as they are, so it is never out of date (API-7). A client generator, an API
browser or the person writing the game reads it there. For the notes above, the operation of the `POST`:

```json
{
  "operationId": "postApiNotes",
  "requestBody": {
    "required": true,
    "content": {
      "application/json": {
        "schema": {
          "type": "object",
          "properties": {
            "text": {"type": "string", "maxLength": 200},
            "stars": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3}
          },
          "required": ["text"]
        }
      }
    }
  },
  "responses": {
    "201": {"description": "Created", "content": {"application/json": {"schema": {
      "type": "object", "properties": {"id": {}, "text": {}, "stars": {}}, "required": ["id", "text", "stars"]}}}}
  },
  "x-origins": ["https://game.example"],
  "x-limit": "10/minute",
  "x-maxsize": 16384
}
```

- Each component with `q:endpoint` is a path, at its route: `components/api/boards/[id]/cards.q` is
  `/api/boards/{id}/cards`, with `id` a path parameter. `description="..."` on a `q:endpoint` is the
  operation's summary.
- The `q:param`s keep their rules: `minlength` is `minLength`, `min` and `range` are `minimum` and `maximum`,
  `pattern`, `enum` and the default stay; `type="date"`, `email` and `url` are strings with their format. For
  `GET` and `DELETE` they are query parameters; for the others, a JSON (or form) body.
- The answers are the `q:respond`s' statuses — an object with its keys when `json=` writes a dictionary —,
  `204` when the endpoint may end without one, and the refusals it may give: `400` and `415` for a body,
  `401` and `403` for who may call it, `413` with `maxsize=`, `422` for its parameters, `429` with `limit=`,
  `500`. Who may call it is the security of the session's cookie, with the roles of `require_role`.
- `api.title` and `api.version` in `quantum.config.yaml` are the document's title and version (the project's
  folder and `1` by default); `api.openapi: false` takes it away. Without an endpoint it is `404`.
- `quantum check --openapi openapi.json` writes the same document without a server, for a pipeline or a
  repository; `quantum check` itself lists the endpoints it found, and says when a `q:param` has the name of a
  route segment (the segment replaces it, ROUTE-2), when a `q:respond` sends a body with a status that has none
  (`204`), and when two files are at one path and only one can ever answer (DEV-3).

## When it fails

A failure in an endpoint's statements is `500` with `{"error": "server"}`: never a page. The message is in
the answer only with `server.debug`, and always in the server's log with its traceback (API-6).

## The rules

| Rule | What it says |
|------|--------------|
| [API-1](/reference/spec#API-1) | each method its endpoint; the `q:param`s from the body, checked; JSON refusals |
| [API-2](/reference/spec#API-2) | `q:respond json= status=`; `204` without it |
| [API-3](/reference/spec#API-3) | roles and guards, refused with `401` and `403` |
| [API-4](/reference/spec#API-4) | `origins=` and the browser's preflight |
| [API-5](/reference/spec#API-5) | `limit=` and `maxsize=`; `server.proxies` (CFG-4) |
| [API-6](/reference/spec#API-6) | a failure is JSON |
| [API-7](/reference/spec#API-7) | `/api/openapi.json`; `api.title`, `api.version`, `api.openapi` |
| [DEV-3](/reference/spec#DEV-3) | `quantum check` and the endpoints; `--openapi FILE` |
| [INV-3](/reference/spec#INV-3) | `${NAME}` in a credential |
