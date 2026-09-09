# Admin, Flex e Terminal — auditoria por execução e plano

> Escrito em 2026-09-07, a pedido: um plano de ação para finalizar o admin, e
> uma auditoria de como estão funcionando a funcionalidade Flex (`quantum-as4`)
> e a de app tipo terminal (`qt:`).
>
> **Método:** tudo abaixo foi medido rodando, não lendo. Onde eu não consegui
> exercitar, digo que não consegui. Complementa `PRODUCTION_READINESS.md`, que
> propunha *parquear* as três — a evidência aqui refina essa recomendação.

---

## Resumo em três linhas

| Subsistema | Estado real medido | Recomendação |
|---|---|---|
| **Terminal (`qt:`)** | **Funciona melhor que o esperado.** 4/4 exemplos constroem, geram Textual válido e importável | **Promover a Experimental suportado**, não parquear. Falta 1 bug conhecido |
| **Flex (`quantum-as4`)** | **Funciona, com bordas afiadas.** 8/9 exemplos compilam para JS válido; 3 alvos (web/GTK/CLI) | **Repo próprio.** Funciona demais para deletar, dilui demais para ficar |
| **Admin** | **Grande e vivo (29k linhas, 270 rotas), com peças desligadas** | **Finalizar por recorte**, não por completude — plano abaixo |

---

## 1. Terminal (`qt:`) — auditoria

### O que eu rodei

Os 4 exemplos `qt:` do repo (`adventure.q`, `chat-tui.q`, `dashboard.q`,
`filebrowser.q`), via `quantum run`, a partir de um diretório **fora** do repo,
com `PYTHONPATH` apontando para ele.

### Funciona

- **4 de 4 constroem** (`rc=0`) e escrevem o `.py` no diretório de trabalho.
- **O Python gerado é válido e importável.** Cada um define uma classe
  `<nome>App(App)` do Textual; carreguei os módulos e inspecionei as classes.
- **A tradução é fiel.** As 13 tags `qt:` do `adventure.q` viram widgets
  Textual reais com a estrutura preservada:

  | `.q` | Python gerado |
  |---|---|
  | `<qt:layout>` / `<qt:panel>` | `with Horizontal():` / `with Vertical(id=...)` |
  | `<qt:text>` | `yield Static(..., id=...)` |
  | `<qt:tree>` | `yield Tree("Backpack", id="inv-tree")` |
  | `<qt:log>` | `yield RichLog(max_lines=50, ...)` |
  | `<qt:input>` | `yield Input(placeholder=..., id="cmd")` |
  | `<qt:header>` / `<qt:footer>` | `yield Header()` / `yield Footer()` |
  | `<qt:css>` | `CSS = """..."""` |
  | `<qt:keybinding>` | `BINDINGS = [Binding("q", "quit", "Quit")]` |

- **Estado reativo é declarado**: `hp = reactive(100.0)`,
  `cpu_pct = reactive(42.0)`, `current_room = reactive("entrance")`.
- `textual` e `rich` estão instalados; o alvo tem dependência real e declarada
  no cabeçalho do arquivo gerado.

### O bug (bem delimitado)

**Databinding não é ligado ao estado reativo.** O gerador declara a variável
reativa *e* emite o placeholder literal, sem conectar os dois:

```python
hp = reactive(100.0)                                   # declarada
yield Static("[bold red]HP: {hp}/100[/]", id="hp-display")   # literal
```

O usuário vê `HP: {hp}/100` na tela. Acontece em 2 dos 4 exemplos (`{hp}` em
`dungeon-quest`, `{cpu_pct}` em `server-dashboard`). As duas metades existem;
falta o `watch_<var>` / f-string / `.update()` que as liga.

**Correção:** no `terminal_code_generator.py`, quando o conteúdo de um widget
contém `{var}` e `var` é uma reactive declarada, emitir um `watch_var` que
chama `.update()` no widget por id. É trabalho de horas, não de dias.

### Outros achados menores

- O docstring gerado diz `Run: python dungeon_quest.py` (underscore) mas o
  arquivo é `dungeon-quest.py` (hífen). A instrução não funciona copiada.
- O output vai para o **cwd** por padrão. Rodar os exemplos a partir da raiz do
  repo suja o repositório (já mitigado por `.gitignore` nesta sessão, mas a
  causa — default de saída no cwd — permanece).

### Veredito

**Não parquear.** É o subsistema mais saudável dos três: pequena superfície,
dependência única e madura (Textual), tradução fiel, e um único bug conhecido
com correção clara. Merece subir de "Experimental sem promessa" para
"Experimental suportado" assim que o databinding reativo for ligado.

