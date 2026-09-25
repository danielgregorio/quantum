---
order: 8
title: "Componentes reutilizáveis"
description: "Um componente com props e um slot, importado de uma pasta _ que nunca é servida."
source: cookbook/basics/components-and-slots.md
source_hash: e3f5b5e42dc9
---

# Componentes reutilizáveis

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/basics/components-and-slots). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** escrever um card uma vez e usá-lo em qualquer página, com conteúdo diferente.

<<< @/../examples/cookbook/basics/components-and-slots/quantum.config.yaml{yaml}

Um componente também é um arquivo `.q`. Os `q:param` dele são as props, e o
`q:slot` é onde entra o conteúdo de quem o chama. Guarde-o numa pasta cujo
nome começa com `_`: ele pode ser importado e nunca responde a uma URL.

<<< @/../examples/cookbook/basics/components-and-slots/components/_shared/Card.q{xml}

O `q:import` traz o componente para a página, e `<Card>` o usa. Cada atributo
é uma prop, e o conteúdo entre as tags preenche o slot, calculado com as
variáveis da página:

<<< @/../examples/cookbook/basics/components-and-slots/components/index.q{xml}

<<< @/../examples/cookbook/basics/components-and-slots/tests/cards.test.q{xml}

<<< @/../examples/cookbook/basics/components-and-slots/output/test-report.txt{text}

Veja [COMP-1](../../../reference/spec.md#COMP-1), [COMP-3](../../../reference/spec.md#COMP-3)
e [ROUTE-3](../../../reference/spec.md#ROUTE-3).
