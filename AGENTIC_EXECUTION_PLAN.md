# Quantum — Plano: `agentic_execution` (testar, auditar, implementar)

> Origem: proposta de estender o core agentic do Quantum (`agent`/`team`/`llm`/`job`/`schedule`)
> com execução real de código — nós `sandbox`, `workspace`, `mission` — em vez de manter o
> orquestrador Larva como projeto separado. Este plano nasce de uma investigação que rodou os
> exemplos citados como prova de maturidade e achou 3 de 3 quebrados antes de qualquer chamada
> de LLM. Não é motivo para abandonar a proposta — é motivo para não construir a Fase 2 em cima
> de um chão que ninguém verificou ainda. Datas relativas abaixo assumem início em 2026-09-07.

---

## 0. O que já sabemos (não re-auditar)

| Achado | Local | Evidência |
|---|---|---|
| `q:loop items="..."` sem `type="array"` explícito é classificado como range loop | `src/core/features/loops/src/ast_node.py:49-53` | `python src/cli/runner.py run examples/agent_demo.q` → `Range loop requires 'from' attribute` |
| `AgentNode.validate()` exige `execute` mesmo quando o agente está dentro de um `AgentTeamNode` (que tem seu próprio `execute`) | `src/core/features/agents/src/ast_node.py:361-365` | `run examples/multi_agent_support.q` → `AgentNode requires <q:execute> to run` × 3 |
| `AgentExecutor` chama `services.agent.execute(tool_nodes=, timeout=, exec_context=, runtime=)` — nenhum desses kwargs existe em `AgentService.execute()` | `src/runtime/executors/ai/agent_executor.py:83-97` vs `src/runtime/agent_service.py:188-201` | leitura direta; dispararia `TypeError` se alcançado |
| `TeamExecutor` chama `services.agent.execute_team(...)` — mas `execute_team` é método de `MultiAgentService`, exposto em `services.multi_agent`, nunca em `services.agent` | `src/runtime/executors/ai/team_executor.py:75-80` vs `src/runtime/agent_service.py:1080` vs `src/runtime/service_container.py:120-135` | leitura direta; dispararia `AttributeError` se alcançado |
| `job-queue-example.q` falha no parser antes de chegar no job | — | `run examples/job-queue-example.q` → `Query requires 'name' attribute` |
| Nenhum teste exercita `q:agent`/`q:team` através do executor contra as classes reais | `tests/unit/executors/test_agent_executor.py:40-43` (mock com assinatura inventada), `tests/generated/test_agentdemo.py` (stub gerado, chama funções sem import) | leitura direta |
| Documentação se contradiz: `ROADMAP.md:11,57` diz "AI Agents 100% Complete"; `src/core/features/agents/manifest.yaml:5` diz `status: planned, target_release: Q3 2025` | — | leitura direta |
| `agent_service.py` e os testes que o acompanham entraram num commit-checkpoint (09/fev); `agent_executor.py`/`team_executor.py` e seus testes entraram em outro, 11 dias depois (20/fev). Nunca reconciliados. | `git log --follow -- <arquivo>` | histórico git |

Conclusão que este plano assume: o **loop de raciocínio** (`AgentService.execute()` chamado direto, sem passar pelo executor) é provavelmente sólido — tem teste real contra a classe real. A **ponte entre a tag `.q` e esse loop** é que está quebrada. É um problema de solda, não de motor.

---

## Fase 0 — Testar (meio dia, não mexe em sandbox/workspace)

Objetivo: sair com `agent`, `team`, `job`, `schedule`, `message_queue` rodando de verdade contra
um Ollama real — não "existe o arquivo", não "o manifest diz completo".

1. **Rodar, não ler**, cada um destes contra o runtime local, registrando o erro exato:
   `job-queue-example.q`, `job-schedule-example.q`, `job-thread-example.q`, `message-queue-example.q`.
