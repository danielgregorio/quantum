---
order: 5
title: "Un formulario a partir de la tabla"
description: "q:action table= toma sus parámetros del esquema; un ui:form sin campos dibuja un campo por columna."
source: cookbook/forms-and-actions/form-from-table.md
source_hash: 8dcaa96980a9
---

# Un formulario a partir de la tabla

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/forms-and-actions/form-from-table).
:::

**Tarea:** un formulario para una tabla sin volver a escribir cada campo y cada regla.

<<< @/../examples/cookbook/forms-and-actions/form-from-table/quantum.config.yaml{yaml}

El esquema ya dice lo que necesita un libro:

<<< @/../examples/cookbook/forms-and-actions/form-from-table/migrations/V001_library.sql{sql}

`<q:action table="books" datasource="db">` lo lee y hace un `q:param` de cada
columna excepto la clave, en el orden de la tabla:

| Columna | Se convierte en |
|---|---|
| `title VARCHAR(120) NOT NULL` | obligatorio, de 120 caracteres como máximo |
| `author_id ... REFERENCES authors(id)` | un entero que debe nombrar a un autor existente |
| `genre ... CHECK (genre IN (...))` | uno de los tres |
| `pages INTEGER` (acepta NULL) | un entero; si se deja en blanco, llega a la acción como `None` |
| `lent BOOLEAN` | una casilla |

Un `ui:form` sin campos propios dibuja uno por parámetro, con la etiqueta
tomada del nombre (`author_id` se convierte en "Author"). El campo del autor
es una lista con los nombres de los autores. `null="true"` en el parámetro
`pages` de la consulta guarda un valor en blanco como `NULL`.

<<< @/../examples/cookbook/forms-and-actions/form-from-table/components/index.q{xml}

<<< @/../examples/cookbook/forms-and-actions/form-from-table/tests/books.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/form-from-table/output/test-report.txt{text}

Un `q:param` escrito en la acción tiene prioridad sobre el del esquema, y
`columns="a,b"` deja solo esas columnas. Ver
[UI-10](../../../reference/spec.md#UI-10).
