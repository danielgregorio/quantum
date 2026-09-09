# Quantum — Plano para virar framework

> Escrito em 2026-09-07, depois da auditoria funcional completa
> (`FULL_AUDIT_2026-09.md`) e das correções das Fases 1-7 (`AUDIT_FIX_PLAN.md`).
> Premissa: o Quantum hoje é um **protótipo muito largo com boas ideias dentro**, não um
> framework. Este documento é o caminho de um estado para o outro. Game engine (`qg:`,
> Godot, Mario) fica **fora de escopo** por decisão do autor — ver Fase 0.4.

---

## Onde estamos (2026-09-07)

Fases 0, 1.2 e 3 (itens 1-3) concluídas nesta data. **Restam três blocos**, e eles são
independentes entre si até a Fase 4:

| # | Bloco | Por que importa | Estado |
|---|---|---|---|
| **1.1** | Empacotamento | Enquanto ninguém consegue instalar, nada é testado por outra pessoa além do autor | ✅ Concluída |
| **2.1** | Um avaliador de expressão no lugar de dois | É o que muda a *sensação* de usar a linguagem, não só a lista de features. Mata o P0.1 de segurança junto | ✅ Concluída — 1 avaliador, 0 `eval()`, −324 linhas |
| **4** | Um app real em uso | É o juiz dos outros dois: troca opinião por evidência | ✅ Uma tela em uso — 11 atritos, 4 bugs, em [`DOGFOOD_NOTES.md`](DOGFOOD_NOTES.md) |

Ordem recomendada: **1.1 → 2.1 → 4**. O empacotamento primeiro porque destrava qualquer
outra pessoa usar; o avaliador depois porque é o refactor mais delicado e merece um repo já
instalável; o app por último porque só ele consegue julgar os dois.

---

## 0. O que "virar framework" significa, operacionalmente

Não é uma qualidade abstrata. São quatro propriedades verificáveis, e nenhuma delas é
verdade hoje:

| Propriedade | Estado hoje (verificado) |
|---|---|
| Alguém que não é o autor instala e constrói algo real | ❌ `pip install` instala pacotes chamados `src.core`/`src.runtime` no site-packages; `q:query` exige um servidor FastAPI separado rodando em `localhost:8000` |
| A superfície anunciada é a superfície que funciona | ❌ 30 features anunciadas; a auditoria achou a maioria de `ai/`, `jobs/`, `messaging/` nunca executada de ponta a ponta |
| Quebrar é difícil, e quando quebra o erro ensina | ⚠️ Melhorou hoje (teste de contrato + hint de XML), mas `{a + b}` ainda concatena strings silenciosamente |
| Existe um motivo legível em 30 segundos para escolher isso | ❌ O README/ROADMAP apresenta "framework web + engine de jogo + compilador Flex" |

Cada fase abaixo ataca uma dessas linhas.

---

## Fase 0 — Definir o núcleo (decisão, não código)

**A fase mais importante e a única que não pode ser delegada.** Sem ela, todo o resto é
manutenção de superfície indefinida.

### 0.1 — Classificar cada tag em três níveis

Não deletar nada. Mudar o que é **anunciado, testado, documentado e suportado**.

| Nível | Contrato | Tags propostas |
|---|---|---|
| **Core** | Documentado, testado end-to-end, estável, quebra = bug crítico | `q:component`, `q:param`, `q:set`, `q:if`, `q:loop`, `q:function`, `q:return`, `q:query`, `q:action`, `q:redirect`, `q:flash`, escopos (`session`/`application`/`request`), `q:invoke`, `q:data` |
| **Diferencial** | Mesmo contrato do Core — é a razão de existir do projeto | `q:llm`, `q:knowledge`, `q:agent`, `q:team` |
| **Experimental** | Mantido, mas rotulado; sem promessa de estabilidade; não aparece no README | `q:job`/`q:schedule`/`q:thread`, `q:message`/`q:queue`/`q:websocket`, `q:mail`, `q:file`, `ui:*`, terminal (`qt:`), htmx/islands |
| **Parked** | Sai do repo do framework | `qg:` + Godot codegen, `quantum-as4` (compilador MXML/AS4) |