2. Consertar os 4 bugs da seção 0, nesta ordem (cada um desbloqueia o teste do próximo):
   - `LoopNode`: inferir `loop_type='array'` quando `items` está presente e `type` não foi dado (ou no mínimo corrigir `agent_demo.q` para `type="array"` explícito — mas o bug de fundo no parser vai morder o próximo dev que escrever um loop sem `type`).
   - `AgentNode.validate()`: pular a checagem de `execute` quando o agente é filho de `AgentTeamNode` (precisa de contexto de validação, hoje `validate()` não sabe se está aninhado).
   - `AgentExecutor.execute()`: construir um `tool_executor` real (fecha sobre `exec_context`/`runtime` para rodar o `body` AST de cada `AgentToolNode`) e chamar `AgentService.execute()` com a assinatura real (`timeout_ms=`, `tool_executor=`), removendo `tool_nodes`/`exec_context`/`runtime` como kwargs soltos.
   - `TeamExecutor.execute()`: trocar `services.agent.execute_team` por `services.multi_agent.execute_team`, e alinhar para a assinatura real de `MultiAgentService.execute_team(name, task, entry_agent, context, tool_executor)` — isso implica registrar o time via `create_team()` antes de executar, não só montar um dict `team_config` solto.
3. Corrigir (ou substituir) `tests/unit/executors/test_agent_executor.py` para mockar a assinatura real de `AgentService`/`MultiAgentService`, não uma inventada. Apagar ou reescrever `tests/generated/test_agentdemo.py` — hoje é ruído, não cobertura.
4. Rodar `agent_demo.q` e `multi_agent_support.q` até ver resposta real de LLM (Ollama), não erro de validação.

**Critério de saída:** os 6 exemplos desta fase rodam limpo, com resposta real de LLM, e o teste
que cobre `AgentExecutor`/`TeamExecutor` falha se alguém quebrar a assinatura de novo.

---

## Fase 1 — Auditar (escopo estreito, guiado pela dependência da feature nova — não um sweep geral)

Isto **não** é a "auditoria cara" do framework inteiro (isso já existe, é o `PUBLIC_RELEASE_PLAN.md`,
com P0/P1 próprios). É auditar só o que o `mission_executor` vai efetivamente tocar.

| Item | Pergunta a responder | Como |
|---|---|---|
| `llm_providers.py` | Multi-provider funciona de verdade ou só tem a classe? | Rodar `agent_demo.q` com `provider="ollama"` E com um provider cloud real (`anthropic` ou `openai`), comparando resultado |
| `job_executor` / `schedule_executor` / `thread_executor` | Já coberto pela Fase 0 | — |
| `message_queue_service` / `message_broker` | Fila sustenta o volume de um loop de orquestrador rodando a cada 2min? | Rodar `message-queue-example.q`; checar se há teste de concorrência/reentrância |
| `quantum_jobs.db` | Dá pra reusar como histórico de runs/custo sem tabela nova? | Inspecionar schema atual (`sqlite3 quantum_jobs.db ".schema"`) e comparar com o que `larva.db` precisava |
| Scripting (`q:python`, `q:pyimport`, `q:pyclass`) | Isso já é execução de código in-process sem isolamento — um agente mal-instruído pode chamar `q:python` com `subprocess` livre? | Ler `src/runtime/executors/scripting/python_executor.py`; confirmar se há allowlist de módulos ou se é `exec()` puro |

**Critério de saída:** tabela de duas colunas — "pronto pra reusar sem tocar" vs "precisa de reforço
antes do sandbox/workspace existirem" — sem isso vira uma lista de suposições de novo.

---

## Fase 2 — Mac Mini como servidor de IA

O documento original já previa isto na Fase 1 ("Larva standalone faz o primeiro voo no Mac Mini").
Formalizando o papel dele neste plano:

**Papel proposto (duplo):**
1. Host de inferência Ollama para o tier híbrido do `mission.q` — triagem local barata (o `<agent provider="ollama">` do exemplo do documento original), enquanto o trabalho pesado vai para provider cloud.
2. Host candidato do driver `docker` do `sandbox_service` — os containers de missão não deveriam competir por CPU/RAM com a máquina onde o runtime principal do Quantum roda.

