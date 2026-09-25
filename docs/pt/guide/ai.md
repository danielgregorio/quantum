---
source: guide/ai.md
source_hash: bc7fc37ab4d4
---
# IA

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/ai). O código é o mesmo do original.
:::

Chamadas a modelos, geração aumentada por recuperação (RAG) e agentes são
tags. Elas conversam com um servidor [Ollama](https://ollama.com); não há cola
em Python para escrever.

Os exemplos desta página rodam a cada mudança contra um servidor de modelos
substituto (`tests/docs/test_guide_ai.py`), que confere o que eles enviam ao
modelo e o que entregam à página. As próprias tags de IA são testadas contra
um modelo de verdade antes de cada versão (`tests/live_ai/test_ai_real.py`).

## Apontar para o servidor de modelos {#pointing-at-the-model-server}

| Configuração | Usada quando |
|---------|-----------|
| a variável de ambiente `QUANTUM_LLM_BASE_URL` | está definida — ela vence |
| `llm.base_url` no `quantum.config.yaml` | a variável não está definida |
| `http://localhost:11434` | nenhuma das duas está definida |

Todas as tags de IA usam o mesmo servidor. Os modelos que você nomeia
(`phi3`, `nomic-embed-text`, …) precisam estar baixados nele:
`ollama pull phi3`.

## Escolher o modelo {#choosing-the-model}

`model=` em `q:llm` e `q:agent` nomeia o modelo. Sem ele:

| Configuração | Usada quando |
|---------|-----------|
| a variável de ambiente `QUANTUM_LLM_DEFAULT_MODEL` | está definida — ela vence |
| `llm.model` no `quantum.config.yaml` | a variável não está definida |

```yaml
llm:
  base_url: http://localhost:11434
  model: phi3
```

Não há modelo embutido: sem nenhuma das duas, uma tag sem `model=` para a
página com um erro que diz o que configurar. `model=` aceita expressões —
`model="{chosen}"` — como `endpoint=` e `apiKey=`.

Para o `q:knowledge`, instale também o extra de RAG:
`pip install "quantum-framework[rag]"`.

## `q:llm` — uma chamada ao modelo {#q-llm-—-one-model-call}

```xml
<q:set name="product" value="Quantum" />

<q:llm name="slogan" model="phi3" temperature="0" maxTokens="60">
  <q:prompt>Write a one-sentence slogan for {product}, a web framework.</q:prompt>
</q:llm>

<p>{slogan}</p>
```

`slogan` guarda o texto do modelo. O prompt aceita databinding.

### Saída estruturada {#structured-output}

Com `responseFormat="json"`, a resposta é interpretada como um objeto:

```xml
<q:llm name="person" model="phi3" responseFormat="json" temperature="0">
  <q:prompt>Return JSON with keys "name" and "age" for: "Maria Souza is 34 years old".</q:prompt>
</q:llm>

<p>{person.name} — {person.age}</p>
```

### Mensagens de chat {#chat-messages}

Em vez de `q:prompt`, passe a conversa:

```xml
<q:llm name="reply" model="phi3">
  <q:message role="system">You are a concise assistant. Answer in one sentence.</q:message>
  <q:message role="user">What is Quantum?</q:message>
</q:llm>
```

Se o servidor não está acessível ou o modelo não existe, a página falha com
um erro que diz isso — ela não renderiza uma resposta vazia.

## `q:knowledge` — geração aumentada por recuperação {#q-knowledge-—-retrieval-augmented-generation}

Uma base de conhecimento indexa o texto uma vez e responde perguntas a partir
dele:

```xml
<q:knowledge name="manual" embedModel="nomic-embed-text"
             chunkSize="200" chunkOverlap="20">
  <q:source type="text">Quantum pages are served on port 8080 by default.
    The quantum stop command stops the server.</q:source>
  <q:source type="text">Variables are set with q:set and loops use q:loop.</q:source>
</q:knowledge>
```

Uma fonte é `text`, `file` (`path`), `directory` (`path`, `pattern`) ou
`query` (as linhas de uma consulta). Uma fonte que não pode ser lida é um
erro que a nomeia, nunca uma base menor; um tipo que não lê nada não passa
pelo parser:

```xml
<q:knowledge name="site">
  <q:source type="url" url="https://example.com" />
</q:knowledge>
```

**Erro:** `<q:source type="url">: use text, file, directory or query`

Buscar os trechos — os mais próximos primeiro:

```xml
<q:query name="chunks" datasource="knowledge:manual">
  SELECT content, relevance FROM chunks WHERE content SIMILAR TO :question LIMIT 3
  <q:param name="question" value="Which port does the server use?" type="string" />
</q:query>
```

Para o modelo responder a partir dos trechos, use `q:llm knowledge=`
([abaixo](#answers-that-cite-their-sources)) — ele cita as fontes e diz
quando a base não tem nada sobre a pergunta. O antigo `mode="rag"` no
`q:query` não fazia nenhuma das duas coisas, e foi removido:

```xml
<q:query name="answer" datasource="knowledge:manual" mode="rag">
  SELECT answer FROM knowledge WHERE question = :question
  <q:param name="question" value="What is the default port?" type="string" />
</q:query>
```

**Erro:** `mode="rag" was removed`

Comportamentos que vale saber:

- O índice é guardado em `./.quantum/knowledge` (`persistPath` o muda,
  `persist="false"` o mantém em memória). Ele é **reconstruído
  automaticamente** quando o texto de uma fonte, o modelo de embedding ou a
  divisão em trechos muda, e reaproveitado caso contrário — calcular os
  embeddings é a parte cara.
- Qualquer `name` serve; não precisa ser um nome válido de coleção do
  ChromaDB.
- Uma fonte `type="query"` é compartilhada por todos os usuários da
  aplicação: quem pergunta pode recuperar qualquer uma das linhas dela. Ainda
  não há filtro por usuário — não indexe linhas que só alguns usuários podem
  ver.

### Respostas que citam as fontes {#answers-that-cite-their-sources}

`knowledge=` no `q:llm` responde a partir de uma base de conhecimento e diz de
onde vem cada afirmação:

```xml
<q:llm name="answer" model="phi3" knowledge="docs" top="4" minRelevance="0.79">
  <q:message role="user">{question}</q:message>
</q:llm>

<p>{answer}</p>
<q:loop type="array" items="{answer_result.sources}" var="s">
  <p>[{s.n}] {s.source}</p>
</q:loop>
```

- A pergunta (a última mensagem do usuário, ou o prompt) recupera os `top`
  trechos; eles chegam ao modelo numerados, com a instrução de responder só a
  partir deles e citá-los como `[1]`.
- `answer_result.sources` os lista — `n`, `source`, `name` (o nome do
  arquivo), `text`, `relevance` — e `answer_result.cited`, os números que a
  resposta de fato cita. Se um modelo cita ou não depende do modelo: o phi3
  cita, um modelo de 1.5B muitas vezes não; `cited` diz o que aconteceu, nunca
  adivinha.
- `minRelevance` (de 0 a 1) descarta os trechos menos relevantes que ele. Sem
  ele, os `top` trechos mais próximos sempre voltam, tenham relação com a
  pergunta ou não. A escala depende do modelo de embedding e do tamanho dos
  trechos — olhe a `relevance` de algumas fontes antes de escolher o piso. Com
  o `nomic-embed-text` sobre este guia, em trechos de 1500 caracteres, as
  perguntas que o guia responde ficaram entre 0,80 e 0,87 e as sem relação (o
  preço do bitcoin, uma receita de arroz) entre 0,74 e 0,79, então o
  `projects/docs-assistant` usa 0,79. Um piso é uma troca: uma pergunta curta
  e vaga ("What is a guard?") ficou em 0,77 e também é recusada.
- Quando nada é recuperado — uma base vazia, ou nenhum trecho acima de
  `minRelevance` — o modelo **não** é chamado (ele responderia de memória, sem
  citar): `{answer}` fica vazio e `answer_result.found` é falso.
- `answer_result.grounded` é verdadeiro quando a resposta cita pelo menos uma
  fonte, falso quando não cita nenhuma. Mostre uma resposta sem citação como
  tal — a base não a sustentou.

`minRelevance` é um número entre 0 e 1:

```xml
<q:llm name="answer" model="phi3" knowledge="docs" minRelevance="high">
  <q:prompt>How do I paginate?</q:prompt>
</q:llm>
```

**Erro:** `a relevance between 0 and 1`
- Com `onerror="continue"`, uma falha (nenhum servidor de modelos, uma base
  que não pôde ser construída) chega à página como
  `answer_result.success = false` em vez de pará-la.

### Respostas que chegam enquanto são escritas {#answers-that-arrive-as-they-are-written}

Um modelo pode levar segundos para responder. `stream="true"` deixa a página
renderizar na hora e a resposta aparecer palavra por palavra:

```xml
<q:llm name="answer" model="phi3" knowledge="docs" stream="true">
  <q:message role="user">{question}</q:message>
</q:llm>

<ui:stream for="answer" />
```

- O script do próprio framework lê a resposta; você não escreve JavaScript.
  Sem JavaScript, um link a abre. O `quantum console` também a mostra
  chegando.
- As fontes (`answer_result.sources`) aparecem na página na hora; a resposta
  vem depois. O que ela cita não se sabe quando a página renderiza, então
  `grounded` fica vazio ali.
- A transmissão pertence ao visitante que perguntou, é lida uma vez e expira
  em dez minutos. Uma falha no meio aparece como um erro depois do texto já
  escrito.
- Os provedores que não conseguem transmitir enviam a resposta inteira; o
  `quantum run` a espera como de costume.

## `q:agent` — um modelo que usa ferramentas {#q-agent-—-a-model-that-uses-tools}

Um agente raciocina num loop e chama ferramentas que você escreve em Quantum:

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

`calc` guarda a resposta final. `calc_result` diz como ele chegou lá:

| Campo | Contém |
|-------|----------|
| `success` | se o agente terminou |
| `iterations` | os passos de raciocínio usados |
| `actions` | cada chamada de ferramenta: `tool`, `args`, `call` (por extenso: `add(a=17, b=25)`), `result`, `error` |
| `error.message` | por que ele não terminou, quando `success` é falso |

```xml
<q:loop items="{calc_result.actions}" var="a">
  <li>{a.call} → {a.result}</li>
</q:loop>
```

Os argumentos do modelo são convertidos para os tipos dos `q:param`
declarados na ferramenta antes de ela rodar; um argumento que ele deixa de
fora recebe o `default` do parâmetro. `maxIterations` limita os passos de
raciocínio (10 por padrão) e `timeout` é em milissegundos. O atributo é
`maxIterations`:

```xml
<q:agent name="calc" model="phi3" max_iterations="4">
  <q:execute task="What is 17 plus 25?" />
</q:agent>
```

**Erro:** `the attribute is maxIterations, not max_iterations`

Um agente que não termina — nenhum servidor de modelos, um timeout, nenhuma
resposta dentro de `maxIterations` — para a página com o motivo. Com
`onerror="continue"`, isso chega à página: `{calc}` fica vazio e
`calc_result.success` é falso.

O `projects/shop-agent` é uma aplicação completa: um agente que responde
perguntas sobre o banco SQLite de uma loja por meio de quatro ferramentas de
consulta só de leitura. O modelo nunca escreve SQL — ele escolhe uma
ferramenta e os argumentos dela, e a página lista cada chamada.

::: warning As ferramentas rodam com as suas permissões
O corpo de uma ferramenta pode rodar `q:query`. Tudo o que uma ferramenta pode
fazer, um prompt que conduz o modelo pode fazê-la fazer — dê às ferramentas
só o acesso de que a tarefa precisa.
:::

## `q:team` {#q-team}

O `q:team` coordena vários agentes com passagens de um para outro. Ele é
**Experimental**: ainda não tem regra na SPEC nem aplicação que o prove,
então não tem promessa de estabilidade (veja [Estabilidade](/pt/stability/)).
