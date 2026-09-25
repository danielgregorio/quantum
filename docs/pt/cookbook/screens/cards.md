---
order: 4
title: "Cards"
description: "ui:card com cabeçalho, corpo e rodapé, num ui:grid; ou um card só com título."
source: cookbook/screens/cards.md
source_hash: fb4a0ba08d55
---

# Cards

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/screens/cards). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** mostrar alguns itens lado a lado, cada um na sua caixa.

<<< @/../examples/cookbook/screens/cards/quantum.config.yaml{yaml}

`ui:card` contém um `ui:card-header`, um `ui:card-body` e um
`ui:card-footer`, todos opcionais. `ui:grid columns="3"` distribui os cards em
três colunas. Um card só com título e algum texto não precisa das partes:
`title=` basta.

<<< @/../examples/cookbook/screens/cards/components/index.q{xml}

<<< @/../examples/cookbook/screens/cards/tests/cards.test.q{xml}

<<< @/../examples/cookbook/screens/cards/output/test-report.txt{text}

Veja [UI-7](../../../reference/spec.md#UI-7).
