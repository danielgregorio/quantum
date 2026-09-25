---
order: 9
title: "Uma escolha numa lista"
description: "enum no q:param dá ao ui:select e ao ui:radio as suas opções e recusa qualquer outra; uma caixa é um boolean."
source: cookbook/forms-and-actions/choices.md
source_hash: 52d2092cd49d
---

# Uma escolha numa lista

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/forms-and-actions/choices). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** um campo que aceita um valor de uma lista, e uma caixa de sim/não.

<<< @/../examples/cookbook/forms-and-actions/choices/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/choices/migrations/V001_orders.sql{sql}

A lista é escrita uma vez, como `enum` no `q:param` da ação. Um `ui:select`
ou `ui:radio` sem opções próprias as pega dali, e o servidor recusa um valor
que não está nela. `default` preenche um campo que ficou de fora. Uma caixa
só envia um valor quando está marcada, então `type="boolean"`
`default="false"` a torna `true` ou `false`.

<<< @/../examples/cookbook/forms-and-actions/choices/components/index.q{xml}

<<< @/../examples/cookbook/forms-and-actions/choices/tests/order.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/choices/output/test-report.txt{text}

Veja [ACT-2](../../../reference/spec.md#ACT-2) e [UI-9](../../../reference/spec.md#UI-9).
