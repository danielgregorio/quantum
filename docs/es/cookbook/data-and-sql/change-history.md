---
order: 6
title: "Historial de cambios"
description: "\"history: true registra quién cambió qué fila, y cómo; ui:history lo muestra en la página.\""
source: cookbook/data-and-sql/change-history.md
source_hash: c1de2e8e5d97
---

# Historial de cambios

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/data-and-sql/change-history).
:::

**Tarea:** saber quién cambió una página de una wiki, cuándo, y qué cambió.

`history: true` en la fuente de datos es toda la configuración:

<<< @/../examples/cookbook/data-and-sql/change-history/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/change-history/migrations/V001_pages.sql{sql}

Cada escritura que hace una acción se registra en una tabla
`quantum_history` de la misma base de datos, en la misma transacción:
cuándo, el usuario de la sesión, la acción, la fila, y la fila antes y
después. `ui:history` lista los cambios de una fila, del más reciente al más
antiguo, con cada columna cambiada como `old → new`.

<<< @/../examples/cookbook/data-and-sql/change-history/components/index.q{xml}

`test:as` inicia la sesión de la prueba; `history=` verifica lo que se
registró. Una escritura rechazada, o revertida, no deja historial:

<<< @/../examples/cookbook/data-and-sql/change-history/tests/history.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/change-history/output/test-report.txt{text}

Ver [DB-11](../../../reference/spec.md#DB-11).
