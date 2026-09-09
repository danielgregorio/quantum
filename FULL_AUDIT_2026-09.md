# Quantum — Auditoria Funcional Completa (2026-09-07)

> Escopo: core engine (30 features + executors/parsers de todas as categorias) + quantum-as4
> (compilador) + quantum_admin (painel) + quantum-lsp (language server). Método: rodar cada
> feature de verdade (`python src/cli/runner.py run <exemplo>.q` ou equivalente), nunca confiar
> em `manifest.yaml`/`ROADMAP.md`/relatórios internos sem confirmar por execução. Motivada por
> uma investigação anterior que achou `q:agent`/`q:team` quebrados apesar de "100% Complete" no
> ROADMAP — esta auditoria estende o mesmo método a todo o resto do repo.
>
> Esta auditoria é sobre **correção funcional** (a feature faz o que diz fazer?). Ela complementa,
> não substitui, `PUBLIC_RELEASE_PLAN.md` (segurança/higiene/empacotamento) e
> `AGENTIC_EXECUTION_PLAN.md` (plano para a feature `agentic_execution`) — os três devem ser lidos
> juntos.

---

## O achado principal: não são bugs isolados, é um padrão mecânico

Praticamente metade dos bugs desta auditoria tem a **mesma causa raiz**, confirmada por
`git log --follow` em cada arquivo: um serviço (`*_service.py`) foi escrito num commit, com
testes que instanciam a classe real e passam. Onze dias depois, um segundo commit adicionou os
executores que chamam esse serviço a partir da tag `.q` — escritos contra uma interface
**imaginada** (nomes de método e de property diferentes dos reais), cada um acompanhado de um
teste unitário que mocka essa mesma interface imaginada. Ninguém rodou um exemplo de ponta a
ponta entre as duas sessões. O resultado: o motor por baixo costuma estar são; a solda entre a
tag e o motor é que quebra.

Confirmado nestas fronteiras exatas:

| Tag | Executor chama | Serviço real tem | Onde |
|---|---|---|---|
| `q:agent` | `services.agent.execute(tool_nodes=, exec_context=, runtime=, timeout=)` | `AgentService.execute(..., timeout_ms=, tool_executor=)` — sem os outros kwargs | `agent_executor.py:83-97` vs `agent_service.py:188` |
| `q:team` | `services.agent.execute_team(...)` | `execute_team` só existe em `MultiAgentService` (`services.multi_agent`) | `team_executor.py:75-80` |
| `q:llm` | `services.llm.invoke(...)` | `LLMService` só tem `generate()`/`chat()` | `llm_executor.py:78` |
| `q:knowledge` | `services.knowledge.create(...)` | `KnowledgeService` só tem `index_knowledge()`/`search()`/`rag_query()` | `knowledge_executor.py:94` |
| `q:schedule` | `services.scheduler.*` | property real é `services.job_executor` | `schedule_executor.py:93-105` |
| `q:thread` | `services.threading.run/join/terminate` | métodos reais: `run_thread/join_thread/terminate_thread` | `thread_executor.py:75-83` |
| `q:queue`/`q:message` | `services.messaging.*`, `.queue_info()` | property real `message_queue`; método real `get_queue_info()` | `queue_executor.py:88-103` |
| `q:websocket` | `services.websocket.create_connection/send/close` | serviço nem registrado como property; métodos reais `register_connection/send_message/remove_connection` | `websocket_executor.py:63-164` |
| `q:action` (`q:set`/`q:if` no corpo) | `context.resolve_expression()`, `context.evaluate_condition()` | `ExecutionContext` nunca teve esses métodos | `action_handler.py:260,275,286` |

Isso é **9 pontes quebradas pela mesma razão mecânica**, cobrindo as categorias `ai/`, `jobs/`,
`messaging/` inteiras, mais o `q:action` (achado de forma independente, mesmo padrão). Em todos
os 9 casos, o teste unitário correspondente mocka a interface imaginada, não a real — nenhum
pegaria isso rodando `pytest`.

**Implicação para a Fase 0 do `AGENTIC_EXECUTION_PLAN.md`:** o escopo estimado ali ("3 bugs, meio
dia") estava subdimensionado. São pelo menos 9 pontes com o mesmo formato de conserto (alinhar
nome de property + nome de método + assinatura), mais os dois bugs transversais abaixo.

---

## Dois bugs transversais de alta alavancagem

### 1. `q:loop` sem `type=` explícito sempre vira "range"