### 0.2 — A frase de 30 segundos

O projeto precisa de uma, e ela precisa caber numa linha. Minha proposta, derivada do que
de fato funciona hoje:

> **Quantum — aplicações web declarativas em XML, com IA e RAG embutidos na linguagem.
> Sem build chain, sem JavaScript, sem framework de front.**

Isso é honesto (validei `q:llm` e `q:knowledge` de ponta a ponta hoje), é diferenciado
(nenhum framework declarativo tem RAG como tag de primeira classe), e não menciona jogo,
Flex, terminal ou mobile — que é exatamente o ponto.

### 0.3 — O público

Dev solo e times pequenos construindo ferramentas internas, dashboards, painéis admin e
apps com IA, que não querem uma cadeia de build de front-end. O ângulo homelab/self-hosted
é real e já aparece nos rascunhos de post (`medium-posts/drafts/21-i-built-a-language-for-my-homelab.md`).

### 0.4 — O game engine

Fica de fora **do framework**, não do seu tempo. Recomendação: repo próprio
(`quantum-game` ou similar), consumindo o `quantum` como dependência. Motivos concretos:

- É o que mais dilui a frase de 30 segundos.
- Tem 448 testes e 3 falhas pré-existentes que ficaram fora de escopo hoje — ele tem
  ritmo próprio, e amarrá-lo ao ciclo de release do framework atrasa os dois.
- A regra do CLAUDE.md (codegen é a fonte da verdade, nunca editar output) continua
  valendo lá, intocada.

**Critério de saída da Fase 0:** um documento de uma página com a tabela de níveis e a
frase de 30 segundos, e o README refletindo só o Core + Diferencial.

---

## Fase 1 — Tornar instalável (a barra de "outra pessoa consegue usar")

Hoje um estranho não consegue passar dos 10 primeiros minutos. Dois bloqueadores
concretos, ambos verificados:

### 1.1 — Empacotamento — ✅ CONCLUÍDA (2026-09-07)

> **Resultado:** `src/` virou o pacote `quantum/` (com os `__init__.py` que nunca
> existiram — eram namespace packages implícitos). 972 linhas de import reescritas em 220
> arquivos, 89 dos 123 hacks de `sys.path` removidos (sobraram os 2 legítimos de plugin e
> 1 guard no plugin de pytest). Critério de aceite atingido: `pip install .` em venv limpo
> e `quantum run hello.q` rodando **fora** do repo. Suíte: 2418 passando, 4 falhas todas
> pré-existentes e verificadas como tal. Dois bugs caíram junto: o `generator.py` emitia
> `from compiler.python.runtime import` dentro do **código gerado** (invisível a um grep de
> imports, pego pelos testes do transpiler), e `test_state_persistence.py` fazia `os.chdir()`
> no import sem restaurar — era ele poluindo o cwd de toda a suíte e me custou tempo real
> de debug hoje de manhã.

`pyproject.toml` declara `quantum = "src.cli.runner:main"` com `include = ["src*"]`, o que
instala pacotes de topo chamados `src.core` e `src.runtime` no site-packages. Colisão
garantida, e imports internos só funcionam por causa dos hacks de `sys.path`.

**O número assustador se decompõe.** Foram 123 ocorrências de `sys.path` medidas; depois de
categorizar, o trabalho real é bem menor:

