---
order: 2
title: "Variables y expresiones"
description: "q:set guarda un valor, las llaves calculan con él y default completa lo que falta."
source: cookbook/basics/variables.md
source_hash: 103530a1b6f1
---

# Variables y expresiones

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/basics/variables).
:::

**Tarea:** guardar valores en variables y calcular con ellos.

<<< @/../examples/cookbook/basics/variables/quantum.config.yaml{yaml}

`q:set` guarda un valor con un nombre. Las llaves calculan con él: en un
atributo `q:` y en el HTML. `type="number"` convierte el texto en número, y
un valor que es una sola expresión conserva su tipo, así que `total` es un
número. `operation="increment"` cambia una variable en su lugar, y la página
se ejecuta de arriba abajo: `total` se calculó antes de que `quantity`
creciera. `default` se guarda cuando el valor está vacío o no existe, como
`?note=` en una visita sin parámetros.

<<< @/../examples/cookbook/basics/variables/components/index.q{xml}

<<< @/../examples/cookbook/basics/variables/tests/receipt.test.q{xml}

<<< @/../examples/cookbook/basics/variables/output/test-report.txt{text}

Ver [SET-1](../../../reference/spec.md#SET-1), [SET-3](../../../reference/spec.md#SET-3)
y [SET-5](../../../reference/spec.md#SET-5).
