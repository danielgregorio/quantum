---
order: 9
title: "Cargar un archivo CSV en una tabla"
description: "Insertar todas las filas de un archivo en una transacción — una fila que falla no deja nada atrás."
source: cookbook/data-and-sql/load-a-csv-into-a-table.md
source_hash: 74e71bd4db57
---

# Cargar un archivo CSV en una tabla

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/data-and-sql/load-a-csv-into-a-table).
:::

**Tarea:** cargar una lista de productos en la base de datos, todo o nada.

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/migrations/V001_products.sql{sql}

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/import/products.csv{text}

La acción lee el archivo con `q:data` y después inserta cada fila dentro de un
solo `q:transaction`; las consultas que contiene, también las del bucle, usan
su fuente de datos.

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/components/index.q{xml}

La segunda prueba carga el archivo cuando uno de sus productos ya está: la
segunda fila falla, y la primera, ya insertada, se revierte.

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/tests/load.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/output/test-report.txt{text}

Ver [DATA-1](../../../reference/spec.md#DATA-1) y [DB-4](../../../reference/spec.md#DB-4).
