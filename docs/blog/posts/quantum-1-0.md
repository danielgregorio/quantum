---
title: Quantum 1.0
date: 2026-09-25
description: Declarative web applications in XML, with AI and RAG in the language — what 1.0 promises, how it was checked, and what comes next.
tags: [release, 1.0]
---

# Quantum 1.0

*2026-09-25*

Quantum 1.0 is out. This post says what it is, what the version number
promises, how we checked that the promise holds, and what comes next.

## What Quantum is

**Declarative web applications in XML, with AI and RAG built into the
language. No build chain, no JavaScript, no front-end framework.**

A page is a `.q` file. State, parameterised SQL, forms and their validation,
components, authentication, file uploads and mail are tags; so are an LLM call
that answers from a knowledge base and cites its sources, and an agent whose
tools are written in Quantum itself. `quantum start` serves a folder of pages;
there is nothing to compile.

It is for solo developers and small teams building internal tools, dashboards,
admin panels and AI applications who would rather not maintain a front-end build
chain. It is not a general-purpose replacement for a JavaScript framework.

## What 1.0 promises

The promise is written down in
[Support tiers](https://github.com/danielgregorio/quantum/blob/main/SUPPORT_TIERS.md),
and the engine enforces it:

- **Core** — components, `q:set`, `q:if`, `q:loop`, `q:function`,
  `q:query` and `q:transaction`, `q:action` and forms, `q:invoke`, `q:data`,
  composition, files, mail, the Core set of `ui:*`, authentication.
- **AI** — `q:llm`, `q:knowledge`, `q:agent`.
- **Experimental** — tags that run but carry no promise (jobs, messaging,
  websockets, Python scripting, the terminal target, …). A tag outside Core and
  AI prints a warning the first time it runs.
- **Laboratory** — the 2D game engine and other targets kept to exercise the
  language, with no promise at all.

From 1.0, **Core and AI follow semantic versioning**: a 1.x release does not
break a program that uses only them. A change that would waits for 2.0.
Experimental and Laboratory may change in any release.

## How it was checked

A promise is only as good as what checks it. Four things do:

1. **A specification with rule IDs.** [SPEC.md](https://github.com/danielgregorio/quantum/blob/main/SPEC.md)
   states what a Quantum program means in 137 numbered rules (`LOOP-2`,
   `DB-4`, `IA-6`…), and it is frozen at 1.0. Every rule is cited by at least
   one conformance test — 866 of them — and CI fails if a rule has no test or
   a test cites a rule that does not exist.
2. **Apps that use it.** The repository has small, real apps for each tier: a
   task list drawn with `ui:*` in the browser, the terminal and a desktop
   window; a blog; a helpdesk with attachments and mail; a bank transfer
   inside one `q:transaction`; a documentation assistant and a shop agent for
   the AI tags.
3. **`quantum test`.** Apps are tested in their own language — a `*.test.q`
   visits a page, submits an action and checks the redirect, the flash, the
   table rows and the history, each test on a fresh database built from the
   migrations. The apps' suites run in CI.
4. **Live AI tests.** The AI tags are tested against a real model server before
   every release, with structural assertions (the tool was called, the right
   chunk was retrieved), never exact text.

And the [status page](../../status/index.md) is not written by hand:
a script runs every example and reports what parses and what executes.

## What changed on the way

The road from 0.9 to 1.0 was mostly about making the promise true: behaviour
that used to fail silently — a misspelt name, an attribute that did nothing, a
missing key, a query field that does not exist — is now an error that points to
the line. The [changelog](../../changelog/v1-0-0.md) has the details, version
by version.

## What comes next

- **`quantum test` grows**: more of what an app does should be checkable in its
  own language.
- **Experimental → Core, one tag at a time**, and only with a SPEC rule, a test
  that cites it, an example that runs and a guide page.
- **This site**: translations and a domain of its own.

Bugs, questions and ideas are welcome on
[GitHub Issues](https://github.com/danielgregorio/quantum/issues). If Quantum is
useful to you, the [support page](../../sponsor/index.md) says what help pays for.
