---
order: 2
title: "Una lista paginada"
description: "Una página de una lista larga a la vez, con ui:pager dibujando los enlaces a las demás."
source: cookbook/data-and-sql/paginated-list.md
source_hash: 5d55378336e3
---

# Una lista paginada

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/data-and-sql/paginated-list).
:::

**Tarea:** mostrar 23 publicaciones de diez en diez, con enlaces a las otras páginas.

<<< @/../examples/cookbook/data-and-sql/paginated-list/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/paginated-list/migrations/V001_posts.sql{sql}

`paginate="true"` hace que la consulta devuelva una página — la de `?page=`
en la URL, o la primera — y completa `posts_result.pagination` con los
totales. `<ui:pager for="posts">` dibuja anterior, los números de página y
siguiente, conservando los demás parámetros de la URL.

<<< @/../examples/cookbook/data-and-sql/paginated-list/components/index.q{xml}

Un `page` que no es un número positivo es la página 1, nunca un error:

<<< @/../examples/cookbook/data-and-sql/paginated-list/tests/posts.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/paginated-list/output/test-report.txt{text}

Ver [DB-2](../../../reference/spec.md#DB-2), [DB-9](../../../reference/spec.md#DB-9)
y [UI-11](../../../reference/spec.md#UI-11).