| Onde | Qtd | Natureza |
|---|---|---|
| `tests/generated/` | 47 | Stubs auto-gerados que o `conftest.py` **já marca como skip**. Some com a decisão de apagar ou regerar — 38% do total, zero trabalho de engenharia |
| `tests/` (fora de generated) | 42 | Padrão único e uniforme (`parent.parent / 'src'`). Delete mecânico depois que o pacote existir |
| `scripts/` | 5 | Idem |
| **`src/`** | **34** | **O trabalho real.** (Mais 2 que são carregamento dinâmico de plugin — legítimos, ficam) |
| Total | 123 | |

Os 34 de `src/` também se agrupam: 8 em `cli/`, 5 em `compiler/`, 9 em
`core/features/*/ast_node.py` (todos o mesmo `try: from core.ast_nodes import QuantumNode /
except ImportError:` — viram import relativo simples num pacote de verdade), e o resto
espalhado em `runtime/`.

**Procedimento, em commits separados e revisáveis:**

1. **Decidir sobre `tests/generated/`** antes de tudo. São stubs quebrados e já skipados;
   apagá-los remove 47 hacks e ~100 testes falsos de uma vez. (Ver `SUPPORT_TIERS.md`: o
   gerador que os produziu vive no `quantum_admin` e produz scaffolding incompleto.)
2. `git mv src/{core,runtime,cli} quantum/` — preserva histórico.
3. Reescrever os 511 imports mecanicamente (`from core.X` → `from quantum.core.X`).
   **Commit sozinho**, para o diff ser revisável de relance.
4. Remover os 34 hacks de `src/` **por grupo** (cli, compiler, features, runtime), rodando
   a suíte entre cada grupo. Este passo não pode ser automatizado às cegas — cada hack
   existe porque algo não importava, e o teste é quem diz se o import agora resolve.
5. Delete mecânico dos 42+5 hacks de `tests/`/`scripts/`.
6. `pyproject.toml`: `packages = ["quantum"]`, entry point `quantum.cli.runner:main`.

**Critério de aceite (o único que prova):** `pip install .` em venv limpo, depois
`cd /tmp && quantum run hello.q`. Rodar **fora** do diretório do repo é o que distingue
"pacote correto" de "funciona porque o cwd salvou".

**Rede de segurança:** 2.444 testes verdes. É a condição ideal para um refactor amplo —
mecânico e verificável a cada passo.

### 1.2 — `q:query` precisa funcionar sem infraestrutura externa

Achado da auditoria (Cluster A) e provavelmente o maior bloqueador de adoção: uma
datasource nomeada resolve via a API do Quantum Admin em `localhost:8000`, a menos que
esteja em `local_datasources` — que **nenhum exemplo configura**. O novo usuário roda
`examples/test-query-basic.q` e recebe `Cannot connect to Quantum Admin API`.

Um framework onde a feature mais fundamental depende de um segundo servidor FastAPI
rodando não é instalável.

**Ação:** datasource declarada direto no `quantum.config.yaml` (SQLite no mínimo) deve
funcionar com zero processos externos. O Quantum Admin passa a ser o caminho *avançado*,
nunca o caminho padrão. Mensagem de erro deve dizer explicitamente como declarar uma
datasource local.

### 1.3 — Getting started que funciona de verdade

Um `quantum init` que gera um projeto mínimo com SQLite, um componente com `q:query` e
`q:loop`, e roda com `quantum start`. Testado a partir de um clone limpo, por execução
real — não por leitura.

**Critério de saída:** em uma máquina limpa, `pip install quantum && quantum init blog &&
cd blog && quantum start` sobe um app com dados de um banco. Cronometrar: se levar mais de
5 minutos, ainda não está pronto.

---

## Fase 2 — Endurecer o núcleo

### 2.1 — Um avaliador de expressão, no lugar de dois

**O enquadramento mudou depois de medir.** Isto não é "trocar o `eval()` por algo seguro" —
é **consolidar duas implementações paralelas em uma**, e os `eval()` morrem no processo.

Hoje existem dois avaliadores que fazem a mesma coisa:

