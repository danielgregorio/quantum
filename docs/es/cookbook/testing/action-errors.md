---
order: 3
title: "Probar lo que una acción rechaza"
description: "Probar los errores de campo, la regla de negocio y el éxito de una acción — error=, message=, flash= y la tabla."
source: cookbook/testing/action-errors.md
source_hash: 2e4ddc8a6560
---

# Probar lo que una acción rechaza

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/testing/action-errors).
:::

**Tarea:** demostrar que un formulario rechaza lo que debe — un campo que rompe
su regla, un valor que el negocio no permite — y que no se escribe nada cuando
lo hace.

Un registro con dos tipos de rechazo: las reglas de los `q:param` (verificadas
antes de que la acción se ejecute) y una regla de negocio en la propia acción
(la dirección ya es de un miembro):

<<< @/../examples/cookbook/testing/action-errors/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/testing/action-errors/migrations/V001_members.sql{sql}

<<< @/../examples/cookbook/testing/action-errors/components/index.q{xml}

`error="name"` verifica el campo en el que se rechazó el envío, y `message=` el
texto que se muestra junto a él. Un rechazo que decide la propia acción es una
redirección con un mensaje flash, que se verifica con `flash=`. `table=` con
`count=` demuestra que no se escribió nada:

<<< @/../examples/cookbook/testing/action-errors/tests/signup.test.q{xml}

<<< @/../examples/cookbook/testing/action-errors/output/test-report.txt{text}

Las reglas que acepta un `q:param` (`required`, `minlength`, `type="email"`,
`enum`…) están en [Actions & Forms](../../../guide/actions.md) (en inglés).

*Probado:* esta página importa los archivos de
`examples/cookbook/testing/action-errors/`, y el resultado de arriba es el
informe de ejecutarlos.
