---
order: 4
title: "Filtrar y ordenar una tabla"
description: "Enlaces que filtran las filas y encabezados que las ordenan — ambos en SQL, ambos en la URL."
source: cookbook/data-and-sql/filter-and-sort.md
source_hash: 2fd626dc0a23
---

# Filtrar y ordenar una tabla

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/data-and-sql/filter-and-sort).
:::

**Tarea:** una tabla de tareas que quien la lee filtra (abiertas, terminadas,
todas) y ordena haciendo clic en un encabezado.

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/migrations/V001_tasks.sql{sql}

El filtro es `?show=`, pasado a la consulta como parámetro. `sortable="true"`
en la consulta y `sort="true"` en la tabla convierten cada encabezado en un
enlace que ordena la consulta en SQL según `?sort=` y `?dir=` — así que
también funciona en una consulta paginada. Una columna que la consulta no
devuelve se ignora.

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/tests/tasks.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/output/test-report.txt{text}

Ver [UI-13](../../../reference/spec.md#UI-13).
