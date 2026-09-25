---
order: 4
title: "Condicionais"
description: "q:if, q:elseif e q:else, com condições que são expressões."
source: cookbook/basics/conditionals.md
source_hash: 6ed2fdc28533
---

# Condicionais

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/basics/conditionals). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** mostrar uma coisa ou outra dependendo de um valor.

<<< @/../examples/cookbook/basics/conditionals/quantum.config.yaml{yaml}

Roda o primeiro ramo cuja condição vale; `q:else` roda quando nenhuma vale.
Uma condição é uma expressão, com `and`, `or` e `not`. Dentro de um
atributo, `<` se escreve `&lt;`: um arquivo `.q` é XML.

<<< @/../examples/cookbook/basics/conditionals/components/index.q{xml}

<<< @/../examples/cookbook/basics/conditionals/tests/stock.test.q{xml}

<<< @/../examples/cookbook/basics/conditionals/output/test-report.txt{text}

Veja [IF-1](../../../reference/spec.md#IF-1) e [IF-2](../../../reference/spec.md#IF-2).
