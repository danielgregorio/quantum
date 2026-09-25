---
order: 2
title: "Registrarse y guardar un hash de la contraseña"
description: "Crear una cuenta con hashPassword, para que la base de datos nunca tenga la contraseña, con reglas en cada campo."
source: cookbook/login-and-permissions/sign-up.md
source_hash: f0ed6cc4abc2
---

# Registrarse y guardar un hash de la contraseña

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/login-and-permissions/sign-up).
:::

**Tarea:** crear una cuenta sin guardar nunca la contraseña en sí.

<<< @/../examples/cookbook/login-and-permissions/sign-up/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/login-and-permissions/sign-up/migrations/V001_users.sql{sql}

`hashPassword(password)` devuelve un hash bcrypt con una sal nueva cada vez;
el `INSERT` guarda eso. Las reglas de los `q:param` se ejecutan antes que
todo lo demás: una contraseña de menos de 12 caracteres nunca llega a la
consulta.

<<< @/../examples/cookbook/login-and-permissions/sign-up/components/index.q{xml}

Las pruebas miran la tabla: la fila tiene un hash bcrypt (empieza con `$2b$`)
y ninguna fila tiene la contraseña tal como se escribió:

<<< @/../examples/cookbook/login-and-permissions/sign-up/tests/signup.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/sign-up/output/test-report.txt{text}

Para iniciar sesión con ese hash, ver [Iniciar sesión con una contraseña hasheada](./login-with-hashed-password.md).
