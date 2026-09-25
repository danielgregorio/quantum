---
source: stability/index.md
source_hash: 1de73600d71a
---

# Estabilidade

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. A página em inglês
é gerada a partir do `SUPPORT_TIERS.md` e esta tradução pode ficar para trás;
se algo não bater, vale o [original em inglês](/stability/).
:::

O que o Quantum promete, tag por tag. A partir da 1.0, **o Núcleo (Core) e a
IA seguem o versionamento semântico (semver)**: uma versão 1.x não quebra um
programa que usa só esses níveis — o significado deles é fixado pelas regras
da [SPEC](/reference/spec), e uma quebra espera a 2.0. Experimental e
Laboratório não têm essa promessa.

Esta página é a promessa. O que de fato roda hoje é medido na página de
[Status](/status/), e cada mudança está no [registro de mudanças](/changelog/).

## A frase

> **Quantum — aplicações web declarativas em XML, com IA e RAG na própria
> linguagem. Sem cadeia de build, sem JavaScript, sem framework de front-end.**

Se algo não cabe nessa frase, não entra no README nem na apresentação. Pode
continuar existindo — em outro nível, ou em outro repositório.

## Para quem é

Quem desenvolve sozinho e equipes pequenas que fazem ferramentas internas,
dashboards, painéis de administração e aplicações de IA, e não querem uma
cadeia de build de front-end.

---

## Os níveis

### Núcleo (Core) — o que o framework é

Documentado, testado de ponta a ponta, estável. Uma quebra aqui é um bug
crítico. Nenhuma tag entra sem: uma regra no `SPEC.md` com um teste que a
cita, um exemplo que roda, uma página no guia e uma linha no
`FEATURE_STATUS.md`.

| Tag | Papel |
|---|---|
| `q:component` | Unidade de composição, com `q:param` / `q:return` |
| `q:set` | Variáveis e escopos (`session.` / `application.` / `request.`) |
| `q:if` | Condicional (`q:elseif` / `q:else`) |
| `q:loop` | Iteração (array, list, range, query) |
| `q:function` | Função reutilizável, com `q:param` / `q:return` |
| `q:query` | SQL parametrizado — `q:param` obrigatório, injeção impossível por construção; paginação, verificação de esquema (`quantum check`), histórico (DB-11) |
| `q:transaction` | Consultas que confirmam ou desfazem juntas (DB-4) |
| `q:action` | Tratamento de formulário, com `q:redirect` e `q:flash`; as regras dos `q:param` são verificadas no servidor e mostradas ao lado de cada campo |
| `q:invoke` | Chama uma função, um componente ou um serviço HTTP |
| `q:data` | Importa e transforma CSV/JSON/XML |
| `q:import` / `q:slot` | Composição de componentes |
| `q:file` | Uploads em `paths.uploads`, e downloads em que a página decide quem pode baixar (FILE-1, FILE-2) |
| `q:mail` | E-mail pela configuração `mail:`, com um modo de log para desenvolvimento (MAIL-1, MAIL-2) |
| `ui:*` — o conjunto do Núcleo | Telas numa página, listadas na regra UI-7 da SPEC. Desenhadas com o mesmo significado pelo navegador (`quantum start`), pelo console (`quantum console`) e pela janela (`quantum desktop`, a página numa janela local); um mesmo roteiro de paridade roda num navegador de verdade e no console |
| `require_auth` / `require_role` | Autenticação e autorização por componente, sobre o escopo `session` (decisão D4); `hashPassword` / `verifyPassword` nas expressões |

### IA — a razão de o projeto existir

O mesmo contrato do Núcleo, mais um teste ao vivo contra um modelo de verdade
antes de cada versão. É o que o Quantum tem e nenhum outro framework
declarativo tem.

| Tag | Papel | Provado por |
|---|---|---|
| `q:llm` | Completação e chat; `knowledge=` responde a partir de uma base e cita as fontes; `stream="true"` envia a resposta enquanto ela é escrita | IA-1…IA-8, `projects/docs-assistant` |
| `q:knowledge` | Uma base de conhecimento vetorial (RAG) sobre textos, arquivos e consultas | IA-2, IA-6, IA-8, `projects/docs-assistant` |
| `q:agent` | Um agente cujas ferramentas são declaradas em `.q`, com contrato de falha e limite de tempo | IA-4, IA-5, `projects/shop-agent` |

### Experimental — existe, sem promessa

