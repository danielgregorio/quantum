---
order: 4
title: "Una guarda que redirige"
description: "Un q:if de nivel superior con q:redirect protege una página y todas sus acciones; un envío sin sesión no escribe nada."
source: cookbook/login-and-permissions/guard-that-redirects.md
source_hash: 94e99b99ab2d
---

# Una guarda que redirige

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/login-and-permissions/guard-that-redirects).
:::

**Tarea:** enviar a los visitantes sin sesión a la página de inicio de sesión
con un mensaje, y asegurarse de que tampoco puedan enviar datos a las
acciones de la página.

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/migrations/V001_notes.sql{sql}

Un `q:if` al principio de la página cuya rama tiene un `q:redirect` es una
**guarda**. Se ejecuta antes de la página y antes de cada una de sus
acciones, así que un envío mandado directamente a `add` también se detiene:

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/components/index.q{xml}

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/components/login.q{xml}

La segunda prueba envía datos a la acción sin sesión y verifica que no se
escribió ninguna fila:

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/tests/guard.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/output/test-report.txt{text}

Una guarda puede verificar cualquier cosa que tenga la sesión. Para pedir
solo un usuario con sesión iniciada o un rol, `require_auth` y
`require_role` lo dicen en un atributo
([Una página solo para un rol](./page-for-one-role.md)).
