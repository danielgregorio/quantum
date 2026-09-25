---
order: 5
title: "Todo tipo de campo"
description: "ui:form com rótulos ui:formitem: texto, número, uma seleção com opções, um switch, radios e um campo de várias linhas."
source: cookbook/screens/form-fields.md
source_hash: ef4d1aa946f9
---

# Todo tipo de campo

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/screens/form-fields). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** um formulário que usa cada tipo de campo, com rótulos.

<<< @/../examples/cookbook/screens/form-fields/quantum.config.yaml{yaml}

`ui:formitem label="…"` coloca um rótulo ao lado do seu campo. `ui:select`
pega as escolhas de `ui:option` com os seus próprios textos, e `ui:radio` as
pega do `enum` do `q:param` da ação. Um `ui:switch` é uma caixa booleana, e
`rows` faz um campo de várias linhas. As regras de cada campo vêm da ação
([Cada erro no seu campo](../forms-and-actions/field-errors.md)).

<<< @/../examples/cookbook/screens/form-fields/components/index.q{xml}

<<< @/../examples/cookbook/screens/form-fields/tests/booking.test.q{xml}

<<< @/../examples/cookbook/screens/form-fields/output/test-report.txt{text}

Veja [UI-9](../../../reference/spec.md#UI-9) e [UI-14](../../../reference/spec.md#UI-14).
