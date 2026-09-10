# Changelog

Quantum is pre-1.0: minor versions may break compatibility. Every change that
can alter the behaviour of an existing app is listed under **Breaking**.

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
