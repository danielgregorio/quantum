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

## Choosing the model

`model=` on `q:llm` and `q:agent` names the model. Without it:

| Setting | Used when |
|---------|-----------|
| `QUANTUM_LLM_DEFAULT_MODEL` environment variable | set — it wins |
| `llm.model` in `quantum.config.yaml` | the variable is not set |

```yaml
llm:
  base_url: http://localhost:11434
  model: phi3
```

There is no built-in model: with neither set, a tag without `model=` stops the
page with an error that says what to configure. `model=` takes expressions —
`model="{chosen}"` — like `endpoint=` and `apiKey=`.

For `q:knowledge` also install the RAG extra: `pip install "quantum-framework[rag]"`.

## `q:llm` — one model call

```xml
<q:set name="product" value="Quantum" />

<q:llm name="slogan" model="phi3" temperature="0" maxTokens="60">
  <q:prompt>Write a one-sentence slogan for {product}, a web framework.</q:prompt>
</q:llm>

<p>{slogan}</p>
```

`slogan` holds the model's text. The prompt accepts databinding.

### Structured output

With `responseFormat="json"` the answer is parsed into an object:

```xml
<q:llm name="person" model="phi3" responseFormat="json" temperature="0">
  <q:prompt>Return JSON with keys "name" and "age" for: "Maria Souza is 34 years old".</q:prompt>
</q:llm>

<p>{person.name} — {person.age}</p>
```

### Chat messages

Instead of `q:prompt`, give the conversation:

```xml
<q:llm name="reply" model="phi3">
  <q:message role="system">You are a concise assistant. Answer in one sentence.</q:message>
  <q:message role="user">What is Quantum?</q:message>
</q:llm>
```

If the server is unreachable or the model does not exist, the page fails with
an error that says so — it does not render an empty answer.

## `q:knowledge` — retrieval-augmented generation

A knowledge base indexes text once and answers questions from it:

```xml
<q:knowledge name="manual" embedModel="nomic-embed-text"
             chunkSize="200" chunkOverlap="20">
  <q:source type="text">Quantum pages are served on port 8080 by default.
    The quantum stop command stops the server.</q:source>
  <q:source type="text">Variables are set with q:set and loops use q:loop.</q:source>
</q:knowledge>
```

A source is `text`, `file` (`path`), `directory` (`path`, `pattern`) or `query`
(the rows of a query). A source that cannot be read is an error that names it,
never a smaller base; a type that reads nothing does not parse:

```xml
<q:knowledge name="site">
  <q:source type="url" url="https://example.com" />
</q:knowledge>
```

**Error:** `<q:source type="url">: use text, file, directory or query`

Search the chunks — the closest ones first:

```xml
<q:query name="chunks" datasource="knowledge:manual">
  SELECT content, relevance FROM chunks WHERE content SIMILAR TO :question LIMIT 3
  <q:param name="question" value="Which port does the server use?" type="string" />
</q:query>
```