| Onde | Métodos |
|---|---|
| `component.py` (passada de execução) | `_evaluate_condition`, `_evaluate_comparison_condition`, `_evaluate_databinding_expression`, `_evaluate_array_index`, `_evaluate_arithmetic_expression`, `_evaluate_function_call` |
| `renderer.py` (passada de renderização) | `_evaluate_condition`, `_evaluate_expression`, `_evaluate_nested_property`, `_evaluate_array_access` |

É a arquitetura de duas passadas (2.3) reaparecendo na camada de expressão — e é a razão
de `{a + b}` se comportar diferente conforme onde aparece.

**6 chamadas de `eval()` a eliminar:** `renderer.py:375,394,743`,
`expression_cache.py:238,282`, `component.py:646`. As três primeiras são o P0.1 de
segurança do `PUBLIC_RELEASE_PLAN.md` — resolvido de graça por este trabalho.

**A gramática necessária é pequena, e foi medida** (1.224 expressões em `examples/*.q`):

| % | Forma | Nota |
|---|---|---|
| 33,7% | variável simples (`{hp}`) | trivial |
| 23,0% | acesso pontilhado (`{a.b.c}`) | dict/atributo, mais `.length` em array |
| 14,0% | aritmética (`{a + b}`) | **é a que está quebrada hoje** |
| ~5% | chamada de função | `q:function` do usuário + stdlib |
| ~4% | literal objeto/array | `{'id': 1, 'name': 'Alice'}` |
| ~2% | comparação, indexação, booleano | `>`, `==`, `a[0]`, `!x`, `and`/`or` |

57% é só variável ou acesso pontilhado — o caminho quente é trivial, e a superfície
arriscada é ~15%. Isso é perfeitamente tratável com `ast.parse` + whitelist de nós.

**Achado colateral que importa:** parte do que parece expressão nos exemplos é
**CSS e JavaScript dentro de `<style>`/`<script>`** (`{background: linear-gradient(...)}`).
O avaliador novo **não pode** tentar avaliar conteúdo desses contextos — é fonte de
comportamento estranho hoje e precisa ser uma regra explícita, não um acidente.

**Plano:**

1. **Corpus de compatibilidade primeiro.** Extrair as 1.224 expressões reais dos exemplos
   para uma tabela de teste `(expressão, contexto, resultado esperado)`. Rodar contra o
   avaliador *atual* para fixar o comportamento de hoje — inclusive o errado, marcado como
   tal. Sem isso, não há como saber se a substituição regrediu algo.
2. **Escrever `quantum/core/expressions.py`**: `ast.parse` + whitelist (`BinOp`, `Compare`,
   `BoolOp`, `UnaryOp`, `Name`, `Constant`, `Subscript`, `Attribute` sem dunder, `Dict`,
   `List`, `Call` só para funções registradas). Coerção numérica consistente, sem depender
   de `type=` explícito.
3. **Biblioteca padrão mínima e honesta:** datas (`now`, `dateAdd`, `dateFormat` — hoje
   nenhuma existe, e a falta quebrou a autenticação), strings (`upper`, `lower`, `trim`,
   `replace`, `len`), arrays (`first`, `last`, `sort`, `join`), números (`round`, `abs`,
   `min`, `max`).
4. **Trocar os dois avaliadores por chamadas a ele**, um de cada vez, com a suíte entre
   cada troca.
5. **Marcar como regra:** contextos `<style>`/`<script>` não passam pelo avaliador.

**Critério de saída:** zero `eval()` no caminho de databinding; `{a + b}` com dois números
soma; `{now()}` existe; corpus de compatibilidade verde.

---

#### ✅ 2.1 CONCLUÍDA (commits `d8db907`..`96aeac9`)

Todos os critérios de saída atendidos. O que o plano **não** previu e apareceu ao executar:

