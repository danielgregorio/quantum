---
order: 4
title: "Un agente sobre tu base de datos"
description: "q:agent con una herramienta de consulta de solo lectura — el modelo elige la herramienta y sus argumentos, nunca el SQL."
source: cookbook/ai/agent-over-your-database.md
source_hash: 144fdb043555
---

# Un agente sobre tu base de datos

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/ai/agent-over-your-database).
:::

**Tarea:** dejar que un asistente responda "¿qué productos se están
agotando?" a partir de la base de datos de la tienda, sin dejar nunca que el
modelo escriba SQL.

<<< @/../examples/cookbook/ai/agent-over-your-database/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/ai/agent-over-your-database/migrations/V001_products.sql{sql}

La herramienta es una función que tú escribes, con una consulta de solo
lectura. El modelo ve su nombre, su descripción y su parámetro; decide
llamarla y con qué valor, y ese valor se convierte al tipo del parámetro
antes de que la consulta se ejecute. `stock_result.actions` lista cada
llamada, escrita completa.

<<< @/../examples/cookbook/ai/agent-over-your-database/components/index.q{xml}

<<< @/../examples/cookbook/ai/agent-over-your-database/tests/agent.test.q{xml}

En CI, el modelo de reemplazo sigue un guion corto — llamar a la
herramienta, y después terminar:

<<< @/../examples/cookbook/ai/agent-over-your-database/tests/fake-model.json{json}

<<< @/../examples/cookbook/ai/agent-over-your-database/output/test-report.txt{text}

Una herramienta puede hacer todo lo que hace su cuerpo, y un prompt puede
empujar al modelo a llamarla: dales a las herramientas solo el acceso que la
tarea necesita.

*Probado:* en CI estas pruebas se ejecutan contra un servidor de modelo de reemplazo, que responde a partir de la primera fuente que recibe; antes de cada versión se ejecutan contra un modelo real (`tests/live_ai/test_cookbook_ai.py`). Por eso verifican la estructura — qué fuente, qué herramienta, qué muestra la página cuando algo falla — y nunca las palabras del modelo.

Ver [IA-4](../../../reference/spec.md#IA-4) y [IA-5](../../../reference/spec.md#IA-5).