To have the model answer from the chunks, use `q:llm knowledge=`
([below](#answers-that-cite-their-sources)) — it cites its sources and says
when the base has nothing on the question. The old `mode="rag"` on `q:query`
did neither, and was removed:

```xml
<q:query name="answer" datasource="knowledge:manual" mode="rag">
  SELECT answer FROM knowledge WHERE question = :question
  <q:param name="question" value="What is the default port?" type="string" />
</q:query>
```

**Error:** `mode="rag" was removed`

Behaviour worth knowing:

- The index is stored in `./.quantum/knowledge` (`persistPath` changes it,
  `persist="false"` keeps it in memory). It is **rebuilt automatically** when a
  source's text, the embedding model or the chunking changes, and reused
  otherwise — embedding is the expensive part.
- Any `name` works; it does not have to be a valid ChromaDB collection name.
- A `type="query"` source is shared by every user of the app: whoever asks can
  retrieve any of its rows. There is no per-user filter yet — do not index rows
  that only some users may see.

### Answers that cite their sources

`knowledge=` on `q:llm` answers from a knowledge base and tells you where each
statement comes from:

```xml
<q:llm name="answer" model="phi3" knowledge="docs" top="4" minRelevance="0.79">
  <q:message role="user">{question}</q:message>
</q:llm>

<p>{answer}</p>
<q:loop type="array" items="{answer_result.sources}" var="s">
  <p>[{s.n}] {s.source}</p>
</q:loop>
```

- The question (the last user message, or the prompt) retrieves the `top`
  chunks; they reach the model numbered, with the instruction to answer only
  from them and cite them like `[1]`.
- `answer_result.sources` lists them — `n`, `source`, `name` (the file name), `text`, `relevance` — and
  `answer_result.cited` the numbers the answer actually cites. Whether a model
  cites depends on the model: phi3 does, a 1.5B model often does not; `cited`
  says what happened, it never guesses.
- `minRelevance` (0 to 1) drops the chunks less relevant than it. Without it
  the `top` nearest chunks always come back, related to the question or not.
  The scale depends on the embedding model and the chunk size — look at the
  `relevance` of a few sources before choosing the floor. With
  `nomic-embed-text` on this guide in 1500-character chunks, questions the
  guide answers scored 0.80–0.87 and unrelated ones (the price of bitcoin, a
  rice recipe) 0.74–0.79, so `projects/docs-assistant` uses 0.79. A floor is a
  trade-off: a short, vague question ("What is a guard?") scored 0.77 and is
  turned away too.
- When nothing is retrieved — an empty base, or no chunk above `minRelevance` —
  the model is **not** asked (it would answer from memory, uncited): `{answer}`
  is empty and `answer_result.found` is false.
- `answer_result.grounded` is true when the answer cites at least one source,
  false when it cites none. Show an uncited answer as such — the base did not
  back it.

`minRelevance` is a number between 0 and 1:

```xml
<q:llm name="answer" model="phi3" knowledge="docs" minRelevance="high">
  <q:prompt>How do I paginate?</q:prompt>
</q:llm>
```

**Error:** `a relevance between 0 and 1`
- With `onerror="continue"`, a failure (no model server, a base that could not
  be built) reaches the page as `answer_result.success = false` instead of
  stopping it.

### Answers that arrive as they are written

A model can take seconds to answer. `stream="true"` lets the page render at
once and the answer appear word by word:

```xml
<q:llm name="answer" model="phi3" knowledge="docs" stream="true">
  <q:message role="user">{question}</q:message>
</q:llm>

<ui:stream for="answer" />
```

- The framework's own script reads the answer; you write no JavaScript.
  Without JavaScript, a link opens it. `quantum console` shows it arriving too.
- The sources (`answer_result.sources`) are on the page at once; the answer
  follows. What it cites is not known when the page renders, so `grounded` is
  empty there.
- The stream belongs to the visitor who asked, is read once, and expires in ten
  minutes. A failure halfway shows as an error after the text already written.
- Providers that cannot stream send the answer whole; `quantum run` waits for
  it as usual.

## `q:agent` — a model that uses tools

An agent reasons in a loop and calls tools you write in Quantum:

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

`calc` holds the final answer. `calc_result` says how it got there:

| Field | Contains |
|-------|----------|
| `success` | whether the agent finished |
| `iterations` | reasoning steps used |
| `actions` | each tool call: `tool`, `args`, `call` (written out: `add(a=17, b=25)`), `result`, `error` |
| `error.message` | why it did not finish, when `success` is false |

```xml
<q:loop items="{calc_result.actions}" var="a">
  <li>{a.call} → {a.result}</li>
</q:loop>
```

The model's arguments are converted to the tool's declared `q:param` types
before the tool runs; an argument it leaves out takes the param's `default`. `maxIterations` caps the reasoning steps (10 by default)
and `timeout` is in milliseconds. The attribute is `maxIterations`:

```xml
<q:agent name="calc" model="phi3" max_iterations="4">
  <q:execute task="What is 17 plus 25?" />
</q:agent>
```

**Error:** `the attribute is maxIterations, not max_iterations`

An agent that does not finish — no model server, a timeout, no answer within
`maxIterations` — stops the page with the reason. With `onerror="continue"` it
reaches the page instead: `{calc}` is empty and `calc_result.success` is false.

`projects/shop-agent` is a complete app: an agent answering questions about a
shop's SQLite database through four read-only query tools. The model never
writes SQL — it picks a tool and its arguments, and the page lists every call.

::: warning Tools run with your permissions
A tool body can run `q:query`. Whatever a tool can do, a prompt that steers the
model can make it do — give tools only the access the task needs.
:::

## `q:team`

`q:team` coordinates several agents with handoffs. It is **Beta and less
exercised** than the tags above: it has not yet been validated end to end
against a capable model (see [SUPPORT_TIERS.md](https://github.com/danielgregorio/quantum/blob/main/SUPPORT_TIERS.md)).
