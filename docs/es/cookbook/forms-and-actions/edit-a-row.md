---
order: 6
title: "Editar una fila"
description: "Una página por fila con [id].q, un formulario abierto con los valores de la fila, y las reglas de la tabla al guardar."
source: cookbook/forms-and-actions/edit-a-row.md
source_hash: 5e7078307baa
---

# Editar una fila

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/forms-and-actions/edit-a-row).
:::

**Tarea:** una página que edita un libro, a la que se llega desde la lista.

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/migrations/V001_books.sql{sql}

La lista enlaza cada libro a `/book/{id}`:

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/components/index.q{xml}

`components/book/[id].q` responde a `/book/2` con `id = 2`. La acción toma
`title` y `genre` de la tabla ([Un formulario a partir de la tabla](./form-from-table.md))
y `values="{book}"` abre el formulario con los valores de la fila. Basta con
una consulta de una fila.

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/components/book/[id].q{xml}

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/tests/edit.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/output/test-report.txt{text}

Ver [UI-10](../../../reference/spec.md#UI-10).
