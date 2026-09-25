---
order: 3
title: "Bucles"
description: "q:loop sobre una lista (con su posición), un rango de números y un texto separado por comas."
source: cookbook/basics/loops.md
source_hash: d76dbb1437b0
---

# Bucles

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/basics/loops).
:::

**Tarea:** repetir parte de una página para cada elemento de una lista o cada número de un rango.

<<< @/../examples/cookbook/basics/loops/quantum.config.yaml{yaml}

`type="array"` recorre una lista, con `index=` nombrando la posición desde 0.
`type="range"` cuenta desde `from` hasta `to`, ambos incluidos, de `step` en
`step`. `type="list"` divide un texto por comas y quita los espacios de cada
elemento.

<<< @/../examples/cookbook/basics/loops/components/index.q{xml}

<<< @/../examples/cookbook/basics/loops/tests/loops.test.q{xml}

<<< @/../examples/cookbook/basics/loops/output/test-report.txt{text}

Para recorrer las filas de una consulta, ver [Varios formularios en una página](../forms-and-actions/several-actions.md).
Las reglas: [LOOP-5](../../../reference/spec.md#LOOP-5) y [LOOP-6](../../../reference/spec.md#LOOP-6).
