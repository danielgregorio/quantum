---
order: 3
title: "Transmitir una respuesta"
description: "Un q:llm en streaming y ui:stream — la página se muestra de inmediato y la respuesta aparece a medida que se escribe."
source: cookbook/ai/stream-an-answer.md
source_hash: 5dbf53d20a59
---

# Transmitir una respuesta

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/ai/stream-an-answer).
:::

**Tarea:** un modelo puede tardar segundos en responder; mostrar la página de
inmediato y la respuesta a medida que llega.

<<< @/../examples/cookbook/ai/stream-an-answer/quantum.config.yaml{yaml}

Con `stream="true"`, `q:llm` no espera: la recuperación ya se hizo, así que
las fuentes están en la página, y `<ui:stream for="answer">` va completando la
respuesta a medida que el modelo la escribe — con el propio script del
framework, sin JavaScript que escribir. Sin JavaScript es un enlace, y
`quantum console` también muestra la respuesta a medida que llega.

<<< @/../examples/cookbook/ai/stream-an-answer/components/index.q{xml}

<<< @/../examples/cookbook/ai/stream-an-answer/tests/stream.test.q{xml}

<<< @/../examples/cookbook/ai/stream-an-answer/output/test-report.txt{text}

El stream pertenece al visitante que preguntó, se lee una vez y vence en diez
minutos.

*Probado:* en CI estas pruebas se ejecutan contra un servidor de modelo de reemplazo, que responde a partir de la primera fuente que recibe; antes de cada versión se ejecutan contra un modelo real (`tests/live_ai/test_cookbook_ai.py`). Por eso verifican la estructura — qué fuente, qué herramienta, qué muestra la página cuando algo falla — y nunca las palabras del modelo.

Ver [IA-7](../../../reference/spec.md#IA-7).
