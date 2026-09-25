---
order: 10
title: "Leer un archivo JSON"
description: "Un array JSON como una lista de registros, con un campo calculado en cada uno."
source: cookbook/data-and-sql/read-json.md
source_hash: 19816ee3c86a
---

# Leer un archivo JSON

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/data-and-sql/read-json).
:::

**Tarea:** mostrar un carrito a partir de un archivo JSON, con el subtotal de
cada línea, del mayor al menor.

<<< @/../examples/cookbook/data-and-sql/read-json/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/read-json/import/products.json{json}

Un array JSON es la lista tal como está. `q:compute` agrega un campo a cada
registro; `{price}` y `{qty}` son los propios campos del registro.

<<< @/../examples/cookbook/data-and-sql/read-json/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/read-json/tests/cart.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/read-json/output/test-report.txt{text}

Ver [DATA-1](../../../reference/spec.md#DATA-1) y [DATA-3](../../../reference/spec.md#DATA-3).
