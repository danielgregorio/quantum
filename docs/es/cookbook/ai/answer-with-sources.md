---
order: 1
title: "Respuestas con sus fuentes"
description: "Responder preguntas a partir de tus propios documentos con q:knowledge y q:llm knowledge=, y listar las fuentes."
source: cookbook/ai/answer-with-sources.md
source_hash: f578e2c9daff
---

# Respuestas con sus fuentes

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/ai/answer-with-sources).
:::

**Tarea:** una página que responde preguntas sobre una tienda a partir de sus
documentos de políticas, y muestra de qué documento salió cada respuesta.

<<< @/../examples/cookbook/ai/answer-with-sources/quantum.config.yaml{yaml}

Tres archivos Markdown en `knowledge/`:

<<< @/../examples/cookbook/ai/answer-with-sources/knowledge/returns.md{md}

`q:knowledge` lee la carpeta, la divide en fragmentos y calcula sus
embeddings. `q:llm knowledge="docs"` recupera los fragmentos más cercanos a
la pregunta y se los envía al modelo numerados, con la instrucción de
responder solo a partir de ellos y citarlos como `[1]`.
`answer_result.sources` lista lo que se recuperó; `answer_result.grounded`
dice si la respuesta cita algo de eso.

<<< @/../examples/cookbook/ai/answer-with-sources/components/index.q{xml}

<<< @/../examples/cookbook/ai/answer-with-sources/tests/ask.test.q{xml}

<<< @/../examples/cookbook/ai/answer-with-sources/output/test-report.txt{text}

*Probado:* en CI estas pruebas se ejecutan contra un servidor de modelo de reemplazo, que responde a partir de la primera fuente que recibe; antes de cada versión se ejecutan contra un modelo real (`tests/live_ai/test_cookbook_ai.py`). Por eso verifican la estructura — qué fuente, qué herramienta, qué muestra la página cuando algo falla — y nunca las palabras del modelo.

Ver [IA-2](../../../reference/spec.md#IA-2), [IA-6](../../../reference/spec.md#IA-6)
y [la guía de IA](../../../guide/ai.md#answers-that-cite-their-sources) (en inglés).
