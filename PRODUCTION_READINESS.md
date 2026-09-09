# Quantum — caminho até produção

> Escrito em 2026-09-07, depois da auditoria de 16 dimensões que executou o que auditou
> (resultado em `auditoria` / os achados em `scratchpad/audit_findings.json`) e das correções
> desta sessão. Este documento responde a uma pergunta direta: **como sair de "protótipo largo
> com núcleo bom e borda perigosa" para "pronto para produção".**
>
> Pré-requisito de leitura: `SUPPORT_TIERS.md` (o que é Core / Diferencial / Experimental /
> Parked) e `PUBLIC_RELEASE_PLAN.md` (os P0/P1 de release). Este plano os sequencia.

---

## A moldura, antes de qualquer fase

**"Pronto para produção" não é um marco. É uma propriedade relativa a uma superfície definida.**
O erro mais caro seria tentar deixar as 40 tags registradas prontas ao mesmo tempo. A auditoria
mostrou por quê: várias tags fazem parse e explodem em runtime, features anunciadas não funcionam
de ponta a ponta, e a documentação ensina tags que não existem. Não dá para endurecer tudo isso —
dá para **escolher o que você suporta e fazer aquilo ser à prova de bala**, marcando o resto como
experimental e tirando do caminho de quem chega.

Por isso há **dois marcos**, não um:

| Marco | O que significa | Distância honesta |
|---|---|---|
| **M1 — Core pronto para ferramenta interna** | O Core (14 tags) é seguro, falha fechado, tem teste que pega regressão, e roda atrás de um WSGI de verdade em rede confiável | Semanas de trabalho focado |
| **M2 — Superfície anunciada pronta para exposição pública** | Tudo que o README promete funciona de ponta a ponta, sem crítico conhecido, com contrato de estabilidade | Meses; e talvez não valha para a superfície inteira |

Mirar **M1 primeiro** é o que troca "protótipo" por "usável por outra pessoa" no menor caminho.
O resto do documento é a sequência para chegar em M1 e depois em M2.

**O padrão que todas as fases combatem é o mesmo, e é o achado central da auditoria:
falha silenciosa e falha aberta.** A condição que não resolve virava `True`; a transação que
falhava dizia "rolled back" e perdia o dado; a ação que erra devolve 500 sem uma linha no log.
Não são N bugs independentes — é uma política de erro ausente. Corrigir isso como *classe* vale
mais que corrigir cada instância.

---

## O método (já provado nesta sessão, não se negocia)

Cada correção segue o mesmo ritual, porque foi ele que fez a diferença entre "achei que consertei"
e "consertei":

1. **Reproduzir por execução.** Escrever o `.q`/exploit e rodar. Ler o código e inferir é como os
   9 bugs de ponte executor↔serviço passaram: os testes mockavam uma interface imaginada.
2. **Corrigir.**
3. **Travar com um teste de regressão que FALHA no código anterior.** Se o teste passa nos dois,
   ele não testa nada — foi o caso do teste de injeção que passava no código vulnerável, e do
   `assert status in [200,400,404]` que escondia um 500.
4. **Medir a suíte declarada** (`pytest tests examples`), não `pytest tests/`. E nunca usar
   `git stash` para provar "pré-existência" — ele não enxerga quebra vinda de commit anterior da
   mesma sessão; use `git worktree` num commit-base.

---

## Progresso — execução de 2026-09-07 (83 commits)

Registro do que foi feito de fato, pelo método acima (reproduzir → corrigir →
travar com teste que falha no código antigo). Cada linha tem commit.

