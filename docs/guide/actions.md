# Actions & Forms

A form posts to a page, and a `q:action` inside that page handles the post.
The action declares the fields it accepts, validates them, does its work and
redirects — the classic *post / redirect / get* cycle, with no JavaScript.

## A form and its action

Save as `components/contact.q` and open `http://localhost:8080/contact`:

```xml
<q:component name="contact" xmlns:q="https://quantum.lang/ns">
  <q:action name="send" method="POST">
    <q:param name="name" type="string" required="true" minlength="2" />
    <q:set name="session.lastContact" value="{name}" />
    <q:redirect url="/contact" flash="Thank you, {name}!" />
  </q:action>

  <html><body>
    <q:if condition="flash"><p class="{flashType}">{flash}</p></q:if>
    <p>Last contact: {session.lastContact}</p>
    <form method="POST" action="/contact">
      <input name="name" />
      <button>Send</button>
    </form>
  </body></html>
</q:component>
```

What happens:

1. **GET** renders the page. The action does not run.
2. **POST** with `name=Ana` runs the action: `name` is validated, stored in the
   session, and the browser is redirected to `/contact`.
3. The page after the redirect shows `Thank you, Ana!` once. `flash` holds the
   message and `flashType` its kind (`success` unless you say otherwise).

## Declaring fields with `q:param`

Each field declared with `q:param` becomes a variable in the action, already
validated and converted to the declared type. Rules:

| Attribute | Checks |
|-----------|--------|
| `required="true"` | the field is present and not empty |
| `type` | `string`, `number`, `integer`, `boolean`, `email`, `url` |
| `minlength` / `maxlength` | text length |
| `min` / `max` | numeric range |
| `pattern` | regular expression |
| `enum` | one of a comma-separated list |
| `range="1..10"` | between the two, both included |
| `accept` (with `type="file"`) | the upload's type: `image/*`, `.pdf`, `application/pdf` — checked against the file name as well as the type the browser declares |

When a rule fails, the action does **not** run: the browser goes back to the
page it came from, and `flash` carries the reason with `flashType="error"` —
for example `Parameter 'name' must be at least 2 characters`.

The raw submitted values are also available as `form.<field>` — as text, not
validated. Use them for display; use `q:param` for anything you store or compute.

## Several actions on one page

With more than one action, the form says which one it wants in a field named
`action`:

```xml
<q:component name="tasks" xmlns:q="https://quantum.lang/ns">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" />
    <q:redirect url="/tasks" flash="Created: {title}" />
  </q:action>

  <q:action name="clear" method="POST">
    <q:redirect url="/tasks" flash="List cleared" />
  </q:action>

  <html><body>
    <q:if condition="flash"><p>{flash}</p></q:if>
    <form method="POST" action="/tasks">
      <input type="hidden" name="action" value="create" />
      <input name="title" />
      <button>Create</button>
    </form>
    <form method="POST" action="/tasks">
      <input type="hidden" name="action" value="clear" />
      <button>Clear</button>
    </form>
  </body></html>
</q:component>
```

If `action` is missing, or names no action on the page, the request is refused
with `400 Bad Request`, naming what was asked for and the actions that exist —
no other action runs in its place.

## Redirects and flash messages

`q:redirect` ends the action. `flash` is optional and accepts databinding.
For a flash of another kind, use `q:flash` before the redirect:

```xml
<q:flash type="error" message="Invalid credentials" />
<q:redirect url="/login" />
```

`q:flash` works inside a `q:action`, where the next page shows it. Anywhere else
it would do nothing, so it does not parse:

```xml
<q:flash type="warning" message="Read the terms first" />
```

**Error:** `is outside a q:action`

## Protecting an action

An action is protected through its page: `require_auth` / `require_role` on the
`q:component`, or a guard (a top-level `q:if` with `q:redirect`), which runs
before every action of the page. `q:action` itself takes no protection
attribute:

```xml
<q:action name="save" method="POST" require_auth="true">
  <q:redirect url="/" />
</q:action>
```

**Error:** `require_auth= is not supported`

## Next steps

- [Sessions & Scopes](/guide/sessions) — what `session.` keeps between requests
- [Authentication](/guide/authentication) — protecting pages with a login
