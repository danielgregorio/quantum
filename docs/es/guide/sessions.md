---
source: guide/sessions.md
source_hash: 51e837228e46
---

# Sesiones y ámbitos

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/sessions).
:::

Un `q:set` simple vive durante una solicitud (SET-2). Tres ámbitos con prefijo
conservan los valores más tiempo, o exponen la propia solicitud:

| Ámbito | Vive | Se comparte con |
|-------|-------|-------------|
| `session.` | entre solicitudes, para un visitante | solo ese visitante |
| `application.` | mientras el proceso del servidor se ejecuta | todos los visitantes de ese proceso |
| `request.` | una solicitud | — |

`application.` es memoria del proceso del servidor: desaparece después de un
reinicio, y con `gunicorn --workers 4` cada worker tiene la suya. Guarda en la
base de datos lo que deba durar — ver [Cómo se ejecuta una página](/es/guide/how-a-page-runs).

El servidor web guarda las sesiones en una cookie firmada, así que funcionan con
`quantum start` sin configurar nada. Cuando publiques, define `QUANTUM_SECRET_KEY`
(o `security.secret_key` en la configuración): sin ella, cada proceso firma con
una clave propia, y un reinicio cierra la sesión de todos.

Los ejemplos de esta página se ejecutan en CI (`tests/docs/test_guide_sessions.py`).

## Contar visitas {#counting-visits}

Guárdalo como `components/visits.q`:

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

Dos visitantes que abren `/visits` uno después del otro ven:

| Solicitud | `session.mine` | `application.everyone` |
|---------|------------------|---------------------|
| visitante A, 1.ª | 1 | 1 |
| visitante A, 2.ª | 2 | 2 |
| visitante B, 1.ª | 1 | 3 |

y la última línea dice `GET /visits`. `operation="increment"` empieza en cero
cuando la variable todavía no existe (SET-3).

## Un valor que todavía no existe {#a-value-that-does-not-exist-yet}

Hacer cuentas con un valor de sesión que nunca se definió es un error que lo dice
y señala la solución (EXPR-3):

```xml
<q:set name="session.visits" value="{session.visits + 1}" />
```

**Error:** `session value used in 'session.visits + 1' is not set`

Usa `operation="increment"` para un contador, o dale al valor un `default`
(SET-1):

```xml
<q:set name="session.visits" operation="increment" />
<q:return value="Visits: {session.visits}" />
```

**Output:** `Visits: 1`

La referencia sola no es un error: un `{session.name}` que no existe se renderiza
vacío (una página se renderiza antes del inicio de sesión), y en una condición es
falso:

```xml
<q:return value="Hello, {session.name}!" />
```

**Output:** `Hello, !`

Eso hace que "¿el visitante inició sesión?" sea una sola línea. Guárdalo como
`components/welcome.q`:

```xml
<q:component name="welcome" xmlns:q="https://quantum.lang/ns">
  <q:if condition="session.authenticated">
    <p>Welcome back!</p>
    <q:else><a href="/login">Sign in</a></q:else>
  </q:if>
</q:component>
```

Un visitante nuevo ve **Sign in**; una vez que una acción definió
`session.authenticated`, la misma página dice **Welcome back!**

## Escribir desde una acción {#writing-from-an-action}

Las acciones escriben en `session.` de la misma forma, y el cambio se guarda
antes de la redirección — ver [Acciones y formularios](/es/guide/actions) y
[Autenticación](/es/guide/authentication).

## Valores de la solicitud {#request-values}

| Variable | Contiene |
|----------|----------|
| `request.method` | `GET`, `POST`… |
| `request.path` | la ruta, sin la query string |
| `request.url` | la URL completa, con la query string |

La propia query string está en `query.` (`{query.page}`), y un formulario enviado
en `form.`.