**[A CONFIRMAR — preencher antes de codar a Fase 3]:**
- Modelo/specs do Mac Mini (RAM, cores, Apple Silicon geração) — define quantos containers de sandbox cabem em paralelo e qual tamanho de modelo Ollama é viável localmente.
- Já tem Ollama instalado? Quais modelos puxados?
- Já tem Docker (Docker Desktop ou colima/lima) instalado e funcional em Apple Silicon?
- Endereço/hostname na rede local, e se a máquina onde o Quantum runtime roda enxerga essa rede.
- Se o Mac Mini vai rodar Ollama **e** containers de sandbox **e** o Larva standalone da Fase 1 do documento original ao mesmo tempo — checar se os três cabem sem brigar por recursos, ou se algum desses fica para uma segunda máquina depois.

**Config, quando confirmado:**
`quantum.config.yaml:59-67` hoje tem um único `llm.base_url` apontando para o forge
(`http://10.10.1.40:11434`). Não sobrescrever — `llm_providers.py` já aceita `endpoint=` por
chamada, então o Mac Mini entra como um segundo endpoint Ollama nomeado (ex.: `ollama-macmini`),
selecionável por agente (`<agent provider="ollama" endpoint="{macmini}">`), sem quebrar quem já
usa o forge para outras coisas.

**Critério de saída:** Mac Mini alcançável a partir de onde o runtime roda, respondendo a uma
chamada `q:llm`/`q:agent` real; specs documentadas o suficiente para decidir tamanho do sandbox
Docker na Fase 3.

---

## Fase 3 — Implementar `agentic_execution`

Como no documento original, sem mudanças de arquitetura — só agora construído sobre uma Fase 0/1
verificadas em vez de assumidas:

```
src/core/features/agentic_execution/
  manifest.yaml            # status: experimental, não "complete" — aprendendo com o ROADMAP.md desatualizado
  intentions/primary.intent
  src/ast_node.py          # SandboxNode, WorkspaceNode, MissionNode
  docs/README.md

src/runtime/executors/execution/
  sandbox_executor.py
  workspace_executor.py
  mission_executor.py      # só isto depende de agent/team/job já estarem saudáveis (Fase 0/1)

src/runtime/
  sandbox_service.py       # driver docker migrado de runner.py (Larva)
  workspace_service.py     # migrado de worktrees.py
  vcs_service.py           # migrado de review.py + sources/github.py
```

Guard rails do documento original mantidos:
- Feature atrás de flag em `quantum.config.yaml`, desligada por padrão.
- `driver="local"` recusa rodar sem sandbox explícito.
- Supervisão de processo (timeout, teto de custo, kill de container) fica em Python testável — não vira lógica `.q`.
- **Novo, por causa do que a Fase 0 achou**: todo teste desta feature precisa rodar contra as classes reais de `agent`/`multi_agent`, nunca contra um mock com assinatura inventada — é exatamente esse padrão que produziu os dois bugs de wiring.

**Critério de saída:** `mission_executor` executa uma missão real de ponta a ponta contra um repo
de teste, em `autonomy="draft"`, sem abrir PR de verdade ainda (só reporta o que faria).

---

## Fase 4 — Dogfooding

`larva.q` em `examples/`, trabalhando o backlog do próprio Quantum — vitrine do release público
(`PUBLIC_RELEASE_PLAN.md` já está em andamento; isso vira o exemplo que prova a tese de `agent`/`team`
como primitivas de linguagem, não só o `mario.q`).

---

## Riscos (do documento original, mantidos)

`sandbox` executa código arbitrário em container; `vcs_service` mexe em credencial de git;
`SECURITY.md` acabou de ser escrito. Mitigação: feature experimental, off por padrão, sem PR
automático até a Fase 4 ser validada manualmente algumas vezes.

---

## Ordem de execução

1. Fase 0 (meio dia) — sem isso, nada abaixo tem chão confiável.
2. Fase 1 (paralelo ou logo depois, ~meio dia) — sem Mac Mini ainda, usa o forge.
3. Fase 2 (depende de resposta do usuário sobre specs do Mac Mini) — pode rodar em paralelo com a Fase 1.
4. Fase 3 — só começa com Fase 0 fechada e Fase 1 com a tabela de "pronto vs precisa reforço".
5. Fase 4 — depois que uma missão real funcionar manualmente pelo menos uma vez.
