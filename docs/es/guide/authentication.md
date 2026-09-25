---
source: guide/authentication.md
source_hash: 6718120df989
---

# Autenticación

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/authentication).
:::

En Quantum, la autenticación son tres piezas que ya existen en el núcleo:
**atributos de página** que exigen un inicio de sesión, la **sesión** que recuerda
quién inició sesión, y **funciones de contraseña** para verificar un inicio de
sesión de forma honesta. No hay un servidor de autenticación aparte ni JavaScript.

## Proteger una página {#protecting-a-page}

```xml
<q:component name="dashboard" require_auth="true" require_role="admin"
             xmlns:q="https://quantum.lang/ns">
  <html><body>
    <p>Hello, {session.userName}</p>
  </body></html>
</q:component>
```

| Visitante | Resultado |
|---------|--------|
| sin sesión iniciada | redirigido a `/login` |
| sesión vencida | redirigido a `/login?expired=true` |
| con sesión iniciada, pero `session.userRole` no es `admin` | `403 Forbidden` |
| con sesión iniciada como `admin` | la página |

`require_role` acepta varios roles separados por comas:
`require_role="admin,editor"`.

Los `q:action` de la página también quedan protegidos: un POST sin sesión es
redirigido y la acción no se ejecuta.

### Guardas {#guards}

Un `q:if` al principio de la página cuya rama tiene un `q:redirect` es una
*guarda*. Se ejecuta antes de la página y antes de cada una de sus acciones:

```xml
<q:component name="login" xmlns:q="https://quantum.lang/ns">
  <!-- Already logged in? Go to the dashboard. -->
  <q:if condition="session.authenticated">
    <q:redirect url="/dashboard" />
  </q:if>
  <html><body><p>Please sign in.</p></body></html>
</q:component>
```

Una clave de sesión que todavía no existe se lee como vacía en una condición,
así que `not session.authenticated` es verdadero para un visitante que no inició
sesión.

Dos reglas impiden que una guarda falle dejando pasar:

- En una página con acciones, una guarda solo puede leer lo que existe antes de
  que la página se ejecute — `session`, `query`, `form`, `cookie`, los
  segmentos de la ruta — no una variable que define la página. Una acción no
  ejecuta las sentencias de la página, así que esa variable no existiría ahí.
  Esto es un error de análisis.
- Una condición de guarda que no se puede evaluar (`not session.user.is_admin`
  cuando no hay `session.user`) es un error, no "falso".

Para proteger una página, prefiere `require_auth` / `require_role`: dicen lo que
quieren decir.

## Iniciar sesión {#logging-in}

Un inicio de sesión busca al usuario, verifica la contraseña contra el hash
guardado y abre la sesión. La tabla aquí es `users (id, email, name, role, password_hash)`,
en una fuente de datos llamada `db` declarada en `quantum.config.yaml`.

Guárdalo como `components/login.q`:

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

- Una contraseña equivocada y un correo desconocido reciben el **mismo**
  mensaje, así que el formulario no revela qué correos tienen cuenta.
- `session.sessionExpiry` es **obligatoria**. Una sesión sin ella cuenta como
  vencida — la verificación falla cerrando. `dateAdd('h', 8)` significa dentro de
  ocho horas.
- `session.authenticated`, `session.userRole` y `session.sessionExpiry` son los
  nombres que leen `require_auth` y `require_role`.

## Crear una cuenta {#creating-an-account}

Guarda el hash, nunca la contraseña:

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

`hashPassword` usa bcrypt, con una sal nueva en cada llamada.
`verifyPassword` devuelve false — nunca un error — para una contraseña vacía, un
hash que falta o cualquier cosa que no sea un hash válido.

## Cerrar sesión {#logging-out}

```xml
<q:action name="signOut" method="POST">
  <q:set name="session.authenticated" value="false" type="boolean" />
  <q:set name="session.userRole" value="" />
  <q:redirect url="/login" />
</q:action>
```

## Próximos pasos {#next-steps}

- [Sesiones y ámbitos](/es/guide/sessions) — los valores de sesión que se usan arriba
- [Acciones y formularios](/es/guide/actions) — cómo se declaran los campos del formulario de inicio de sesión
- [Consultas a la base de datos](/es/guide/query) — declarar la fuente de datos `db`
