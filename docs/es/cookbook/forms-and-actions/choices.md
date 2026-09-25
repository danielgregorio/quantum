---
order: 9
title: "Una opción de una lista"
description: "enum en q:param le da sus opciones a ui:select y ui:radio y rechaza cualquier otra cosa; una casilla es un booleano."
source: cookbook/forms-and-actions/choices.md
source_hash: 52d2092cd49d
---

# Una opción de una lista

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/forms-and-actions/choices).
:::

**Tarea:** un campo que toma un valor de una lista, y una casilla de sí/no.

<<< @/../examples/cookbook/forms-and-actions/choices/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/choices/migrations/V001_orders.sql{sql}

La lista se escribe una sola vez, como `enum` en el `q:param` de la acción.
Un `ui:select` o un `ui:radio` sin opciones propias las toma de ahí, y el
servidor rechaza un valor que no está en ella. `default` completa un campo
que falta. Una casilla envía un valor solo cuando está marcada, así que
`type="boolean"` `default="false"` la convierte en `true` o `false`.

<<< @/../examples/cookbook/forms-and-actions/choices/components/index.q{xml}

<<< @/../examples/cookbook/forms-and-actions/choices/tests/order.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/choices/output/test-report.txt{text}

Ver [ACT-2](../../../reference/spec.md#ACT-2) y [UI-9](../../../reference/spec.md#UI-9).
