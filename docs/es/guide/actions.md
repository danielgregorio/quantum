---
source: guide/actions.md
source_hash: 2e221351f1c5
---

# Acciones y formularios

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/actions).
:::

Un formulario envía datos a una página, y un `q:action` dentro de esa página
procesa el envío. La acción declara los campos que acepta, los valida, hace su
trabajo y redirige — el clásico ciclo *post / redirect / get*, sin JavaScript.

## Un formulario y su acción {#a-form-and-its-action}

Guárdalo como `components/contact.q` y abre `http://localhost:8080/contact`:

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

Qué pasa:

1. **GET** renderiza la página. La acción no se ejecuta.
2. **POST** con `name=Ana` ejecuta la acción: `name` se valida, se guarda en la
   sesión, y el navegador es redirigido a `/contact`.
3. La página después de la redirección muestra `Thank you, Ana!` una vez. `flash`
   tiene el mensaje y `flashType` su tipo (`success`, salvo que digas otra cosa).

## Declarar campos con `q:param` {#declaring-fields-with-q-param}

Cada campo declarado con `q:param` se convierte en una variable de la acción, ya
validada y convertida al tipo declarado. Reglas:

| Atributo | Verifica |
|-----------|--------|
| `required="true"` | que el campo esté presente y no vacío |
| `type` | `string`, `number`, `integer`, `boolean`, `email`, `url` |
| `minlength` / `maxlength` | la longitud del texto |
| `min` / `max` | el rango numérico |
| `pattern` | una expresión regular |
| `enum` | uno de una lista separada por comas |
| `range="1..10"` | entre los dos, ambos incluidos |
| `accept` (con `type="file"`) | el tipo del archivo subido: `image/*`, `.pdf`, `application/pdf` — verificado contra el nombre del archivo y también contra el tipo que declara el navegador |

Cuando una regla falla, la acción **no** se ejecuta: el navegador vuelve a la
página de la que vino, y `flash` lleva el motivo con `flashType="error"` — por
ejemplo `Parameter 'name' must be at least 2 characters`.

Los valores enviados tal cual también están disponibles como `form.<field>` —
como texto, sin validar. Úsalos para mostrar; usa `q:param` para todo lo que
guardes o calcules.

## Varias acciones en una página {#several-actions-on-one-page}

Con más de una acción, el formulario dice cuál quiere en un campo llamado
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

Si falta `action`, o no nombra ninguna acción de la página, la solicitud se
rechaza con `400 Bad Request`, nombrando lo que se pidió y las acciones que
existen — ninguna otra acción se ejecuta en su lugar.

## Redirecciones y mensajes flash {#redirects-and-flash-messages}

`q:redirect` termina la acción. `flash` es opcional y acepta enlace de datos.
Para un mensaje flash de otro tipo, usa `q:flash` antes de la redirección:

```xml fragment=action
<q:flash type="error" message="Invalid credentials" />
<q:redirect url="/login" />
```

`q:flash` funciona dentro de un `q:action`, donde la página siguiente lo
muestra. En cualquier otro lugar no haría nada, así que no pasa el análisis:

```xml
<q:flash type="warning" message="Read the terms first" />
```

**Error:** `is outside a q:action`

## Proteger una acción {#protecting-an-action}

Una acción se protege a través de su página: `require_auth` / `require_role` en
el `q:component`, o una guarda (un `q:if` de nivel superior con `q:redirect`),
que se ejecuta antes de cada acción de la página. El propio `q:action` no acepta
ningún atributo de protección:

```xml
<q:action name="save" method="POST" require_auth="true">
  <q:redirect url="/" />
</q:action>
```

**Error:** `require_auth= is not supported`

## Próximos pasos {#next-steps}

- [Sesiones y ámbitos](/es/guide/sessions) — lo que `session.` conserva entre solicitudes
- [Autenticación](/es/guide/authentication) — proteger páginas con un inicio de sesión
