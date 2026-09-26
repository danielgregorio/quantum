---
title: Playground
description: Edit a Quantum app and run it in your browser — the real quantum-framework, with its database and its tests.
layout: page
sidebar: false
aside: false
---

<div class="playground-page vp-doc">

# Playground

Every example is a [Cookbook](/cookbook/) recipe: edit its files, press **Run**,
and use the page on the right — links, forms and the database work. **Run tests**
runs its `*.test.q` files with `quantum test`.

It is not a simulation: your browser runs the real `quantum-framework` from PyPI
([Pyodide](https://pyodide.org/)), with a SQLite database built from the
recipe's migrations. Nothing leaves your machine. The AI recipes are not here —
they need a model.

<ClientOnly>
  <QuantumPlayground />
</ClientOnly>

</div>
