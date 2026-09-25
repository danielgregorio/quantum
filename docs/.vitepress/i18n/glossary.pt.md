# pt glossary (glossário em português)

Terms used in the Brazilian Portuguese pages, so every page says the same
thing the same way. Brazilian Portuguese (pt-BR): `você` (never `tu` or
`vós`), `arquivo`, `pasta`, `tela`, `computador`, `baixar`. Not a site page:
docs/.vitepress/ is not published.

## Never translated

Keep these exactly as written, in `code` where the English has it:

- Quantum, VitePress, Python, SQLite, PostgreSQL, MySQL, Ollama, PyPI, GitHub,
  pip, npm, JavaScript, HTML, XML, RAG, LLM, SPA, React Native, Godot, CI
- Every tag and namespace: `q:component`, `q:set`, `q:query`, `q:action`,
  `q:llm`, `q:knowledge`, `q:agent`, `ui:*`, `test:expect`… and the prefixes
  `q:`, `ui:`, `qg:`, `qt:`
- Every attribute (`name`, `datasource`, `required`, `minlength`, `flash`…)
- Commands and flags: `quantum run`, `quantum start`, `quantum stop`,
  `quantum test`, `quantum check`, `quantum console`, `quantum desktop`,
  `--port`, `pip install`
- File and folder names: `quantum.config.yaml`, `components/`, `migrations/`,
  `*.test.q`, `.q`, `SPEC.md`, `SUPPORT_TIERS.md`
- Rule IDs: `LOOP-2`, `DB-4`, `IA-6`…
- Code blocks: identical to the English page, comments included (a test
  checks it).
- The tier names are translated (below), but when a sentence quotes the policy
  word itself, add the English in parentheses the first time: Núcleo (Core).

## Terms

| English | Português | Note |
|---|---|---|
| component | componente | |
| page | página | |
| action | ação | a `q:action` |
| form | formulário | |
| field | campo | |
| query | consulta | |
| datasource | fonte de dados | |
| migration | migração | |
| database | banco de dados | |
| table (database) | tabela | |
| row | linha | |
| column | coluna | |
| flash message | mensagem flash | |
| redirect | redirecionamento / redirecionar | |
| session | sessão | |
| scope | escopo | |
| expression | expressão | |
| databinding | databinding | kept, as Brazilian developers say it |
| tag | tag | kept |
| attribute | atributo | |
| parser | parser | kept |
| runtime | runtime | kept |
| build chain | cadeia de build | |
| front-end framework | framework de front-end | |
| knowledge base | base de conhecimento | |
| agent | agente | |
| tool (of an agent) | ferramenta | |
| model / language model | modelo / modelo de linguagem | |
| embedding | embedding | |
| chunk | trecho | |
| cite its sources | citar as fontes | |
| failure contract | contrato de falha | |
| tier | nível | |
| Core | Núcleo | |
| AI (tier) | IA | |
| Experimental | Experimental | |
| Laboratory | Laboratório | |
| stable | estável | |
| semantic versioning | versionamento semântico (semver) | |
| specification (SPEC) | especificação (SPEC) | |
| rule (of the SPEC) | regra | |
| conformance test | teste de conformidade | |
| test / test suite | teste / suíte de testes | `quantum test` stays |
| recipe (Cookbook) | receita | the Cookbook is Receitas (as in the nav) |
| release | versão / lançamento | |
| changelog | registro de mudanças | |
| sponsor | patrocinar / patrocinador | |
| issue (GitHub) | issue | kept in English, as developers write it |
| pull request | pull request | |
| virtual environment | ambiente virtual | |
| extra (pip) | extra | |
| terminal / console | terminal / console | |
| desktop window | janela de desktop | |
| deploy | deploy / publicar | |
| roadmap | roadmap | kept |
| tutorial | tutorial | |
| showcase | vitrine | |

## Tone

Plain and direct, as the English: short sentences, no marketing words (no
"poderoso", "revolucionário", "incrível"). Address the reader as `você`. Keep
the English order of sections and headings so anchors map one to one.

## Machine-translated pages

Until a native speaker reviews a page, it starts with this notice (and links
to its English original):

```md
::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/path/to/english).
:::
```
