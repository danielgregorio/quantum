# AI

Model calls, retrieval-augmented generation and agents are tags. They talk to
an [Ollama](https://ollama.com) server; there is no Python glue to write.

Everything on this page is checked against a real model by
`tests/live_ai/test_ai_real.py` — never against a fake one.

## Pointing at the model server

| Setting | Used when |
|---------|-----------|
| `QUANTUM_LLM_BASE_URL` environment variable | set — it wins |
| `llm.base_url` in `quantum.config.yaml` | the variable is not set |
| `http://localhost:11434` | neither is set |

Every AI tag uses the same server. The models you name (`phi3`,
`nomic-embed-text`, …) must be pulled on it: `ollama pull phi3`.

For `q:knowledge` also install the RAG extra: `pip install "quantum-framework[rag]"`.

## `q:llm` — one model call

```xml
<q:set name="produto" value="Quantum" />

<q:llm name="slogan" model="phi3" temperature="0" maxTokens="60">
  <q:prompt>Write a one-sentence slogan for {produto}, a web framework.</q:prompt>
</q:llm>

<p>{slogan}</p>
```

`slogan` holds the model's text. The prompt accepts databinding.

### Structured output

With `responseFormat="json"` the answer is parsed into an object:

```xml
<q:llm name="dados" model="phi3" responseFormat="json" temperature="0">
  <q:prompt>Return JSON with keys "name" and "age" for: "Maria Souza is 34 years old".</q:prompt>
</q:llm>

<p>{dados.name} — {dados.age}</p>
```

### Chat messages

Instead of `q:prompt`, give the conversation:

```xml
<q:llm name="resposta" model="phi3">
  <q:message role="system">You are a concise assistant. Answer in one sentence.</q:message>
  <q:message role="user">What is Quantum?</q:message>
</q:llm>
```

If the server is unreachable or the model does not exist, the page fails with
an error that says so — it does not render an empty answer.

## `q:knowledge` — retrieval-augmented generation

A knowledge base indexes text once and answers questions from it:

```xml
<q:knowledge name="manual" model="phi3" embedModel="nomic-embed-text"
             chunkSize="200" chunkOverlap="20">
  <q:source type="text">Quantum pages are served on port 8080 by default.
    The quantum stop command stops the server.</q:source>
  <q:source type="text">Variables are set with q:set and loops use q:loop.</q:source>
</q:knowledge>
```

Search the chunks — the closest ones first:

```xml
<q:query name="trechos" datasource="knowledge:manual">
  SELECT content, relevance FROM chunks WHERE content SIMILAR TO :pergunta LIMIT 3
  <q:param name="pergunta" value="Which port does the server use?" type="string" />
</q:query>
```

Or ask, and let the model answer from the best chunks:

```xml
<q:query name="resposta" datasource="knowledge:manual" mode="rag" model="phi3">
  SELECT answer, sources FROM knowledge WHERE question = :pergunta
  <q:param name="pergunta" value="What is the default port?" type="string" />
</q:query>

<p>{resposta[0].answer}</p>
```

Behaviour worth knowing:

- The index is stored in `./.quantum/knowledge` (`persistPath` changes it,
  `persist="false"` keeps it in memory). It is **rebuilt automatically** when a
  source's text, the embedding model or the chunking changes, and reused
  otherwise — embedding is the expensive part.
- Any `name` works; it does not have to be a valid ChromaDB collection name.
- If the model cannot produce the answer, the query fails with an error. The
  failure is never returned as if it were the answer.

## `q:agent` — a model that uses tools

An agent reasons in a loop and calls tools you write in Quantum:

```xml
<q:agent name="calc" model="phi3" max_iterations="4">
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

`calc` holds the final answer. `calc_result` says how it got there:

| Field | Contains |
|-------|----------|
| `success` | whether the agent finished |
| `iterations` | reasoning steps used |
| `actions` | each tool call: `tool`, `args`, `result`, `error` |
| `error.message` | why it did not finish, when `success` is false |

```xml
<q:loop items="{calc_result.actions}" var="a">
  <li>{a.tool}({a.args}) → {a.result}</li>
</q:loop>
```

The model's arguments are converted to the tool's declared `q:param` types
before the tool runs.

::: warning Tools run with your permissions
A tool body can run `q:query`. Whatever a tool can do, a prompt that steers the
model can make it do — give tools only the access the task needs.
:::

## `q:team`

`q:team` coordinates several agents with handoffs. It is **Beta and less
exercised** than the tags above: it has not yet been validated end to end
against a capable model (see [SUPPORT_TIERS.md](https://github.com/danielgregorio/quantum/blob/main/SUPPORT_TIERS.md)).
