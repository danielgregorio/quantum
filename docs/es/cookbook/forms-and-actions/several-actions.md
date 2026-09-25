---
order: 4
title: "Varios formularios en una página"
description: "Cada formulario y cada botón envía el nombre de su acción; un nombre que la página no tiene responde 400."
source: cookbook/forms-and-actions/several-actions.md
source_hash: 50553f79a7ea
---

# Varios formularios en una página

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/forms-and-actions/several-actions).
:::

**Tarea:** agregar, quitar y vaciar desde una sola página, cada cosa con su propia acción.

<<< @/../examples/cookbook/forms-and-actions/several-actions/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/several-actions/migrations/V001_cart.sql{sql}

Cada `ui:form on-submit` y cada `ui:button on-click` envía el nombre de su
acción en un campo llamado `action`; la página ejecuta esa acción y ninguna
otra. `with="id={cart.id}"` envía el id de la fila con el botón.

<<< @/../examples/cookbook/forms-and-actions/several-actions/components/index.q{xml}

En una página con más de una acción, un envío cuyo `action` falta o no nombra
ninguna de ellas responde `400` y lista las acciones que hay. No se ejecuta
nada en su lugar, como verifica la última prueba:

<<< @/../examples/cookbook/forms-and-actions/several-actions/tests/cart.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/several-actions/output/test-report.txt{text}

Ver [ACT-5](../../../reference/spec.md#ACT-5).
