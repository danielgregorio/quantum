# Quantum — Plano de Correção (Auditoria 2026-09)

> Baseado em `FULL_AUDIT_2026-09.md`. Fases ordenadas por (1) risco em produção, (2)
> alavancagem/custo de conserto, (3) dependência entre fixes. Cada fase tem critério de
> saída verificável por execução real — nunca "o código parece certo".

---

## Fase 1 — `q:action` / autenticação (produção, não proposta futura) — ✅ CONCLUÍDA (2026-09-07)

Único achado com blast radius de segurança real hoje, não numa feature em desenho.

> **Status:** todos os 5 itens abaixo feitos e validados por execução real (Flask test
> client contra `examples/test-auth-login.q`/`test-auth-protected.q`, com comparação
> antes/depois via `git stash` provando que os testes novos falham no código original e
> passam no corrigido). Achados adicionais no caminho, também corrigidos: (a)
> `session.authenticated` precisa de `type="boolean"` explícito no `q:set` — sem isso vira
> string `"true"` e `AuthService.is_authenticated()` (`is True` estrito) nunca autentica;
> (b) `AuthService.is_session_expired()` exige `session.sessionExpiry` (ISO datetime) e
> falha fechado (sem ele, expirado por padrão) — não existe função de data relativa
> embutida na linguagem (`dateAdd`/`now()` não existem), então isso precisa ser hardcoded
> ou calculado numa `q:function` por enquanto. Suíte completa: 2380 passed / 237 skipped /
> 3 failed (as 3 falhas são pré-existentes e não relacionadas — `game_engine_2d`/
> `smw_polished.q`, confirmado via `git stash`). Testes novos em
> `tests/integration/test_action_auth.py`.

1. `src/runtime/action_handler.py`: parar de reimplementar um mini-interpretador
   (`resolve_expression`, `evaluate_condition` — métodos que nunca existiram). Delegar
   `q:set`/`q:if` ao `ExecutorRegistry` real, o mesmo caminho que já faz `q:set` funcionar
   fora de actions (confirmado funcionando em `test-set-all-scopes.q`).
2. `action_handler.py` / `web_server.py:436`: parar de criar um `ExecutionContext()` novo e
   vazio por action. Passar o contexto da sessão Flask real, e sincronizar de volta
   (mesmo mecanismo que já existe no runtime de renderização, `web_server.py:488`).
3. `action_handler.py:84-87` + `web_server.py:436-439`: parar de devolver `(referrer, 500)`
   como se fosse redirect. Erro em action deve retornar erro visível (500 de verdade, sem
   `Location:` de redirect), não uma resposta ambígua.
4. Escrever os testes que não existem: `q:action` com `q:set`, com `q:if`, um fluxo de
   login completo (POST login → GET rota protegida → deve passar), um fluxo de erro em
   action (deve dar 500 legível, não redirect disfarçado).
5. Reconciliar `forms_actions/manifest.yaml` (`stable`) x `authentication/manifest.yaml`
   (`planned`) x `ROADMAP.md` (`✅ Complete` para ambos) — atualizar os três para o estado
   real pós-fix.

**Critério de saída:** `python src/cli/runner.py <servidor>` real, POST em
`/test-auth-login` com credenciais válidas, GET em `/test-auth-protected` retorna a página
(não 302 para `/login`). Suite de testes novos passando.

---

## Fase 2 — Os dois bugs transversais de alta alavancagem — ✅ CONCLUÍDA (2026-09-07)

> **Status:** os 2 bugs corrigidos, mais um terceiro achado no caminho (mesma causa raiz em
> dois lugares): `loop_parser.py` corrigido (infere `array` quando `items=` presente sem
> `type=`); isso desbloqueou um bug até então inalcançável — `LoopExecutor`/`IfExecutor`
> tentavam executar `TextNode`/`HTMLNode` no corpo via `ExecutorRegistry`, que não tem (nem
> deveria ter) executor para nós só-de-renderização; corrigido espelhando o skip-list que
> `component.py:355-360` já usa no nível de topo. `state_management/ast_node.py` corrigido
> (`'integer'` adicionado a `valid_types`). Validado com `test-data-csv/json/xml-simple.q`
> (antes quebrados, agora `[SUCCESS]`) e `test-query-loop.q`/`test-query-params.q` (passam da
> validação, caem no problema já catalogado de dependência do Admin API). `game_engine_2d`
> deliberadamente fora do escopo desta rodada (a pedido do usuário). Testes novos em
> `tests/unit/test_loop_parser.py`. Suíte completa: 2380 passed / 237 skipped / 3 failed
> (mesmas 3 falhas pré-existentes de sempre, confirmadas via `git stash` — zero regressão).