**1. `q:data` era pior que tudo que o plano listou.** `DataImportService._evaluate_condition`
interpolava os valores de cada registro importado no texto do filtro — citando strings como
`f"'{value}'"` — e chamava `eval()` **puro**, sem `__builtins__` vazio, sem nada. Uma aspa
simples numa célula de CSV fechava o literal e o resto da célula rodava como Python com
`__import__` disponível. Verificado explorável antes da correção. É a entrada menos confiável
do framework e tinha a defesa mais fraca do código. Não estava na lista de 6 `eval()`.

**2. O `eval()` de `component.py` era pior do que parecia.** O `ExpressionCache` acima dele
bloqueia dunders com denylist de regex — mas todo `ValueError` que ele levantava caía direto
num `eval(substituted)` sem restrição. A denylist fazia um trabalho que o `except` desfazia
na linha seguinte, e `{().__class__}` num template avaliava para a classe `tuple`.

**3. O teste óbvio de injeção não prova nada.** Mandar um payload
`().__class__.__mro__[1].__subclasses__()` por uma condição e afirmar `is False` **passa no
código vulnerável**, porque o payload avalia para uma lista que genuinamente não é `'admin'`.
Afirmar o *resultado* não distingue "não executou" de "executou e deu falso". Os testes em
`tests/unit/test_expression_injection.py` detectam **execução**: um objeto sonda com uma
property que registra ter sido lida, e se as aspas dentro de um valor agem como delimitador
ou como dado. Quatro deles falham contra o código pré-migração — é isso que os torna úteis.

**4. `{n}` e `{n,m}` são quantificadores de regex, não expressões.**
`examples/form_validation.q` tem `pattern="\d{10,11}"`. O avaliador antigo os preservava
**por acidente** (falhava e devolvia o literal); o novo leria `{10,11}` como a tupla
`(10, 11)` e corromperia a validação em silêncio. `is_regex_quantifier()` os exclui
explicitamente. A lacuna de fundo é que **Quantum não tem escape para chave literal** —
isso merece decisão própria (ver 2.2/2.4), não um heurístico.

**5. O passo 4 do plano ("trocar um de cada vez") virou "trocar e depois deletar".**
Manter as cadeias antigas como fallback derrotaria o objetivo — duas gramáticas que
discordam era o problema. Então foram **medidas**, não julgadas: instrumentando a suíte
inteira, os quatro métodos do `renderer.py` deram **zero chamadas**, e a cadeia do
`component.py` deu **863 chamadas sobre 434 expressões distintas, e falhou nas 863** —
nenhuma expressão que ela resolvesse e o avaliador novo não. Deletados: −324 linhas nos
dois arquivos Python (−325/+35 no commit inteiro, que inclui o `.gitignore`).

> **Correção de método, registrada por verificação independente:** o commit `96aeac9` diz
> "73 chamadas, 73 falhas". Esse número veio de `pytest tests/`, que é um **subconjunto**
> dos `testpaths` declarados no `pytest.ini` (`tests examples quantum-as4`). A metade
> que sustenta a decisão — *zero resolvidas* — se confirma em todos os escopos medidos;
> a contagem não. Mesma causa: `_evaluate_comparison_condition` foi reportado como "zero
> chamadas" quando no escopo declarado ele recebe 93 e resolve as 93 — sem dano, porque
> esse método **não** foi deletado.

**6. Dois bugs reais corrigidos de brinde:**
- `<q:set name="gameOver" value="{false}">` guardava a *string* `'{false}'`, que é truthy —
  a flag nunca podia ser falsa (`examples/kenney_platformer.q:550`).
- Filtro `{age} > 18` em `q:data`: CSV entrega tudo como string, então comparava `'30'` com
  `18`, levantava, e o `except` nu virava `False`. Agora coage e compara como número.

**7. O passo 5 (`<style>`/`<script>` fora do avaliador) não foi feito** como regra no
avaliador — o corpus foi extraído já removendo esses blocos, e nenhum exemplo regrediu, mas
a regra explícita no caminho de renderização continua pendente.

