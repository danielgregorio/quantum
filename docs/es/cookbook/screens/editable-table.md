---
order: 2
title: "Una tabla que se edita en su lugar"
description: "ui:table edit= convierte cada celda en un pequeño formulario verificado contra el esquema de la tabla; sin acción que escribir."
source: cookbook/screens/editable-table.md
source_hash: f6364e25b3ad
---

# Una tabla que se edita en su lugar

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/screens/editable-table).
:::

**Tarea:** dejar que la gente cambie un valor en una tabla sin abrir una página de edición.

<<< @/../examples/cookbook/screens/editable-table/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/screens/editable-table/migrations/V001_items.sql{sql}

`edit="items"` hace de cada celda un pequeño formulario que guarda una
columna de una fila. El esquema de la tabla es la regla: `shelf` debe ser A,
B o C por su `CHECK`, y un valor rechazado vuelve como un mensaje flash de
error. Una columna con `edit="false"` se muestra, no se edita, y un envío que
lo intenta igual responde `400`. `sort="true"` pone enlaces en los
encabezados.

<<< @/../examples/cookbook/screens/editable-table/components/index.q{xml}

Una prueba edita una celda como lo hace el navegador, con la acción `__edit`:

<<< @/../examples/cookbook/screens/editable-table/tests/stock.test.q{xml}

<<< @/../examples/cookbook/screens/editable-table/output/test-report.txt{text}

Ver [UI-5](../../../reference/spec.md#UI-5) y [UI-13](../../../reference/spec.md#UI-13).
