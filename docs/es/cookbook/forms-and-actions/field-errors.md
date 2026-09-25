---
order: 1
title: "Mostrar cada error en su campo"
description: "Escribe las reglas una vez en el q:param de la acción; el formulario las lee y muestra cada rechazo junto a su campo."
source: cookbook/forms-and-actions/field-errors.md
source_hash: 25cb71a331e3
---

# Mostrar cada error en su campo

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/forms-and-actions/field-errors).
:::

**Tarea:** rechazar un formulario malo y decir, junto a cada campo, qué está mal en él.

<<< @/../examples/cookbook/forms-and-actions/field-errors/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/field-errors/migrations/V001_guests.sql{sql}

Las reglas se escriben una vez, en los `q:param`s de la acción. El `ui:form`
las lee y las pone en sus campos (`required`, `minlength`, `type="number"`,
`min`...), así que el navegador verifica primero. El servidor vuelve a
verificar, todos los campos a la vez: cuando uno falla, la acción no se
ejecuta, la página vuelve y cada campo muestra su propio mensaje.

<<< @/../examples/cookbook/forms-and-actions/field-errors/components/index.q{xml}

En una prueba, `error="field"` verifica que el campo fue rechazado, y
`message=` el texto que se muestra junto a él:

<<< @/../examples/cookbook/forms-and-actions/field-errors/tests/guests.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/field-errors/output/test-report.txt{text}

Las reglas y sus mensajes: [ACT-2](../../../reference/spec.md#ACT-2) y
[UI-9](../../../reference/spec.md#UI-9).
