---
order: 3
title: "Loops"
description: "q:loop sobre uma lista (com a posição), um intervalo de números e um texto separado por vírgulas."
source: cookbook/basics/loops.md
source_hash: d76dbb1437b0
---

# Loops

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/basics/loops). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** repetir parte de uma página para cada item de uma lista ou cada número de um intervalo.

<<< @/../examples/cookbook/basics/loops/quantum.config.yaml{yaml}

`type="array"` percorre uma lista, com `index=` nomeando a posição a partir
de 0. `type="range"` conta de `from` até `to`, os dois incluídos, de `step`
em `step`. `type="list"` divide um texto pelas vírgulas e tira os espaços de
cada item.

<<< @/../examples/cookbook/basics/loops/components/index.q{xml}

<<< @/../examples/cookbook/basics/loops/tests/loops.test.q{xml}

<<< @/../examples/cookbook/basics/loops/output/test-report.txt{text}

Para percorrer as linhas de uma consulta, veja
[Vários formulários numa página](../forms-and-actions/several-actions.md).
As regras: [LOOP-5](../../../reference/spec.md#LOOP-5) e [LOOP-6](../../../reference/spec.md#LOOP-6).
