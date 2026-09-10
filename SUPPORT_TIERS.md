# Quantum — Níveis de suporte

> Revisado em 2026-09-10 pelas decisões do plano *Núcleo impecável* (autenticação no Core;
> jogos e AS4 ficam no repo como Laboratório).
>
> Decisão original da Fase 0 do `FRAMEWORK_PLAN.md`, tomada em 2026-09-07 com base na auditoria
> funcional (`FULL_AUDIT_2026-09.md`) e nas correções das Fases 1-7 do
> `AUDIT_FIX_PLAN.md`.
>
> Este documento é **política** — o que o projeto promete. O estado real de cada feature
> (roda ou não, hoje) é o `FEATURE_STATUS.md`, que é gerado por execução e não editado à
> mão. Os dois existem porque promessa e realidade divergiram por meses, e essa divergência
> foi o achado central da auditoria.

---

## A frase

> **Quantum — aplicações web declarativas em XML, com IA e RAG embutidos na linguagem.
> Sem build chain, sem JavaScript, sem framework de front-end.**

Se algo não cabe nessa frase, não pertence ao README nem ao pitch. Pode continuar
existindo — em outro nível, ou em outro repo.

## Para quem

Dev solo e times pequenos construindo ferramentas internas, dashboards, painéis
administrativos e aplicações com IA, que não querem uma cadeia de build de front-end.

---

## Os níveis

### Core — o que o framework é

Documentado, testado de ponta a ponta, estável. Quebra aqui é bug crítico. Nenhuma tag
entra sem: exemplo que roda, teste de integração contra o serviço real, página de doc, e
linha no `FEATURE_STATUS.md`.

| Tag | Papel |
|---|---|
| `q:component` | Unidade de composição, com `q:param` / `q:return` |
| `q:set` | Variáveis e escopos (`session.` / `application.` / `request.`) |
| `q:if` | Condicional |
| `q:loop` | Iteração (array, list, range, query) |
| `q:function` | Função reutilizável, com `q:param` / `q:return` |
| `q:query` | SQL parametrizado — `q:param` obrigatório, injeção impossível por construção |
| `q:action` | Handler de formulário (POST/PUT/DELETE), com `q:redirect` e `q:flash` |
| `q:invoke` | Chamada de função, componente ou HTTP |
| `q:data` | Import e transformação de CSV/JSON/XML |
| `q:import` / `q:slot` | Composição de componentes |
| `require_auth` / `require_role` | Autenticação e autorização por componente, sobre o escopo `session` (decisão D4, 2026-09-10). Lacuna aberta: um `.q` ainda não verifica senha sem `q:python` — `AUTH-1` em `tests/conformance/test_known_gaps.py` |

### Diferencial — a razão de existir

Mesmo contrato do Core. É o que o Quantum tem que nenhum outro framework declarativo tem.

| Tag | Papel | Estado verificado (2026-09-07) |
|---|---|---|
| `q:llm` | Completion e chat contra LLM | ✅ validado contra Ollama real |
| `q:knowledge` | Base de conhecimento vetorial (RAG), consultada via `q:query datasource="knowledge:nome"` | ✅ validado: indexação real + busca com score |
| `q:agent` | Agente com loop ReAct e tools declaradas em `.q` | ✅ validado: tool chamada, args coagidos, resposta correta |
| `q:team` | Múltiplos agentes com handoff e contexto compartilhado | ⚠️ wiring corrigido e testado; falta validação end-to-end com modelo capaz |

### Experimental — existe, mas sem promessa

Mantido e funcionando (a maioria foi consertada hoje), porém **fora do README e do pitch**,
sem garantia de estabilidade de API. Sai daqui para o Core quando tiver o mesmo rigor:
exemplo + teste de integração + doc + linha no status.

| Área | Tags |
|---|---|
| Jobs | `q:job`, `q:schedule`, `q:thread` |
| Mensageria | `q:message`, `q:queue`, `q:subscribe`, `q:messageAck`, `q:messageNack`, `q:websocket`, `q:websocket-send`, `q:websocket-close` |
| Serviços | `q:mail`, `q:file`, `q:log`, `q:dump`, `q:persist` |
| Scripting | `q:python`, `q:pyclass`, `q:pyimport` — **desligáveis** via `security.python_scripting` (ver SECURITY.md) |
| Eventos | `q:dispatchEvent` |
| UI / alvos alternativos | namespace `ui:*`, alvo terminal (`qt:`), htmx, islands |

### Laboratório — fica no repo, fora da promessa

Decisão D1/D2 (2026-09-10): estes projetos **ficam no repositório** porque pressionam a
linguagem — é jogando que aparecem features e bugs que o núcleo precisa. Não entram no
pitch nem têm promessa de estabilidade, e o runtime avisa uma vez ao rodar um deles
(`quantum/core/tiers.py`). Os testes deles continuam na suíte principal: uma mudança no
núcleo que quebre um jogo aparece no CI.

| Área | Nota |
|---|---|
| Game engine 2D (`qg:`), codegen Godot, projeto Mario | A regra do `CLAUDE.md` (codegen é a fonte da verdade, nunca editar o output gerado) continua valendo. Mudanças de linguagem que quebrem o Mario migram os fontes `.q` na mesma mudança. |
| `quantum-as4` (compilador MXML/AS4 → JS) | Tem regressão aberta em `test_transpiler_comprehensive.py` |

### Sem nível — decisão pendente

| Tag | Situação |
|---|---|
| `q:decorator` / `q:pydecorator` | Parser e nó AST existem; **nenhum consumidor em lugar nenhum** do runtime. Não é bug de wiring — é uma feature que nunca teve a outra metade. Ou se projeta a aplicação de decorators a `q:function`, ou se remove a tag. Enquanto não se decidir, não deve aparecer em doc alguma. |
| `q:transaction` | Parser exige `datasource` no elemento pai; os exemplos põem só nas `q:query` filhas. Alinhar antes de classificar. |

---

## Como isso não apodrece

O `ROADMAP.md` apodreceu porque era mantido à mão e ninguém verificava. As defesas:

1. **`FEATURE_STATUS.md` é gerado**, por execução real (`DOCS_CONSOLIDATION_PLAN.md`,
   Fase 2).
2. **`manifest.yaml` perde a autoridade** sobre "funciona ou não" — 29 arquivos para manter
   sincronizados à mão foi exatamente o motivo de terem divergido.
3. **Este documento só muda por decisão explícita**, e a mudança é pequena: mover uma tag
   de nível.
