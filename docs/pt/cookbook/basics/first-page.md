---
order: 1
title: "Uma primeira página, e uma segunda"
description: "Cada arquivo em components/ é uma página na sua própria URL; uma URL sem arquivo é 404."
source: cookbook/basics/first-page.md
source_hash: 2f3e3e2fd454
---

# Uma primeira página, e uma segunda

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/basics/first-page). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** servir duas páginas com links uma para a outra.

<<< @/../examples/cookbook/basics/first-page/quantum.config.yaml{yaml}

Um arquivo em `components/` é uma página, na URL do seu caminho:
`components/index.q` responde em `/` e `components/about.q` responde em
`/about`. Inicie o servidor com `quantum start` na pasta que tem o
`quantum.config.yaml`.

<<< @/../examples/cookbook/basics/first-page/components/index.q{xml}

<<< @/../examples/cookbook/basics/first-page/components/about.q{xml}

Uma URL sem arquivo responde `404`:

<<< @/../examples/cookbook/basics/first-page/tests/pages.test.q{xml}

<<< @/../examples/cookbook/basics/first-page/output/test-report.txt{text}

Veja [ROUTE-1](../../../reference/spec.md#ROUTE-1).