`src/core/parsers/control_flow/loop_parser.py:50` (`loop_type = self.get_attr(element, 'type',
'range')`) ignora a presença de `items=` e assume range quando `type` não é dado. Confirmado
quebrando exemplos em pelo menos três features não relacionadas: `agents` (`agent_demo.q`),
`data_import` (`test-data-csv/json/xml-simple.q`), `scripting` (`python-data-processing.q`).
Zero teste de parser cobre "items sem type". **Fix de uma linha, resolve exemplos quebrados em
clusters diferentes.**

### 2. `type="integer"` aceito em alguns nós, rejeitado em outros

`src/core/features/state_management/src/ast_node.py:105-106` não inclui `'integer'` em
`valid_types`, enquanto `AgentToolParamNode` (agents) aceita. Confirmado quebrando
`test-query-loop.q`, `test-query-params.q`, e — mais sério — **todo o `game_engine_2d` via
pipeline oficial** (`qg:sprite` usa `type="integer"`, então `python src/cli/runner.py run` nunca
compila um jogo; só funciona pelo script não documentado `compile_game.py` na raiz do repo).

---

## Tabela consolidada por cluster

### Cluster A — Control Flow, Data, Query
| Item | Status | Nota |
|---|---|---|
| `set`/`if`/`loop` (sintaxe padrão), `invoke` | ✅ Sólido | 30+ exemplos passam limpo |
| `q:loop items= sem type=` | ❌ Quebrado | ver bug transversal #1 |
| `type="integer"` | ❌ Inconsistente | ver bug transversal #2 |
| `q:query` contra datasource | ⚠️ Dependência não documentada | requer Quantum Admin API em `localhost:8000`; nenhum exemplo/doc avisa |
| `q:transaction` | ❌ Quebrado como shipped | parser exige `datasource` na tag pai; exemplos só põem nos filhos |
| `q:data`/`q:transform` | ❌ Quebrado como shipped | parser espera `operation=` direto; exemplos usam sintaxe aninhada |

### Cluster B — LLM, Knowledge Base, Scripting
| Item | Status | Nota |
|---|---|---|
| `q:llm`, `q:knowledge` | ❌ Quebrado | mesmo padrão mecânico da tabela principal |
| `q:pydecorator` | ❌ Sem executor registrado | parser existe, executor não |
| RAG (chromadb) | ⚠️ Dependência não instalada por padrão | extra opcional do pyproject |
| `q:python`/`q:pyclass`/`q:pyimport` | 🔴 **Risco de segurança** | `exec()`/`eval()` puro, sem allowlist, acesso total a filesystem/rede/os — relevante direto para `agentic_execution`: a fuga de sandbox já existe hoje na linguagem |

### Cluster C — Jobs & Messaging
| Item | Status | Nota |
|---|---|---|
| `job_execution_demo.q`, `message_queue_demo.q` | ❌ Quebrado em runtime | mesmo padrão mecânico |
| `q:thread`, `q:websocket` | ❌ Quebrado (websocket é o pior — nem registrado) | mesmo padrão |
| `q:queue`/`q:message` | ⚠️ Quase certo | conserto mais barato do lote |
| `job-schedule-example.q` | ❌ Quebrado no parser XML | `<` de SQL lido como tag — mesma classe de bug já vista (e só remendada localmente) em `q:llm` |
| `quantum_jobs.db` | ✅ Schema simples, reusável | falta coluna tipo `pr_url`/`result` para servir de histórico de missão |
| `.quantum.pid` | Não é daemon vivo | processo não existe mais, é lixo de shutdown sujo |
| Motor (`JobExecutor`) | ✅ Parece completo | schedules, backoff, retries, prioridade — o problema é só a solda |

### Cluster D — Forms, Auth, Session
| Item | Status | Nota |
|---|---|---|
| `q:action` com `q:set`/`q:if` | 🔴 **Quebrado, feature de segurança** | ver seção dedicada abaixo |
| `require_auth`/`require_role` (o portão) | ✅ Funciona isolado | mas não adianta sem login funcionar |
| `q:set` em escopos fora de `q:action` | ✅ Funciona | caminho de código diferente (executor real) |
| Testes automatizados de action/auth/sessão | ❌ Não existem | busca exaustiva no repo, zero achado |

### Cluster E — Rendering & UI
| Item | Status | Nota |
|---|---|---|
| `html_rendering`, `theming`, `component_composition` | ✅ Sólido | 16/18 exemplos, testes genuínos (58/58) |
| `htmx_partials`, `islands_architecture` | ✅ Doc honesta | manifest diz "planned", exemplos confirmam — só HTML cru, nenhuma tag própria |
| `ui_engine` multi-target | ⚠️ Meia-verdade | só HTML+Textual comprovados; desktop/mobile só aceitos no CLI, nunca exercitados |
| `renderer.py` eval() (P0.1 já catalogado) | 🔴 Ainda não corrigido | `renderer.py:375,394,741` |
| `renderer.py` comentário enganoso | 🔴 Achado novo | linha 696 afirma "does NOT use eval()" a 45 linhas de um `eval()` real |

