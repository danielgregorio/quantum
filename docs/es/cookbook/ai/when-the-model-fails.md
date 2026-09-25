---
order: 5
title: "Cuando el modelo falla"
description: "onerror en q:llm — un modelo caído o demasiado lento no se lleva la página con él."
source: cookbook/ai/when-the-model-fails.md
source_hash: 2fc39501021e
---

# Cuando el modelo falla

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/ai/when-the-model-fails).
:::

**Tarea:** una página que usa un modelo debe seguir funcionando — y decir qué
pasó — cuando el servidor del modelo está caído, lento, o no tiene el modelo.

<<< @/../examples/cookbook/ai/when-the-model-fails/quantum.config.yaml{yaml}

Sin `onerror`, un fallo de IA detiene la página con un error que nombra el
servidor y la causa. Con `onerror="continue"`, la página sigue:
`summary_result.success` es false, `summary_result.error.message` dice por
qué, y `summary` está vacío. El ejemplo apunta `endpoint=` a un servidor que
no está en ejecución, así que falla igual en todas partes.

<<< @/../examples/cookbook/ai/when-the-model-fails/components/index.q{xml}

<<< @/../examples/cookbook/ai/when-the-model-fails/tests/failure.test.q{xml}

<<< @/../examples/cookbook/ai/when-the-model-fails/output/test-report.txt{text}

`onerror` funciona igual en `q:llm`, `q:knowledge`, `q:agent` y `q:query`.

Ver [IA-5](../../../reference/spec.md#IA-5).
