---
order: 6
title: "Clasificar mensajes con respuestas JSON"
description: "responseFormat json — la respuesta del modelo es un objeto cuyos campos verificas y guardas."
source: cookbook/ai/sort-tickets-with-json.md
source_hash: 77e549b1b79e
---

# Clasificar mensajes con respuestas JSON

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/ai/sort-tickets-with-json).
:::

**Tarea:** archivar cada mensaje de soporte en una categoría, decidida por el
modelo, en una tabla.

<<< @/../examples/cookbook/ai/sort-tickets-with-json/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/ai/sort-tickets-with-json/migrations/V001_tickets.sql{sql}

`responseFormat="json"` le pide JSON al modelo y lo analiza: `ticket` es un
objeto. Sus campos son una entrada como cualquier otra — la página verifica
la categoría antes de guardarla, y las propias reglas de los `q:param` de la
acción se ejecutan antes de que se llame al modelo.

<<< @/../examples/cookbook/ai/sort-tickets-with-json/components/index.q{xml}

<<< @/../examples/cookbook/ai/sort-tickets-with-json/tests/tickets.test.q{xml}

<<< @/../examples/cookbook/ai/sort-tickets-with-json/tests/fake-model.json{json}

<<< @/../examples/cookbook/ai/sort-tickets-with-json/output/test-report.txt{text}

*Probado:* en CI estas pruebas se ejecutan contra un servidor de modelo de reemplazo, que responde a partir de la primera fuente que recibe; antes de cada versión se ejecutan contra un modelo real (`tests/live_ai/test_cookbook_ai.py`). Por eso verifican la estructura — qué fuente, qué herramienta, qué muestra la página cuando algo falla — y nunca las palabras del modelo.

Ver [IA-1](../../../reference/spec.md#IA-1).
