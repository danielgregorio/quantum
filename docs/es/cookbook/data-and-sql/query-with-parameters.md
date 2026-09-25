---
order: 1
title: "Una consulta con parámetros"
description: "Filtrar por un valor de la URL, vinculado como un q:param — el valor nunca se vuelve SQL."
source: cookbook/data-and-sql/query-with-parameters.md
source_hash: b54ace8bb289
---

# Una consulta con parámetros

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/data-and-sql/query-with-parameters).
:::

**Tarea:** listar los productos cuyo nombre contiene lo que pide la URL
(`/?name=mouse`), de forma segura.

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/migrations/V001_products.sql{sql}

Cada `:name` del SQL se vincula al `q:param` del mismo nombre: el valor va a
la base de datos separado del texto SQL, convertido antes por su `type`. Un
`:name` sin `q:param` no pasa el análisis, así que no hay forma de pegar un
valor en el SQL por accidente.

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/components/index.q{xml}

La última prueba envía SQL en la URL. Es solo un texto a buscar: ningún
producto lo tiene en su nombre, y la tabla queda intacta.

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/tests/products.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/output/test-report.txt{text}

Ver [DB-1](../../../reference/spec.md#DB-1).
