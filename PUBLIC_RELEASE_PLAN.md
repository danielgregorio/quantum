# Quantum — Auditoria e Plano de Release Público

> Auditoria realizada em 2026-06-12. Objetivo: tornar a linguagem Quantum utilizável pelo público geral.

---

## 1. Estado Atual (Auditoria)

### O que está forte

| Área | Estado |
|------|--------|
| Engine core | 78.684 LOC Python, 30 features, arquitetura modular (ParserRegistry/ExecutorRegistry), código legado removido (Operação Guilhotina) |
| Testes | 2.666 coletados na suíte principal (2.354 passando em ~39s) + 17 no quantum-lsp; ~2.683 no total |
| Documentação | 74 páginas VitePress (guide, api, internals, examples) |
| Exemplos | 220 arquivos .q |
| CI/CD | GitHub Actions: test matrix (3.11/3.12), docker, release, deploy de docs |
| Ecossistema | LSP (quantum-lsp), extensão VSCode, admin panel (FastAPI), compilador AS4/MXML, backend Godot 4 |
| Packaging | pyproject.toml com metadata, extras (dev/db/rag) |

### Bloqueadores críticos (P0) — impedem QUALQUER release público

#### P0.1 — RCE via `eval()` no databinding — ✅ RESOLVIDO (2026-09-07)

> **Resolvido** pela Fase 2.1 do `FRAMEWORK_PLAN.md` (commits `d8db907`..`96aeac9`).
> `quantum/core/expressions.py` avalia via `ast.parse` com whitelist de nós; os dois
> avaliadores hand-rolled foram consolidados em um e deletados (−324 linhas).
> Prova em `tests/unit/test_expression_injection.py` — testes que detectam **execução**
> (objeto-sonda com property que registra leitura), não só o resultado, e que **falham**
> contra o código pré-migração.
>
> **Três coisas que este item não previa e apareceram ao corrigir:**
>
> 1. **`q:data` era pior.** `core/features/data_import/src/runtime.py` interpolava os
>    valores de cada registro importado no texto do filtro e chamava `eval()` **puro** —
>    sem `__builtins__` vazio. Uma aspa simples numa célula de CSV escapava. É a entrada
>    menos confiável do framework e tinha a defesa mais fraca do código.
> 2. **O `eval()` de `component.py` era irrestrito.** O `ExpressionCache` acima dele
>    bloqueia dunders por denylist, mas todo `ValueError` caía num `eval(substituted)` sem
>    globals restritos. A denylist fazia trabalho que o `except` desfazia.
> 3. **O compilador Python-output** (`quantum/compiler/python/runtime.py:80`) tinha a
>    mesma forma. Corrigido junto — agora `{expr}` significa a mesma coisa interpretado ou
>    compilado.
>
> **Ainda aberto, menor:** `quantum/runtime/expression_cache.py:238,282` mantém
> `compile()`+`eval()` com denylist de regex. Agora só é alcançável **atrás** do whitelist
> (medido: nunca resolve nada que o avaliador novo não resolva), e avalia texto de template,
> não dados interpolados. Não é mais P0, mas o módulo é candidato a deleção.
>
> **Também fora do escopo desta correção:** `q:python`/`q:pyclass`
> (`executors/scripting/`) usam `exec`/`eval` por design — é escape hatch de confiança
> total, já documentado no `SECURITY.md`, desligável por config.

~~`src/runtime/expression_cache.py:237,274` e `src/runtime/renderer.py:375,394,741` avaliam
expressões com `eval()` usando `__builtins__` vazio. **Isso NÃO é seguro**: o sandbox é
trivialmente bypassável via traversal de atributos (`().__class__.__mro__[1].__subclasses__()`).
Em um framework web onde databinding pode receber input de usuário, isso é execução remota
de código.~~

