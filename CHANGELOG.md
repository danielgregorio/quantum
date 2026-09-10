# Changelog

Quantum is pre-1.0: minor versions may break compatibility. Every change that
can alter the behaviour of an existing app is listed under **Breaking**.

## 0.11.0

The release that writes the language down: `SPEC.md` states what a program
means, rule by rule, and every rule is pinned by a test that cites it.

### Breaking

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
- **`q:invoke function=` failures report `error.message`**, the same shape as
  HTTP failures; `error` used to be a plain string.

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

### Added

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
