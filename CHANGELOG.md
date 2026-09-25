# Changelog

From 1.0, the Core and AI tiers follow semantic versioning: a 1.x release does
not break a program that uses only them, and a break waits for 2.0.
Experimental and Laboratory may change in any release (`SUPPORT_TIERS.md`).
Before 1.0, minor versions could break compatibility. Every change that can
alter the behaviour of an existing app is listed under **Breaking**.

## Unreleased

### Added

- A translated page records the English page it came from and the hash of its
  text (`source:` / `source_hash:`). When the English changes, the page says
  "this translation may be out of date" with a link to the English, and CI
  lists the stale pages (`scripts/translation-status.py`; `--stamp` after
  updating a translation). `tests/docs/test_translations.py` checks that every
  translation names an English page that exists and is in its language's
  navigation.
- The site speaks four languages: English, and /pt/ (pt-BR), /es/ and
  /zh/ (zh-CN), with a language switcher and each language's interface text;
  the pages are translated next. The top nav is Home · Docs (Guide, Tutorial,
  Reference, SPEC) · Showcase · Blog · Changelog · Status · Sponsor. Search
  splits Chinese into words (it found nothing inside a Chinese sentence), and
  each page carries hreflang alternates and Open Graph tags.

### Documented

- The Blog index, Status and Community pages in Brazilian Portuguese.
  `scripts/generate-site-pages.py` writes the translated Blog index and Status
  page (`LANGS`) around the same posts and the same measured tables, stamped
  with the English page's hash; the nav's Blog and Status links go to the
  translation when there is one.
- The rest of the guide in Brazilian Portuguese: AI, files and mail, data
  import, services, sessions, the admin, project structure and
  `q:application` — every guide page now has a pt version. The pt guide
  pages keep the English heading anchors, so a link to a section works in
  both.
- Roadmap and Community in the top nav, in every language. The Showcase in
  Portuguese, Spanish and Chinese, written by `scripts/generate-showcase.py`
  with the same measured numbers as the English page; the Roadmap and the
  tutorial in Chinese. All machine translated and marked so.
- The core guide in Brazilian Portuguese (/pt/guide/): getting started,
  components, how a page runs, state, loops, conditionals, functions,
  expressions, actions, queries, authentication, UI and testing,
  machine-translated, with the code and its output identical to the English
  and the same heading anchors; the pt guide sidebar has Portuguese labels.
- The core guide in Spanish and Simplified Chinese: Getting Started,
  Components, How a Page Runs, State Management, Loops, Conditionals,
  Functions, Expressions & Databinding, Actions & Forms, Database Queries,
  Authentication, One App, Many Screens and Testing an App — machine
  translated and marked as such. The prose is translated segment by segment
  around the English page's code, which is copied as it is; each heading keeps
  the English anchor, so links to a section work in every language.
- The Cookbook in Spanish (/es/cookbook/) and Simplified Chinese
  (/zh/cookbook/): all 51 recipes, machine translated and marked as such. The
  code and results on each page are the English page's imports of the tested
  files, line for line; the prose follows each language's glossary.
- The repository's front door meets the site's bar. README's Quantum examples
  are files of Cookbook recipes, byte for byte, and its quick start is run as
  shown (`tests/docs/test_readme.py`, which also checks the site and file links
  of README, CONTRIBUTING, SECURITY, SUPPORT_TIERS and the Code of Conduct);
  the deprecated-content check reads those five files too. README's AI
  examples used a model name as if it were a default and an attribute
  (`minRelevance`) its text no longer explained; it now links the Cookbook,
  Tutorial, Reference, Showcase, Stability and Roadmap. CONTRIBUTING pointed to
  Discussions, which are off; SECURITY called 1.0 "experimental" and suggested
  an environment variable nothing reads; SUPPORT_TIERS cited two files that are
  not in the repository.
- The Cookbook in Brazilian Portuguese (/pt/cookbook/), machine-translated:
  the code and the results are the same files the English imports. The
  generator writes each language's Cookbook index (`LANGS` in
  `scripts/generate-cookbook.py`), linking the English page where a recipe is
  not translated yet. All 51 recipes are translated; a test checks that every
  translated page imports the same files as its English page, in order.
- Cookbook, "Screens": a layout that fits the screen, a table edited in
  place, tabs, cards, every kind of field, and the same page in a terminal;
  six tested recipes, two of them also checked in the console
  (`tests/docs/test_cookbook_console.py`).
- Cookbook, "Basics": a first page, variables and expressions, loops,
  conditionals, functions, a page per URL, the query string and reusable
  components with a slot; eight tested recipes.
- Cookbook, "AI": answers with their sources, when the documents do not know
  (`minRelevance`), a streamed answer, an agent over your database, when the
  model fails (`onerror`), sorting messages with JSON answers, and answers
  from a table; seven recipes. In CI they run against a stand-in model server
  (`scripts/generate-cookbook.py`); before a release, against a real one
  (`tests/live_ai/test_cookbook_ai.py`). Their tests check structure, never the
  model's words.
- The CLI and LSP server pages say what exists. The CLI page taught exit
  codes, environment variables and a `quantum pkg uninstall` that do not
  exist, and `quantum start --debug` as debug mode; the LSP page, a
  `pip install quantum-lsp` (it is not on PyPI), rename, code actions,
  options and editor packages the server does not have. The VS Code page no
  longer implies the extension runs the language server. Five old notes
  linked from no menu leave the site: a benchmark nothing reproduces, the
  `q:query` implementation plan and the performance-phase notes.
- The essential pages in Brazilian Portuguese (/pt/): why Quantum,
  installation, quick start, the tutorial, stability, sponsor, the roadmap and
  the 1.0 post, machine-translated until a native speaker reviews them, with a
  glossary (`docs/.vitepress/i18n/glossary.pt.md`) that keeps the terms the same
  on every page.
- Cookbook, "Data & SQL": a query with parameters, a paginated list, search
  as you type, filter and sort, writes that happen together (a transaction
  rolled back when its last write fails), change history, adding a column
  with a migration, reading CSV and JSON, loading a CSV into a table in one
  transaction, and totals computed over a query's result; eleven tested
  recipes.
- Cookbook, "Forms & actions": each error on its field, a refused form that
  keeps what was typed, redirect with a flash (`q:flash` for a warning),
  several forms on one page, a form from the table, edit a row, confirm
  before deleting, numbers and dates, and a choice from a list; nine tested
  recipes.
