---
source: guide/applications.md
source_hash: 508e483fc213
---

# q:application

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/applications).
:::

Una **aplicación web** en Quantum no es un `q:application`: es una carpeta de
páginas en `components/`, servida por `quantum start`. Ver
[Primeros pasos](/es/guide/getting-started) y el [Inicio rápido](/es/guide/quick-start).

`q:application` es el elemento raíz de los programas que **no** son páginas web.
Ninguno forma parte del núcleo con soporte (ver `SUPPORT_TIERS.md`):

| `type` | Nivel | Qué hace `quantum run app.q` |
|--------|------|-------------------------------|
| `game` | Laboratorio | construye un juego 2D (`--engine pixi` o `--engine godot`) |
| `terminal` | Experimental | construye una interfaz de terminal |
| `ui` | Experimental | construye una interfaz, solo el diseño (`--target html` o `textual`; `mobile` es Laboratorio) |

Ejecutar una aplicación experimental o de Laboratorio imprime una advertencia,
una sola vez, que lo dice. Sus etiquetas y su salida pueden cambiar en cualquier
versión.

## Eliminados: `type="html"`, `type="api"`, `type="microservices"` {#removed-type-html-type-api-type-microservices}

Versiones anteriores documentaban servidores web y API JSON declarados como
`q:application` con bloques `q:route`. Nunca ejecutaron sus rutas — `html`
fallaba al iniciar, y `api` respondía con el texto literal del primer
`q:return` — y se eliminaron en la 0.11. Un `q:application` sin `type`
significaba `type="html"`, así que también se rechaza. `type="testing"` (el
motor `qtest:`) se eliminó en la 0.22; lo reemplaza [`quantum test`](/es/guide/testing).

El analizador ahora se detiene con indicaciones:

```text
<q:application> type="html" was removed in Quantum 0.11: it never ran its
routes. Build a web app as pages in components/ (components/index.q is /) and
run `quantum start`. See https://quantumframework.net/guide/getting-started
```

En qué se convierte cada ruta:

| Antes | Ahora |
|--------|-----|
| `<q:route path="/about" method="GET">` | `components/about.q` |
| `<q:route path="/" method="GET">` | `components/index.q` |
| `<q:route path="/users" method="POST">` | un [`q:action`](/es/guide/actions) en `components/users.q` |
| ruta de API JSON | no disponible |