---

## 2. Flex / `quantum-as4` — auditoria

### O que eu rodei

`quantum-mxml build` sobre os 9 exemplos `.mxml`, mais `build-gtk` e
`build-cli`, mais `node --check` no JavaScript gerado.

### Funciona

- **8 de 9 exemplos compilam** para web, produzindo 6 arquivos cada
  (`app.js`, `runtime.js`, `reactive-runtime.js`, HTML, CSS).
- **O JavaScript gerado é sintaticamente válido** — `node --check` passa em
  todos os testados. Não é esqueleto: de 47KB (`hello`) a 150KB
  (`ecommerce-admin`).
- **Três alvos funcionam**: `build` (web), `build-gtk` (desktop) e `build-cli`
  (terminal Python) todos retornam 0 e produzem arquivo.
- ~6.000 linhas de compilador em 30 arquivos, com parser MXML, ponte de AST e
  três backends.

### Os problemas

1. **O comando documentado não existe.** `CLAUDE.md:156` manda rodar
   `python quantum-as4/compiler/codegen.py build app.mxml -o dist` — que morre
   com `ImportError: attempted relative import with no known parent package`.
   O entry point real é `quantum-as4/quantum-mxml`. Quem seguir a doc trava no
   primeiro comando.

2. **Quebra o `pytest` do projeto inteiro.** `pytest.ini` declara
   `testpaths = tests examples quantum-as4`, e
   `quantum-as4/test_direct_compile.py` faz `sys.path.insert(0, 'compiler')` —
   caminho **relativo**, que só resolve com cwd em `quantum-as4/`. Rodando da
   raiz, o import falha e o pytest **aborta a coleta inteira**. É por isso que
   `pytest` sem argumentos não roda nada neste repo.

3. **Os `test_*.py` não são testes.** São 6 scripts de depuração
   (`test_codegen_debug`, `test_direct_compile`, `test_object_literal_bug`,
   `test_parser_bug`, `test_regex_debug`, `test_parse_products`) com código no
   nível do módulo, que executam ao serem importados. Contribuem **0 testes** e
   1 erro de coleta.

4. **Falha de encoding no Windows.** `advanced-components-demo` morre com
   `'charmap' codec can't encode character '\U0001f4c4'` — um emoji no fonte. E
   **deixa o diretório de saída pela metade** (1 arquivo, `app.js` de 0 bytes),
   o que é pior que não gerar nada: parece que compilou.

5. **Dois `BUG_REPORT_*.md` versionados na raiz do subprojeto** documentando
   bugs abertos (`else` blocks, prefixo `this.`) — sinal de que o subprojeto
   tem dívida conhecida e não rastreada no fluxo principal.

### Veredito

**Repo próprio, como `PRODUCTION_READINESS.md` propôs — mas por um motivo
diferente do que eu supunha.** Não é que esteja morto: compila 8 de 9 exemplos
para JS válido em três alvos, o que é bastante. É que ele **tem ritmo próprio,
dívida própria e, hoje, quebra o `pytest` do framework**. Separar serve aos
dois: o as4 ganha CI própria e os `test_*.py` viram testes de verdade; o
framework recupera o `pytest` sem argumentos.

**Antes de separar, três correções de minutos:** apagar/renomear os 6 scripts
de depuração ou movê-los para `scripts/`, corrigir o comando no `CLAUDE.md`, e
tratar o `UnicodeEncodeError` escrevendo com `encoding='utf-8'` explícito.

---

## 3. Admin — plano de finalização

### Estado real medido

- **29.286 linhas** em 35 arquivos Python (FastAPI).
- **270 rotas**, das quais **51 de API** e **15 de UI**.
- Áreas: `projects` (32 rotas — o coração), `resources` (6), `jobs` (2), mais
  dashboard, datasources, docker, users, settings, webhooks.
- **Importa e sobe.**

### O que estava desligado (corrigido nesta sessão, commit `e75ba80`)

1. **Subsistema de Jobs morto.** `job_service.py` empurrava `<repo>/src` no
   `sys.path` e importava `runtime.job_executor` — layout pré-empacotamento. O
   import falhava, o `except` virava um warning, `HAS_JOB_EXECUTOR` ficava
   `False`, e o dashboard reportava **zero jobs para sempre**. Uma linha; o
   dano foi a falha ter virado um log que ninguém lia.