**Validação além da suíte:** os 168 `examples/*.q` foram renderizados in-process antes e
depois; 166 saem byte a byte idênticos, e os 2 restantes diferem só num ID de job incremental
e num tempo de execução medido (rodar o mesmo código duas vezes produz as mesmas 2 diferenças).

### 2.2 — Mensagens de erro como UX principal

Numa linguagem declarativa, a mensagem de erro **é** a interface de debugging. Já
melhorou hoje (erro de XML agora aponta a linha e ensina `&lt;`/CDATA). Falta o resto:
toda `ParserError`/`ExecutorError` deve dizer o arquivo, a linha, a tag e o que fazer.
O `PUBLIC_RELEASE_PLAN.md` P1.5 já registra `except: pass` espalhados pelo runtime — cada
um é um erro silencioso que vira uma hora de debug de alguém.

### 2.3 — A arquitetura de duas passadas: documentar, não reescrever

O executor e o `HTMLRenderer` percorrem a AST **os dois**, e os dois iteram o mesmo
`q:loop`. Foi isso que fez `TextNode` dentro de loop explodir hoje, e significa que um
loop com efeito colateral executa duas vezes.

**Recomendação explícita: não reescrever isso agora.** Reescrever o motor de execução é o
tipo de movimento que mata projetos nesse estágio. O caminho proporcional:

1. Documentar o contrato: quais nós são *executados* e quais são *renderizados* (a lista
   já existe de fato em `component.py:355-360`, só não está escrita em lugar nenhum).
2. Testes que fixam esse comportamento.
3. Unificar só se essa classe de bug reaparecer duas ou três vezes. Aí sim há evidência
   que justifica o risco.

### 2.4 — O substrato XML

Não tem conserto barato, e é honesto dizer isso em vez de fingir que tem. `<` cru em SQL
ou JS quebra o arquivo inteiro; já mordeu três vezes (q:llm, q:schedule, e o exemplo de
hoje). Auto-CDATA **não** é a saída — corpos de `q:query` contêm `<q:param>` aninhados que
seriam destruídos (verifiquei hoje ao rejeitar essa abordagem).

Opções reais, em ordem de custo:
- **Curto prazo (feito):** erro que ensina o `&lt;`/CDATA.
- **Médio:** documentar CDATA como o idioma oficial para corpos de SQL/JS, e usá-lo em
  todos os exemplos, consistentemente.
- **Longo, se algum dia doer o suficiente:** um `q:script` com sintaxe não-XML, que é
  exatamente o caminho que o ColdFusion percorreu com `cfscript`. Registrar como
  possibilidade, não como plano.

**Critério de saída da Fase 2:** avaliador de expressão novo com whitelist, sem `eval()`
no caminho de databinding, biblioteca padrão mínima documentada, e nenhum `except: pass`
no runtime do Core.

---

## Fase 3 — Afiar o diferencial (a camada de IA) — ✅ ITENS 1-3 CONCLUÍDOS (2026-09-07)

> **Status:** multi-provider unificado (`q:llm` agora usa o mesmo
> `MultiProviderLLMService` que `q:agent` sempre usou, e ganhou `provider=`/`apiKey=`),
> cache com TTL implementado e validado (`runtime/llm_cache.py`, chaveado por tudo que muda
> a resposta), e persistência de RAG ligada por padrão (segunda execução reusa o índice em
> disco, verificado). Itens 4 (streaming) e 5 (doc com números) seguem abertos.

É o que justifica o projeto existir em 2026. Depois das correções de hoje, `q:llm` e
`q:knowledge` funcionam de verdade (validados contra Ollama e ChromaDB reais), e `q:agent`
roda um loop ReAct completo com tools. Isso é uma base real — falta transformar em
produto.

