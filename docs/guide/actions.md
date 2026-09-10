# Actions & Forms

A form posts to a page, and a `q:action` inside that page handles the post.
The action declares the fields it accepts, validates them, does its work and
redirects — the classic *post / redirect / get* cycle, with no JavaScript.

## A form and its action

Save as `components/contato.q` and open `http://localhost:8080/contato`:

```xml
<q:component name="contato" xmlns:q="https://quantum.lang/ns">
  <q:action name="enviar" method="POST">
    <q:param name="nome" type="string" required="true" minlength="2" />
    <q:set name="session.ultimoContato" value="{nome}" />
    <q:redirect url="/contato" flash="Obrigado, {nome}!" />
  </q:action>

  <html><body>
    <q:if condition="flash"><p class="{flashType}">{flash}</p></q:if>
    <p>Último contato: {session.ultimoContato}</p>
    <form method="POST" action="/contato">
      <input name="nome" />
      <button>Enviar</button>
    </form>
  </body></html>
</q:component>
```

What happens:

1. **GET** renders the page. The action does not run.
2. **POST** with `nome=Ana` runs the action: `nome` is validated, stored in the
   session, and the browser is redirected to `/contato`.
3. The page after the redirect shows `Obrigado, Ana!` once. `flash` holds the
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

When a rule fails, the action does **not** run: the browser goes back to the
page it came from, and `flash` carries the reason with `flashType="error"` —
for example `Parameter 'nome' must be at least 2 characters`.

The raw submitted values are also available as `form.<campo>` — as text, not
validated. Use them for display; use `q:param` for anything you store or compute.

## Several actions on one page

With more than one action, the form says which one it wants in a field named
`action`:

```xml
<q:component name="tarefas" xmlns:q="https://quantum.lang/ns">
  <q:action name="criar" method="POST">
    <q:param name="titulo" required="true" />
    <q:redirect url="/tarefas" flash="Criada: {titulo}" />
  </q:action>

  <q:action name="limpar" method="POST">
    <q:redirect url="/tarefas" flash="Lista limpa" />
  </q:action>

  <html><body>
    <q:if condition="flash"><p>{flash}</p></q:if>
    <form method="POST" action="/tarefas">
      <input type="hidden" name="action" value="criar" />
      <input name="titulo" />
      <button>Criar</button>
    </form>
    <form method="POST" action="/tarefas">
      <input type="hidden" name="action" value="limpar" />
      <button>Limpar</button>
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
<q:flash type="error" message="Credenciais inválidas" />
<q:redirect url="/login" />
```

## Next steps

- [Sessions & Scopes](/guide/sessions) — what `session.` keeps between requests
- [Authentication](/guide/authentication) — protecting pages with a login
