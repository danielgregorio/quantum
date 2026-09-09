# Quantum — Plano de Consolidação de Documentação

> Origem: a auditoria de 2026-09 (`FULL_AUDIT_2026-09.md`) achou `manifest.yaml`,
> `ROADMAP.md` e relatórios internos (`STATUS.md`, `*_TEST_REPORT.md`) se contradizendo
> entre si e com a realidade, repetidamente, em features diferentes. O problema não é um
> documento errado — é a ausência de qualquer mecanismo que force reconciliação entre "o
> que o doc diz" e "o que rodar de verdade mostra". Este plano varre os 170 arquivos `.md`
> do repo, decide o que é referência viva, o que é registro histórico, e o que é status
> obsoleto — e propõe um documento definitivo + uma skill que o mantém honesto por
> construção, não por disciplina manual.

---

## 0. Por que não é só "apagar e reescrever"

Reescrever `ROADMAP.md` à mão produz um `ROADMAP.md` novo que apodrece do mesmo jeito em
3 meses — é exatamente o padrão que a auditoria expôs (o antigo foi atualizado em 08/fev e
já nasceu errado sobre `q:agent` um dia depois). A correção estrutural é: **o documento de
status não pode ser texto solto que alguém edita de memória** — ele precisa ser gerado (ou
pelo menos checado) por uma skill que roda comandos reais e só então escreve o veredito.
Isso é o núcleo deste plano; a limpeza de arquivos antigos é a parte fácil.

---

## 1. Inventário: 170 arquivos `.md`, categorizados

Levantamento completo via `find . -iname "*.md"` (excluindo `node_modules`, `.git`, `dist`,
`__pycache__`, venvs). Categorias:

### A — Fora de escopo (não tocar)

| Área | Contagem | Por quê |
|---|---|---|
| `medium-posts/**` | 23 | Conteúdo editorial (posts de blog), não é documentação técnica do projeto |
| `projects/quantum-rag/data/guides/**` | 8 | Corpus derivado para RAG — deveria ser *gerado* de `docs/guide/`, não mantido à mão; fora do escopo de "documentação do projeto" |
| `.claude/commands/**`, `.github/PULL_REQUEST_TEMPLATE.md` | 9 | Config de tooling, não documentação de produto |
| `vscode-quantum/**`, `benchmarks/**/README.md` | 5 | READMEs de subferramenta, baixo risco, não implicados na auditoria |

### B — Referência viva (manter, verificar acurácia depois — não é este plano)

| Área | Contagem | Nota |
|---|---|---|
| `docs/guide/*`, `docs/api/*`, `docs/examples/*`, `docs/ui/*`, `docs/targets/*`, `docs/tools/*`, `docs/extensibility/*`, `docs/internals/*`, `docs/features/*` | ~65 | O site VitePress público. É a "documentação de uso", categoria diferente do problema achado (que é documentação de *status interno*). Merece uma passada de acurácia própria depois (ex.: `docs/examples/agents.md` provavelmente descreve `q:agent` como se funcionasse) — **não** entra na varredura de arquivamento agora, só é sinalizado |
| `docs/devlog/*` (3 arquivos) | 3 | Registro histórico datado, nunca alega status atual — mantém como está |
| `quantum-as4/README.md`, `quantum-lsp/README.md` | 2 | Não confirmados desatualizados nesta sessão — manter, revisar na Fase 3 (abaixo) |

### C — Arquivar em `docs/archive/` (status/plano obsoleto ou superado)

