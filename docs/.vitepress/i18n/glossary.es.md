# es glossary (glosario en español)

Terms used in the Spanish pages, so every page says the same thing the same
way. Neutral Latin-American Spanish: `tú` (never `vos` or `vosotros`),
`computadora`, `archivo`, `carpeta`. Not a site page: docs/.vitepress/ is not
published.

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

| English | Español | Note |
|---|---|---|
| component | componente | |
| page | página | |
| action | acción | a `q:action` |
| form | formulario | |
| field | campo | |
| query | consulta | |
| datasource | fuente de datos | |
| migration | migración | |
| database | base de datos | |
| table (database) | tabla | |
| row | fila | |
| flash message | mensaje flash | |
| redirect | redirección / redirigir | |
| session | sesión | |
| scope | ámbito | |
| expression | expresión | |
| databinding | enlace de datos | |
| tag | etiqueta | |
| attribute | atributo | |
| parser | analizador (parser) | "parser" alone is fine after the first time |
| runtime | entorno de ejecución | |
| build chain | cadena de build | |
| front-end framework | framework de front-end | |
| knowledge base | base de conocimiento | |
| agent | agente | |
| tool (of an agent) | herramienta | |
| model / language model | modelo / modelo de lenguaje | |
| embedding | embedding | |
| chunk | fragmento | |
| cite its sources | citar sus fuentes | |
| failure contract | contrato de fallo | |
| tier | nivel | |
| Core | Núcleo | |
| AI (tier) | IA | |
| Experimental | Experimental | |
| Laboratory | Laboratorio | |
| stable | estable | |
| semantic versioning | versionado semántico (semver) | |
| specification (SPEC) | especificación (SPEC) | |
| rule (of the SPEC) | regla | |
| conformance test | prueba de conformidad | |
| test / test suite | prueba / conjunto de pruebas | `quantum test` stays |
| recipe (Cookbook) | receta | the Cookbook is el Recetario |
| release | versión / publicación | |
| changelog | registro de cambios | |
| sponsor | patrocinar / patrocinador | |
| issue (GitHub) | issue | kept in English, as developers write it |
| pull request | pull request | |
| virtual environment | entorno virtual | |
| extra (pip) | extra | |
| terminal / console | terminal / consola | |
| desktop window | ventana de escritorio | |
| deploy | desplegar / despliegue | |
| roadmap | hoja de ruta | |

## Tone

Plain and direct, as the English: short sentences, no marketing words (no
"potente", "revolucionario", "increíble"). Address the reader as `tú`. Keep
the English order of sections and headings so anchors map one to one.

## Machine-translated pages

Until a native speaker reviews a page, it starts with this notice (and links
to its English original):

```md
::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/path/to/english).
:::
```
