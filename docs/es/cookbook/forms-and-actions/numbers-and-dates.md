---
order: 8
title: "Números y fechas"
description: "type=integer, decimal y date en q:param — la acción recibe números verificados y fechas reales, con min y max."
source: cookbook/forms-and-actions/numbers-and-dates.md
source_hash: be7e0a2f2ba4
---

# Números y fechas

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/forms-and-actions/numbers-and-dates).
:::

**Tarea:** recibir un monto, una cantidad y una fecha, y hacer cuentas con
ellos sin convertir nada a mano.

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/migrations/V001_expenses.sql{sql}

Un formulario envía texto. `type="decimal"` y `type="integer"` lo convierten
en número antes de que la acción se ejecute, así que `amount / people`
funciona. `min` y `max` se verifican sobre ese número. `type="date"` acepta
`YYYY-MM-DD` y un día que existe, y lo guarda como texto, listo para la base
de datos.

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/components/index.q{xml}

El formulario recibe `type="number"` con los mismos `min` y `max`, y
`type="date"`, así que el navegador verifica primero. Las pruebas envían
directamente al servidor, como lo haría un script:

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/tests/split.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/output/test-report.txt{text}

Ver [ACT-2](../../../reference/spec.md#ACT-2) y [UI-9](../../../reference/spec.md#UI-9).