| Arquivo | Motivo confirmado nesta sessão ou por convenção de nome |
|---|---|
| `ROADMAP.md` | Contradiz `manifest.yaml` e a realidade em múltiplas features (confirmado) |
| `IMPLEMENTATION_STATUS.md`, `IMPLEMENTATION_STRATEGY.md`, `IMPLEMENTATION_SUMMARY.md` | Nome já indica snapshot de um momento passado |
| `TEST_RESULTS.md`, `TEST_QUICK_REF.md`, `REGRESSION_TEST_SUMMARY.md`, `TESTING_STRATEGY.md` | Substituídos pelo dashboard gerado (seção 3) |
| `QHTML_PHASE1_COMPLETE.md`, `QHTML_PHASE1_ARCHITECTURE.md`, `QHTML_RENDERING_OPTIONS.md` | Relatório de fase encerrada |
| `IMPACT_ANALYSIS_QUERY.md`, `MIGRATION_QUERY_FEATURE.md` | Análise pontual de uma migração já feita |
| `INTENT_DRIVEN_ARCHITECTURE.md`, `RECURSIVE_INTENT_SYSTEM.md`, `LLM_INTEGRATION_STRATEGY.md`, `FEATURE_STRUCTURE_SPEC.md`, `FEATURE_WORKFLOW.md` | Specs/propostas de arquitetura — se ainda valem, o conteúdo *técnico* migra para `ARCHITECTURE.md` ou `CLAUDE.md`; a versão solta é arquivada |
| `PILOT_REFACTOR_PLAN.md` | Plano de refactor, não confirmado se concluído — arquivar com nota "status não verificado" |
| `docs/proposals/*` (11 arquivos) | O nome do diretório já diz o que é: propostas pontuais, não referência viva |
| `docs/OPERACAO_GUILHOTINA_REPORT.md`, `docs/PARSER_SIMPLIFICATION_PLAN.md` | Relatórios de operação encerrada — valor histórico, não de referência |
| `docs/SESSION_STATE.md` | Notas de sessão de trabalho (Mario, Fase 18) — é rascunho de trabalho, não deveria nem estar versionado como doc permanente |
| `quantum-as4/STATUS.md`, `quantum-as4/TESTING.md`, `quantum-as4/ADOBE_EXAMPLES_TEST_REPORT.md` | Confirmado nesta sessão: alegam "100%"/"production ready" contra uma amostra que não cobre os casos que quebram (Cluster G) |
| `quantum-as4/BUG_REPORT_ELSE_BLOCKS.md` | Confirmado corrigido — vira entrada de changelog, não bug report ativo |
| `quantum-as4/BUG_REPORT_THIS_PREFIX.md` | Confirmado parcialmente corrigido com regressão nova — mantém como issue ativa até fechar de vez (não arquivar ainda; mover para `AUDIT_FIX_PLAN.md` como item rastreado) |
| `quantum_admin/RESOURCE_MANAGER_PLAN.md`, `IMPLEMENTATION_PLAN.md`, `LOGS_IMPLEMENTATION_PLAN.md` | Confirmado nesta sessão: descrevem como "a fazer" coisas já implementadas e funcionando |
| `quantum_admin/README.md` | Confirmado nesta sessão: 79 vs 235 endpoints reais, porta errada (8001 vs 8000 real), 11 vs 25 modelos — reescrever, não só arquivar |

**Total categoria C: ~35 arquivos** movidos para `docs/archive/` (estrutura de pastas
preservada), mais 2 (`quantum_admin/README.md`, e o conteúdo técnico realocado de
`ARCHITECTURE`-adjacent) que são **reescritos**, não só arquivados.

### D — Manter e corrigir no lugar (não é lixo, só está errado)

| Arquivo | Ação |
|---|---|
| `README.md` (raiz) | Já catalogado como P1.2 em `PUBLIC_RELEASE_PLAN.md` ("completamente desatualizado") — reescrever, não arquivar (é a porta de entrada do projeto) |
| `ARCHITECTURE.md` | Absorve o conteúdo técnico ainda válido de `INTENT_DRIVEN_ARCHITECTURE.md`/`RECURSIVE_INTENT_SYSTEM.md`/`FEATURE_STRUCTURE_SPEC.md` antes destes serem arquivados |
| `CLAUDE.md` | Confirmado como o doc mais confiável do repo nesta sessão inteira — nenhuma mudança estrutural, só referenciar o novo dashboard (seção 3) |
| `PUBLIC_RELEASE_PLAN.md`, `AGENTIC_EXECUTION_PLAN.md`, `AUDIT_FIX_PLAN.md`, `FULL_AUDIT_2026-09.md` | Documentos de trabalho ativo desta e da sessão de 12/06 — **não tocar agora**; cada um se arquiva sozinho quando o trabalho que descreve terminar (ver ciclo de vida, seção 4) |

---

## 2. O documento definitivo: um dashboard gerado, não um texto solto

Nome proposto: **`FEATURE_STATUS.md`** (raiz do repo). Substitui `ROADMAP.md` como fonte
de verdade sobre "o que funciona". Estrutura:

```markdown
# Quantum — Feature Status
> Gerado por `/status-check` em 2026-09-07T14:32:00. Não editar à mão — rode a skill.

| Feature | Tag | Testes | Roda de verdade? | Última verificação | Nota |
|---|---|---|---|---|---|
| agents | q:agent | 48/48 (100%) | ❌ AttributeError em agent_executor.py:83 | 2026-09-07 | Fase 3a AUDIT_FIX_PLAN.md |
| forms_actions | q:action | 4/4 (100%) | ✅ | 2026-09-07 | — |
| ...
```

Regras que tornam isso diferente do `ROADMAP.md` antigo:

1. **Cada linha tem uma data de "última verificação"** e uma coluna "roda de verdade?"
   preenchida por execução real (o mesmo método desta auditoria inteira), nunca copiada do
   `manifest.yaml`.
2. **O cabeçalho do arquivo avisa para não editar à mão** — só a skill (seção 3) regrava.
3. **`manifest.yaml` de cada feature perde a responsabilidade de declarar `status:`**
   como fonte de verdade sobre funcionamento — o campo pode continuar existindo para
   metadados (fase, categoria), mas `FEATURE_STATUS.md` é quem manda sobre "funciona ou
   não". Evita o problema de hoje: 29 arquivos `manifest.yaml` para manter sincronizados
   manualmente é o motivo de terem divergido.
