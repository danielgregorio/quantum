---
order: 6
title: "Una página por URL"
description: "components/product/[id].q responde a /product/1, /product/2...; el segmento es una variable."
source: cookbook/basics/page-per-url.md
source_hash: b03561c27215
---

# Una página por URL

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/basics/page-per-url).
:::

**Tarea:** un solo archivo que responde a una URL por cada elemento.

<<< @/../examples/cookbook/basics/page-per-url/quantum.config.yaml{yaml}

Un segmento `[name]` en el nombre de un archivo o carpeta coincide con
cualquier valor, y la página lo recibe como la variable `name`. Llega como
texto; `type="integer"` en un `q:set` lo convierte en número.

<<< @/../examples/cookbook/basics/page-per-url/components/product/[id].q{xml}

<<< @/../examples/cookbook/basics/page-per-url/tests/product.test.q{xml}

<<< @/../examples/cookbook/basics/page-per-url/output/test-report.txt{text}

Con una base de datos, la página lee la fila con ese id: ver
[Editar una fila](../forms-and-actions/edit-a-row.md). La regla:
[ROUTE-1](../../../reference/spec.md#ROUTE-1).
