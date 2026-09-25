---
order: 7
title: "Respuestas a partir de una tabla"
description: "Una fuente de q:knowledge que es una consulta — las filas de tu tabla de preguntas frecuentes, recuperadas como documentos."
source: cookbook/ai/knowledge-from-a-table.md
source_hash: f7b220a49066
---

# Respuestas a partir de una tabla

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/ai/knowledge-from-a-table).
:::

**Tarea:** responder preguntas sobre cuentas a partir de unas preguntas
frecuentes guardadas en la base de datos.

<<< @/../examples/cookbook/ai/knowledge-from-a-table/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/ai/knowledge-from-a-table/migrations/V001_faq.sql{sql}

Una fuente `type="query"` convierte cada fila en un texto para indexar. Todo
lo que contiene lo comparten todos los usuarios de la aplicación — cualquier
pregunta puede recuperar cualquier fila — así que indexa solo lo que todos
pueden leer.

<<< @/../examples/cookbook/ai/knowledge-from-a-table/components/index.q{xml}

<<< @/../examples/cookbook/ai/knowledge-from-a-table/tests/faq.test.q{xml}

<<< @/../examples/cookbook/ai/knowledge-from-a-table/output/test-report.txt{text}

*Probado:* en CI estas pruebas se ejecutan contra un servidor de modelo de reemplazo, que responde a partir de la primera fuente que recibe; antes de cada versión se ejecutan contra un modelo real (`tests/live_ai/test_cookbook_ai.py`). Por eso verifican la estructura — qué fuente, qué herramienta, qué muestra la página cuando algo falla — y nunca las palabras del modelo.

Ver [IA-8](../../../reference/spec.md#IA-8) y [IA-9](../../../reference/spec.md#IA-9).
