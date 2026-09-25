---
source: guide/ai.md
source_hash: bc7fc37ab4d4
---

# IA

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/ai).
:::

Las llamadas a modelos, la generación aumentada por recuperación y los agentes
son etiquetas. Hablan con un servidor [Ollama](https://ollama.com); no hay código
Python de pegamento que escribir.

Los ejemplos de esta página se ejecutan en cada cambio contra un servidor de
modelo de reemplazo (`tests/docs/test_guide_ai.py`), que verifica lo que le
envían al modelo y lo que le entregan a la página. Las propias etiquetas de IA
se prueban contra un modelo real antes de cada versión (`tests/live_ai/test_ai_real.py`).

## Apuntar al servidor del modelo {#pointing-at-the-model-server}

| Configuración | Se usa cuando |
|---------|-----------|
| variable de entorno `QUANTUM_LLM_BASE_URL` | está definida — tiene prioridad |
| `llm.base_url` en `quantum.config.yaml` | la variable no está definida |
| `http://localhost:11434` | ninguna de las dos está definida |

Todas las etiquetas de IA usan el mismo servidor. Los modelos que nombres
(`phi3`, `nomic-embed-text`, …) deben estar descargados en él: `ollama pull phi3`.

## Elegir el modelo {#choosing-the-model}

`model=` en `q:llm` y `q:agent` nombra el modelo. Sin él:

| Configuración | Se usa cuando |
|---------|-----------|
| variable de entorno `QUANTUM_LLM_DEFAULT_MODEL` | está definida — tiene prioridad |
| `llm.model` en `quantum.config.yaml` | la variable no está definida |

```yaml
llm:
  base_url: http://localhost:11434
  model: phi3
```

No hay un modelo incluido: si no está definida ninguna de las dos, una etiqueta
sin `model=` detiene la página con un error que dice qué configurar. `model=`
acepta expresiones — `model="{chosen}"` — igual que `endpoint=` y `apiKey=`.

Para `q:knowledge`, instala también el extra de RAG: `pip install "quantum-framework[rag]"`.

## `q:llm` — una llamada al modelo {#q-llm-—-one-model-call}

```xml
<q:set name="product" value="Quantum" />

<q:llm name="slogan" model="phi3" temperature="0" maxTokens="60">
  <q:prompt>Write a one-sentence slogan for {product}, a web framework.</q:prompt>
</q:llm>

<p>{slogan}</p>
```

`slogan` tiene el texto del modelo. El prompt acepta enlace de datos.

### Salida estructurada {#structured-output}

Con `responseFormat="json"`, la respuesta se analiza y se convierte en un objeto:

```xml
<q:llm name="person" model="phi3" responseFormat="json" temperature="0">
  <q:prompt>Return JSON with keys "name" and "age" for: "Maria Souza is 34 years old".</q:prompt>
</q:llm>

<p>{person.name} — {person.age}</p>
```

### Mensajes de chat {#chat-messages}

En lugar de `q:prompt`, da la conversación:

```xml
<q:llm name="reply" model="phi3">
  <q:message role="system">You are a concise assistant. Answer in one sentence.</q:message>
  <q:message role="user">What is Quantum?</q:message>
</q:llm>
```

Si no se puede llegar al servidor o el modelo no existe, la página falla con un
error que lo dice — no renderiza una respuesta vacía.

## `q:knowledge` — generación aumentada por recuperación {#q-knowledge-—-retrieval-augmented-generation}

Una base de conocimiento indexa un texto una vez y responde preguntas a partir de él:

```xml
<q:knowledge name="manual" embedModel="nomic-embed-text"
             chunkSize="200" chunkOverlap="20">
  <q:source type="text">Quantum pages are served on port 8080 by default.
    The quantum stop command stops the server.</q:source>
  <q:source type="text">Variables are set with q:set and loops use q:loop.</q:source>
</q:knowledge>
```

Una fuente es `text`, `file` (`path`), `directory` (`path`, `pattern`) o `query`
(las filas de una consulta). Una fuente que no se puede leer es un error que la
nombra, nunca una base más chica; un tipo que no lee nada no pasa el análisis:

```xml
<q:knowledge name="site">
  <q:source type="url" url="https://example.com" />
</q:knowledge>
```

**Error:** `<q:source type="url">: use text, file, directory or query`

Busca en los fragmentos — primero los más cercanos:

```xml
<q:query name="chunks" datasource="knowledge:manual">
  SELECT content, relevance FROM chunks WHERE content SIMILAR TO :question LIMIT 3
  <q:param name="question" value="Which port does the server use?" type="string" />
</q:query>
```

Para que el modelo responda a partir de los fragmentos, usa `q:llm knowledge=`
([más abajo](#answers-that-cite-their-sources)) — cita sus fuentes y dice cuándo
la base no tiene nada sobre la pregunta. El antiguo `mode="rag"` de `q:query` no
hacía ninguna de las dos cosas, y se eliminó:

```xml
<q:query name="answer" datasource="knowledge:manual" mode="rag">
  SELECT answer FROM knowledge WHERE question = :question
  <q:param name="question" value="What is the default port?" type="string" />
</q:query>
```

**Error:** `mode="rag" was removed`

Comportamientos que conviene conocer:

- El índice se guarda en `./.quantum/knowledge` (`persistPath` lo cambia,
  `persist="false"` lo mantiene en memoria). Se **reconstruye automáticamente**
  cuando cambia el texto de una fuente, el modelo de embeddings o la división en
  fragmentos, y se reutiliza en los demás casos — calcular los embeddings es la
  parte cara.
- Cualquier `name` funciona; no tiene que ser un nombre válido de colección de ChromaDB.
- Una fuente `type="query"` la comparten todos los usuarios de la aplicación:
  quien pregunta puede recuperar cualquiera de sus filas. Todavía no hay un
  filtro por usuario — no indexes filas que solo algunos usuarios pueden ver.

### Respuestas que citan sus fuentes {#answers-that-cite-their-sources}

`knowledge=` en `q:llm` responde a partir de una base de conocimiento y te dice
de dónde sale cada afirmación:

```xml
<q:llm name="answer" model="phi3" knowledge="docs" top="4" minRelevance="0.79">
  <q:message role="user">{question}</q:message>
</q:llm>

<p>{answer}</p>
<q:loop type="array" items="{answer_result.sources}" var="s">
  <p>[{s.n}] {s.source}</p>
</q:loop>
```

- La pregunta (el último mensaje del usuario, o el prompt) recupera los `top`
  fragmentos; llegan al modelo numerados, con la instrucción de responder solo a
  partir de ellos y citarlos como `[1]`.
- `answer_result.sources` los lista — `n`, `source`, `name` (el nombre del
  archivo), `text`, `relevance` — y `answer_result.cited` los números que la
  respuesta realmente cita. Que un modelo cite depende del modelo: phi3 lo hace,
  un modelo de 1.5B muchas veces no; `cited` dice lo que pasó, nunca adivina.
- `minRelevance` (de 0 a 1) descarta los fragmentos menos relevantes que él. Sin
  él, los `top` fragmentos más cercanos siempre vuelven, estén relacionados con
  la pregunta o no. La escala depende del modelo de embeddings y del tamaño de
  los fragmentos — mira la `relevance` de algunas fuentes antes de elegir el
  mínimo. Con `nomic-embed-text` sobre esta guía, en fragmentos de 1500
  caracteres, las preguntas que la guía responde obtuvieron 0.80–0.87 y las que
  no tienen relación (el precio del bitcoin, una receta de arroz) 0.74–0.79, así
  que `projects/docs-assistant` usa 0.79. Un mínimo es un compromiso: una
  pregunta corta y vaga ("What is a guard?") obtuvo 0.77 y también queda afuera.
- Cuando no se recupera nada — una base vacía, o ningún fragmento por encima de
  `minRelevance` — al modelo **no** se le pregunta (respondería de memoria, sin
  citar): `{answer}` está vacío y `answer_result.found` es false.
- `answer_result.grounded` es true cuando la respuesta cita al menos una fuente,
  y false cuando no cita ninguna. Muestra una respuesta sin citas como tal — la
  base no la respalda.

`minRelevance` es un número entre 0 y 1:

```xml
<q:llm name="answer" model="phi3" knowledge="docs" minRelevance="high">
  <q:prompt>How do I paginate?</q:prompt>
</q:llm>
```

**Error:** `a relevance between 0 and 1`
- With `onerror="continue"`, a failure (no model server, a base that could not
  be built) reaches the page as `answer_result.success = false` instead of
  stopping it.

### Respuestas que llegan a medida que se escriben {#answers-that-arrive-as-they-are-written}

Un modelo puede tardar segundos en responder. `stream="true"` deja que la página
se renderice de inmediato y que la respuesta aparezca palabra por palabra:

```xml
<q:llm name="answer" model="phi3" knowledge="docs" stream="true">
  <q:message role="user">{question}</q:message>
</q:llm>

<ui:stream for="answer" />
```

- El propio script del framework lee la respuesta; no escribes JavaScript. Sin
  JavaScript, un enlace la abre. `quantum console` también la muestra a medida
  que llega.
- Las fuentes (`answer_result.sources`) están en la página de inmediato; la
  respuesta viene después. Lo que cita no se conoce cuando se renderiza la
  página, así que ahí `grounded` está vacío.
- El stream pertenece al visitante que preguntó, se lee una vez y vence en diez
  minutos. Un fallo a mitad de camino se muestra como un error después del texto
  ya escrito.
- Los proveedores que no pueden hacer streaming envían la respuesta completa;
  `quantum run` la espera como siempre.

## `q:agent` — un modelo que usa herramientas {#q-agent-—-a-model-that-uses-tools}

Un agente razona en un bucle y llama herramientas que escribes en Quantum:

```xml
<q:agent name="calc" model="phi3" maxIterations="4">
  <q:instruction>Use the add tool, then answer with the number.</q:instruction>

  <q:tool name="add" description="Add two numbers">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:function name="doAdd">
      <q:set name="s" value="{a + b}" type="number" />
      <q:return value="{s}" />
    </q:function>
  </q:tool>

  <q:execute task="What is 17 plus 25?" />
</q:agent>

<p>{calc}</p>
```

`calc` tiene la respuesta final. `calc_result` dice cómo llegó a ella:

| Campo | Contiene |
|-------|----------|
| `success` | si el agente terminó |
| `iterations` | los pasos de razonamiento usados |
| `actions` | cada llamada a una herramienta: `tool`, `args`, `call` (escrita completa: `add(a=17, b=25)`), `result`, `error` |
| `error.message` | por qué no terminó, cuando `success` es false |

```xml
<q:loop items="{calc_result.actions}" var="a">
  <li>{a.call} → {a.result}</li>
</q:loop>
```

Los argumentos del modelo se convierten a los tipos de los `q:param` declarados
por la herramienta antes de que se ejecute; un argumento que omite toma el
`default` del parámetro. `maxIterations` limita los pasos de razonamiento (10
por defecto) y `timeout` está en milisegundos. El atributo es `maxIterations`:

```xml
<q:agent name="calc" model="phi3" max_iterations="4">
  <q:execute task="What is 17 plus 25?" />
</q:agent>
```

**Error:** `the attribute is maxIterations, not max_iterations`

Un agente que no termina — sin servidor de modelo, por un timeout, sin respuesta
dentro de `maxIterations` — detiene la página con el motivo. Con
`onerror="continue"`, en cambio, llega a la página: `{calc}` está vacío y
`calc_result.success` es false.

`projects/shop-agent` es una aplicación completa: un agente que responde
preguntas sobre la base de datos SQLite de una tienda a través de cuatro
herramientas de consulta de solo lectura. El modelo nunca escribe SQL — elige
una herramienta y sus argumentos, y la página lista cada llamada.

::: warning Las herramientas se ejecutan con tus permisos
El cuerpo de una herramienta puede ejecutar `q:query`. Todo lo que puede hacer
una herramienta, un prompt que dirige al modelo puede hacer que lo haga — dales
a las herramientas solo el acceso que la tarea necesita.
:::

## `q:team` {#q-team}

`q:team` coordina varios agentes con traspasos. Es **Experimental**: todavía no
tiene una regla en la SPEC ni una aplicación que lo demuestre, así que no tiene
promesa de estabilidad (ver [Estabilidad](/es/stability/)).