Consertos baratos, desbloqueiam exemplos em múltiplos clusters de uma vez só.

1. `src/core/parsers/control_flow/loop_parser.py:50` — inferir `loop_type='array'` quando
   `items=` está presente e `type=` não foi dado, em vez de assumir `'range'` sempre.
   Adicionar teste de parser cobrindo "items sem type" (não existe hoje).
2. `src/core/features/state_management/src/ast_node.py:105-106` — adicionar `'integer'` a
   `valid_types`, alinhando com `AgentToolParamNode.valid_types` (agents), que já aceita.
   Conferir se há motivo real pra `'integer'` e `'number'` serem tratados diferente antes
   de só igualar as duas listas (podem ter sido divergentes por design, não por acidente —
   checar histórico/uso antes de assumir bug).

**Critério de saída:** `agent_demo.q`, `test-data-csv/json/xml-simple.q`,
`python-data-processing.q` (bug #1) e `test-query-loop.q`, `test-query-params.q`, qualquer
exemplo `qg:` via `python src/cli/runner.py run` (bug #2) rodam sem erro de validação.

---

## Fase 3 — As 9 pontes executor↔serviço — ✅ CONCLUÍDA (2026-09-07)

> **Status:** 3a/3b/3c feitas e validadas por execução real contra Ollama e serviços reais.
> Achados extras corrigidos no caminho: `AgentNode.validate()` rejeitava agentes dentro de
> `q:team`; `<q:return>` era descartado silenciosamente de TODA `q:function` (ReturnParser
> nunca foi ligado a nenhum dos dois parsers de função); `services.websocket` nunca existiu
> no ServiceContainer; `apscheduler` não estava declarado em lugar nenhum. Um achado ficou
> reclassificado: `q:pydecorator` não é bug de wiring — não existe consumidor nenhum de
> decorators no runtime, então implementar só o executor seria infra especulativa. Fica como
> decisão de design pendente, não como conserto.

Mesmo formato de conserto em todas: alinhar nome de property no `ServiceContainer`, nome
de método, e assinatura de kwargs. Fazer por categoria, não tudo de uma vez, para manter
cada PR revisável.

### 3a — categoria `ai/`
- `agent_executor.py:83-97` → `AgentService.execute()`: remover `tool_nodes`/
  `exec_context`/`runtime` como kwargs soltos; construir um `tool_executor` real (fecha
  sobre `exec_context`/`runtime` pra rodar o `body` AST de cada `AgentToolNode`) e passar
  via `tool_executor=`; `timeout=` → `timeout_ms=`.
- `team_executor.py:75-80` → trocar `services.agent.execute_team` por
  `services.multi_agent.execute_team`; registrar o time via `create_team()` antes de
  executar (a assinatura real é `execute_team(name, task, entry_agent, context,
  tool_executor)`, não um dict solto `team_config`).
- `llm_executor.py:78` → `services.llm.invoke()` não existe; usar `generate()`/`chat()`
  conforme o modo (completion vs chat) real do `LLMService`.
- `knowledge_executor.py:94` → `services.knowledge.create()` não existe; usar
  `index_knowledge()`/`search()`/`rag_query()` conforme a operação.
- `pydecorator`: registrar o executor que falta (parser existe, executor não).
- Reescrever `tests/unit/executors/test_agent_executor.py`,
  `test_llm_executor.py`, `test_knowledge_executor.py` (e o de team) para mockar a
  assinatura real das classes, não uma inventada.

**Critério de saída:** `agent_demo.q`, `multi_agent_support.q`, `llm_demo.q`, `rag.q`,
`quantum-assistant.q` rodam contra o Ollama do forge (`10.10.1.40:11434`) com resposta real.

### 3b — categoria `jobs/`
- `schedule_executor.py:93-105` → `services.scheduler` não existe; usar
  `services.job_executor` (métodos reais: `add_schedule`/`pause_schedule`/
  `resume_schedule`/`run_now`).
- `thread_executor.py:75-83` → `services.threading.run/join/terminate` não existem; usar
  `run_thread`/`join_thread`/`terminate_thread`.
- Reescrever `tests/unit/executors/test_schedule_executor.py` (mocka
  `.schedule/.pause/.resume/.delete`, nomes que não existem) e o de thread.

**Critério de saída:** `job_execution_demo.q`, `job-schedule-example.q`,
`job-thread-example.q` executam sem `AttributeError`.

### 3c — categoria `messaging/`
- `queue_executor.py:88-103` → trocar property `messaging` por `message_queue`; trocar
  `queue_info()` por `get_queue_info()`. É o conserto mais barato do lote.
- `message_executor.py` → mesma troca de property.
- `websocket_executor.py:63-164` → registrar `websocket` como property em
  `ServiceContainer` (hoje `WebSocketService` existe mas nunca foi exposto); alinhar
  `create_connection/send/close` para `register_connection/send_message/remove_connection`.
- Reescrever os testes correspondentes.

**Critério de saída:** `message_queue_demo.q` roda sem erro; um teste manual de
`q:websocket` (conexão + envio + fechamento) completa sem `AttributeError`.

---

## Fase 4 — Segurança de scripting — ✅ CONCLUÍDA (2026-09-07)

> **Status:** allowlist rejeitada com justificativa (os exemplos reais importam json/csv/
> collections/statistics/functools — um allowlist permissivo o bastante não seria fronteira
> nenhuma, e fronteira que parece mais forte do que é, é pior que interruptor honesto).
> Implementado `security.python_scripting` (default true, sem quebrar nada), documentado em
> SECURITY.md e no quantum.config.yaml. É o que `agentic_execution` precisa desligar.

Bloqueador de política, não só de código — decidir antes de implementar:

1. Definir a postura: allowlist de módulos/builtins permitidos (mais trabalho, mais
   permissivo) vs. flag explícita `unsafe="true"` exigida na tag pra liberar `exec()`/
   `eval()` livre (mais simples, nega por padrão) vs. remover o modo dinâmico de geração de
   corpo `q:python` a partir de LLM/agente enquanto não houver sandbox real.
2. Implementar a opção escolhida em `python_executor.py:85,88`, `pyclass_executor.py:51,
   61,72`, `pyimport_executor.py:41`.
3. Teste de regressão de segurança: tentar `import os; os.system(...)` ou
   `subprocess.run(...)` via `q:python` e confirmar que é bloqueado (ou exige o flag
   explícito) por padrão.

**Por que antes da Fase 3 do `AGENTIC_EXECUTION_PLAN.md`:** se um `mission`/`agent` algum
dia usar `q:python` como tool, a fuga do `sandbox_service` planejado já existe aqui — o
sandbox de container é irrelevante enquanto essa porta seguir aberta por padrão.

**Critério de saída:** o teste de regressão do item 3 falha (bloqueia) por padrão, e
existe um jeito documentado e explícito de destravar quando necessário.

---

## Fase 5 — Exemplos e parsers desalinhados (sobras do Cluster A/C)

Cada item aqui é "decidir se o parser regrediu ou o exemplo nunca foi atualizado" e depois
alinhar os dois — não tem bug de wiring por trás, é sintaxe divergente.

1. `q:transaction`: parser exige `datasource` na tag pai (`transaction_parser.py:37-40`);
   exemplos só põem nas `q:query` filhas. Decidir a direção certa e corrigir o outro lado.
2. `q:data`/`q:transform`: parser espera `operation=` direto (`data_parser.py:136-139`);
   exemplos usam `q:compute` aninhado. Mesma decisão.
3. `job-queue-example.q:40`: `q:query` de UPDATE sem `name` — ajustar o exemplo (padrão
   CFML de update sem result set precisa de suporte explícito no parser, ou o exemplo
   precisa de um `name` dummy — verificar qual).
4. `job-thread-example.q:79,84,89`: `q:invoke` fire-and-forget sem `name` — mesma decisão.
5. `message-queue-example.q:203-205`: falta `q:param` num bloco de query — só corrigir o
   exemplo, é inconsistência local, os outros 3 blocos do mesmo arquivo já fazem certo.
6. Bug de raiz do `<` em SQL/atributo lido como abertura de tag XML — já apareceu e foi
   remendado localmente em `q:llm` (devlog 30/jan) e reapareceu em
   `job-schedule-example.q:12`. Consertar na raiz do parser XML (permitir `<` cru dentro de
   corpo de `q:query`/CDATA implícito), não pontualmente de novo.
7. `q:query` sem Quantum Admin de pé: documentar a dependência claramente (README de
   `examples/`, ou mensagem de erro melhor apontando pra `local_datasources` como
   alternativa) — não necessariamente remover a dependência.

**Critério de saída:** os 6 exemplos citados rodam limpo; mensagem de erro de `q:query`
sem Admin API explica a causa em vez de só falhar a conexão.

---

## Fase 6 — Achados pontuais de menor risco

Sem urgência de segurança, mas cada um é a primeira impressão de um novo usuário.

1. `file_uploads`: `file_parser.py:45` default `'makeunique'` → `'makeUnique'` (1 linha).
2. `game_engine_2d`: fazer `python src/cli/runner.py run` funcionar para exemplos `qg:`
   (hoje só funciona via `compile_game.py`, não documentado) — depende da Fase 2 (bug de
   `type="integer"`) estar resolvida primeiro; depois disso, decidir se `compile_game.py`
   vira o caminho oficial documentado ou se sua lógica migra para o `runner.py`.
3. quantum-as4: consertar a regressão e a recorrência achadas em
   `test_transpiler_comprehensive.py` (chamada de método de instância sem `this.`; `.this.`
   duplicado em acesso encadeado) — rodar essa suíte, que já existe, antes de declarar o
   bug de prefixo fechado.
4. quantum-as4: `test_direct_compile.py` (import relativo quebrado); declarar `selenium`
   no `requirements.txt` ou remover a alegação de suite Selenium funcional do `TESTING.md`.
5. `renderer.py:696`: corrigir o comentário que afirma "does NOT use eval()" — a correção
   do `eval()` em si já está rastreada como P0.1 em `PUBLIC_RELEASE_PLAN.md`, não duplicar
   aqui; só a mentira do comentário é escopo desta fase.
6. `quantum_admin`: atualizar contagem de endpoints no README (79 → 235 reais); instalar
   `GitPython` ou avisar na UI quando ausente, em vez de degradar silenciosamente.
7. `quantum-lsp`: estender `quantum_lsp/schema/tags.py` para cobrir `q:agent`, `q:team`,
   `q:schedule`, `q:job`, `q:thread`, `q:websocket`, `q:queue`, `q:action` — hoje sem
   autocomplete/diagnóstico para nada chegado depois de 30/jan. Fazer depois da Fase 3
   (schema deve descrever a interface já corrigida, não a quebrada).
8. Varredura de `manifest.yaml` x `ROADMAP.md` em todas as features tocadas por esta
   auditoria, atualizando status para refletir o estado pós-fix.

---

## Fase 7 — Prevenção — ✅ CONCLUÍDA (2026-09-07)

> **Status:** `tests/unit/test_executor_service_contracts.py` percorre estaticamente todos os
> executores e verifica que cada `self.services.<svc>.<metodo>()` existe na classe real.
> Verificado contra o código pré-fix: acusa as 4 violações de `services.scheduler`. Limitação
> conhecida e deliberada: checa existência do método, não compatibilidade de assinatura — foi
> um mismatch de assinatura (`subscribe(handlers=)`) que escapou dele e só apareceu rodando o
> exemplo. Execução real continua sendo necessária.

O achado central desta auditoria é que **nenhum teste existente pegaria os bugs achados**,
porque os mocks foram escritos contra a mesma interface imaginada que os executores. Sem
isso, qualquer feature nova daqui pra frente pode reintroduzir o mesmo padrão.

1. Um teste de contrato simples: para cada executor registrado, usar `inspect.signature`
   para confirmar que os métodos/kwargs que ele chama em `services.*` existem de fato na
   classe real. Não precisa ser sofisticado — pegar o padrão já visto (nome de método
   errado, property errada) é suficiente para a maioria dos casos.
2. Regra de processo (não código): nenhum executor novo é considerado "pronto" sem rodar
   pelo menos um exemplo `.q` de ponta a ponta contra o serviço real — não só contra um
   mock. Isso já está implícito em [[quantum-verify-dont-trust-docs]] na memória do
   projeto; formalizar como checklist de PR se fizer sentido para o fluxo de trabalho.

---

## Ordem de execução resumida

Fase 1 (segurança em produção) → Fase 2 (2 bugs baratos, alta alavancagem) → Fase 3 (9
pontes, em 3 PRs por categoria) → Fase 4 (política de scripting, bloqueia
`agentic_execution`) → Fase 5 (exemplos/parsers) → Fase 6 (polish) → Fase 7 (prevenção,
pode entrar em paralelo a qualquer momento depois da Fase 3).