| Fase | Feito | Commit |
|---|---|---|
| **0** | Superfície imposta em código: `quantum/core/tiers.py` + aviso único por tag experimental no parser | `f2ccabd` |
| **1** | `migrate up` executava os `.down.sql` (perda de dados) | `103cfa0` |
| **1** | `sanitize_sql` era teatro (bloqueava UNION legítimo, furado por newline); trocado por guarda útil + colapso da cópia divergente do validador | `62201eb` |
| **1/2** | `q:set` increment/decrement corrompia valor (estoque 7−5 = −5); `q:elseif` derrubava o renderer | `c190320` |
| **1/2** | `q:action` descartava quase todo o corpo — **`q:query` dentro de action não fazia nada** | `613b1c9` |
| **1/2** | `require_auth` nunca autenticava (o login do próprio framework gravava `"true"` string); falha de action não logava nada | `56c6052` |
| **1/2** | `q:invoke function=` devolvia None em silêncio (10ª ponte executor↔serviço) | `ee777f8` |
| **3** | O teste de contrato das pontes varria **0 executores** e reportava SKIPPED; agora varre 26 e falha se esvaziar | `a5bccbf` |
| **3** | `pytest` sem argumentos abortava a coleta; os 11 `test_*.py` do as4 eram scripts de depuração com 0 testes | `f49a18e` |
| **4** | As duas metades da pilha de IA apontavam para **servidores Ollama diferentes** | `9be3c48` |
| **5** | Admin: Jobs desconectado pelo refactor; passo de build do deploy reportava sucesso sem compilar | `e75ba80` |
| **6** | `FEATURE_STATUS.md` **gerado por medição**, nunca escrito | `75f7449` |
| — | Auditoria por execução de admin, Flex (`quantum-as4`) e terminal (`qt:`) → `SATELLITES_AUDIT.md` | `94941c5` |

### Segunda leva (os que eu tinha deixado de fora)

| Fase | Feito | Commit |
|---|---|---|
| **1** | `q:file` apagava e escrevia em qualquer lugar do disco — caminho databound sem containment | `4389616` |
| **1/2** | `q:messageAck`/`Nack` sem executor (reentrega infinita com `ack="manual"`); `q:job dispatch` descartando todo `value=` | `3f9e387` |
| **0/2** | Parser aceita o HTML que as pessoas escrevem — atributo booleano, `&` cru, tag vazia aberta. Componentes que não parseiam: **10 → 4** | `a879aec` |
| **1** | `quantum jobs worker start` marcava **toda a fila** como failed no primeiro poll | `c6fd2a8` |
| **2** | `quantum mq` descartava toda mensagem e reportava sucesso | `abeaac9` |
| **5/2** | Config validada no boot (YAML quebrado não cai mais em defaults em silêncio); falha de componente filho agora loga | `2c7dcef` |
| **4** | `q:team` não conseguia fazer handoff — nenhum agente tinha a ferramenta | `abc400a`, `c3a13dd` |
| **2** | `q:websocket` parecia conexão viva: **não existe transporte nenhum** no build | `cd4ead4` |

**Uma regressão minha nesta leva, e como apareceu:** o commit `abc400a` passou
sem eu rodar a suíte completa antes — exatamente o erro que este documento
manda evitar. Um teste existente afirmava `len(tools) == 2` e quebrou. Corrigido
em `c3a13dd`, com o teste reescrito para afirmar o **conjunto** de ferramentas em
vez de uma contagem, que voltaria a ficar obsoleta.

### Terceira leva — fechar o que ficou aberto

