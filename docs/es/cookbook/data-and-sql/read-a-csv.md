---
order: 8
title: "Leer un archivo CSV"
description: "q:data convierte un archivo CSV en registros tipados, filtrados y ordenados — sin base de datos."
source: cookbook/data-and-sql/read-a-csv.md
source_hash: 6de028735194
---

# Leer un archivo CSV

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/data-and-sql/read-a-csv).
:::

**Tarea:** mostrar los clientes activos de un archivo CSV, del más antiguo al
más nuevo.

<<< @/../examples/cookbook/data-and-sql/read-a-csv/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/read-a-csv/import/customers.csv{text}

Las columnas declaradas tienen tipo (`true`, `1`, `yes` y `on` son un booleano
verdadero); las demás llegan como texto. `q:transform` ejecuta sus
operaciones en orden.

<<< @/../examples/cookbook/data-and-sql/read-a-csv/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/read-a-csv/tests/customers.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/read-a-csv/output/test-report.txt{text}

Ver [DATA-1](../../../reference/spec.md#DATA-1) y
[DATA-3](../../../reference/spec.md#DATA-3), y [Data Import](../../../guide/data-import.md) (en inglés).
