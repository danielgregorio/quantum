---
order: 7
title: "Agregar una columna con una migración"
description: "Cambiar el esquema con un archivo de migración nuevo; el anterior queda como estaba."
source: cookbook/data-and-sql/add-a-column.md
source_hash: b48dec1e9084
---

# Agregar una columna con una migración

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/data-and-sql/add-a-column).
:::

**Tarea:** los productos necesitan una cantidad en stock, y la base de datos
ya existe.

<<< @/../examples/cookbook/data-and-sql/add-a-column/quantum.config.yaml{yaml}

La primera migración creó la tabla:

<<< @/../examples/cookbook/data-and-sql/add-a-column/migrations/V001_products.sql{sql}

El cambio es un segundo archivo. Las migraciones se ejecutan en orden, cada
una una vez, cada una en su propia transacción; una migración ya aplicada
nunca se edita:

<<< @/../examples/cookbook/data-and-sql/add-a-column/migrations/V002_add_stock.sql{sql}

```bash
quantum migrate up
```

<<< @/../examples/cookbook/data-and-sql/add-a-column/components/index.q{xml}

Cada prueba empieza con una base de datos construida por las migraciones, así
que la prueba ve el esquema que recibe una instalación nueva:

<<< @/../examples/cookbook/data-and-sql/add-a-column/tests/stock.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/add-a-column/output/test-report.txt{text}

¿Prefieres escribir el esquema que quieres y dejar que Quantum escriba la
migración? Ver `quantum migrate plan` en
[Project Structure](../../../guide/project-structure.md) (en inglés).
Ver [DB-6](../../../reference/spec.md#DB-6) y [DB-8](../../../reference/spec.md#DB-8).
