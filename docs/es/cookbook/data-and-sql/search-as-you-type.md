---
order: 3
title: "Buscar mientras escribes"
description: "Un campo que actualiza los resultados después de cada pausa al escribir — la búsqueda la hace la propia consulta de la página."
source: cookbook/data-and-sql/search-as-you-type.md
source_hash: d5ee5239d914
---

# Buscar mientras escribes

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/data-and-sql/search-as-you-type).
:::

**Tarea:** un campo de búsqueda de libros que actualiza la lista mientras
escribes, y que sigue funcionando sin JavaScript.

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/migrations/V001_books.sql{sql}

La búsqueda es un parámetro GET (`?q=`), leído por la propia consulta de la
página. `search="results"` en el campo pide la misma página después de cada
pausa al escribir y reemplaza solo el elemento con `id="results"`; la URL lo
acompaña, así que el resultado se puede compartir o recargar.

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/tests/search.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/output/test-report.txt{text}

Ver [UI-12](../../../reference/spec.md#UI-12).