### Cluster F — Engines Especializadas & Serviços
| Item | Status | Nota |
|---|---|---|
| `logging`, `email_sending` (mock), `terminal_engine`, `testing_engine` | ✅ Funcionam | testing_engine gera pytest real, não stub oco |
| `developer_experience` | ✅ Doc honesta | manifest diz "planned" e é isso mesmo — zero implementação |
| `file_uploads` | ❌ Bug trivial | `file_parser.py:45` default `'makeunique'` vs `ast_nodes.py:1309` só aceita `'makeUnique'` |
| `game_engine_2d` via CLI oficial | ❌ Quebrado | ver bug transversal #2; só funciona via `compile_game.py` não documentado |
| `dump`/`log` databinding em modo CLI | ⚠️ A confirmar | `{var}` não resolve sem parâmetros de request — suspeita de comportamento cross-cutting do modo `run`, não bug isolado |

### Cluster G — quantum-as4 (compilador)
| Item | Status | Nota |
|---|---|---|
| Bug crítico de `else` (bug report interno) | ✅ Genuinamente corrigido | confirmado recompilando o repro exato |
| Bug de prefixo `this.` (bug report interno) | ⚠️ Corrigido só localmente | `test_transpiler_comprehensive.py` (já existente) mostra 4/8 falhas hoje, incluindo regressão nova |
| `STATUS.md`/`ADOBE_EXAMPLES_TEST_REPORT.md` ("100%", "production ready") | ⚠️ Amostra enviesada | exemplos testados ficaram mais simples ao longo do tempo, não cobrem os casos que quebram |
| `test_direct_compile.py` | ❌ Import quebrado | nunca roda |
| Testes Selenium documentados em `TESTING.md` | ❌ Não rodam | dependência nunca declarada no requirements.txt |

### Cluster H — quantum_admin & quantum-lsp
| Item | Status | Nota |
|---|---|---|
| quantum_admin (boot, API) | ✅ Funciona | 235 endpoints reais (README desatualizado diz 79) |
| Resource Manager / sistema de logs (admin) | ✅ Já implementado | os `.md` de planejamento interno descrevem como "a fazer"; já está pronto |
| `quantum_jobs.db` compartilhado core↔admin | ✅ Confirmado | valida a suposição da proposta original de reuso como "larva.db" |
| Git no admin | ⚠️ Degradado silenciosamente | `GitPython` não instalado, sem aviso na UI |
| quantum-lsp suíte de testes | ✅ 17/17 passam | bate exato com CLAUDE.md |
| quantum-lsp schema de tags | ❌ Defasado | zero menção a `q:agent`/`team`/`schedule`/`job`/`thread`/`websocket`/`queue` — sem autocomplete/diagnóstico para nada chegado depois de 30/jan |

---

## `q:action` — detalhe do achado mais grave

`ActionHandler` (`src/runtime/action_handler.py`) reimplementa um mini-interpretador próprio em
vez de delegar `q:set`/`q:if` ao `ExecutorRegistry` real (o mesmo que já faz `q:set` funcionar
fora de actions). Ele chama `context.resolve_expression()` e `context.evaluate_condition()`,
métodos que nunca existiram em `ExecutionContext`.

Consequências, na ordem em que um usuário bateria nelas:
1. Qualquer `q:action` com `q:set`/`q:if` no corpo lança `AttributeError`.
2. Essa exceção é capturada e devolvida como `(referrer, 500)` — o cliente recebe uma resposta
   com formato de redirect mas `status=500`. **Parece que funcionou; não funcionou.**
3. Mesmo corrigindo (1), login não persistiria: `handle_action()` cria um `ExecutionContext()`
   novo e vazio, desconectado da sessão Flask (`web_server.py:436`), e nunca sincroniza de volta
   — só o runtime de *renderização* (chamada separada) faz esse sync.
4. O portão (`require_auth`/`require_role`) funciona corretamente isolado — mas não há caminho
   documentado para completar login, então isso é irrelevante na prática.
5. Zero teste automatizado cobre este caminho.
6. `forms_actions` manifest diz `stable`; `authentication` manifest diz `planned`; `ROADMAP.md`
   diz que os dois estão `✅ Complete`. As três fontes se contradizem.