#### P0.2 — Secrets commitados no repositório
- `quantum.config.yaml:143` — API key real commitada
- `cookies.txt` rastreado no git (cookies de sessão)
- **Ação**: rotacionar a key AGORA; remover do histórico com `git filter-repo` antes de
  tornar o repo público (a key fica recuperável no histórico mesmo após delete).

#### P0.3 — Sem arquivo LICENSE
`pyproject.toml` declara MIT mas não existe `LICENSE` no repo. Sem licença, ninguém pode
legalmente usar o código. **Ação**: adicionar LICENSE (MIT) na raiz.

#### P0.4 — Higiene do repositório
- `node_modules/` com **1.150 arquivos rastreados** no git
- ~**300 arquivos** de debug/temp rastreados (`debug_*.png`, `test_post*.txt`, `tmp_*`)
- Tarballs de deploy (`*.tar.gz`), bancos `.db`, HTMLs gerados, arquivos com nomes
  corrompidos de path Windows (`C:projetosquantum...`)
- **Ação**: limpeza agressiva da raiz + `.gitignore` reforçado. Um repo público nesse
  estado destrói credibilidade no primeiro clique.

### Alta prioridade (P1) — antes do alpha

#### P1.1 — Pacote pip não instala de forma limpa
- Entry point: `quantum = "src.cli.runner:main"` com `include = ["src*"]` — instala
  pacotes chamados `src.core`, `src.runtime` no site-packages (colisão garantida com
  qualquer outro pacote que faça o mesmo)
- Imports internos (`from core.parser import ...`) só funcionam via hack
  `sys.path.append` em `src/cli/runner.py:23`
- **Ação**: renomear para pacote real `quantum/` (ou usar `package-dir` mapeando
  `src` → `quantum_framework`), corrigir todos os imports, validar com
  `pip install` em venv limpo + smoke test.

#### P1.2 — README completamente desatualizado
Descreve "Initial Runner implementation" e estrutura antiga, enquanto o projeto tem
30 features, IA, websockets e game engine. É a porta de entrada do projeto.

#### P1.3 — Working tree sujo / testes quebrados por arquivos deletados
28 failed + 47 errors apontam para `examples/mario/*.q` e componentes do blog deletados
mas não commitados. **Ação**: resolver o estado do git (commitar deleções + atualizar/
remover os testes correspondentes) até a suíte ficar 100% verde.

#### P1.4 — CI não bloqueia nada
`ruff check ... || true` no ci.yml — lint sempre passa. **Ação**: remover `|| true`,
corrigir os erros de lint existentes, tornar o job obrigatório.

#### P1.5 — Tratamento de erros engolido
Bare `except:` / `except: pass` espalhados pelo runtime (ex.: renderer.py). Para usuários
externos, erros silenciosos são a pior experiência de debugging possível. **Ação**: passada
de revisão trocando por exceções tipadas com mensagens úteis (a linguagem é declarativa —
mensagens de erro são a UX principal).

### Médio prazo (P2) — antes do beta

- **Auditoria de segurança web dedicada**: CSRF nos `q:action`, sanitização de output
  (XSS no databinding renderizado), SQL injection no `q:query`, headers de segurança,
  rate limiting, gestão de sessão
- **237 testes skipped** — revisar o que é dívida vs. intencional
- **Suítes satélite fora do CI**: quantum-lsp (17 testes, passam mas ninguém roda no CI),
  quantum-as4 (coleta pytest quebrada — ImportError em `test_direct_compile.py`; arquivos
  são scripts de debug, não testes), quantum_admin (2 arquivos que pytest não coleta).
  Integrar ao ci.yml ou mover scripts de debug para fora do padrão `test_*.py`
- **Versionamento**: adotar SemVer real (hoje diz 1.0.0 mas status Beta), CHANGELOG.md
- **Comunidade**: CONTRIBUTING.md, CODE_OF_CONDUCT.md, issue/PR templates
- **Raiz do repo**: consolidar os ~25 documentos .md soltos em `docs/`

---

