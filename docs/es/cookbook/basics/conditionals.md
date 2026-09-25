---
order: 4
title: "Condicionales"
description: "q:if, q:elseif y q:else, con condiciones que son expresiones."
source: cookbook/basics/conditionals.md
source_hash: 6ed2fdc28533
---

# Condicionales

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/basics/conditionals).
:::

**Tarea:** mostrar una cosa u otra según un valor.

<<< @/../examples/cookbook/basics/conditionals/quantum.config.yaml{yaml}

Se ejecuta la primera rama cuya condición se cumple; `q:else` se ejecuta
cuando ninguna se cumple. Una condición es una expresión, con `and`, `or` y
`not`. Dentro de un atributo, `<` se escribe `&lt;`: un archivo `.q` es XML.

<<< @/../examples/cookbook/basics/conditionals/components/index.q{xml}

<<< @/../examples/cookbook/basics/conditionals/tests/stock.test.q{xml}

<<< @/../examples/cookbook/basics/conditionals/output/test-report.txt{text}

Ver [IF-1](../../../reference/spec.md#IF-1) y [IF-2](../../../reference/spec.md#IF-2).
