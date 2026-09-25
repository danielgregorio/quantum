# q:application

A **web app** in Quantum is not a `q:application`: it is a folder of pages in
`components/`, served by `quantum start`. See [Getting Started](/guide/getting-started)
and the [Quick Start](/guide/quick-start).

`q:application` is the root element for programs that are **not** web pages.
None of them is part of the supported core (see `SUPPORT_TIERS.md`):

| `type` | Tier | What `quantum run app.q` does |
|--------|------|-------------------------------|
| `game` | Laboratory | builds a 2D game (`--engine pixi` or `--engine godot`) |
| `terminal` | Experimental | builds a terminal UI |
| `ui` | Experimental | builds a UI, layout only (`--target html` or `textual`; `mobile` is Laboratory) |

Running an experimental or Laboratory application prints a one-time warning
saying so. Their tags and output can change in any release.

## Removed: `type="html"`, `type="api"`, `type="microservices"`

Earlier versions documented web servers and JSON APIs declared as
`q:application` with `q:route` blocks. They never ran their routes — `html`
failed on start, and `api` answered with the literal text of the first
`q:return` — and were removed in 0.11. `q:application` without a `type` meant
`type="html"`, so it is refused too. `type="testing"` (the `qtest:` engine) was
removed in 0.22; its replacement is [`quantum test`](/guide/testing).

The parser now stops with directions:

```text
<q:application> type="html" was removed in Quantum 0.11: it never ran its
routes. Build a web app as pages in components/ (components/index.q is /) and
run `quantum start`. See https://quantumframework.net/guide/getting-started
```

What each route becomes:

| Before | Now |
|--------|-----|
| `<q:route path="/about" method="GET">` | `components/about.q` |
| `<q:route path="/" method="GET">` | `components/index.q` |
| `<q:route path="/users" method="POST">` | a [`q:action`](/guide/actions) in `components/users.q` |
| JSON API route | not available |
