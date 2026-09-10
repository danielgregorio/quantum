# Authentication

Authentication in Quantum is three pieces that already exist in the core:
**page attributes** that demand a login, the **session** that remembers who
logged in, and **password functions** to check a login honestly. There is no
separate auth server and no JavaScript.

## Protecting a page

```xml
<q:component name="painel" require_auth="true" require_role="admin"
             xmlns:q="https://quantum.lang/ns">
  <html><body>
    <p>Olá, {session.userName}</p>
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

## Logging in

A login looks the user up, checks the password against the stored hash, and
opens the session. The table here is `usuarios (id, email, nome, papel, senha_hash)`,
in a datasource named `db` declared in `quantum.config.yaml`.

Save as `components/login.q`:

```xml
<q:component name="login" xmlns:q="https://quantum.lang/ns">
  <q:action name="entrar" method="POST">
    <q:param name="email" type="email" required="true" />
    <q:param name="senha" required="true" />

    <q:query name="usuario" datasource="db">
      SELECT id, nome, papel, senha_hash FROM usuarios WHERE email = :email
      <q:param name="email" value="{email}" type="string" />
    </q:query>

    <q:if condition="usuario.length == 1 and verifyPassword(senha, usuario[0].senha_hash)">
      <q:set name="session.authenticated" value="true" type="boolean" />
      <q:set name="session.userId" value="{usuario[0].id}" />
      <q:set name="session.userName" value="{usuario[0].nome}" />
      <q:set name="session.userRole" value="{usuario[0].papel}" />
      <q:set name="session.sessionExpiry" value="{dateAdd('h', 8)}" />
      <q:redirect url="/painel" />
    </q:if>

    <q:flash type="error" message="E-mail ou senha inválidos" />
    <q:redirect url="/login" />
  </q:action>

  <html><body>
    <q:if condition="flash"><p class="{flashType}">{flash}</p></q:if>
    <form method="POST" action="/login">
      <input name="email" type="email" />
      <input name="senha" type="password" />
      <button>Entrar</button>
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
<q:action name="criarConta" method="POST">
  <q:param name="email" type="email" required="true" />
  <q:param name="nome" required="true" />
  <q:param name="senha" required="true" minlength="10" />

  <q:query name="novo" datasource="db">
    INSERT INTO usuarios (email, nome, papel, senha_hash)
    VALUES (:email, :nome, 'user', :hash)
    <q:param name="email" value="{email}" type="string" />
    <q:param name="nome" value="{nome}" type="string" />
    <q:param name="hash" value="{hashPassword(senha)}" type="string" />
  </q:query>

  <q:redirect url="/login" flash="Conta criada. Entre com seu e-mail." />
</q:action>
```

`hashPassword` uses bcrypt, with a fresh salt for every call.
`verifyPassword` returns false — never an error — for an empty password, a
missing hash or anything that is not a valid hash.

## Logging out

```xml
<q:action name="sair" method="POST">
  <q:set name="session.authenticated" value="false" type="boolean" />
  <q:set name="session.userRole" value="" />
  <q:redirect url="/login" />
</q:action>
```

## Next steps

- [Sessions & Scopes](/guide/sessions) — the session values used above
- [Actions & Forms](/guide/actions) — how the login form's fields are declared
- [Database Queries](/guide/query) — declaring the `db` datasource