## 2. Plano de Release (fases)

### Fase 0 — Higiene (1–2 semanas)
1. Rotacionar API key exposta (imediato)
2. Resolver working tree: commitar deleções pendentes, corrigir/remover testes órfãos
3. Limpar raiz: remover debug/tmp/tarballs/node_modules do git, reforçar `.gitignore`
4. `git filter-repo` para expurgar secrets e binários do histórico
5. Adicionar LICENSE (MIT)
6. **Critério de saída**: suíte 100% verde, `git status` limpo, zero secrets no histórico

### Fase 1 — Segurança (2–4 semanas)
1. Substituir `eval()` por avaliador AST com whitelist (expression_cache + renderer)
2. Revisar superfícies web: XSS no rendering, CSRF, SQL injection no q:query
3. Passada de bare-except → erros tipados com mensagens claras
4. **Critério de saída**: zero `eval`/`exec` em caminho de dados do usuário; testes de
   regressão de segurança adicionados

### Fase 2 — Empacotamento (1–2 semanas)
1. Refatorar layout do pacote (eliminar hack de sys.path, namespace próprio)
2. Validar `pip install` + `quantum run hello.q` em venv limpo (Windows + Linux)
3. CI bloqueante (lint sem `|| true`, matrix verde obrigatória)
4. Publicar no **TestPyPI** e validar instalação de lá
5. **Critério de saída**: `pip install quantum-framework && quantum run hello.q` funciona
   em máquina virgem

### Fase 3 — Experiência do desenvolvedor (2–3 semanas)
1. Reescrever README: o que é, por que existe, exemplo de 10 linhas, GIF/screenshot
2. "Getting started" de 5 minutos na doc (instalação via pip → primeiro app rodando)
3. Curadoria de exemplos: 10–15 exemplos polidos e testados em CI (os 220 atuais viram
   pasta de testes internos)
4. Playground online (rodar .q no browser) — maior alavanca de adoção; avaliar esforço
5. Publicar extensão VSCode no marketplace (syntax highlight é o mínimo)
6. **Critério de saída**: um dev desconhecido consegue ir de zero a app rodando em 5 min
   só seguindo a doc

### Fase 4 — Alpha público (1 semana)
1. Tornar o repo público no GitHub
2. Publicar `1.0.0a1` no PyPI (ou renumerar para `0.9.0a1` — mais honesto que 1.0)
3. Anúncio controlado: Show HN, r/programming, r/Python, dev.to
4. Canal de feedback: GitHub Discussions + issues templates
5. **Critério de saída**: primeiros usuários externos rodando, pipeline de feedback ativo

### Fase 5 — Estabilização → Beta/1.0 (contínuo)
1. Triagem de bugs reportados, ciclo de release quinzenal
2. Documentar política de estabilidade da linguagem (quais tags são estáveis vs.
   experimentais — ex.: `qg:`/`qt:` marcadas como experimental)
3. Benchmark público vs. alternativas (Flask puro, htmx, etc.)
4. 1.0 quando: 3 meses sem breaking change em tags estáveis + zero P0/P1 abertos

---

## 3. Riscos e decisões em aberto

| Risco/Decisão | Nota |
|---------------|------|
| Escopo enorme (web + games + TUI + IA + desktop) | Para o público, **focar o pitch no web framework**; games/TUI como "experimental". Pitch difuso = adoção zero. |
| Nome `quantum-framework` no PyPI | Verificar disponibilidade/colisões; "quantum" é termo saturado (computação quântica). Considerar nome mais buscável. |
| Assets Nintendo no repo (sprites SMW) | **Remover antes do repo público** — copyright da Nintendo, e eles processam. Substituir exemplos por assets livres (Kenney.nl). |
| Concorrência de mindshare (htmx, Livewire, Hotwire) | Diferencial real do Quantum: full-stack declarativo + IA nativa (q:llm/q:agent). Liderar o marketing por aí. |