Isto é mais sério que os bugs de `agent`/`team`: é uma feature de segurança, já tratada como
candidata a release público no `PUBLIC_RELEASE_PLAN.md`, que falha de um jeito que se parece com
sucesso.

---

## O que está genuinamente sólido (não precisa de atenção agora)

- `set`/`if`/`loop` com sintaxe padrão, `invoke` — núcleo mais usado da linguagem.
- `html_rendering`, `theming`, `component_composition` (testes genuínos, 58/58).
- `htmx_partials`, `islands_architecture` — únicos casos de manifest honesto batendo com a
  realidade ("planned" e de fato não implementado).
- `testing_engine` — gera pytest real e válido.
- `logging`, `email_sending` (modo mock), `terminal_engine` (build).
- `quantum_admin` — mais maduro que seus próprios planos internos sugerem.
- `quantum-lsp` — o que existe é genuinamente testado (17/17), só está defasado em cobertura.
- O bug crítico de `else` no quantum-as4 — corrigido de verdade, confirmado.
- O motor de jobs (`JobExecutor`: schedules, backoff, retries, prioridade) por baixo do `q:schedule` quebrado.

---

## Recomendação de ordem de ataque

1. **`q:action`/auth (Cluster D)** — é o único achado com blast radius de segurança real em
   produção, não só em uma proposta futura. Prioridade sobre tudo abaixo.
2. **Os dois bugs transversais** (`loop_parser` range-default, `type="integer"`) — alavancagem
   alta, conserto barato, desbloqueiam exemplos em múltiplos clusters de uma vez.
3. **As 9 pontes executor↔serviço** (tabela principal) — mesmo formato de conserto em todas;
   dá para tratar como um único PR mecânico por categoria (`ai/`, `jobs/`, `messaging/`).
4. **Segurança de `q:python`/`q:pyclass`/`q:pyimport`** — resolver antes de qualquer coisa da
   proposta `agentic_execution` chegar perto de deixar um LLM escolher/gerar tool bodies.
5. Todo o resto (P1/P2 de documentação, `file_uploads`, `game_engine_2d` via CLI, quantum-as4
   `this.`-prefix, quantum-lsp schema) — sem urgência de segurança, mas cada um é uma queda de
   braço na primeira impressão de um novo usuário ou contribuidor.

Este documento não substitui `AGENTIC_EXECUTION_PLAN.md`; atualiza a Fase 0/1 dele com o escopo
real (9 pontes, não 3) e adiciona o achado de `q:action` como bloqueador anterior a qualquer
trabalho de sandbox/mission.

---

## Tabela de features: % de testes passando vs. realidade

Números reais de `pytest tests/ -v` (2026-09-07): **2380 passed / 237 skipped / 3 failed**
sobre 2620 testes coletados na suíte principal, mais os testes próprios de `quantum-as4` e
`quantum-lsp` (fora do `pytest tests/`). **O ponto central desta tabela é justamente que o
percentual sozinho engana**: a categoria `ai/` inteira mostra 100% de testes passando e está
100% quebrada em execução real, porque o mock foi escrito contra a mesma interface inventada
que o executor chama. A coluna "Avaliação" é o que importa; a de "%" é só para não esconder o
dado.