2. **O passo de build do deploy mentia.** Procurava `src/cli/runner.py`
   (removido), caía no ramo "CLI not found, skipping compilation" e **marcava o
   passo como "Build successful" mesmo assim**. Quando o caminho resolvia, ele
   dormia 1 segundo e logava "Build completed: 0 errors, 0 warnings" sem
   invocar nada. Agora: caminho correto, compilador ausente **falha** o passo, e
   o caso ainda simulado é reportado como `skipped — build not implemented`.

### O que ainda falta, e o plano

**A regra que organiza o plano: finalizar por recorte, não por completude.**
29k linhas e 270 rotas não ficam "prontas"; um recorte definido fica. O admin
tem o mesmo problema do framework — superfície larga demais para a energia
disponível.

#### Fase A — Decidir o recorte (dias)

O admin faz hoje: projetos, recursos, jobs, datasources, docker, usuários,
settings, webhooks, deploy. **Escolher o núcleo.** Minha leitura da evidência:
o núcleo é **projetos + datasources + jobs** — é o que tem rotas de verdade
(32+1+2), é o que o framework precisa, e é o que a tela reescrita em `.q`
(`components/admin/projects.q`) já prova ser possível. Docker, webhooks e
deploy-para-nuvem são superfície que não se sustenta.

#### Fase B — Segurança, antes de qualquer exposição (bloqueante)

A auditoria achou, e eu confirmei por leitura:

- `auth_service.py:67` — `JWT_SECRET_KEY` default
  `'quantum-admin-secret-change-in-production'`
- senha de admin default `'admin'`
- `settings_service.py:50` — `secret_key = 'change-me-in-production'`
- CORS `allowed_origins = ['*']`

**Ação:** falhar no boot se qualquer um desses não estiver configurado, em vez
de assumir um default adivinhável. Mesma regra do servidor principal
(corrigida nesta sessão): default seguro, e recusa explícita quando a
configuração é perigosa.

#### Fase C — Verdade nos status (o tema desta sessão)

O passo de build era o caso mais grave, mas o padrão pede varredura: **todo
lugar do admin que reporta sucesso precisa ter feito o trabalho.** Procurar
`_update_step(..., "completed", ...)`, `status: 'success'` e `return True` em
caminhos simulados. Um painel administrativo que mente sobre o estado é pior
que um que não mostra nada.

#### Fase D — Ligar o deploy de verdade, ou removê-lo

O passo de build está honesto agora, mas ainda não compila. Duas saídas
legítimas: invocar `python -m quantum.cli.runner` de verdade, ou remover a área
de deploy do recorte (Fase A). **Não deixar simulado.**

#### Fase E — Reescrever as telas do núcleo em `.q`

A prova de conceito existe: `components/admin/projects.q`, 100 linhas,
substituindo rota FastAPI + fetch em JS + template Jinja. Foi ela que revelou
11 atritos do framework. Reescrever as telas do núcleo (projetos, datasources,
jobs) tem duplo retorno: encolhe o admin e continua sendo o melhor teste de uso
que o framework tem.

#### Fase F — Testes

O admin não aparece na suíte. Um teste de fumaça por área do núcleo — sobe,
bate na rota, confere o corpo — impede que o próximo refactor o desconecte em
silêncio, que é exatamente o que aconteceu com Jobs.

### Sequência

```
A (recorte)  →  B (segurança)  →  C (verdade nos status)  →  F (testes)
                                        ↓
                              D (deploy) e E (telas .q)
```

B é bloqueante para qualquer exposição. C é barato e remove a pior classe de
dano (decisão tomada sobre informação falsa). E é o que paga a longo prazo.

---

## O que isso muda no `PRODUCTION_READINESS.md`

A Fase 0 daquele plano propunha **parquear** game engine e `quantum-as4`, e
tratar terminal como Experimental sem promessa. A evidência refina:

- **`quantum-as4`: parquear confirmado** — mas por ritmo próprio e por quebrar
  o `pytest`, não por estar quebrado. Ele funciona.
- **Terminal: promover, não parquear.** É o subsistema mais saudável, com um
  único bug delimitado.
- **Admin: não é satélite, é produto.** Precisa de plano próprio (acima), e a
  Fase B dele é bloqueante junto com a Fase 1 do plano principal.

---

## Execução das Fases A–F (2026-09-07, mesma sessão)

O que foi feito, com o método do `PRODUCTION_READINESS.md`: reproduzir por
execução, corrigir, travar com teste. Não é um resumo do plano — é o registro
do que rodou.

### Fase A — recorte: **decidido**