4. **`ROADMAP.md`** vira, depois de arquivado, uma seção curta dentro do próprio
   `FEATURE_STATUS.md` chamada "Próximos passos" — texto livre é aceitável para
   *intenção futura*; o que não pode ser texto livre é *status atual*.

---

## 3. A skill: `/status-check`

Nova skill em `.claude/skills/status-check/` (ou `.claude/commands/status-check.md`,
seguindo a convenção já usada por `docs.md`, `feature.md`, etc. deste repo). Diferente da
skill `docs` existente (que ensina *estilo* de página de guia) — esta audita *veracidade*.

**O que ela faz quando invocada** (`/status-check` ou `/status-check <feature>`):

1. Para a feature (ou todas, se nenhuma for passada): localiza `manifest.yaml`,
   `examples/*.q` relevantes e os arquivos de teste correspondentes em `tests/`.
2. **Roda de verdade**: `python src/cli/runner.py run <exemplo>.q` para pelo menos um
   exemplo por feature, e `pytest <arquivo_de_teste>` para a suíte correspondente.
3. Compara o resultado real contra a última linha registrada em `FEATURE_STATUS.md`.
4. Regrava só as linhas que mudaram, com nova data de verificação.
5. **Nunca aceita `manifest.yaml: status:` como evidência** — se não conseguir rodar nada
   (sem exemplo, sem teste), marca explicitamente "não verificável" em vez de herdar o
   status antigo.
6. Roda como parte do checklist de PR (manual por enquanto — automação em CI é possível
   depois, mas fora do escopo deste plano).

Isso opera sobre o mesmo princípio já salvo em memória do projeto
([[quantum-verify-dont-trust-docs]]): a skill *é* essa regra, encodada como processo em
vez de guidance que alguém pode esquecer de seguir.

**Diferença chave vs. escrever manualmente**: a skill se recusa a marcar algo "✅" sem ter
rodado um comando e visto o resultado nesta invocação — não há caminho para ela copiar um
status antigo sem re-verificar.

---

## 4. Ciclo de vida dos documentos de trabalho ativo

Pra não repetir o problema com os documentos que EU criei nesta sessão:

- `FULL_AUDIT_2026-09.md` — arquiva quando todas as fases de `AUDIT_FIX_PLAN.md`
  fecharem (o conteúdo relevante de longo prazo migra pro `FEATURE_STATUS.md`).
- `AUDIT_FIX_PLAN.md` — arquiva quando a Fase 7 fechar.
- `AGENTIC_EXECUTION_PLAN.md` — arquiva quando a feature `agentic_execution` sair de
  "experimental" no `FEATURE_STATUS.md`.
- `PUBLIC_RELEASE_PLAN.md` — arquiva quando o release público sair (é o marco natural).

Regra geral: **um doc de plano/auditoria tem uma condição de arquivamento escrita nele
desde o nascimento** — não fica "por aí" indefinidamente depois que o trabalho termina.

---

## Fases de execução

### Fase 1 — Gerar o `FEATURE_STATUS.md` inicial
Rodar a skill (ainda a construir) manualmente pela primeira vez, reaproveitando os números
já levantados em `FULL_AUDIT_2026-09.md` (não precisa re-rodar tudo — a auditoria de hoje
já É a primeira verificação real). Critério de saída: arquivo existe, com data de hoje em
toda linha.

### Fase 2 — Construir a skill `/status-check`
Implementar o comando descrito na seção 3. Critério de saída: rodar `/status-check agents`
de verdade, ver o AttributeError confirmado (ou a Fase 3a do `AUDIT_FIX_PLAN.md` já ter
fechado, e então ver ✅) e o arquivo atualizado sozinho.

### Fase 3 — Mover a categoria C para `docs/archive/`
Preservando estrutura de pastas (`docs/archive/ROADMAP.md`,
`docs/archive/quantum-as4/STATUS.md`, etc.). Reescrever (não arquivar) `README.md` da raiz
e `quantum_admin/README.md` com os números reais confirmados nesta sessão.

### Fase 4 — Consolidar conteúdo técnico ainda válido
Migrar as partes de `INTENT_DRIVEN_ARCHITECTURE.md`/`RECURSIVE_INTENT_SYSTEM.md`/
`FEATURE_STRUCTURE_SPEC.md` que ainda descrevem arquitetura real (não status) para
`ARCHITECTURE.md`, antes de arquivar os originais.

### Fase 5 — Passada de acurácia na documentação viva (categoria B)
Escopo separado, maior: verificar se `docs/examples/agents.md`, `docs/api/tags-reference.md`
etc. descrevem tags como funcionando quando na verdade dependem de fixes do
`AUDIT_FIX_PLAN.md` ainda não fechados. Não é destrutivo — é edição de conteúdo, entra
como uma fase própria depois que a Fase 3 do `AUDIT_FIX_PLAN.md` (as 9 pontes) fechar, pra
não documentar duas vezes o mesmo texto.

---

Quer que eu comece pela Fase 1 (gerar o `FEATURE_STATUS.md` a partir do que já temos) ou
pela Fase 3 (mover os ~35 arquivos pra `docs/archive/`)?