| Fase | Feito | Commit |
|---|---|---|
| **4** | `q:websocket` ganhou **transporte de verdade** (cliente `websockets`, loop asyncio próprio): autoConnect abre o socket, `q:websocket-send` escreve no fio, quadros recebidos chegam no `on-message`. 13 testes contra um servidor local | `554e799` |
| **1** | Admin: **credenciais publicadas no próprio código** (chave JWT e senha `admin`) — token forjável sem passar pelo login. Aleatórias por processo; `QUANTUM_ADMIN_ENV=production` recusa subir sem configuração | `6553d1e` |
| **1** | Admin: **a API era aberta**. `/api/projects`, `/api/dashboard`, `/api/jobs-list`, `/api/resources/*` respondiam 200 sem token. Um middleware nega `/api` por padrão; 0 rotas abertas | `6553d1e` |
| **1** | Admin: webhook falhava ABERTO — sem `GITHUB_WEBHOOK_SECRET`, um POST não assinado **dispara deploy** | `6553d1e` |
| **2** | Admin: a **tela de login não conseguia logar** (`{URL_PREFIX}` literal → 404) e dois painéis davam 500. Varredura das 160 rotas GET | `6553d1e` |
| **2** | Admin: o pipeline de deploy dizia "Deployment successful" e "Application is healthy" **sem fazer nada**. Health check virou real; o resto **falha** em vez de mentir | `4806b2b` |
| **2** | Credenciais de nuvem gravadas em texto puro numa coluna chamada `credentials_encrypted`; senha de datasource entregue **cifrada** ao driver | `4806b2b` |
| **2** | `q:param`: `default`, `type`, `min`, `max`, `pattern`, `enum`, `minlength`, `maxlength` eram **decoração** — o parser lia, o runtime descartava | `60eed2e` |
| **2** | `q:python`/`q:class` não rodavam código indentado ("unexpected indent" na linha 2) — ou seja, nenhum bloco real | `776e31e` |
| **2** | `q:file action="upload"` era **inalcançável pela web**: `request.files` nunca entrava no contexto | `5f4299d` |
| **3** | `ComponentRuntime()` sem config não lia `quantum.config.yaml` — todo `q:query` caía na API opcional do admin. **13 das 29 falhas antigas eram isso** | `a766bbd` |
| **2** | `q:function` não era chamável de expressão, e dentro dela **não enxergava os próprios parâmetros** | `caaa2d8` |
| **3** | Restantes das 29 falhas antigas: `q:application` executado como componente, teste negativo contado como falha, teste de tilemap afirmando implementação substituída, `smw_polished.q` que não parseava | `cc0d072` |
| **5** | htmx **vendorizado** (o resolvedor já preferia a cópia local; o arquivo nunca foi adicionado). Broker durável selecionável por `MESSAGE_BROKER_TYPE=sqlite` — antes isso levantava "Unknown adapter type" | `bb8462d` |
| **6** | O **language server não publicava diagnóstico nenhum**, em nenhum arquivo: `TypeError` em toda chamada. Agora reporta tag desconhecida, atributo faltando e XML malformado — conferido contra os 216 `.q` do repo, 0 falso positivo | `49fcc5d` |
| **E** | Segunda tela do admin em `.q` (datasources), e as duas telas agora **executadas** na suíte contra banco real | `3ed1a80` |
| **6** | `level="warn"` era erro de parse. Com isso, **todas** as tags do FEATURE_STATUS.md passam a ter exemplo que parseia: 4 → 0 | `dfe8645` |

**Suíte:** `pytest` (testpaths declarados) — **3.181 passando, 1 falhando**,
contra 2.382 passando / 29 falhando no primeiro commit da sessão. As 29 falhas
antigas foram todas resolvidas ou explicadas. A que sobra é honesta:
`test-ui-components-new.q` usa oito tags `ui:` que nunca foram implementadas
(calendar, carousel, date-picker, slide, step, stepper, toast,
toast-container) — feature que não existe, não bug. Escondê-la seria o tipo
errado de verde. Mais `quantum-lsp`: 17 → 35 testes.

### Os 8 componentes `ui:` — terminados no parser e no html, NAO no resto

`calendar, carousel, date-picker, slide, step, stepper, toast,
toast-container` tinham nó AST e renderização mobile, e nenhum parser — por
isso nada conseguia chegar neles. Parser e html estão feitos e **aprovados**
por revisão adversarial. Textual e desktop foram **reprovados**, com defeitos
reais e reproduzidos. Ficam registrados aqui em vez de serem chamados de
prontos:

**Textual — corrigido.** `show=` do toast virava comentário e o toast
disparava incondicionalmente; `step.completed` era sobrescrito depois do
mount; `step.icon` era descartado. Os três consertados, com 28 testes.

**Desktop — corrigido.** Stepper não-linear apagava o progresso; `completed`
tri-state colapsado; `date-picker` com `format` != ISO mandava texto
formatado ao Python; `calendar` sem id pegava o do popup. Os quatro
consertados, e a regra do `completed` virou uma função só que os três alvos
chamam.

**E um quinto, maior, atrás deles:** `bind=` nunca escreveu de volta no
Python no alvo desktop. `def __set_state` numa classe vira
`_QuantumAPI__set_state` por name mangling e o pywebview só expõe nomes
públicos, então a chamada caía num `console.warn` silencioso — em qualquer
input, não só nos componentes novos.

**Um defeito pré-existente que apareceu no caminho e foi corrigido:**
`TOAST_JS` e `CALENDAR_JS` viviam em strings triplas não-raw, então o Python
comia as barras e o browser recebia `dismiss('' + id + '')` — erro de sintaxe
que derrubava o módulo inteiro. `__quantumToast` e `__quantumCalendar` nunca
existiram em página nenhuma. Corrigido na fonte, com teste sobre o JS emitido.