Núcleo = **projetos + datasources + jobs**, como a leitura da evidência
indicava. Docker, webhooks e deploy-para-nuvem ficam fora: continuam no código,
sem promessa.

### Fase B — segurança: **feita** (`6553d1e`)

Quatro achados, todos reproduzidos antes de corrigir:

1. **Chave JWT default publicada neste repositório.** Forjei um token de admin
   com ela, sem senha e sem passar pelo login — foi aceito. Agora é aleatória
   por processo; `QUANTUM_ADMIN_ENV=production` recusa subir sem
   `JWT_SECRET_KEY` explícito, e o valor-placeholder é recusado se alguém o
   configurar de propósito.
2. **Senha `admin`/`admin`.** Também aleatória por processo, **impressa no
   boot** — um login que ninguém consegue ler é o mesmo que login nenhum.
3. **A API inteira era aberta.** `/api/projects`, `/api/dashboard`,
   `/api/jobs-list` e toda a família `/api/resources/*` respondiam 200 sem
   token, enquanto duas rotas respondiam 401. Auditar rota a rota foi o que
   produziu esse estado, então a decisão passou a ser **negar por padrão** num
   middleware: hoje **0 rotas** da API respondem sem token, e o fluxo de login
   continua funcionando de ponta a ponta. O htmx não manda `Authorization`
   sozinho — era por isso que fechar rota a rota teria apagado a UI — então o
   shell compartilhado anexa o token a toda requisição htmx e manda para o
   login em caso de 401.
4. **CORS `*` com credenciais.** Agora loopback por padrão,
   `QUANTUM_ADMIN_CORS_ORIGINS` para configurar, `*` recusado em produção.

Um quinto, achado no caminho e pior que os outros: **o webhook do GitHub
falhava aberto**. Sem `GITHUB_WEBHOOK_SECRET` — o estado de qualquer instalação
nova — `verify_github_signature` registrava "skipping verification" e devolvia
`True`, então um POST não assinado com `X-GitHub-Event: push` chegava em
`process_github_push`, **que dispara deploy**. Hoje recusa.

E o `secret_key` de `SecuritySettings` era um chamariz: nada no admin o lia, e
o gerador de settings o escrevia em disco onde parecia ser o lugar de pôr um
segredo. Removido.

### Fase C — verdade nos status: **feita** (`4806b2b`)

A varredura achou o pior caso onde o plano suspeitava: **o pipeline de deploy
inteiro era teatro.** `_step_push` dormia 0,5 s e dizia "Image pushed to
registry"; `_deploy_local` dizia "Local server started on
http://localhost:8000"; `_deploy_docker` dizia "Docker container running";
`_step_health` dizia "Health checks passed: Application is healthy". Cada um
com um comentário "in a real implementation, we would…" invisível da tela, que
mostrava um pipeline verde.

- O **health check virou real** (é um GET; dá para fazer honestamente). Sem URL
  configurada ele diz *skipped*, não *passed*.
- Todo passo que não faz o trabalho **falha** e diz por quê. Um botão de deploy
  que reporta falha é inútil; um que reporta sucesso é perigoso.

No mesmo lote: credenciais de nuvem gravadas em texto puro numa coluna chamada
`credentials_encrypted`; a senha do datasource entregue **cifrada** ao driver
(logo "testar conexão" falhava em todo datasource com senha, culpando a
credencial); botões `alert('... TODO')` na tela de usuários — Adicionar e
Excluir agora funcionam (faltava a rota DELETE), Editar sumiu porque não havia
nada atrás dele.

### Fase D — deploy: **resolvido por honestidade, não por implementação**

O passo de build compila de verdade (`e75ba80`). Push, deploy docker e deploy
ssh **não** — e agora dizem isso em vez de dizer que funcionaram. Implementá-los
de verdade exige build de imagem, que o admin não tem em lugar nenhum; fingir
era a única alternativa e é a que foi removida.

### Fase E — telas em `.q`: **parcial** (`3ed1a80`)

`components/admin/projects.q` já existia; agora existe também
`components/admin/datasources.q`. As duas passaram a ser **executadas** na
suíte contra um banco real com linhas dentro — uma tela vazia renderiza bem e
não prova nada. Falta a de jobs.

### Fase F — testes: **feita**

De zero para **58 testes de admin**, mais 11 das telas `.q`. Cobrem: nenhuma
rota de API respondendo sem token, o login servindo uma página que consegue
logar, nenhuma rota 500, o webhook recusando sem segredo, o deploy não mentindo
e o gerenciamento de usuários funcionando de verdade.