Mantido e funcionando, mas **fora do README e da apresentação**, sem garantia
de estabilidade da API. Passa para o Núcleo com o mesmo rigor: uma regra na
SPEC e seu teste, um exemplo, uma página no guia e uma linha no status.

| Área | Tags |
|---|---|
| Multiagente | `q:team` — ainda sem regra na SPEC e sem aplicação que o prove |
| Jobs | `q:job`, `q:schedule`, `q:thread` |
| Mensageria | `q:message`, `q:queue`, `q:subscribe`, `q:messageAck`, `q:messageNack`, `q:websocket`, `q:websocket-send`, `q:websocket-close` |
| Serviços | `q:log`, `q:dump` |
| Scripting | `q:python`, `q:pyclass`, `q:pyimport` — **desligados por padrão**, ligados com `security.python_scripting` (veja o SECURITY.md) |
| Eventos | `q:dispatchEvent` |
| Decorators | `q:decorator` / `q:pydecorator` — um parser e um nó da AST sem consumidor no runtime; ou os decorators ganham um desenho para `q:function`, ou as tags saem. Sem documentação até lá |
| UI / outros alvos | Elementos `ui:*` fora do conjunto do Núcleo (só no navegador; o console diz que não os desenha); o build avulso de `q:application type="ui"` (`--target html`/`textual`, só o layout, UI-8); o alvo de terminal (`qt:`), htmx, islands |

### Laboratório — fica no repositório, fora da promessa

Decisão D1/D2 (2026-09-10): estes projetos **ficam no repositório** porque
pressionam a linguagem — brincando é que aparecem funcionalidades e bugs de
que o núcleo precisa. Não estão na apresentação e não têm promessa de
estabilidade, e o runtime avisa uma vez quando um deles roda
(`quantum/core/tiers.py`). Os testes deles rodam no CI num job próprio
(`pytest -m laboratory`), obrigatório como o principal, para que uma mudança
no núcleo que quebre um jogo apareça — e um CI vermelho diz na hora qual lado
quebrou.

| Área | Observação |
|---|---|
| Engine de jogos 2D (`qg:`), codegen para Godot | Os jogos em `projects/` e `examples/` são gerados pelo codegen; nunca edite a saída gerada. Mudanças na linguagem que quebram um jogo migram os fontes `.q` dele na mesma mudança |
| `quantum-as4` (compilador MXML/AS4 → JS) | Tem uma regressão aberta em `test_transpiler_comprehensive.py` |
| `quantum run --target mobile` (React Native) | Traduz `q:set`/`q:function` para JavaScript por conta própria — o oposto de "um runtime só". Celulares ficam fora da 1.0. Avisa uma vez (`tiers.warn_ui_target`) |

---

## Como isto não apodrece

O antigo `ROADMAP.md` apodreceu porque era mantido à mão e ninguém o conferia
(ele não existe mais; o [Roadmap](/pt/roadmap/) do site lista só planos, e diz
isso). As defesas:

1. **O `FEATURE_STATUS.md` é gerado**, rodando os exemplos de verdade
   (`scripts/generate-feature-status.py`).
2. **O `manifest.yaml` não tem autoridade** sobre "funciona ou não" — 29
   arquivos sincronizados à mão é exatamente o motivo de terem se desencontrado.
3. **O engine impõe os níveis** (`quantum/core/tiers.py`, testado em
   `tests/unit/test_tiers.py`); esta página e esse arquivo mudam juntos.
4. **Este documento só muda por uma decisão explícita**, e a mudança é
   pequena: mover uma tag de um nível para outro.

## Mudanças para a 1.0

| Mudança | Por quê |
|---|---|
| Os nomes dos níveis estão em inglês: Core, AI, Experimental, Laboratory (eram Core, Diferencial, Experimental, Laboratório) | O repositório é em inglês |
| `q:file`, `q:mail` e `q:transaction` → Núcleo | Cada um tem regras na SPEC com testes (FILE-1/2, MAIL-1/2, DB-4) e uma aplicação no CI que o usa (`projects/helpdesk`, `projects/blog`) |
| `q:team` → Experimental | Sem regra na SPEC e sem aplicação que o prove; o nível de IA promete só o que está provado |
| Conjunto `ui:*` do Núcleo → Núcleo (0.16) | UI-1…UI-14, o roteiro de paridade, três renderizadores |
| `q:decorator` / `q:transaction` deixaram de estar "sem nível" | `q:transaction` ganhou sua regra (DB-4); os decorators são Experimental, com a observação acima |