- Cookbook, "Login & permissions": log in with a hashed password, sign up and
  store a hash, a page for one role only, a guard that redirects (and stops the
  page's actions), and sign out; five tested recipes.
- Every `xml` example of the guide now runs: with the result it shows, or in
  a test that runs the page's code as written (`tests/docs/test_guide_*.py`);
  the docs guard's list of pages that were only parsed is empty. Running them
  fixed what they claimed: the components page said several `q:return`s
  returned a list (the first one ends the component, SPEC RET-1), and the
  home page's example now imports the tested "first test" recipe.
- The site in Spanish (`/es/`, machine translated, reviews welcome): the home,
  Why Quantum, Installation, Quick start, Stability, Sponsor, the Roadmap,
  the tutorial and the "Quantum 1.0" post. Code blocks are the English ones; the terms are in
  `docs/.vitepress/i18n/glossary.es.md`.
- Cookbook recipes: "When the mail server says no" (`onerror="continue"`),
  "Test data with test:given" (and `test:as`) and "Testing what an action
  refuses" (`error=`, `message=`, `flash=`, `table=`). Recipes in a topic
  keep an order (`order:` in the page's front matter).
- Pages that described what does not work are gone: the plugin system
  (nothing loads plugins), the package manager page (pages cannot import a
  component from an installed package; `q:import from=` is a folder under
  `paths.components`), and the HTML, terminal and mobile target pages (what
  is true about them is in the guide's "Standalone builds"). The VS Code
  extension page is generated from its manifest and says how to run it from
  source — it is not on the Marketplace.
- A Stability page (/stability/), generated from SUPPORT_TIERS.md: what 1.0
  promises, tag by tag, and the semver promise for Core and AI.
- Simplified Chinese (zh-CN) for Why Quantum, Installation, Quick start,
  Stability, Support and the "Quantum 1.0" post — machine translated, marked
  as such until a native speaker reviews them. A translated page must show
  the English code, block for block (the docs guard checks it), and the nav
  links to a translation when one exists. The zh glossary is in
  docs/.vitepress/i18n/glossary.zh.md.
- The site no longer publishes the 15 hand-written example and feature pages
  (`docs/examples/*`, `docs/features/*`) whose code did not work with 1.0: they
  taught removed attributes (`persist=`, `maxSize=`, `cache=`) and tags that
  never existed (`q:try`). The Cookbook, the Showcase and the tutorial replace
  them; the files stay in the repository to be rewritten as recipes.
- `tests/docs/test_no_deprecated_content.py`: a published page that shows
  something removed or renamed in the changelog (a tag, an attribute, a CLI
  command, a tier name, a default) as current fails CI. Two pages were fixed:
  the UI guide named `quantum new`, and the CLI reference a retired tier name.
- The hand-written `ui:` component pages (docs/ui/) are gone: they taught
  components that do not exist. The generated [UI tags](/reference/ui)
  reference and the "One App, Many Screens" guide replace them. The Cookbook
  is in the Docs menu in all four languages.
- Tutorial, "Build the tasks app": from `pip install` to the app in
  `projects/tarefas`, in English, in eight steps (validated forms, finish and
  delete, a filter, a table that sorts and edits itself, an edit page with
  history, a `quantum test` suite). Each step's code is built and run as shown
  by `tests/docs/test_tutorial_tasks_app.py`, and the finished app is checked
  against `projects/tarefas`, tag by tag.
- Showcase: the seven proving apps with a screenshot of each running
  (`scripts/showcase-screenshots.py`, the AI apps on a stand-in model server),
  what it demonstrates, the SPEC rules it cites, its size, its tests and its
  source. The numbers are measured by `scripts/generate-showcase.py`, and
  `tests/docs/test_showcase.py` fails when the page and the apps disagree.
- The Cookbook: short recipes for one task each. A recipe is a small app in
  `examples/cookbook/` with a `quantum test` suite; its page imports the tested
  files, and what it shows as a result is written by running it
  (`scripts/generate-cookbook.py`). The first two: a first test with
  `quantum test`, and mail in development with `host: log`.
- Quantum code on the site is tested: CI fails on an `xml` block that is not a
  run guide example, a parsed guide or generated-reference example, or on a
  page marked "Under review"; a `quantum.config.yaml` snippet must load
  without errors or warnings. Two snippets taught keys that do not exist.
- Every `xml` example on the site is checked by the real parser in CI
  (tests/docs/test_docs_xml_blocks.py); the guide's examples with a result
  are also run. 121 of 607 failed: the guide's are fixed, the editor
  illustrations are plain text, and 22 hand-written pages that document tags
  that do not exist (the `ui:` component pages, UI features, some example and
  target pages) say "Under review" at the top until tested examples replace
  them.
- The site has a changelog (one page per version, with stable anchors), a
  status page ("what really works today", from FEATURE_STATUS.md), a blog
  with an RSS feed and the "Quantum 1.0" post, a support page and a community
  page. `scripts/generate-site-pages.py` builds the derived pages, and CI fails
  if they are stale.
- The site has a Reference generated from the code (`docs/reference/`,
  `scripts/generate-reference.py`): the Core and AI tags with every attribute,
  type, value, default and the rules that specify them; the expression
  functions; the command line; the configuration keys; the `ui:*` tags, Core
  (UI-7) and Experimental apart, with every attribute the UI parser reads;
  and the SPEC with an anchor per rule (`reference/spec#EXPR-14`) that lists
  the entries citing it. A test fails when a committed page differs from what
  the generator writes. It replaces the hand-written `api/tags-reference`,
  `api/attributes-reference` and `api/ui-reference` pages.
- The site has a Roadmap (`roadmap/`): what 1.0 promises, and what is next,
  each item with its status (planned, in design, in progress) and no dates.

### Fixed

- Two pages with an in-memory `q:knowledge` of the same name and different
  sources deleted each other's index: the other page's search failed with
  chromadb's "Collection [...] does not exist", or — at the wrong moment —
  found nothing, which reads as an honest "I don't know". In-memory bases are
  now separate by sources as well as name (IA-2), and a base that was built
  with chunks and has none when searched is an error, never `found` false
  (IA-6). The three most recently built in-memory versions of each base are
  kept; older ones are dropped.

- `python -m quantum.cli.runner` — the installation guide's way to run
  `quantum` without the script on `PATH` — no longer prints a
  `RuntimeWarning` before every command. `quantum start --debug` says what it
  does: it prints the traceback when the server fails to start; debug mode is
  `server.debug` in `quantum.config.yaml`.
- A `q:query` inside a `q:loop` or a `q:if` of a `q:transaction datasource="…"`
  takes the transaction's datasource, like one directly inside it (DB-4); it
  had to repeat `datasource=`, or the page did not parse.
- `q:set name="cart"` is local even when the session has a `cart` (SET-3,
  EXPR-11). It used to overwrite `session.cart` and leave `cart` undefined, so
  the page showed `{len(cart)}` as written.
- `q:set name="session.cart" operation="append"` starts a list when the key
  does not exist yet (SET-3). It was refused as "non-array": a missing scope
  key reads as `''`.
- A page's extracted stylesheet and script (`static/styles-<hash>.css`) are
  written whole or not at all. Written in place, a second request during the
  write linked the file while it was still empty or partial, and its browser
  got an unstyled page, cached under a name that never changes.
- `q:loop type="range"` takes expressions in `from`, `to` and `step`, like any
  other `{...}` attribute (LOOP-5): `to="{count}"` was read as the text
  "{count}" — an error in a statement, zero rows in markup — and `step="{n}"`
  became 1. A bound that is not a whole number is now an error that names it,
  in markup too, where it used to draw zero rows.
- `q:param type="date"` on an action is checked on the server: `2026-02-30`
  or `tomorrow` is refused on its field (ACT-2). Only the browser's date
  input checked it before, and any text reached the action.
- A `q:param` `default=` on an action has the param's type (ACT-2). It was
  used as text, so `type="boolean" default="false"` gave `"false"`, which is
  true: an unchecked box read as checked.
- `quantum run --target desktop` is no longer offered: the command line says
  the target was removed and points to `quantum desktop` (UI-8). It used to
  accept the choice and fail later, in the build.

## 1.0.0

Quantum 1.0: **declarative web applications in XML, with AI and RAG built into
the language. No build chain, no JavaScript, no front-end framework.**

The road from the first public release ([0.9.0](#090)) to here was mostly
about making that sentence true, and only that sentence:

- **What is promised is written down.** `SUPPORT_TIERS.md` splits the
  language into Core (the web framework: components, state, conditions,
  loops, functions, parameterised queries and transactions, actions and
  forms, composition, files, mail, the Core set of `ui:*`, authentication),
  AI (`q:llm`, `q:knowledge`, `q:agent`), Experimental and Laboratory, and the
  engine enforces it: a tag outside Core and AI warns once when it runs
  ([0.10.0](#0100), [0.21.0](#0210)).
- **What a program means is specified.** `SPEC.md` states the Core and AI as
  rules with IDs, frozen at 1.0, and every rule is cited by a conformance
  test that fails if the rule and the runtime disagree
  (`tests/conformance/`, with `test_spec_ids.py` checking both directions).
  Decisions that used to be silent — a missing name, a failed expression, a
  missing key, an attribute that did nothing — are errors that say where
  they are ([0.11.0](#0110) through [1.0](#10-changes-since-0220)).
- **What is claimed is run.** Apps in the repository prove the tiers:
  `projects/tarefas` (the UI engine), `projects/blog` and `projects/helpdesk`
  (Core, files and mail), `projects/bank-transfer` (`q:transaction`),
  `projects/docs-assistant` and `projects/shop-agent` (AI). **`quantum test`**
  ([0.22.0](#0220)) tests an app in its own language, on a fresh database
  built from its migrations; the apps' suites run in CI.
  `FEATURE_STATUS.md` is generated by executing every example, never written
  by hand.
- **AI you can build on.** Answers cite the chunks they came from and say
  when they are grounded, a relevance floor keeps the model from answering
  from nothing, answers can stream, and every AI tag has a failure contract
  (`onerror`, time budgets) instead of an exception in the page
  ([0.20.0](#0200), [0.22.0](#0220)).
- **One page, three renderers.** The same `.q` page with `ui:*` is drawn by
  the browser (`quantum start`), the terminal (`quantum console`) and a
  desktop window (`quantum desktop`), with forms that know their action's
  rules, tables from data and a declared responsive layout ([0.15.0](#0150)
  through [0.18.0](#0180)).
- **Tools around the language.** `quantum check` (pages, SQL and query
  fields against the database), `migrate plan` from a `schema.sql`, change
  history, the `/_dev` panel, errors that point to the line
  ([0.17.0](#0170), [0.19.0](#0190)).
- **In English.** Code, messages, tests, the SPEC and the documentation.

The changes since [0.22.0](#0220) — released as part of 1.0, with no 0.23
of their own — are below.

### 1.0: changes since 0.22.0

#### Added

- `get(x, key, default)` in expressions reads a key that may be missing, or a
  list index that may be out of range, and gives `default` (`null` when left
  out) (EXPR-16).
- `quantum start --hot-reload` (and `--hot-reload-port`): the open pages
  reload when a component or static file is saved, CSS changes restyle
  without reloading, and a `.q` that no longer parses shows its error on the
  page (DEV-4). The watcher, the WebSocket and the page script existed, but
  no command started them.
- `random()`, `random(a, b)`, `chance(p)` and `pick(list)` in expressions
  (EXPR-15).
- The HTML a `.q` accepts is a rule (PARSE-4): boolean attributes, a bare
  `&`, void elements left open, `<` inside a quoted attribute value and named
  HTML entities.

- CI checks the game projects (snake, tictactoe, kenney-platformer)
  build to valid JavaScript, serve their game and are committed up to date
  (Laboratory job).

#### Breaking

- Laboratory (2D game engine and Godot codegen): the game names are neutral.
  A game now writes `death-sequence="classic"`, calls `game.setPatrolAI`, and
  uses the Godot codegen's tags `item_block` and `bonus_coin`, its HUD counter
  `bonus_coins`, its sound trigger `player-died` and its event
  `item-block-hit`; the world map moves the sprite `id="player"`. The 0.22
  names for these are no longer accepted. Behaviour is otherwise the same; the
  games in the repository were migrated and rebuilt.
- Admin: `GET /datasources/{id}/logs` answers failures with an HTTP status and
  a `detail` instead of 200 and an `error` key: 404 for an unknown datasource or
  a container that no longer exists, 409 for a datasource with no container,
  503 when Docker is not available or does not answer. `?tail=` is unchanged;
  the datasource logs dialog reads the status.
- `d['missing']` on an object without that key is an error that names the key
  and suggests a similar one, as `d.missing` already was (EXPR-16, was G19);
  it used to be `null`, so a misspelt key rendered nothing. Read an optional
  key with `get(d, 'key', default)` or test it with `'key' in d`.
- `skip_rows` on `q:data` skips the first lines of the file, before the header,
  as the name says; it used to read the first line as the header and then drop
  data rows (DATA-1).
- Attributes that were accepted and did nothing are parse errors that say so
  (PARSE-3): `model` on `q:knowledge` (the model is chosen on `q:llm`, IA-2),
  `unique` on `q:set` (use `operation="unique"`), every attribute of `q:column`
  but `name` and `type` (`required`, `default`, `validate`, `pattern`, `min`,
  `max`, `minlength`, `maxlength`, `range`, `enum`; filter rows with
  `q:transform`), and `q:flash` outside a `q:action` (ACT-3).
- `in` compares like `==` (EXPR-14): `'5' in [5]` and `5 in ['5']` are true
  — a value from a form now finds its number in a list. `in` on something that
  is not a list, an object or a text is an error.
- `q:set` without `type` keeps the type of a value that is exactly one
  expression, like `q:return` and props (SET-5): `value="{[1, 2]}"` stores the
  list, `value="{len(x)}"` the number, `value="{dateAdd('h', 8)}"` the date.
  It used to store text, so `len()` counted characters and `{n + 1}` on a
  stored number failed. Text with several parts (`"{n} items"`) and literals
  (`"007"`) are still text. To keep the old behaviour, write `type="string"`
  — the blog's and the admin's login pages now do, for the session's expiry.
- A value outside an attribute's list is a parse error with the line
  (PARSE-5): `q:set` `type`, `operation`, `scope` and `validate` (`date`,
  `datetime`, `struct` and `null` were accepted as `q:set` types and did
  nothing); `q:loop` `type`;
  `q:param` `type` (inside `q:query` only the types the query understands —
  `number` there is now reported where it is written, it failed when the query
  ran); `q:invoke` `method` and `authType`. An unknown `authType` used to send
  the request with no credentials; an unknown form-field type was plain text.
- `q:loop items=` over something that is not a list is an error (LOOP-6), in
  a statement and in markup, like a `ui:table` source: `items="{5}"` looped
  once over `"5"`, and in markup a missing value drew zero rows. Give a value
  that may not exist yet a list first: `<q:set name="session.cart"
  type="array" value="{session.cart}" default="[]"/>`.
- `q:invoke responseFormat="json"` on a response that is not JSON is a
  failure (INV-2), with the Content-Type and the start of the body; it used to
  succeed with `{"error", "text"}` as the value.

#### Removed

- `quantum deploy` and `quantum apps`: they talked to a deploy service that was
  never published, so for anyone else they could only fail. Serve an app with
  `quantum start` behind your own server (`DEPLOYMENT.md`).
- The examples built on third-party game art that cannot be redistributed; the
  games that remain use the Kenney assets (CC0).
- The Codecov upload from CI: it needed a repository token and was failing
  (429) without one; the coverage floor is enforced in CI by
  `coverage report --fail-under`.
- The admin's deploy feature, which lived only in the legacy FastAPI backend
  (`quantum_admin/backend`; the `.q` admin that ships never had it) and deployed
  nothing real: DeployService, the deploy pipeline with versions and rollback,
  the per-project CI/CD retry, auto-deploy on a webhook push, the cloud
  integrations (AWS, Kubernetes, Azure, GCP), the deploy-only environment fields
  and the deploy screens. The generic Docker features for datasources stay;
  webhooks still record events; a `global.yaml` with a `deployment:` block and
  an admin database with deploy columns still load.
- `projects/quantum-landing`: a marketing page that promised what does not
  ship (version 1.0.0, one-command deploy, the game engine as a feature) and
  linked to demos that no longer exist.
- `projects/llm-demo`: an LLM chat superseded by `projects/docs-assistant`;
  its script inserted the server's reply into the page with `innerHTML`
  (XSS).
- `projects/quantum-rag`: a RAG demo over a stale copy of the guide,
  superseded by `projects/docs-assistant`.
- `projects/quantum-fighter`: only a prebuilt `game.html`, with no `.q`
  source to build it from.
- `projects/quantum-tower` and its copy `examples/tower_defense.q`: the game
  called runtime functions that do not
  exist (`scheduleOnce`, `createSprite`, `attachBehavior`, `removeClickable`,
  `clickedSprite`), so no wave came and no tower could be built, and eight of
  its images and sounds were never committed.

#### Fixed

- The admin's pinned stack is current: fastapi 0.109 (January 2024) -> 0.141,
  with starlette 1.x, pydantic 2.13, pydantic-settings 2.15, uvicorn 0.53,
  httpx 0.28 and websockets 16 (uvicorn's `standard` extra needs >= 13). CI
  had been testing a different admin than the one developers run. Starlette
  1.x's TestClient uses `httpx2` (pinned alongside; the admin itself still
  calls `httpx`), and the pytest filter for the old Starlette's anyio
  deprecation is gone: 0 warnings without it.
- `quantum console`: after a pause in a search-as-you-type field, the redrawn
  field got the focus with its text selected, so the next key replaced what
  had been typed ("b", pause, "a" searched "a"). It keeps the text, with the
  cursor at the end (UI-12). The console tests wait for the search of what
  was typed, not for a page load; the browser test waits for the URL of the
  whole text.
- The editor schemas offer the values the parser accepts: `q:param type`
  listed `datetime` for every param (only a `q:query`'s takes it) and lacked
  `time`, `q:invoke method` lacked `HEAD`/`OPTIONS`, and `validate` did not
  say a regular expression starting with `^` is accepted (it was an enum, so
  the language server flagged one). `test_editor_schemas.py` compares every
  closed list the parser checks with the schema.
- In HTML content, an expression that uses a scope variable inside something
  larger — `{session.visits + 1}`, `{session.n > 0}`, `{session.user.name}` —
  rendered empty although the variable existed (it was read as the session key
  "visits + 1"); `cookie.x` could not be read inside an expression at all. It
  is read as in `q:set`, everywhere (EXPR-11).
- `q:set type=` `int`, `long`, `numeric`, `float`, `double` and `text` — the
  names `q:param` accepts — convert like `integer`, `number`, `decimal` and
  `string`; they were accepted and converted nothing (`type="int"` stored the
  text "7") (ERR-1).
- The test suite no longer writes into the repository. It left
  `test_data/quantum_test.db`, `quantum_jobs.db`, `logs/`, `.quantum/knowledge`
  and page bundles in `static/` in the checkout; each writer now uses a
  temporary folder, and the root `conftest.py` fails the run, naming the files,
  when a test writes into the repository (`git status`, ignored files included,
  before and after).
- The job threads of `q:job`, `q:schedule` and `q:thread` are the process's and
  stop when asked. The server builds a service container per request, and
  each built its own job executor: every request to a page with `q:job`
  started one more queue worker, and every request with `q:schedule` one more
  scheduler running the same schedule again, none of them ever stopped. The
  executor is now shared per job database; its workers wait on a stop signal
  instead of sleeping, `stop_workers()`/`shutdown()` join them (a job in
  progress finishes first), and they are shut down when the process exits.
- `components/bank_transfer_demo.q` never ran (it queried a `default`
  datasource with tables nobody created, and read `flash` before it existed)
  and moved money wrongly: an overdraft or a transfer to an account that does
  not exist debited one side and credited nobody. It is now
  `projects/bank-transfer`, the proof app for `q:transaction` (DB-4): a SQLite
  config, a migration with three accounts and a `CHECK (balance >= 0)`, both
  accounts checked before the transaction, and a `quantum test` suite in CI.
- `tests/apps/test_ui_parity_script.py` failed now and then under `-n auto`: a
  pilot's pause could return while a button's Pressed message was still
  bubbling to the app, so the test read the page before the click's page load
  had started (measured: 1 click in 40). `quantum console` counts finished page
  loads (`pages_loaded`), and the console tests wait for the load their own
  action caused (`tests/console_pilot.py`) — no sleeps, no retries.
- The editor tooling describes the language the parser accepts: quantum-lsp's
  Core and AI tags have exactly the attributes the parser reads and does not
  refuse (vscode-quantum's q:llm had no `knowledge`/`top`/`minRelevance`; the
  agent, tool and data sub-tags were missing), and both tools stop offering
  `q:persist`, `q:route`, `q:component basePath`/`health`/`metrics`/`trace` and
  the other removed attributes. vscode-quantum's Core/AI schema and grammar are
  generated from quantum-lsp (`scripts/generate-editor-schemas.py`), its
  snippets all parse, and `tests/conformance/test_editor_schemas.py` fails when
  either drifts from the parser.
- `model=` on `q:llm`, `q:agent` and `q:team` agents takes expressions, like
  `endpoint=` and `apiKey=`; `model="{m}"` was sent to the server literally
  (IA-1).
- `range=` on a `q:action` param is checked, as on a `q:function` param
  (ACT-2, FN-1).
- `encoding=` on `q:data` reads the file (or response) in that encoding; every
  file was read as UTF-8 (DATA-1).
- A tool argument the model leaves out takes its `q:param`'s `default` (IA-4).
- The PARSE-3 test checks that a field is read by the code that runs its node,
  not only that its name appears somewhere in the runtime.
- A date in the session came back shifted by the server's UTC offset (Flask
  read a date without a timezone as UTC): it comes back the same date, and
  `sessionExpiry` may be a date or ISO text (SET-5).
- The redis message broker (`MESSAGE_BROKER_TYPE=redis`, `quantum mq`) could
  not load: its module imported `message_broker` by a bare name, so asking
  for it said "requires 'redis' package" even with redis installed.
- A `q:action` read and wrote an empty application scope of its own:
  `application.x` set in an action was lost and could not be read there;
  actions share the server's application scope, as pages do (EXEC-3).
- `projects/quantum-chat` works again (every post was a 500): its forms are
  `q:action`s, its dead runtime patches and a committed session key are gone,
  and a `quantum test` suite runs in CI.
- `projects/quantum-terminal`'s download links answered 404 under
  `quantum start`.
- The error for `<q:application type="testing">` and `qtest:` tags names
  `quantum test` as available; it said "coming in a later release" (APP-2).
- `quantum start` with hot reload: stopping the reload server no longer
  leaves its event loop and sockets behind ("RuntimeError: Event loop is
  closed" printed later); it uses the current websockets API.
- Reconfiguring logging closes the previous log files instead of leaking
  them; the websocket transport closes its event loop on shutdown.
- Admin: no deprecation warnings (datetime.utcnow, Pydantic class Config,
  FastAPI on_event); an unreachable duplicate GET /datasources/{id}/logs route
  was removed; the deploy health check and the project server start/stop no
  longer leak a connection or a child process.
- `services:` modules are no longer re-executed when the registry is
  reloaded; their classes stay the same objects.
- Dates bound to SQLite use explicit adapters (the same ISO text), instead of
  the default ones Python 3.12 deprecated.
- The test suite runs with no warnings and no flaky failures (17 runs in a
  row, shuffled): a test left pytest's own PID where `quantum stop` would kill
  it.
- A persisted `q:knowledge` base is stored in the working directory it is
  indexed from (IA-2). The default `./.quantum/knowledge` was handed to
  ChromaDB as a relative path, which it keys one store per process by, so a
  process that indexed bases from two directories wrote both to the first
  (and failed with "Failed to get segments" once it was gone — a flaky CI
  test). In one component, a `persist="false"` base no longer made the bases
  after it in-memory too.
- `quantum stop` no longer kills a process it did not start (RUN-3): a stale
  `.quantum.pid` whose PID the system had given to another program made it
  kill that program. The file records each process's start time, and a PID
  whose process started at another time is left alone (the stale file is
  removed, exit 1). A `.quantum.pid` written by 0.22 or earlier has no start
  time: stop refuses it once, and the server is stopped by hand.

#### Documented

- The docs build fails on a link to a page that does not exist
  (`ignoreDeadLinks: false`), and CI builds the docs on every push and pull
  request, not only when publishing them.
- The Hot Reload page described `quantum dev`, configuration keys,
  environment variables and partial updates that never existed; it now
  describes `quantum start --hot-reload` as it works.
- SPEC gains LOOP-5 (loop types), SET-3 (q:set operation and scope) and SET-4
  (q:set validation), and extends DB-1, ACT-3 (q:flash), DATA-1, INV-1,
  FILE-1, MAIL-1 and IA-1/2/4 — behaviour that already existed; every rule is
  exercised by a test that cites it.
- Every Core and AI tag has a checked example in the guide; the guide explains
  using one component inside another (q:import, props, q:slot).

## 0.22.0

### Added

- **`quantum test`** runs an app's `*.test.q` suites: `q:test` with
  `test:given`, `test:as`, `test:visit`, `test:submit` and `test:expect`
  (status, redirect, flash, text, error, var, queries, table, history), each
  test against a fresh SQLite database built from the migrations, in-process
  through the real server; the report points at the test line and the page
  line; exit code 1 on failure (TEST-1…TEST-4). Guide page "Testing an App".
- `*.test.q` files next to the pages are never served, and `quantum check`
  validates them (ROUTE-4).
- `projects/tarefas` and `projects/blog` have `quantum test` suites (29
  tests), run in CI.
- `q:llm knowledge=` takes `minRelevance` (0–1): chunks less relevant than it
  are not retrieved, and when none remains `found` is false and the model is
  not called. The result has `grounded`, true when the answer cites a source
  (IA-9). The docs assistant uses it: it says "The guide says nothing about
  that" instead of answering from unrelated chunks.

### Breaking

- `q:query mode="rag"` is a parse error that points to `q:llm knowledge=`,
  which cites its sources and reports `found`. `q:query` on
  `knowledge:<name>` still searches the chunks (IA-3).
- A `q:llm`, `q:agent` or `q:team` without `model=` uses
  `QUANTUM_LLM_DEFAULT_MODEL`, else `llm.model` in quantum.config.yaml; with
  neither it fails with an error that says what to configure. It used to fall
  back to `phi3`, which also shadowed the configured model. `llm.default_model`
  is still read (IA-1).
- A slice with a step (`{xs[::-1]}`, `{xs[0:10:2]}`) is an error (EXPR-13).
  The step was silently ignored: `[1, 2, 3][::-1]` returned `[1, 2, 3]`.

### Removed

- **Breaking:** the `qtest:` testing engine and `<q:application
  type="testing">` (decision D-T1). It compiled to a pytest + Playwright file,
  addressed CSS selectors instead of actions and queries, and never ran end to
  end. Removed with it: `quantum/core/features/testing_engine/`,
  `quantum/runtime/testing_code_generator.py`, `testing_builder.py` and
  `testing_templates.py`, the three `examples/*-tests.q`, and the
  grammar/schema entries in quantum-lsp and vscode-quantum. `type="testing"`
  and any `qtest:` tag are now a parse error that names the replacement,
  `quantum test` (APP-2).

### Fixed

- A `q:loop query="…"` over a query with no rows was a 500 ("Query not
  found") when the loop was a statement of the page; it runs zero times
  (LOOP-4).
- `install.py --check` probed write access with a file of a fixed name, so two
  checks at once removed each other's probe and failed; the suite hit it now
  and then under pytest-xdist.

### Documented

- A `type="query"` knowledge source is shared by every user of the app; there
  is no per-user filter yet (IA-8).

## 0.21.0

### Added

- **projects/helpdesk**: tickets with an attachment and e-mail to the support
  team and the requester — in the browser and in the console.
- `q:file action="send"` (FILE-2): a page answers with an uploaded file as a
  download, and decides who may have it. Uploads are never static files.
- `<ui:input rows="6">`, a multi-line field (UI-14). A form whose action takes
  a file posts multipart and draws a file input with the param's `accept`.
- `mail:` in quantum.config.yaml (MAIL-1); `host: log` writes messages to the
  log in development. `q:mail name=` and `onerror="continue"` (MAIL-2).
- `quantum check` also checks the SQL in `q:agent` tools.
- "Why Quantum" page (A6), with its example tested; the docs home no longer
  promises mobile apps or "40+ components".

### Breaking

- `q:mail` sends through `mail:` in the config, and is an error without it. It
  read `SMTP_*` variables and, unless `EMAIL_MOCK=false` was set, printed
  "[MOCK] Email sent" and reported success — no application ever sent mail by
  default. Use `${SMTP_HOST}` etc. in the config (CFG-1).
- A message the server refuses stops the page or action (MAIL-2); it used to
  be an unhandled error too, but some recipients refused was reported as sent.
- The result of `q:mail` is `<name>_result` (`mail_result` by default), not
  `_mail_result`.
- `q:param maxSize=` is a parse error (the attribute is `maxsize`), and so is
  a `maxsize` that is not a size. `q:file action=` other than upload, delete or
  send is a parse error.
- The upload result no longer has `url`: it pointed to `/uploads/...`, which
  was never served.

### Changed

- **The repository is in English** (EN): `SPEC.md` (rule IDs unchanged), the
  tests, the framework code, its messages and comments. Log and error texts
  that were Portuguese now read in English.
- **Support tiers** (`SUPPORT_TIERS.md`, rewritten for 1.0): the tiers are
  Core, AI, Experimental and Laboratory. `q:file`, `q:mail` and
  `q:transaction` move to Core (SPEC rules, tests and an app in CI);
  `q:team` moves to Experimental (no rule, no proving app) and now warns once
  when used. The pytest markers are `laboratory` and `isolated` (were
  `laboratorio` and `isolado`).
- The console's screen widget is `#page` (was `#tela`).
- The wheel no longer ships the old FastAPI admin (`quantum_admin/backend`,
  ~2.6 MB with its 600 KB `main.py`). The library the `.q` admin uses moved to
  `quantum_admin.core`; `quantum admin` is unchanged. The backend stays in the
  repository (A4.2).
- `quantum/runtime/web_server.py` (2150 lines) is split by concern:
  `web_config` (reading the config), `web_html` (asset extraction, htmx, hot
  reload), `web_errors` (welcome and error pages), `web_lifecycle` (start,
  banner, PID, signals). `QuantumWebServer`, `create_app`, `start_server`,
  `ConfigError` and `_validate_config` are imported from where they were.

### Removed

- `quantum/cli/commands` (`new`, `dev`, `build`, `serve`, `test`, `lint`,
  `docs`): a click CLI that the `quantum` command never wired, listed in the
  CLI docs as "future commands". The migration runner it held is now
  `quantum.cli.migrations` (`quantum migrate` is unchanged).

### Fixed

- `q:transaction` failed validation on every run (`quantum run`: "Invalid
  isolation level: "): the parser passed the datasource where the node expected
  the isolation level, and kept the level where nothing read it. An explicit
  `datasource=` never reached the executor. An unknown `isolationLevel` is now
  a parse error (DB-4).
- `quantum run` refused `<ui:alert variant="{...}">` (and a bound `variant` or
  `position` on `ui:toast`/`ui:skeleton`) as an invalid literal; the page
  resolves it when it renders (UI-1).
- `q:param maxsize` was parsed and never checked: any size was accepted.
- `q:file action="upload"` without `destination` failed with "empty file path";
  it saves under `paths.uploads`.
- `<ui:form submit="...">` with fields of its own drew no button.
- `<ui:table source="{rows}">` without `ui:column` drew every row empty; it
  shows one column per field (UI-5).
- Sending mail looked up the machine's full name on every message
  (`socket.getfqdn`): 12 s for the first message on a Windows machine.
- The test suite's admin database was shared by every pytest-xdist worker,
  which failed now and then with "table ... already exists".

## 0.20.0

### Added

- **A failure contract for AI** (IA-5). `onerror="continue"` on `q:llm`,
  `q:knowledge` and `q:query` (any datasource) lets a page handle a failure:
  `<name>_result.success` is false and `error.message` says why — an
  assistant page can say "unavailable" instead of answering 500.
- **Answers that cite their sources** (M5, IA-6). `q:llm knowledge="docs"`
  retrieves the top chunks of a knowledge base, asks the model to answer only
  from them citing `[n]`, and exposes `sources` and `cited` in
  `<name>_result`. With nothing retrieved the model is not called
  (`found: false`) — no uncited answer from memory.
- **Answers that arrive as they are written** (M5, IA-7). `q:llm
  stream="true"` renders the page at once; `<ui:stream for="answer">` shows
  the answer as the model writes it, in the browser (the framework's script,
  no JavaScript to write) and in the console. One-time tokens bound to the
  session; a failure halfway is shown as an error.
- **`urlencode(v)`** in expressions (EXPR-12), for values put in a URL.
- **projects/shop-agent**: a `q:agent` answering questions about a shop's
  SQLite database through read-only query tools; the page lists every call.
- `onerror="continue"` on `q:agent` (IA-5), and `call` in each of
  `<name>_result.actions`: the call written out, `low_stock(below=5)`.
- **projects/docs-assistant**: ask the Quantum guide; the answer is grounded in
  `docs/guide`, cites its pages and streams. It says so when the model server
  or the index is unavailable.

### Breaking

- A `q:knowledge` source that cannot be read (missing file or folder, no file
  matching the pattern, a failing query) is an error; it used to be a log
  warning and the base was built from fewer documents (IA-8).
- `q:source type="url"` (it read nothing) and unknown source types are parse
  errors (IA-8).
- A `q:agent` that does not finish stops the page, like `q:llm` (IA-5); it
  used to leave `success: false` and an empty answer on a page that went on.
  `onerror="continue"` keeps the old behaviour.
- A `q:agent`'s `timeout` (milliseconds, 60000 by default) is now the whole
  run's budget: each model call gets what is left. Before, every call waited
  60 s whatever `timeout` said. An agent on a slow local model may need a
  larger `timeout`.
- `q:agent max_iterations=` is a parse error: the attribute is `maxIterations`.
  The guide and the README wrote `max_iterations`, which was never read.
- Inside a `q:if`, a `q:else`/`q:elseif` right after an inner `</q:if>` is a
  parse error (IF-4): it belonged to the outer `q:if`, not the one it follows.
  `examples/message-queue-example.q` had exactly this bug.

### Fixed

- `q:llm timeout=` was read and never used: every request waited 60 seconds
  (and `stream="true"` too). It is honoured now, and a `q:agent`'s `timeout`
  reaches its model calls.
- A RAG query on a knowledge base that failed to build answered "Knowledge
  base is still loading. Please refresh the page." with `success: true`; it is
  an error with the real reason now.

### Changed

- `q:llm`'s `<name>_result.error` is `{message: ...}`, as `q:invoke`'s.

## 0.19.0

### Added

- **Declarative schema** (M6, DB-10). Keep a `schema.sql` with the tables as
  they should be; `quantum migrate plan` shows what changes against the
  migrations (new tables and columns, rebuilds that keep the rows, indexes),
  marks what loses data, and `--write NAME` saves the migration and its
  rollback after asking. Plans that lose data need `--allow-data-loss`.
  SQLite for now.
- **Change history** (M22, DB-11). `history: true` on a datasource records every
  write an action makes — who, when, which action, the row before and after —
  in the same transaction; `<ui:history table key datasource>` lists a row's
  history in the browser and the console. `projects/tarefas` shows it on the
  edit page.

## 0.18.0

### Added

- **Forms that know the action's rules** (M1, UI-9). A `<ui:form on-submit>`
  takes each field's `required`, `minlength`, `maxlength`, `min`, `max`, type
  and anchored `pattern` from the action's `q:param`s, and a select's options
  from its `enum`; the browser checks them before posting. When the server's
  validation fails, the form comes back with the values sent (never a
  password) and each error next to its field, in the browser and the console.
  An attribute on the field wins; `rules="off"` turns it off.
  `examples/form-rules.q`.

- **Forms from a table** (M17, UI-10). `<q:action table="posts"
  datasource="db">` takes its params from the table's schema: NOT NULL →
  required, `CHECK … IN` → enum, `VARCHAR(n)` → maxlength, the column type,
  nullable columns as `None`, and foreign keys that must name an existing row.
  A `<ui:form>` with no fields of its own draws one per column (select for an
  enum or a foreign key, checkbox for a boolean) and `values="{row}"` opens it
  as an edit form. `projects/tarefas` gained an edit page built this way.
  `quantum check` verifies the action's table and columns.
- **Pagination in a tag** (M14, UI-11). `<ui:pager for="query">` draws
  previous, the page numbers (with gaps) and next over a paginated query,
  keeping the other URL parameters, in the browser and the console.
  `projects/blog` dropped its hand-made pagination (a count query, LIMIT /
  OFFSET, URL building) for it.
- **Search as you type** (M15, UI-12). `<ui:input bind="q" search="results">`
  refreshes the element `#results` after each pause in typing, through htmx
  and the page's own queries, with the search in the URL; a plain GET form
  underneath, so Enter works without JavaScript; the same in the console.
  `projects/blog`'s search page uses it.
- **A table that sorts and edits itself** (M16, UI-13). `<ui:table
  sort="true">` turns headers into links that order the query in SQL
  (`q:query sortable="true"`, before pagination); `<ui:table edit="table"
  datasource="db">` makes each shown column an in-cell form posting to a
  generated action that edits only what the page declares, runs the page's
  guards, validates with the column's schema rules and updates one row by its
  key — shown in `/_dev`. In the console too. `projects/tarefas` has
  `/planilha`.

### Changed

- A failed action validation checks **every** field, not only the first; the
  flash is still the first error.

### Fixed

- `projects/blog`: `/search` with no `?q=` answered 500 (`{trim(query.q)}`
  fails when the URL has no parameters).
- `page=` on a paginated `q:query` was read as a number when the file was
  parsed, so `page="{query.page}"` was always page 1: a page could not move
  through pages at all. It is an expression now, and defaults to the URL's
  `?page=`; an invalid value is page 1 (DB-9).
- A page that failed while rendering answered 500 **without logging
  anything** in production; the error is now in the server log.

## 0.17.0

### Added

- **The `/_dev` panel** (M12, DEV-1). With `server.debug: true`, `/_dev` shows
  the last requests: the component, the action, every query with parameters,
  rows and time (or the database's error), the variables of the action or page
  and of `session` / `application`, the redirect and the flash. Off with
  `debug: false`, and only for requests from the machine itself. `quantum
  start` prints its address.
- **Errors point to the line** (M2, DEV-2). Parse errors say `at line N` —
  everywhere, not only on the page. In debug mode the error page shows the
  `.q` lines around the failing one, marked: the innermost statement or
  element that failed, in the called component's own file when the error is
  inside one; it links the SPEC rules the message cites. Key messages now cite
  their rule (`PARSE-1`, `PARSE-2`, `AUTH-6`, `ACT-9`, `UI-1`, `UI-5`).
- **`quantum check`** (M8, DEV-3): every page parses, every `q:query` compiles
  against the database (EXPLAIN, read-only, nothing runs), and every
  `{query.field}` a page reads — directly, through a loop, a `ui:table` /
  `ui:list` or a `<ui:column key>` — is a column the query returns. Reports
  `file:line: message`; exits 1 on a problem. SQLite for now. The schema
  reader behind it (tables, NOT NULL, defaults, CHECK … IN, foreign keys) is
  the one the declarative schema (M6) and forms from a table (M17) will use.
- **Reloading keeps the session** (DEV-2): in debug mode, without a configured
  `secret_key`, the session key lives in `.quantum/dev-secret-key`; every save
  used to log everyone out.

### Fixed

- **Error pages did not escape** their title, message and details: an error
  message carrying a request value (a query parameter) was written into the
  page as HTML.
- The debug error page showed generic XML hints ("Check your XML syntax") for
  errors that had nothing to do with XML syntax.

## 0.16.0

### Added

- **`quantum desktop`** (UI-4): the application in a desktop window. It
  starts the application's server on a free local port and opens a native
  window (pywebview) on it — the same pages, actions and session as the web,
  with no logic translated. `quantum desktop /some/page --width 800` opens a
  given page and size. Needs the new extra:
  `pip install "quantum-framework[desktop]"`; without it the command says so.
- **Tables and lists from data** (UI-5): `<ui:table source="{rows}">` draws one
  row per record — `<ui:column key="name">` shows a field, a column with
  content draws it per row (`<ui:button on-click="delete" with="id={row.id}">`)
  — and `<ui:list source="{items}" as="item">` repeats its content. Until now
  a table's body was empty and **the whole data source was written into the
  page as an HTML comment**; a list showed `{item.x}` raw. A source that is not
  a list, or a column key the row lacks, is an error.
- **Form fields open with a value** (UI-6): `value=` on `ui:input`,
  `ui:select`, `ui:radio`; `checked=` on `ui:checkbox`, `ui:switch`. Edit
  forms were not possible.
- **The core set of `ui:*`** (UI-7): 37 elements drawn with the same meaning in
  the browser, the console and the desktop, checked by one script run in a
  real browser and in the console (`tests/apps/test_ui_paridade.py`). The
  console now draws grids, tabs, cards, tables, lists, checkboxes, switches,
  radios, progress bars and images; for a tag outside the set it says it
  cannot draw it, instead of drawing something else.

- Guide: **One App, Many Screens** (`docs/guide/ui.md`), every screen in it
  served by a test and checked in the browser's text and the console's.
- Guide: **How a Page Runs** (`docs/guide/how-a-page-runs.md`) and SPEC
  section `EXEC-`: the order of a GET and of a POST, and how long a page
  variable, `flash`, `session.x` and `application.x` live (`application.x` is
  per server process: gone on restart, not shared between gunicorn workers).
  The errors for a statement inside markup (PARSE-2), a page variable read in
  an action (ACT-9) and a guard that reads the page (AUTH-6) link to it.
- CI: the Laboratório tests (games, Godot, React Native) run in a job of their
  own, still required.

### Breaking

- **`quantum run --target desktop` was removed** (UI-8). It generated a
  pywebview app with a JavaScript bridge that translated `q:set` and
  `q:function` on its own — a second implementation of the language. Use
  `quantum desktop`, which opens the same pages in a window.
- **Standalone UI builds are layout only** (UI-8): a `q:set`, `q:function` or
  any command inside `<q:application type="ui">` built with `--target html` or
  `--target textual` is an error. It used to be dropped without a word
  (`{count}` came out raw; buttons called functions that did not exist).
  Write screens as pages.
- **Browser state persistence was removed** (SET-2): `persist`, `persistKey`,
  `persistTtl`, `persistEncrypt` on `q:set`, and the `q:persist` tag. They only
  did anything in the standalone HTML build, and nothing in a page; they are
  now errors that say to use `session.x` or the database.
- `--target mobile` (React Native) is **Laboratório**: it warns once.

### Changed

- A page's title is the same in the browser, the console and the desktop
  window: the first `ui:window`'s `title`, else the component's name (UI-4).
  Pages served in HTML used to be titled `<path> - Quantum`.
- In a page, `ui:section` is a titled group, always open (it was a collapsed
  `<details>`: its content was hidden in the browser); a `ui:card`'s `title`
  shows next to a `ui:card-header` too.

### Fixed

- `examples/python-data-processing.q` used `<ui:code>`, which never existed,
  and `examples/state_persistence_demo.q` used `<ui:form-item>`; neither page
  opened. The first is fixed; the second is removed with the feature it showed.
  `examples/dashboard-ui.q` is now a page; `examples/task-manager-desktop.q`
  (the desktop bridge's demo) is removed.
- `docs/tools/cli.md` told to run `python src/cli/runner.py`, a path that no
  longer exists.

- Text directly inside a `ui:*` container vanished:
  `<ui:card-header>Summary</ui:card-header>` came out empty (UI-1).

## 0.15.0

### Added

- **`ui:*` inside pages** (UI-1). The UI Engine's elements — `ui:window`,
  `ui:vbox`, `ui:panel`, `ui:button`, `ui:form`… — can be used in any page
  served by `quantum start`, next to plain HTML, `q:loop`, `q:if` and the
  page's queries. The page's runtime does the logic; `{expressions}` are
  resolved by it and escaped. Events are the page's actions:
  `<ui:button on-click="save" with="id={row.id}">` posts to
  `<q:action name="save">` with the field `id`, and
  `<ui:form on-submit="create">` posts its fields. An event that names no
  action, or a `ui:` tag that does not exist, is an error with a suggestion.
  Until now `ui:*` only compiled from `<q:application type="ui">`, and inside
  a page it came out as `<window>`/`<vbox>` tags.
- A statement inside `ui:*` markup is a parse error, as inside HTML (PARSE-2).
- **Responsive layout, declared** (UI-2): `stack-below="md"` on `ui:hbox`,
  `hide-below` / `hide-above`, `grow="true"`, and
  `<ui:grid columns="1 sm:2 lg:3">`, with breakpoints `sm` (640 px), `md`
  (768 px) and `lg` (1024 px). The UI Engine's HTML had no media query at all:
  a 280 px sidebar made the page overflow on a phone.
- **`quantum console`** (UI-3): the application's pages in the terminal. It
  starts the application's server and draws each page with Textual from its
  view tree (`Accept: application/vnd.quantum.view+json`); buttons and forms
  send the page's actions, so login, validation and flash are the web's.
  `stack-below` counts terminal columns. The same `.q` is a web page and a
  console app, with no logic translated.
- `projects/tarefas`: a task app written in `ui:*` over SQLite, tested end to
  end in CI — the UI Engine's proof app — including in a real browser at
  1280 and 390 px (Playwright + Chromium, installed in CI) — and in the
  console, with the same script.

### Fixed

- `quantum migrate` reads migration files as UTF-8 on every system (DB-8). On
  Windows it used the system code page, and "página" was stored as
  "pÃ¡gina". The same for the other files the CLI reads.

## 0.14.0

### Fixed

- A `q:function` of the page can be called inside a `q:action` (ACT-10). It
  was a 500 every time: actions ran in one runtime shared by every request
  and thread, which never registered the page's functions. Each request now
  gets its own runtime, so simultaneous requests cannot see each other's
  state either.
- `ui:*` elements inside a served page are an error that says they are not
  supported there yet (UI-0); they came out as `<window>`/`<vbox>` tags no
  browser lays out. Building a UI from a file that is not
  `<q:application type="ui">` says how to fix it instead of raising
  `AttributeError`. The console and desktop targets write different files
  (`<id>_console.py`, `<id>_desktop.py`); they both wrote `<id>.py`, so one
  erased the other.

- `accept` on a `q:param type="file"` restricts the upload (ACT-11): it was
  accepted and never checked, so any file passed. The file name has to match
  as well as the type the browser declares — an `.exe` sent as `image/png` is
  refused.
- `returnType` on `q:function` is checked on every return (FN-4); it was
  accepted and never read.

- `logging.format` sets the format of log lines, and `paths.migrations` the
  folder `quantum migrate` reads (CFG-3); both were documented and ignored.
  Unknown keys under `server`, `paths` and `logging` are named in a warning,
  as they already were under `security` and `performance`.

### Breaking

- Attributes that were accepted and never did anything are parse errors
  (PARSE-3): `mask` on `q:set`, `transform` on `q:invoke`, `validation` on
  `q:param`, `basePath`, `health`, `metrics` and `trace` on `q:component`. A
  test now scans the Core's AST nodes and fails when a field set from the XML
  is not read by anything that executes.
- A `q:function` whose value does not match its `returnType` is an error;
  an unknown `returnType` is a parse error (FN-4).

### Changed

- The test suite runs in parallel in CI (`pytest -n auto`); `pytest-xdist` is in
  the `[dev]` extra. Tests that cannot share the machine are marked `isolado`.

## 0.13.0

### Security

- **A guard written by hand protected nothing.** `<q:if condition="not
  session.authenticated"><q:redirect url="/login"/></q:if>` at the top of a
  page did not redirect (the GET served the page) and did not stop the page's
  `q:action` (the POST ran it without a session). Three causes, all fixed:
  `q:redirect` outside an action was skipped silently (ACT-7); an action never
  ran the page's statements, so no check at the top could stop it — guards
  now run before each action (AUTH-6); and `not session.authenticated` was
  *false* for a visitor with no session, because a missing key made the whole
  condition false (EXPR-8).
- `<q:action require_auth="true">` was parsed and never checked: the action
  ran for anyone. It is now a parse error, with `csrf=` and `rate_limit=`,
  which were not enforced either (AUTH-7).
- `security.max_content_length` never reached Flask, so request bodies —
  uploads — had no size limit. Over the limit (16 MB by default) the answer is
  `413` (CFG-2).

### Fixed

- A `q:if` inside a `q:loop` inside a `q:action` did not see the loop
  variable, and a loop's `from`/`to`/`items` were read from the wrong context
  (ACT-8).
- Keys in `security:` or `performance:` that nothing implements
  (`csrf_protection`, `rate_limiting`, `cors_*`…) are named in a warning when
  the config loads (CFG-2).

- `round()` rounds halves away from zero — `round(2.5)` is 3 and
  `round(0.125, 2)` is 0.13; it was Python's banker's rounding over binary
  floats (2 and 0.12). `ceil()` and `floor()` are new (EXPR-9).
- A JavaScript habit in an expression (`Math.ceil`, `Date.now()`,
  `text.split(' ')`, `parseInt`) names the function to use instead
  (EXPR-10).
- A SQLite `database` that does not exist is an error that points to
  `quantum migrate up`; it used to be created empty, so the page failed later
  with "no such table" (DB-7). A datasource key nothing reads (`sqlite_path`,
  `pool_size`) is named in a warning.
- An error inside a `q:action` about a missing variable says why: an action
  does not run the page's statements (ACT-9).
- Error pages no longer suggest `quantum inspect`, which does not exist.

- Text written directly in a `q:if` / `q:else` branch is rendered (IF-3):
  `<h2><q:if condition="tag">Posts tagged {tag}</q:if><q:else>All</q:else></h2>`
  rendered an empty heading.
- `quantum migrate` runs migration files with more than one statement, and
  applies each file in one transaction: SQLite accepted one statement per
  file ("You can only execute one statement at a time"), so a table and its
  index could not be in the same migration (DB-8).
- `slugify(text)` makes a URL segment from a title (EXPR-9).
- `projects/blog` works end to end and is tested in CI (`tests/apps`): home
  with tag filter and pages, posts with comments, search, and an admin to
  create, edit, publish and delete posts. It had failed on every page. Its
  SQL was PostgreSQL-only while its database was SQLite, it seeded an admin
  whose password nobody knew, and it protected the admin with a hand-written
  guard that did not protect it. The first visit to `/login` now creates the
  admin account; there is no default password.
- `projects/quantum-dashboard` works end to end and is tested in CI: create
  (validated), finish, reopen and delete tasks with `q:action`, filter by
  status. It handled POSTs with a `q:if` at the top of the page, so there was
  no validation and reloading repeated the operation; its database lived in
  `/app/data`; and it started through a `startup.py` that patched the
  framework at run time with imports from the old `src/` layout. Those
  deployment files are gone.
### Breaking

- In a `condition`, a key a scope does not have (`session.x`, `query.x`…) is
  `None` (EXPR-8): `not session.x` is now true when `x` is missing.
- A guard that reads a variable the page sets, on a page with actions, is a
  parse error; a guard condition that cannot be evaluated is an error instead
  of false (AUTH-6).
- `q:redirect` outside an action now redirects.
- `q:action` refuses `require_auth`, `csrf` and `rate_limit` (AUTH-7).
- A datasource that is not in `quantum.config.yaml` is an error. The engine
  used to ask the old admin API on `localhost:8000` for it (DB-7).
- Session, application and request values are read only with their prefix —
  `session.role`, `request.path`. They were also copied in as bare names, so
  `{role}` or `{path}` silently read them (EXPR-11).
- `<q:html>`, `<q:div>` and other HTML element names with the `q:` prefix are a
  parse error (PARSE-1); they were read as the HTML element.

## 0.12.0

### Added

- **`quantum admin`**, with the new `[admin]` extra
  (`pip install "quantum-framework[admin]"`): starts the Quantum Admin — its
  `.q` screens and services now ship in the wheel. Data goes to
  `./.quantum-admin` (`--data`), application paths are relative to the current
  folder (`--root`), it listens on 127.0.0.1:8090. Session keys are kept in the
  data folder, so a restart does not sign everyone out. See *Quantum Admin* in
  the guide.
- **Declared services** (SVC-1..3): a Python function registered with
  `@service("name")`, in a module listed under `services:` in
  `quantum.config.yaml`, is called from a page with
  `<q:invoke name="x" service="name">`. `q:invoke service=` had been parsed
  since the first version and failed with "Unsupported invocation type".
  See the new guide page *Declared Services*.
- `login_url` (AUTH-4): where `require_auth` sends a visitor without a
  session — `security.login_url` in `quantum.config.yaml`, or `login_url=` on
  the component. It was always `/login`. Only local paths are accepted.
- Route segments inside `q:action` (ROUTE-2): a POST to
  `components/app/[name].q` has `name` in the action, as the page render
  does; a form field with the same name does not replace it. `[...path]`
  catch-all segments are now documented (ROUTE-1).
- Private components (ROUTE-3): a file or folder under `components/` whose name
  starts with `_` is not served; it exists to be imported, like a layout.

### Security

- **A layout's slot content leaked between requests.** Filling a `q:slot`
  mutated the component held in the resolver cache, so after the first request
  every later page rendered with that component showed the first page's slot
  content. Composition no longer mutates cached components (COMP-3).
- The session cookie is sent with `SameSite=Lax` and `HttpOnly` (AUTH-5), so a
  form on another site cannot post to a `q:action` with the visitor's session.

### Fixed

- Component composition (COMP-1..4): components are found under
  `paths.components` and the `from=` of `q:import` (they were searched in
  `./components` of the process's working directory); slot content is
  rendered in the page's scope, so loops and conditions over the page's data
  work inside a layout; child components run with the page's configuration
  (datasources, services); props are expressions; a missing or failing
  component is an error instead of an HTML comment on a 200 page. A child
  component sees the page's `session`, `application` and `request` scopes.
- `flash` and the `url` of `q:redirect` evaluate expressions (ACT-3):
  `flash="{result.error}"` ended the action with a 500. `flash` and
  `flashType` always exist on a rendered page (`''` without a message).
- `condition="1"`, `condition="2"` and `condition="{1}"` are true (IF-2).
  They were read as regex quantifiers and were always false in a `q:if`
  outside the markup; the same condition inside the markup was true.
- `and` / `or` short-circuit (EXPR-6): `user and user.name` failed when
  `user` did not exist, because both sides were evaluated first.

### Breaking

- `q:invoke endpoint=` is refused by the parser; it never did anything.
- The admin's screens moved from `components/admin` to
  `quantum_admin/components/admin` (and their CSS/JS from `static/` to
  `quantum_admin/assets`); `quantum start` at the repository root no longer
  serves `/admin`. Use `quantum admin --data quantum_admin` to open the
  repository's existing admin data.
- `components/_anything.q` and everything under a `_folder/` answer 404
  (ROUTE-3). Rename a page that starts with `_`.
- A component call that cannot be resolved or fails now makes the page fail.
- Inside a layout, slot content no longer sees the layout's own variables — it
  renders with the page's.
- A statement (`q:set`, `q:query`, `q:invoke`, `q:action`…) inside an HTML
  element or inside the content of a component call is a parse error
  (PARSE-2). It never ran: statements run before the page is rendered, so
  `<ul><q:set name="y" .../><li>{y}</li></ul>` printed a literal `{y}`, and a
  `q:action` inside a `<section>` was never found. Move it above the markup.
  So is a `q:set` in a `q:loop` that renders rows, when those rows read the
  value it sets: every row showed the last iteration's value. A total
  accumulated in the loop and read after it still works. The comment form of
  `projects/blog` was affected and never worked.

## 0.11.0

The release that writes the language down: `SPEC.md` states what a program
means, rule by rule, and every rule is pinned by a test that cites it.

### Breaking

- **`q:application type="html"`, `type="api"` and `type="microservices"` were
  removed** (APP-1). They never ran their routes. `q:application` without a
  `type` meant `html` and is refused too; the parse error explains how to move
  to pages in `components/` served by `quantum start`.
- **An expression that fails in a `q:` attribute is an error** that names it,
  with a suggestion when a similar name exists (EXPR-1, EXPR-2). It used to be
  left as literal text — `value="x{nada}y"` produced `"x{nada}y"`, and
  `{10 / zero}` produced its own braces. HTML content is still forgiving: an
  unresolved expression there is rendered as written and logged once (EXPR-4).
- **Arithmetic on a session/application value that is not set is an error**
  (EXPR-3). `{session.visitas + 1}` used to become `''` and fail later with
  "could not convert string to float". Reading the value alone still gives
  `''`; for counters use `operation="increment"`.
- **Only a missing name makes a `condition` false** (EXPR-5). A syntax error or
  an unknown function in a condition is now an error instead of a silent false.
- **The first top-level `q:return` ends the component** (RET-1), and a `value`
  that mixes text and expressions is always text: `"007"` stays `"007"` (RET-2).
- **A POST whose `action` field is missing or names no action is refused with
  400** on pages with more than one `q:action` (ACT-5). It used to run the first
  action.
- **`q:set` types are checked** (ERR-1). `type="number"` keeps fractions —
  `{5 / 2}` used to store `2`; `type="integer"` refuses `3.5` instead of
  truncating it; `type="boolean"` refuses anything but true/false/1/0/yes/no.
- **An unknown `q:` tag is a parse error**, with a suggestion (PARSE-1).
  `<q:sett>`, `<q:retrun>` or a tag the docs promised but never existed
  (`q:try`, `q:storedproc`, `q:fetch`, `q:include`, `q:throw`) used to be
  dropped silently, and the program ran without it.
- **`q:query` refuses `cache`, `ttl`, `reactive`, `interval`, `timeout`,
  `maxrows` and `batch`** (DB-5): they never did anything.
- **`quantum migrate` applies migrations to the datasource in
  `quantum.config.yaml`** (DB-6) — the one the pages use — chosen with
  `--datasource` when there are several. It used to read a separate `database:`
  section and, without one, try a local PostgreSQL named `quantum` before
  falling back to `./data/quantum.db`: the migrations landed in a different
  database than the app queried.
- **The `q:fetch` data-fetching feature was removed.** Its parser was never
  registered, so `q:fetch` never ran in a `.q` file; its guide page, example
  and module are gone.
- **`q:function` parameters are always converted and checked** against their
  `q:param` rules, like actions (FN-1). `validate="true"` was needed before, and
  even then `type="email"` and `min`/`max` were not checked.
- **`q:function` refuses attributes that never did anything** (FN-2): `cache`,
  `memoize`, `pure`, `async`, `retry`, `timeout`, `access`, `scope`,
  `validate`, `endpoint` and the REST attributes.
- **Arithmetic operators other than `+` need numbers** (EXPR-7): `'-' * 40`
  and `'%s' % x` are errors instead of Python's repetition and formatting. An
  attribute that is only `{3}` is the number 3, no longer the text `{3}`.
- **`default` on `q:set` applies when `value` resolves to nothing** (SET-1):
  `value="{session.clicks}" default="0"` stores `0` on the first visit instead
  of `''`.
- **`q:param type="number"` keeps whole numbers whole**: `"30"` is `30`, not
  `30.0` (`decimal` is still a float).
- **A failed `q:data` or `q:invoke` stops the component** with an error naming
  the source and the reason, like `q:query` already did (DATA-4, INV-2). They
  used to leave the variable empty and carry on. Add `onerror="continue"` to
  handle the failure through `<name>_result`, whose `error` is now always
  `{message}`.

### Fixed

- `&&` and `||` did not parse, so any condition using them was false for every
  input — including the examples in the conditionals guide (EXPR-6).
- A `q:else`/`q:elseif` written after `</q:if>` was dropped inside `q:loop`,
  `q:function`, HTML elements and most other bodies; it only worked at the top of
  a component (IF-1).
- `q:invoke url=` never worked without an explicit `timeout`, and its
  `q:param`s were sent empty (INV-1).
- `form.<field>` was empty inside `q:action` (ACT-6).
- Conversion errors in `q:set` say what to write: `value="{a} + {b}"` points to
  `{a + b}`, and JSON with single quotes asks for double quotes, instead of
  Python's "could not convert string to float" (ERR-1).
- `quantum run` printed a Python traceback for a failed `q:invoke`, and created
  `./logs/` and `./quantum_jobs.db` in the current directory for any program
  (RUN-1, RUN-2).
- `q:job` and `q:schedule` ran on two different job executors; every service now
  has one instance per runtime.
- A component's `q:function` could not be called from its HTML: `<p>{f(2)}</p>`
  rendered the literal text (FN-3).
- A `q:query` inside `q:transaction datasource="…"` had to repeat the
  datasource or the file did not parse (DB-4).
- `${NAME:default}` (with `:` only) is accepted in `quantum.config.yaml` as well
  as `${NAME:-default}`.

### Added

- `${VAR}` and `${VAR:-default}` in `quantum.config.yaml` read environment
  variables; a missing one stops startup naming the variable (CFG-1).
- `SPEC.md`, with conformance tests in `tests/conformance/`, and known gaps kept
  as strict expected failures until decided.
- The guide examples that show an **Output** are executed by the test suite;
  the expressions and conditionals pages were rewritten from what runs.

## 0.10.0

The release that narrows what Quantum promises to the core language plus AI,
and makes the documentation match what runs.

### Breaking

- **`q:application type="html"` and `type="api"` are now EXPERIMENTAL** and warn
  when run. Neither worked as documented: `type="html"` failed on start, and the
  `type="api"` server returned the literal text of the first `q:return` without
  running the route. Build web apps as pages in `components/` served by
  `quantum start`.
- **`QUANTUM_LLM_BASE_URL` now takes precedence over `llm.base_url`** in
  `quantum.config.yaml`, for every AI tag. Before, `q:llm` used the config and
  `q:agent`/`q:team` used the environment, so one program could talk to two
  model servers.
- **A failed RAG answer raises an error.** It used to be returned as the answer
  text ("Error generating answer: …").
- **Knowledge bases are stored under a new collection name** (`quantum-<name>`)
  and carry a fingerprint of their sources. Existing persisted bases are
  reindexed once, and from now on whenever their sources change.
- **The admin requires a login for every page and data route**, not just `/api`.
  Its session cookie is accepted for reads only.

### Fixed

- `q:query` inside `q:action` could not reach datasources declared in
  `quantum.config.yaml` — no form could write to a database.
- `q:compute` never added its field; `q:field` in XML imports ignored `xpath`
  and `type`; XML imports reported failure, so no transform ran on them.
- The admin served 18 data routes and 3 pages without a login, and its test
  suite wrote into the admin's real database.

### Added

- `hashPassword()` and `verifyPassword()` in expressions, for a real login
  written in `.q` ([Authentication](https://danielgregorio.github.io/quantum/guide/authentication)).
- Guide pages for Actions & Forms, Sessions & Scopes, Data Import,
  Authentication and AI, each written by running its examples.
- `tests/live_ai`: the AI tags tested against a real model server.
- `tests/conformance/test_known_gaps.py`: known gaps in the language, as tests
  that fail until each is decided.
- Laboratório tier: the game engine and the AS4 compiler stay in the repository
  with no stability promise, and warn when run.

## 0.9.1

- Package page on PyPI shows the current README and links.
- `get_memory_usage` no longer crashes on Windows without `psutil`; the admin
  no longer scans 10,000 ports one by one without it.

## 0.9.0

First public release.

- `q:return` inside `q:loop` returns the list instead of being discarded.
- `quantum stop` stops the reloader's child process too, and reports failure
  when a process survives.