**O que ainda NÃO foi feito, honestamente:**

- As **oito tags `ui:`** acima. É construção de feature, não correção.
- O broker durável **não é o padrão** — memória continua o default (correto
  para um processo só, errado em qualquer outro), mas agora **avisa** que
  perde mensagem entre processos em vez de ficar calado.
- **Push/deploy de verdade** no admin (docker build, ssh). Hoje esses passos
  falham dizendo que não estão implementados; antes diziam que tinham
  funcionado.
- A varredura completa dos **`except` largos** silenciosos em caminho quente.
- Fase E completa do admin: falta a tela de jobs em `.q`.

---

## Fase 0 — Definir a superfície de produção (decisão, não código)

**A fase de maior alavancagem, e a única que não pode ser pulada.** Sem ela, "pronto" não tem
critério. `SUPPORT_TIERS.md` já rascunhou a classificação; a auditoria dá os dados para fechá-la.

- **Core (14 tags) — o alvo de M1.** `q:component`/`q:param`/`q:return`, `q:set`, `q:if`,
  `q:loop`, `q:function`, `q:query`, `q:action`/`q:redirect`/`q:flash`, escopos, `q:invoke`,
  `q:data`, `q:import`/`q:slot`. Verificado funcionando nesta sessão — mas alguns têm bugs de
  borda listados nas fases seguintes.
- **Diferencial (4 tags) — o alvo de M2, com uma ressalva.** `q:llm`, `q:knowledge`, `q:agent`,
  `q:team`. `SUPPORT_TIERS.md` marca os três primeiros como "validado", mas isso foi **em
  isolamento**; a auditoria encontrou `q:team` sem handoff, `q:knowledge` sem reindexação e a demo
  de RAG renderizando placeholder. **A validação precisa ser refeita end-to-end**, pelos exemplos
  entregues, não por um `.q` de teste feliz. Ver Fase 4.
- **Experimental — sai do README, ganha rótulo.** Jobs, mensageria, `q:mail`/`q:file`, `ui:*`,
  terminal. Continuam no repo, mas nenhuma promessa de estabilidade e nenhuma aparição no material
  que um iniciante lê.
- **Parked — sai do repo do framework.** Game engine (`qg:`/Godot), `quantum-as4`. Ver Fase 5.

