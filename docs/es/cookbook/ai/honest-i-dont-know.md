---
order: 2
title: "Cuando los documentos no lo saben"
description: "minRelevance deja afuera los fragmentos sin relación; si no queda ninguno, no se le pregunta al modelo y la página lo dice."
source: cookbook/ai/honest-i-dont-know.md
source_hash: 2f44458e4a17
---

# Cuando los documentos no lo saben

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/ai/honest-i-dont-know).
:::

**Tarea:** cuando los documentos no cubren una pregunta, decirlo — en lugar
de dejar que el modelo responda de memoria.

<<< @/../examples/cookbook/ai/honest-i-dont-know/quantum.config.yaml{yaml}

Los mismos tres documentos que en [Respuestas con sus fuentes](./answer-with-sources.md).
Sin `minRelevance`, los fragmentos más cercanos siempre vuelven, estén
relacionados con la pregunta o no. Con él, un fragmento menos relevante que
el mínimo se descarta; cuando no queda ninguno, `answer_result.found` es
false y el modelo nunca se llama.

<<< @/../examples/cookbook/ai/honest-i-dont-know/components/index.q{xml}

<<< @/../examples/cookbook/ai/honest-i-dont-know/tests/honest.test.q{xml}

<<< @/../examples/cookbook/ai/honest-i-dont-know/output/test-report.txt{text}

El mínimo depende del modelo de embeddings y del tamaño de los fragmentos.
Imprime `s.relevance` para algunas preguntas que tus documentos responden y
algunas que no, y pon el mínimo entre ellas — por eso la página de arriba lo
muestra junto a cada fuente.

*Probado:* en CI estas pruebas se ejecutan contra un servidor de modelo de reemplazo, que responde a partir de la primera fuente que recibe; antes de cada versión se ejecutan contra un modelo real (`tests/live_ai/test_cookbook_ai.py`). Por eso verifican la estructura — qué fuente, qué herramienta, qué muestra la página cuando algo falla — y nunca las palabras del modelo.

Ver [IA-9](../../../reference/spec.md#IA-9).
