---
order: 5
title: "Escrituras que ocurren juntas"
description: "Un q:transaction — el débito, el crédito y la línea del registro se confirman juntos, o ninguno."
source: cookbook/data-and-sql/transaction.md
source_hash: 3bce037be24a
---

# Escrituras que ocurren juntas

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/data-and-sql/transaction).
:::

**Tarea:** mover dinero entre dos cuentas de modo que nunca se pueda debitar
de una sin acreditar en la otra.

<<< @/../examples/cookbook/data-and-sql/transaction/quantum.config.yaml{yaml}

La tabla de registro rechaza una transferencia de más de 1000 — lo que la
última prueba usa para hacer fallar la tercera escritura:

<<< @/../examples/cookbook/data-and-sql/transaction/migrations/V001_accounts.sql{sql}

La página verifica lo que puede explicar (dinero insuficiente) y lo dice con
un mensaje flash. Las tres escrituras van dentro de `q:transaction`: si
alguna falla, las anteriores se revierten y la página se detiene con el
error.

<<< @/../examples/cookbook/data-and-sql/transaction/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/transaction/tests/transfer.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/transaction/output/test-report.txt{text}

Ver [DB-4](../../../reference/spec.md#DB-4).
