---
order: 7
title: "Confirmar antes de borrar"
description: "Una página que pregunta primero, a la que se llega con un enlace, y el borrado como un POST desde su botón; sin JavaScript."
source: cookbook/forms-and-actions/confirm-before-delete.md
source_hash: 8e2ffc39c3d9
---

# Confirmar antes de borrar

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/forms-and-actions/confirm-before-delete).
:::

**Tarea:** preguntar "¿estás seguro?" antes de borrar, sin JavaScript.

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/migrations/V001_contacts.sql{sql}

La lista tiene un enlace, no un botón. Abrir un enlace solo lee, así que lo
único que puede hacer es preguntar:

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/components/index.q{xml}

La pregunta es una página propia, `components/delete/[id].q`. Su botón envía
a la acción `remove`, que borra y vuelve a la lista. Si el contacto ya no
existe (una segunda pestaña, una recarga), la página lo dice en lugar de
preguntar.

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/components/delete/[id].q{xml}

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/tests/delete.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/output/test-report.txt{text}
