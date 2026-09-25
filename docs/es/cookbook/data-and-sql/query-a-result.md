---
order: 11
title: "Totales a partir de una consulta"
description: "SQL sobre el resultado de una consulta, en memoria — a la base de datos se le pregunta una sola vez."
source: cookbook/data-and-sql/query-a-result.md
source_hash: 56c2928ad9cd
---

# Totales a partir de una consulta

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/data-and-sql/query-a-result).
:::

**Tarea:** mostrar los totales de ventas por región sin preguntarle dos veces
a la base de datos.

<<< @/../examples/cookbook/data-and-sql/query-a-result/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/query-a-result/migrations/V001_sales.sql{sql}

`q:query source="sales"` ejecuta su SQL sobre el resultado de la consulta
llamada `sales`, que aparece como una tabla con ese nombre. `queries="1"` en
la prueba verifica que a la base de datos se le preguntó una sola vez.

<<< @/../examples/cookbook/data-and-sql/query-a-result/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/query-a-result/tests/totals.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/query-a-result/output/test-report.txt{text}

Ver [DB-3](../../../reference/spec.md#DB-3).
