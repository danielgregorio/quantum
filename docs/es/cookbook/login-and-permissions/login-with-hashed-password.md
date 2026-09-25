---
order: 1
title: "Iniciar sesión con una contraseña hasheada"
description: "Verificar una contraseña contra su hash bcrypt con verifyPassword, abrir la sesión y reservar una página para usuarios con sesión iniciada."
source: cookbook/login-and-permissions/login-with-hashed-password.md
source_hash: 76e6db18e085
---

# Iniciar sesión con una contraseña hasheada

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/login-and-permissions/login-with-hashed-password).
:::

**Tarea:** dejar que un usuario inicie sesión con un correo y una contraseña,
donde la base de datos guarda solo un hash de la contraseña, y mostrar una
página solo a los usuarios con sesión iniciada.

La tabla guarda un hash bcrypt (hecho con `hashPassword`, como en la
[receta de registro](./sign-up.md)), nunca la contraseña:

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/migrations/V001_users.sql{sql}

La acción de inicio de sesión busca al usuario y verifica la contraseña con
`verifyPassword`. Da false, nunca un error, para una contraseña equivocada,
un usuario que no existe o un campo vacío. Si todo sale bien, define las
variables de sesión que leen `require_auth` y `require_role`.
`session.sessionExpiry` es obligatoria: una sesión sin ella cuenta como
vencida.

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/components/login.q{xml}

La página de inicio pide una sesión iniciada con `require_auth="true"`:

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/components/index.q{xml}

Una dirección equivocada y una contraseña equivocada reciben el mismo
mensaje, así que el formulario no le dice a un extraño qué direcciones tienen
una cuenta:

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/tests/login.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/output/test-report.txt{text}

Más en la guía [Authentication](../../../guide/authentication.md) (en inglés).
