# Changelog

Quantum is pre-1.0: minor versions may break compatibility. Every change that
can alter the behaviour of an existing app is listed under **Breaking**.

## 0.12.0

### Added

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

### Breaking

- `q:invoke endpoint=` is refused by the parser; it never did anything.
- A component call that cannot be resolved or fails now makes the page fail.
- Inside a layout, slot content no longer sees the layout's own variables — it
  renders with the page's.

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
