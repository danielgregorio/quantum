---
order: 5
title: "Funciones"
description: "Un q:function con parámetros tipados y verificados, llamado desde q:set y desde el HTML."
source: cookbook/basics/functions.md
source_hash: ee92d47aaa68
---

# Funciones

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/basics/functions).
:::

**Tarea:** escribir un cálculo una sola vez y usarlo donde la página lo necesite.

<<< @/../examples/cookbook/basics/functions/quantum.config.yaml{yaml}

Un `q:function` recibe `q:param`s como una acción: en cada llamada, cada
argumento se convierte a su tipo y se verifica contra sus reglas, y `default`
completa el que falta. `returnType` verifica lo que se devuelve. Una función
se puede llamar en cualquier expresión de la página, incluso dentro de otra
llamada.

<<< @/../examples/cookbook/basics/functions/components/index.q{xml}

<<< @/../examples/cookbook/basics/functions/tests/prices.test.q{xml}

<<< @/../examples/cookbook/basics/functions/output/test-report.txt{text}

Ver [FN-1](../../../reference/spec.md#FN-1), [FN-3](../../../reference/spec.md#FN-3)
y [FN-4](../../../reference/spec.md#FN-4).