1. **`q:llm` multi-provider de fato.** Hoje `q:llm` só fala Ollama (`LLMService`), enquanto
   `q:agent` usa `MultiProviderLLMService` e fala Ollama/OpenAI/Anthropic. Unificar: uma
   camada de provider, usada pelas duas tags, com `provider=` em ambas.
2. **Cache de LLM.** `q:llm` tem atributo `cache` que hoje não está ligado a nada (removi a
   falsa promessa hoje). Chamada de LLM é cara e lenta; cache com TTL é diferencial real,
   não enfeite.
3. **RAG ergonômico.** `q:knowledge` já indexa e busca. Falta: persistência configurada por
   padrão (hoje `persist=false` reindexar tudo a cada boot), erro claro quando `chromadb`
   não está instalado, e um exemplo de ponta a ponta que rode com um comando.
4. **Streaming.** Já está na lista de pendências do devlog de 30/jan. Para chat, resposta
   não-streaming é experiência de 2022.
5. **Documentação com números reais.** "RAG em 3 linhas" com o `.q` completo, o comando
   para rodar, e a saída esperada — verificados por execução, não escritos de memória.

**Critério de saída:** um `examples/rag-chat.q` que qualquer pessoa roda em 2 comandos e
conversa com os próprios documentos.

---

## Fase 4 — Provar com um app real

A prova de que virou framework não é a suíte de testes — é **um app real, em uso**,
construído com ele. E a Fase 4 é o **juiz das outras duas**: é ela que diz se o
empacotamento e o avaliador ficaram bons, com evidência de uso em vez de opinião.

**O alvo com a ironia mais produtiva:** o `quantum_admin` tem 27.199 linhas de FastAPI
imperativo. O projeto que prega "não escreva backend imperativo" tem um backend imperativo
de 27 mil linhas. Reescrever tudo é má ideia; reescrever **uma tela** é o teste honesto.

**Candidata concreta:** a listagem de projetos. Ela já existe como `GET /api/projects`
(verificado hoje: devolve 3 projetos reais do SQLite), então o backend e os dados estão
prontos e a comparação é direta — a mesma tela, nas duas linguagens, lado a lado.

O que ela exercita, não por acaso, é exatamente o Core:

| Precisa de | Tag | Estado |
|---|---|---|
| Ler do SQLite | `q:query` | ✅ funciona sem infra externa desde hoje |
| Iterar as linhas | `q:loop query=` | ✅ |
| Renderizar a tabela | HTML + `{databinding}` | ✅ |
| Ação de criar/editar | `q:action` + `q:redirect` | ✅ corrigido hoje |
| Não repetir layout | `q:import` / `q:slot` | ⚠️ pouco exercitado |

**Procedimento:**

1. Escrever a tela em `.q`, servida pelo próprio Quantum, lendo o `quantum_admin.db`.
2. Colocá-la em uso de verdade — não um demo que roda uma vez.
3. **Anotar tudo que doer, no momento em que doer.** Essa lista é o produto real desta
   fase; é ela que reordena as Fases 2 e 3 com evidência em vez de intuição.
4. Só então decidir se vale reescrever mais telas. Provavelmente não vale, e tudo bem — o
   objetivo é o aprendizado, não a migração.

**Critério de saída:** uma tela em uso servida por `.q`, e uma lista escrita do que doeu.
Se a lista vier vazia, ou eu não olhei direito, ou o framework está pronto — e a segunda
hipótese precisa de mais evidência que uma tela.

---

#### ✅ 4 CONCLUÍDA (commit `2dc63b4`)

`components/admin/projects.q` — 100 linhas, servindo os 3 projetos reais em
`/admin/projects`. A lista **não** veio vazia: **11 atritos**, dos quais **4 eram bugs**,
corrigidos com testes de regressão (6 dos 7 falham contra o código anterior). Nenhum era
pego pelos 2.506 testes existentes.

O relatório completo está em [`DOGFOOD_NOTES.md`](DOGFOOD_NOTES.md). O resumo que muda
este plano:

