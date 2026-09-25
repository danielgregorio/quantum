---
order: 2
title: "Uma tabela editada no lugar"
description: "ui:table edit= transforma cada célula num pequeno formulário verificado contra o esquema da tabela; nenhuma ação a escrever."
source: cookbook/screens/editable-table.md
source_hash: f6364e25b3ad
---

# Uma tabela editada no lugar

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/screens/editable-table). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** deixar as pessoas mudarem um valor numa tabela sem abrir uma
página de edição.

<<< @/../examples/cookbook/screens/editable-table/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/screens/editable-table/migrations/V001_items.sql{sql}

`edit="items"` faz de cada célula um pequeno formulário que salva uma coluna
de uma linha. O esquema da tabela é a regra: `shelf` precisa ser A, B ou C por
causa do `CHECK`, e um valor recusado volta como uma mensagem flash de erro.
Uma coluna com `edit="false"` é mostrada, não editada, e um envio que tenta
mesmo assim responde `400`. `sort="true"` coloca links nos cabeçalhos.

<<< @/../examples/cookbook/screens/editable-table/components/index.q{xml}

Um teste edita uma célula do jeito que o navegador faz, com a ação `__edit`:

<<< @/../examples/cookbook/screens/editable-table/tests/stock.test.q{xml}

<<< @/../examples/cookbook/screens/editable-table/output/test-report.txt{text}

Veja [UI-5](../../../reference/spec.md#UI-5) e [UI-13](../../../reference/spec.md#UI-13).
