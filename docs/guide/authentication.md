# Authentication

Authentication in Quantum is three pieces that already exist in the core:
**page attributes** that demand a login, the **session** that remembers who
logged in, and **password functions** to check a login honestly. There is no
separate auth server and no JavaScript.

## Protecting a page

```xml
<q:component name="dashboard" require_auth="true" require_role="admin"
             xmlns:q="https://quantum.lang/ns">
  <html><body>
    <p>Hello, {session.userName}</p>
  </body></html>
</q:component>
```

| Visitor | Result |
|---------|--------|
| not logged in | redirected to `/login` |
| session expired | redirected to `/login?expired=true` |
| logged in, but `session.userRole` is not `admin` | `403 Forbidden` |
| logged in as `admin` | the page |

`require_role` accepts several roles separated by commas:
`require_role="admin,editor"`.

The page's `q:action`s are protected too: a POST without a session is
redirected and the action does not run.

### Guards

A `q:if` at the top of the page whose branch has a `q:redirect` is a *guard*.
It runs before the page and before each of its actions:

```xml
<q:component name="login" xmlns:q="https://quantum.lang/ns">
  <!-- Already logged in? Go to the dashboard. -->
  <q:if condition="session.authenticated">
    <q:redirect url="/dashboard" />
  </q:if>
  <html><body><p>Please sign in.</p></body></html>
</q:component>
```

A session key that does not exist yet reads as empty in a condition, so
`not session.authenticated` is true for a visitor who has not logged in.

Two rules keep a guard from failing open:

- On a page with actions, a guard may read only what exists before the page
  runs — `session`, `query`, `form`, `cookie`, route segments — not a
  variable the page sets. An action does not run the page's statements, so
  that variable would not exist there. This is a parse error.
- A guard condition that cannot be evaluated (`not session.user.is_admin`
  when there is no `session.user`) is an error, not "false".

To protect a page, prefer `require_auth` / `require_role`: they say what they
mean.

## Logging in

A login looks the user up, checks the password against the stored hash, and
opens the session. The table here is `users (id, email, name, role, password_hash)`,
in a datasource named `db` declared in `quantum.config.yaml`.

Save as `components/login.q`:

```xml
<q:component name="login" xmlns:q="https://quantum.lang/ns">
  <q:action name="signIn" method="POST">
    <q:param name="email" type="email" required="true" />
    <q:param name="password" required="true" />

    <q:query name="user" datasource="db">
      SELECT id, name, role, password_hash FROM users WHERE email = :email
      <q:param name="email" value="{email}" type="string" />
    </q:query>

    <q:if condition="user.length == 1 and verifyPassword(password, user[0].password_hash)">
      <q:set name="session.authenticated" value="true" type="boolean" />
      <q:set name="session.userId" value="{user[0].id}" />
      <q:set name="session.userName" value="{user[0].name}" />
      <q:set name="session.userRole" value="{user[0].role}" />
      <q:set name="session.sessionExpiry" value="{dateAdd('h', 8)}" />
      <q:redirect url="/dashboard" />
    </q:if>

    <q:flash type="error" message="Invalid e-mail or password" />
    <q:redirect url="/login" />
  </q:action>

  <html><body>
    <q:if condition="flash"><p class="{flashType}">{flash}</p></q:if>
    <form method="POST" action="/login">
      <input name="email" type="email" />
      <input name="password" type="password" />
      <button>Sign in</button>
    </form>
  </body></html>
</q:component>
```

- A wrong password and an unknown e-mail get the **same** message, so the form
  does not reveal which e-mails have accounts.
- `session.sessionExpiry` is **required**. A session without it counts as
  expired — the check fails closed. `dateAdd('h', 8)` means eight hours from now.
- `session.authenticated`, `session.userRole` and `session.sessionExpiry` are the
  names `require_auth` and `require_role` read.

## Creating an account

Store the hash, never the password:

```xml
<q:action name="createAccount" method="POST">
  <q:param name="email" type="email" required="true" />
  <q:param name="name" required="true" />
  <q:param name="password" required="true" minlength="10" />

  <q:query name="created" datasource="db">
    INSERT INTO users (email, name, role, password_hash)
    VALUES (:email, :name, 'user', :hash)
    <q:param name="email" value="{email}" type="string" />
    <q:param name="name" value="{name}" type="string" />
    <q:param name="hash" value="{hashPassword(password)}" type="string" />
  </q:query>

  <q:redirect url="/login" flash="Account created. Sign in with your e-mail." />
</q:action>
```

`hashPassword` uses bcrypt, with a fresh salt for every call.
`verifyPassword` returns false — never an error — for an empty password, a
missing hash or anything that is not a valid hash.

## Logging out

```xml
<q:action name="signOut" method="POST">
  <q:set name="session.authenticated" value="false" type="boolean" />
  <q:set name="session.userRole" value="" />
  <q:redirect url="/login" />
</q:action>
```

## Next steps

- [Sessions & Scopes](/guide/sessions) — the session values used above
- [Actions & Forms](/guide/actions) — how the login form's fields are declared
- [Database Queries](/guide/query) — declaring the `db` datasource