- **`quantum start` não subia com o default do repo** (`reload: true`) e saía com código
  **0** mentindo sucesso. O jeito documentado de subir o servidor não subia o servidor.
- **Toda página em rota aninhada carregava sem CSS** — o link era relativo, e 404 de
  stylesheet não falha nada.
- **`<q:loop query="x" var="p">` descartava o `var=` calado** — o loop iterava certo,
  sobre os dados certos, e resolvia nada.
- **`{projects.recordCount}` falhava em silêncio e o erro se propagava por duas tags**
  até virar texto na página.

**A conclusão que reordena as fases:** 6 dos 11 atritos são a mesma doença — **falha
silenciosa**. Três dos quatro bugs não deram mensagem nenhuma. O tempo perdido não foi
consertando, foi descobrindo o que estava errado. Isso põe a **Fase 2.2 (mensagens de
erro) na frente de tudo**, e revela uma **passada na camada HTTP/servidor** que não era
fase nenhuma — dois dos quatro bugs estão lá, e são do tipo que define a primeira
impressão de quem clona o repo.

A Fase 2.1 (avaliador) passou no teste de uso: zero atritos vindos dele nesta tela.

**Candidato secundário, se quiser algo mais leve:** um app do homelab. Menos rigoroso como
teste, mas gera material de divulgação de graça (o ângulo já está nos rascunhos do Medium).

## Fase 5 — Contrato de estabilidade

O que separa "projeto de uma pessoa" de "framework que alguém aposta um projeto em cima".

1. **`FEATURE_STATUS.md` gerado, nunca escrito à mão** — já desenhado no
   `DOCS_CONSOLIDATION_PLAN.md`, com a skill `/status-check` que verifica por execução.
   Isso é a garantia de que a tabela de níveis da Fase 0 não apodrece como o `ROADMAP.md`
   apodreceu.
2. **CI que bloqueia.** Hoje `ruff check ... || true` (P1.4) — o lint nunca reprova nada.
   O teste de contrato criado hoje (`test_executor_service_contracts.py`) deve ser
   obrigatório.
3. **Versionamento e depreciação.** Semver de verdade para as tags Core, com política
   escrita: o que muda numa minor, o que exige major, quanto tempo uma tag fica
   deprecada antes de sair.
4. **Regra de entrada para tag nova.** Nenhuma tag entra no Core sem: exemplo que roda,
   teste de integração contra o serviço real, página de doc, e entrada no
   `FEATURE_STATUS.md`. Essa regra é a lição direta da auditoria de hoje — as 9 pontes
   quebradas existiam porque nenhuma dessas quatro coisas era obrigatória.

---

## Ordem e dependências

```
Fase 0 (decisão)  ──►  Fase 1 (instalável)  ──►  Fase 4 (app real)
       │                      │                        │
       │                      ▼                        ▼
       └──────────────►  Fase 2 (núcleo)  ────►  Fase 5 (contrato)
                              │
                              ▼
                        Fase 3 (IA)
```

- **Fase 0 primeiro, sempre.** Tudo depende de saber o que é o produto.
- **Fase 1 antes da 3.** Não adianta afiar o diferencial se ninguém consegue instalar.
- **Fase 4 é o juiz.** Ela vai reordenar a 2 e a 3 com evidência real de uso.
- **Fase 5 é contínua**, começa junto com a 1.

## O que este plano deliberadamente não faz

- **Não reescreve o motor de execução** (ver 2.3). Risco desproporcional ao ganho hoje.
- **Não mata o game engine nem o quantum-as4.** Separa. São projetos legítimos com ritmo
  próprio; o problema é estarem na mesma frase de apresentação.
- **Não promete performance.** Não há evidência nesta auditoria de que performance seja o
  gargalo de adoção — instalabilidade e confiabilidade são. Otimizar agora seria otimizar
  o problema errado.
