---
source: guide/ai.md
source_hash: bc7fc37ab4d4
---
# AI

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/ai)为准。
:::

模型调用、检索增强生成（RAG）和智能体（agent）都是标签。它们与 [Ollama](https://ollama.com) 服务器通信；不需要编写任何 Python 胶水代码。

本页的示例在每次修改时都会针对一个替身模型服务器运行（`tests/docs/test_guide_ai.py`），检查它们发送给模型的内容以及交给页面的内容。AI 标签本身在每次版本发布前都会针对真实模型进行测试（`tests/live_ai/test_ai_real.py`）。

## 指向模型服务器 {#pointing-at-the-model-server}

| 设置 | 何时使用 |
|---------|-----------|
| 环境变量 `QUANTUM_LLM_BASE_URL` | 已设置——它优先 |
| `quantum.config.yaml` 中的 `llm.base_url` | 环境变量未设置 |
| `http://localhost:11434` | 两者都未设置 |

所有 AI 标签使用同一个服务器。你指定的模型（`phi3`、`nomic-embed-text`……）必须已在该服务器上拉取：`ollama pull phi3`。

## 选择模型 {#choosing-the-model}

`q:llm` 和 `q:agent` 上的 `model=` 指定模型。没有它时：

| 设置 | 何时使用 |
|---------|-----------|
| 环境变量 `QUANTUM_LLM_DEFAULT_MODEL` | 已设置——它优先 |
| `quantum.config.yaml` 中的 `llm.model` | 环境变量未设置 |

```yaml
llm:
  base_url: http://localhost:11434
  model: phi3
```

没有内置模型：两者都未设置时，一个没有 `model=` 的标签会以一个说明需要配置什么的错误停止页面。`model=` 接受表达式——`model="{chosen}"`——`endpoint=` 和 `apiKey=` 也一样。

使用 `q:knowledge` 时还要安装 RAG 可选依赖：`pip install "quantum-framework[rag]"`。

## `q:llm` — 一次模型调用 {#q-llm-—-one-model-call}

```xml
<q:set name="product" value="Quantum" />

<q:llm name="slogan" model="phi3" temperature="0" maxTokens="60">
  <q:prompt>Write a one-sentence slogan for {product}, a web framework.</q:prompt>
</q:llm>

<p>{slogan}</p>
```

`slogan` 保存模型返回的文本。提示词支持数据绑定。

### 结构化输出 {#structured-output}

使用 `responseFormat="json"` 时，回答会被解析成一个对象：

```xml
<q:llm name="person" model="phi3" responseFormat="json" temperature="0">
  <q:prompt>Return JSON with keys "name" and "age" for: "Maria Souza is 34 years old".</q:prompt>
</q:llm>

<p>{person.name} — {person.age}</p>
```

### 聊天消息 {#chat-messages}

不用 `q:prompt`，而是给出对话：

```xml
<q:llm name="reply" model="phi3">
  <q:message role="system">You are a concise assistant. Answer in one sentence.</q:message>
  <q:message role="user">What is Quantum?</q:message>
</q:llm>
```

如果服务器无法访问或模型不存在，页面会以一个说明原因的错误失败——而不是渲染一个空回答。

## `q:knowledge` — 检索增强生成 {#q-knowledge-—-retrieval-augmented-generation}

知识库对文本建立一次索引，然后根据它回答问题：

```xml
<q:knowledge name="manual" embedModel="nomic-embed-text"
             chunkSize="200" chunkOverlap="20">
  <q:source type="text">Quantum pages are served on port 8080 by default.
    The quantum stop command stops the server.</q:source>
  <q:source type="text">Variables are set with q:set and loops use q:loop.</q:source>
</q:knowledge>
```

来源可以是 `text`、`file`（`path`）、`directory`（`path`、`pattern`）或 `query`（一个查询的行）。无法读取的来源是一个指出其名字的错误，而不是一个更小的知识库；读取不到任何内容的类型无法通过解析：

```xml
<q:knowledge name="site">
  <q:source type="url" url="https://example.com" />
</q:knowledge>
```

**Error:** `<q:source type="url">: use text, file, directory or query`

搜索文本块——最接近的排在最前面：

```xml
<q:query name="chunks" datasource="knowledge:manual">
  SELECT content, relevance FROM chunks WHERE content SIMILAR TO :question LIMIT 3
  <q:param name="question" value="Which port does the server use?" type="string" />
</q:query>
```

要让模型根据文本块回答，请使用 `q:llm knowledge=`（[见下文](#answers-that-cite-their-sources)）——它会引用来源，并在知识库中没有相关内容时说明。旧的 `q:query` 上的 `mode="rag"` 两者都做不到，已被移除：

```xml
<q:query name="answer" datasource="knowledge:manual" mode="rag">
  SELECT answer FROM knowledge WHERE question = :question
  <q:param name="question" value="What is the default port?" type="string" />
</q:query>
```

**Error:** `mode="rag" was removed`

值得了解的行为：

- 索引保存在 `./.quantum/knowledge`（`persistPath` 可以修改，`persist="false"` 让它只存在内存中）。当某个来源的文本、嵌入模型或分块方式改变时，它会**自动重建**，否则会复用——计算嵌入是开销最大的部分。
- 任何 `name` 都可以；不必是合法的 ChromaDB 集合名。
- `type="query"` 来源由应用的所有用户共享：任何提问的人都可以检索到其中任意一行。目前还没有按用户过滤——不要索引只有部分用户可以看到的行。

### 引用来源的回答 {#answers-that-cite-their-sources}

`q:llm` 上的 `knowledge=` 根据知识库回答，并告诉你每个说法来自哪里：

```xml
<q:llm name="answer" model="phi3" knowledge="docs" top="4" minRelevance="0.79">
  <q:message role="user">{question}</q:message>
</q:llm>

<p>{answer}</p>
<q:loop type="array" items="{answer_result.sources}" var="s">
  <p>[{s.n}] {s.source}</p>
</q:loop>
```

- 问题（最后一条用户消息，或提示词）检索出 `top` 个文本块；它们被编号后发送给模型，并附带指令：只根据它们回答，并像 `[1]` 这样引用。
- `answer_result.sources` 列出它们——`n`、`source`、`name`（文件名）、`text`、`relevance`——`answer_result.cited` 是回答实际引用的编号。模型是否引用取决于模型：phi3 会引用，1.5B 的模型常常不会；`cited` 说明实际发生了什么，从不猜测。
- `minRelevance`（0 到 1）丢弃相关度低于它的文本块。没有它时，最接近的 `top` 个文本块总会返回，不论是否与问题相关。这个尺度取决于嵌入模型和分块大小——选择下限之前，先看看几个来源的 `relevance`。在本指南上使用 `nomic-embed-text`、按 1500 字符分块时，指南能回答的问题得分在 0.80–0.87，无关问题（比特币的价格、一道米饭的菜谱）在 0.74–0.79，所以 `projects/docs-assistant` 使用 0.79。下限是一种取舍：一个简短、含糊的问题（"What is a guard?"）得分 0.77，也会被拒绝。
- 当什么都没检索到时——知识库为空，或者没有高于 `minRelevance` 的文本块——**不会**调用模型（它会凭记忆回答，而且没有引用）：`{answer}` 为空，`answer_result.found` 为假。
- 回答至少引用一个来源时，`answer_result.grounded` 为真；一个都没引用时为假。请把没有引用的回答如实展示——知识库并不支持它。

`minRelevance` 是 0 到 1 之间的数字：

```xml
<q:llm name="answer" model="phi3" knowledge="docs" minRelevance="high">
  <q:prompt>How do I paginate?</q:prompt>
</q:llm>
```

**Error:** `a relevance between 0 and 1`
- 使用 `onerror="continue"` 时，失败（没有模型服务器、知识库无法构建）会以 `answer_result.success = false` 的形式到达页面，而不是停止页面。

### 边写边到达的回答 {#answers-that-arrive-as-they-are-written}

模型可能需要几秒钟才能回答。`stream="true"` 让页面立即渲染，回答逐字出现：

```xml
<q:llm name="answer" model="phi3" knowledge="docs" stream="true">
  <q:message role="user">{question}</q:message>
</q:llm>

<ui:stream for="answer" />
```

- 框架自带的脚本读取回答；你不需要编写 JavaScript。没有 JavaScript 时，用一个链接打开它。`quantum console` 也会显示回答逐步到达。
- 来源（`answer_result.sources`）立即出现在页面上；回答随后到达。页面渲染时还不知道回答引用了什么，所以那时 `grounded` 为空。
- 流属于提问的访问者，只能读取一次，十分钟后过期。中途失败会在已写出的文本之后显示为一个错误。
- 不支持流式输出的提供方会一次性发送完整回答；`quantum run` 照常等待它。

## `q:agent` — 使用工具的模型 {#q-agent-—-a-model-that-uses-tools}

智能体在循环中推理，并调用你用 Quantum 编写的工具：

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

`calc` 保存最终回答。`calc_result` 说明它是如何得到的：

| 字段 | 内容 |
|-------|----------|
| `success` | 智能体是否完成 |
| `iterations` | 使用的推理步数 |
| `actions` | 每次工具调用：`tool`、`args`、`call`（完整写出：`add(a=17, b=25)`）、`result`、`error` |
| `error.message` | `success` 为假时，它没有完成的原因 |

```xml
<q:loop items="{calc_result.actions}" var="a">
  <li>{a.call} → {a.result}</li>
</q:loop>
```

模型给出的参数会在工具运行前转换为工具声明的 `q:param` 类型；它省略的参数取该参数的 `default`。`maxIterations` 限制推理步数（默认 10），`timeout` 以毫秒为单位。属性名是 `maxIterations`：

```xml
<q:agent name="calc" model="phi3" max_iterations="4">
  <q:execute task="What is 17 plus 25?" />
</q:agent>
```

**Error:** `the attribute is maxIterations, not max_iterations`

没有完成的智能体——没有模型服务器、超时、在 `maxIterations` 内没有回答——会带着原因停止页面。使用 `onerror="continue"` 时，它会到达页面：`{calc}` 为空，`calc_result.success` 为假。

`projects/shop-agent` 是一个完整的应用：一个智能体通过四个只读查询工具，回答关于一家商店 SQLite 数据库的问题。模型从不编写 SQL——它选择一个工具和参数，页面列出每一次调用。

::: warning 工具以你的权限运行
工具的主体可以运行 `q:query`。工具能做的任何事，一个引导模型的提示词都可以让它去做——只给工具完成任务所需的权限。
:::

## `q:team` {#q-team}

`q:team` 通过交接协调多个智能体。它属于**实验层**：还没有 SPEC 规则，也没有证明它的应用，所以没有稳定性承诺（参见[稳定性](/zh/stability/)）。
