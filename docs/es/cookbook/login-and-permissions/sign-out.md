---
order: 5
title: "Cerrar sesión"
description: "Una página de salida que limpia la sesión y redirige; las páginas protegidas quedan cerradas de nuevo."
source: cookbook/login-and-permissions/sign-out.md
source_hash: 86548aa4610b
---

# Cerrar sesión

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/login-and-permissions/sign-out).
:::

**Tarea:** terminar la sesión del usuario.

<<< @/../examples/cookbook/login-and-permissions/sign-out/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/login-and-permissions/sign-out/components/index.q{xml}

Una página puede cambiar la sesión y después redirigir: lo que escribió en la
sesión antes del `q:redirect` queda escrito.

<<< @/../examples/cookbook/login-and-permissions/sign-out/components/logout.q{xml}

<<< @/../examples/cookbook/login-and-permissions/sign-out/components/login.q{xml}

La prueba inicia sesión, la cierra y verifica que la página de inicio vuelve a
pedir que se inicie sesión:

<<< @/../examples/cookbook/login-and-permissions/sign-out/tests/logout.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/sign-out/output/test-report.txt{text}