**Critério de saída:** um documento de uma página com a lista final, e o README refletindo só
Core + Diferencial. Toda tag fora dessas duas listas emite um aviso claro em runtime ("q:job é
experimental e não é suportado em produção") em vez de fingir que é de primeira classe.

---

## Fase 1 — Zerar os críticos de segurança

O bloco que impede QUALQUER release, e a parte mais avançada — 5 grupos já caíram nesta sessão
(traversal RCE, `q:if` fail-open, transação sem atomicidade, debugger na rede, DoS aritmético).
Restam, da auditoria e do `PUBLIC_RELEASE_PLAN.md`:

1. **Os ~17 críticos ainda não verificados.** Cada um pelo método acima. Priorizar por alcance
   sem autenticação e por perda de dados. Suspeitos de alto impacto que a auditoria levantou e que
   eu ainda não reproduzi: `quantum migrate up` rodando os `.down.sql`; `q:file` sem containment
   de caminho (delete/upload arbitrário); `sanitize_sql` que é teatro (bloqueia UNION legítimo e
   é furado por newline); `q:invoke url=` sem allowlist (SSRF).
2. **Segredos (P0.2).** Rotacionar a API key exposta AGORA, e expurgar do histórico com
   `git filter-repo` **antes** de o repo ficar público — a key continua recuperável mesmo depois
   de deletada do HEAD. E trocar os defaults adivinháveis do `quantum_admin` (JWT
   `change-in-production`, `admin/admin`, CORS `*`) por "falha se não configurado".
3. **Containment como invariante, não caso a caso.** Path traversal foi corrigido no roteador de
   componentes nesta sessão; a mesma checagem precisa valer para `q:file`, `q:import` e qualquer
   caminho derivado de entrada. Escrever isso como uma função única e um teste que varre todos os
   pontos de entrada de caminho.
4. **CSP e escaping do HTML servido.** Confirmar por execução que o renderer escapa toda variável
   (o teste de XSS da auditoria não foi verificado por mim), e servir um `Content-Security-Policy`
   por padrão.

**Critério de saída:** uma rodada de auditoria adversarial (como a desta sessão, mas **rodada até o
fim** — a de hoje perdeu os verificadores no limite de sessão) não encontra nenhum crítico
alcançável. Não "os testes passam" — uma varredura que tenta quebrar e falha.

---

## Fase 2 — Matar a falha silenciosa como classe

O tema. Não é uma lista de bugs; é uma política de erro que não existe. Concretamente:

1. **Nada falha aberto.** A regra já aplicada ao `q:if` (condição não-avaliável = `False`) vira
   invariante testado: toda decisão de controle de fluxo que não pôde ser avaliada é o ramo
   seguro, e é logada.
2. **Nada engole exceção sem logar.** Inventariar as capturas largas em caminho quente (parser,
   executores, renderer, web_server, database) e trocar cada `except: pass`/`return None` por um
   log com contexto. Uma falha de banco não pode virar página em branco sem rastro.
3. **A ponte executor↔serviço grita quando quebra.** O teste de contrato que anda a AST e confirma
   que `self.services.X.Y()` existe (criado na auditoria anterior) precisa apontar para o caminho
   certo — a auditoria achou que ele aponta para `src/runtime/...`, layout pré-empacotamento, então
   não guarda mais nada.
4. **`q:action` que falha loga o motivo.** Hoje devolve 500 dizendo "Check server logs" e o log
   não registra nada (achado da auditoria, não verificado por mim).

**Critério de saída:** um teste de "fail-closed" parametrizado sobre os pontos de decisão, e zero
`except` largo silencioso em `quantum/runtime` e `quantum/core`. A guarda `test_no_reachable_eval`
(criada nesta sessão) é o molde: um teste que impede a *classe* de voltar.

---

## Fase 3 — Fazer a suíte de testes ser capaz de falhar

**A auditoria mostrou que a suíte de 2.7k testes não pega esta classe de bug** — e uma suíte que
não pode falhar é pior que nenhuma, porque dá falsa confiança. Antes de confiar no verde, consertar
a medição:

1. **Mocks que espelham a realidade.** Para cada mock de um serviço, um teste que confirma que o
   método mockado existe na classe real. Foi a causa raiz dos 9 bugs de ponte.
2. **Asserts que afirmam algo.** Varrer testes com `assert True`, sem assert, ou
   `assert x in [200,400,404]`. Os 123 testes `.q` que só checam "não levantou exceção" precisam
   comparar a saída renderizada.
3. **CI que bloqueia.** Hoje `pytest` sem argumentos nem coleta (import quebrado em `quantum-as4`),
   e o lint é `ruff ... || true` (nunca reprova). `pytest tests examples` verde deve ser
   obrigatório num PR, e o teste de contrato também.
4. **A dívida das 29 falhas atuais.** Agrupar por causa: quantas são game engine (Parked, fora de
   escopo) e quantas são Core/Diferencial. As de Core/Diferencial entram como bug bloqueante.

**Critério de saída:** um PR que reintroduz qualquer um dos bugs corrigidos nesta sessão é reprovado
pela CI. Verificável: reverter um fix num branch e ver a CI ficar vermelha.

---

## Fase 4 — O diferencial precisa funcionar de verdade

`q:llm`/`q:knowledge`/`q:agent`/`q:team` são a razão de escolher Quantum. Se `q:team` não faz
handoff e o RAG renderiza `{answer.answer}` literal, a proposta é falsa. Isto é M2, mas é o que
justifica o projeto existir.

- Refazer a validação **end-to-end pelos exemplos entregues** (`examples/rag.q`, os de agente/team),
  contra o Ollama, servidos pelo servidor web — não por um `.q` de teste em isolamento.
- Corrigir o que a auditoria apontou: handoff de time, reindexação de `q:knowledge` quando a fonte
  muda, `maxIterations` vs `max_iterations`, falha de LLM engolida e devolvida como resposta.
- Teste que bate no serviço real (marcado para pular quando Ollama não está disponível), não mock.

**Critério de saída:** cada exemplo de IA do repo roda servido e produz saída real; a tabela de
"✅ validado" do `SUPPORT_TIERS.md` reflete validação end-to-end, com a data e o comando.

---

## Fase 5 — Operabilidade

Um framework em produção precisa de coisas que um protótipo não tem:

1. **WSGI de verdade, e o dev server que se recusa a ser o de produção.** `quantum start` é o
   servidor de desenvolvimento do Flask; produção é gunicorn/uwsgi. O default já é loopback +
   sem debugger (corrigido nesta sessão); falta a receita de deploy oficial e um aviso quando
   alguém sobe o dev server ligado em `0.0.0.0`.
2. **Config validada no boot.** Falhar rápido e claro com config ruim, em vez de explodir no
   primeiro request. `runner.py` não carregava o `quantum.config.yaml` até esta sessão — o mesmo
   cuidado vale para validar o que ele carrega.
3. **Migrações que funcionam.** A auditoria diz que `quantum migrate up` roda os `.down.sql` —
   isso é destruição de dados, tratar como crítico (Fase 1).
4. **Logging estruturado, health/readiness, shutdown gracioso.** O básico de observabilidade.
5. **Empacotamento limpo.** `src/` virou `quantum/` nesta sessão; falta o pacote não despejar
   `quantum_admin`/`quantum-as4`/arquivos de teste no site-packages, e declarar os extras
   (`[ai]`, `[postgres]`) que features anunciadas exigem.
6. **Tirar os Parked do repo do framework.** Game engine e `quantum-as4` para repos próprios;
   `quantum-as4` inclusive quebra o `pytest` hoje.

**Critério de saída:** `pip install` num venv limpo, `gunicorn` servindo o Core, health check
verde, config inválida recusada no boot com mensagem legível.

---

## Fase 6 — Docs que batem com a realidade, e contrato de estabilidade

O que separa "alguém consegue usar" de "alguém aposta um projeto em cima".

1. **`FEATURE_STATUS.md` gerado por execução, nunca escrito à mão** (já desenhado no
   `DOCS_CONSOLIDATION_PLAN.md`). É a garantia de que a tabela de tiers não apodrece. A auditoria
   achou docs ensinando tags que nenhum parser registra (`q:fetch`, 58 de 113 tags `ui:`, caminho
   `python src/cli/runner.py`) — isso some quando a doc é gerada do que roda.
2. **Semver + política de depreciação** para as tags Core: o que muda numa minor, o que exige
   major, quanto tempo uma tag fica deprecada.
3. **Regra de entrada para o Core.** Nenhuma tag entra sem: exemplo que roda, teste de integração
   contra o serviço real, página de doc, e entrada no `FEATURE_STATUS.md`. Essa regra é a lição
   direta das 9 pontes quebradas — elas existiam porque nenhuma dessas quatro coisas era obrigatória.

**Critério de saída:** um estranho segue o quick-start e constrói algo real sem bater numa tag que
não existe.

---

## Sequência e esforço, sem otimismo

```
Fase 0  (decisão)      ──┐
Fase 1  (segurança)      ├─►  M1: Core pronto p/ ferramenta interna em rede confiável
Fase 2  (fail-closed)    │        (Fases 0-3, o caminho mais curto para "usável por outra pessoa")
Fase 3  (testes reais) ──┘
Fase 4  (diferencial)  ──┐
Fase 5  (operabilidade)  ├─►  M2: superfície anunciada pronta p/ exposição pública
Fase 6  (docs+contrato) ──┘
```

- **Fase 0 é dias** e destrava todo o resto — é decisão, não código.
- **Fases 1-3 são o grosso do trabalho de M1** e valem semanas de foco. É onde o dano real mora.
- **Fases 4-6 são M2** e são meses. Para boa parte dos usos (ferramenta interna, dashboard,
  homelab — o público declarado na Fase 0.3 do `FRAMEWORK_PLAN.md`), **M1 já é suficiente** e M2
  pode nem valer a pena para a superfície inteira.

A pergunta estratégica que a Fase 0 responde é: **você quer um framework de nicho pequeno e sólido
(Core + Diferencial, à prova de bala) ou uma plataforma larga e frágil?** A auditoria é o argumento
para a primeira. O caminho até produção é, antes de tudo, o caminho de encolher a promessa até ela
ser verdade — e então mantê-la verdade com teste e CI.
