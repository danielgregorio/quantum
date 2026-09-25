---
order: 3
title: "Una página solo para un rol"
description: "require_role reserva una página para los administradores; un miembro recibe 403, y un visitante sin sesión es enviado a iniciarla."
source: cookbook/login-and-permissions/page-for-one-role.md
source_hash: 8674b9cce0ea
---

# Una página solo para un rol

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/login-and-permissions/page-for-one-role).
:::

**Tarea:** mostrar una página solo a los administradores.

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/quantum.config.yaml{yaml}

`require_auth="true"` pide una sesión iniciada; `require_role`, uno de los
roles de la lista en `session.userRole` (varios se separan con comas,
`require_role="admin,editor"`):

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/components/reports.q{xml}

Sin sesión, la respuesta redirige a `/login` (se cambia con
`security.login_url`):

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/components/login.q{xml}

`test:as` inicia la sesión de la prueba con un rol, sin contraseña:

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/tests/reports.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/output/test-report.txt{text}