| Feature | % testes passando | Avaliação | Sugestão |
|---|---|---|---|
| `control_flow` (set/if/loop padrão) | 115/115 (100%) | ✅ Sólido — confirmado por 30+ exemplos reais, além dos testes | Nenhuma ação; só falta o teste de parser do próximo item |
| `q:loop` sem `type=` explícito | 0 testes cobrem este caso (dentro dos 39/39 do executor) | ❌ Bug confirmado, sem rede de segurança — os testes existentes testam o executor com um `LoopNode` já construído, nunca o parser | Fase 2 do `AUDIT_FIX_PLAN.md`: fix de 1 linha + teste de parser novo |
| `query`/`data`/`transaction`/`invoke` | 84/84 (100%) | ⚠️ Parcial — executor testado corretamente, mas `q:query` depende de Quantum Admin API não documentada e `transaction`/`data-transform` têm exemplos desalinhados do parser | Fase 5: documentar dependência, alinhar exemplos |
| `agents` (`q:agent`) | 48/48 (100%) | ❌ Quebrado apesar de 100% — `AgentService` testada direto funciona; o mock do executor usa uma assinatura que nunca existiu na classe real | Fase 3a |
| `team` (`q:team`) | 61/61 (100%) | ❌ Quebrado apesar de 100% — mesmo padrão | Fase 3a |
| `llm_integration` (`q:llm`) | 56/56 (100%) | ❌ Quebrado apesar de 100% — `services.llm.invoke()` não existe | Fase 3a |
| `knowledge_base` (`q:knowledge`/RAG) | 27/27 (100%) | ❌ Quebrado apesar de 100% — mesmo padrão, mais dependência `chromadb` não instalada por padrão | Fase 3a + declarar extra opcional com erro claro |
| `scripting` (`q:python`/`q:pyclass`/`q:pyimport`) | 35/35 (100%) | ⚠️ Funciona, mas sem sandbox — `exec()`/`eval()` livre, acesso total a `os`/rede/filesystem | Fase 4: allowlist ou flag `unsafe=` explícita |
| `jobs` (`q:job`/`q:schedule`/`q:thread`) | ~128/134 nos rodados (94-100% conforme arquivo) | ❌ Quebrado em runtime apesar do % alto — `services.scheduler`/`services.threading` não existem | Fase 3b |
| `messaging` (`q:queue`/`q:message`/`q:websocket`) | 116/116 (100%) | ❌ Quebrado em runtime — `websocket` nem está registrado como serviço | Fase 3c |
| `forms_actions`/`authentication` (`q:action` + auth) | 4/4 (100%) — **testes novos, não existiam antes desta sessão** | ✅ Corrigido e validado nesta sessão (Fase 1 concluída) — login persiste, erro não se disfarça mais de redirect | Cobrir logout e RBAC (`require_role`/`require_permission`) com testes dedicados, ainda inexistentes |
| `html_rendering`/`component_composition` | 58/58 (100%) | ✅ Sólido — confirmado por execução real e testes genuínos | Nenhuma prioridade |
| `theming` | 33/33 (100%) | ✅ Sólido | Nenhuma prioridade |
| `ui_engine` (multi-target) | 174/174 (100%) nos adaptadores | ⚠️ Parcial — adaptadores desktop/mobile testados isoladamente, mas nenhum exemplo em `examples/` exercita `--target desktop`/`mobile` de ponta a ponta | Adicionar 1 exemplo real por target |
| `htmx_partials` | 0 testes dedicados | ⏸️ Não implementado — manifest diz "planned" e bate com a realidade | Nenhuma urgência, é trabalho futuro genuíno, não bug |
| `islands_architecture` | 0 testes dedicados | ⏸️ Não implementado — mesma situação honesta | Nenhuma urgência |
| `game_engine_2d` | 448/451 (99,3%) | ⚠️ Alto % de teste, pipeline **documentado** quebrado — `python src/cli/runner.py run` não compila nenhum exemplo `qg:` por causa do bug de `type="integer"`; só funciona via `compile_game.py`, script não documentado | Fase 2 (fix do tipo) + oficializar/documentar `compile_game.py` |
| `terminal_engine` | 49/49 (100%) | ✅ Sólido — build confirmado por execução real | Nenhuma prioridade |
| `testing_engine` | 80/80 (100%) | ✅ Sólido, boa surpresa — gera pytest real e válido, não stub oco | Nenhuma prioridade |
| `email_sending`/`file_uploads`/`logging`/`dump` | Sem arquivo de teste automatizado dedicado em `tests/` | ⚠️ Só validados manualmente durante a auditoria (execução real de exemplo) — `file_uploads` tem bug conhecido de casing (`makeunique` vs `makeUnique`) | Escrever testes de integração para os 4; sem eles, qualquer regressão futura passa despercebida |
| `quantum-as4` (compilador, fora de `pytest tests/`) | 7/7 (100%) `test_transpiler_v2`; **4/8 (50%)** `test_transpiler_comprehensive` | ⚠️ Misto — bug de `else` genuinamente corrigido; bug de `this.`-prefix corrigido só localmente, com regressão nova não detectada porque ninguém rodou a suíte comprehensive depois do fix | Rodar `test_transpiler_comprehensive.py` sempre após mudanças no transpiler; consertar `test_direct_compile.py` (import quebrado) |
| `quantum_admin` (fora de `pytest tests/`) | Sem suíte pytest dedicada encontrada | ⚠️ Validado só manualmente (boot + smoke test de rota nesta auditoria) | Adicionar testes automatizados de API — hoje a única rede de segurança é rodar `run.py` e olhar |
| `quantum-lsp` (fora de `pytest tests/`) | 17/17 (100%) | ⚠️ Testado, mas defasado em cobertura de conteúdo — schema não conhece `q:agent`/`team`/`schedule`/`job`/`thread`/`websocket`/`queue`/`action` | Estender schema (Fase 6); considerar um teste que falhe quando uma tag nova não tiver entrada no schema |
