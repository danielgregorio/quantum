---
title: Roadmap
---

# Roadmap

What Quantum is today, and what comes next. There are no dates here, and no
promises beyond the [support tiers](https://github.com/danielgregorio/quantum/blob/main/SUPPORT_TIERS.md):
an item is done when it has shipped in a release and its [changelog](../changelog/)
entry says so.

Each item shows its status: **planned** (approved, not started), **in design**
(being written down before any code) or **in progress** (being built now).

## 1.0 — today

Quantum 1.0 is declarative web applications in XML, with AI and RAG built into
the language. What 1.0 promises is set by its tiers:

- **Core** (components, queries and transactions, actions and forms, files, mail,
  authentication, the Core set of `ui:*`) and **AI** (`q:llm`, `q:knowledge`,
  `q:agent`) follow semantic versioning: a 1.x release does not break a program
  that uses only them. AI is also tested against a real model before every release.
- **Experimental** tags work, with no stability promise.
- **Laboratory** projects stay in the repository because they push on the language;
  they are not part of the product and carry no promise.

What runs today is measured, not claimed: see [Status](../status/). Every tag and
rule is in the [Reference](../reference/).

## Next

### AI

| Item | Status |
|---|---|
| A fake model for development: build and test AI pages with no model running, with answers that are the same on every run | planned |
| AI in the [dev panel](../tools/dev-panel): every call a page made, with its prompt, the sources it used, the answer, the time and the tokens | planned |
| Budgets and redaction: a spending limit per application, and personal data removed before it leaves for the model, with the record of both kept | planned |
| Conversations that remember, and a `ui:chat` to hold them | planned |

### An application that knows itself

| Item | Status |
|---|---|
| `quantum map`: which pages and actions read and write each table | planned |
| `quantum explain page.q`: what a page reads, writes and depends on, in plain text | planned |
| `q:cache` by table: a cached fragment that is refreshed when a write touches one of its tables, with no expiry time to guess | planned |

### Testing

`quantum test` shipped in 1.0 ([Testing](../guide/testing)). Next:

| Item | Status |
|---|---|
| One test run against every screen: the browser and the console | planned |
| Tests derived from an action's rules, written for you | planned |
| AI tests replayed from a recording, so they run without a model | planned |
| Coverage in the application's own terms: which pages, actions and rules a suite reaches | planned |

### The website

| Item | Status |
|---|---|
| Cookbook: short recipes, each one tested in CI | in progress |
| The site in more languages | in progress |
| A playground: write Quantum and run it in the browser | planned |
| Benchmarks that anyone can run again | planned |

## Laboratory

| Item | Status |
|---|---|
| Games 2: games as a deterministic declarative simulation, where the same inputs always give the same game, so a game can be tested and replayed | in design |

Laboratory work carries no promise: it can change or stop at any point.
