---
order: 1
title: "Um layout que cabe na tela"
description: "ui:hbox lado a lado numa tela larga, empilhado numa estreita, com grow, width e hide-below."
source: cookbook/screens/responsive-layout.md
source_hash: a5899ccac57b
---

# Um layout que cabe na tela

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/screens/responsive-layout). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** um menu lateral ao lado do conteúdo numa tela larga, acima dele
num celular.

<<< @/../examples/cookbook/screens/responsive-layout/quantum.config.yaml{yaml}

`stack-below="md"` coloca as caixas de um `ui:hbox` uma sobre a outra abaixo
da largura `md` (768 px no navegador, 96 colunas num terminal). `width` fixa a
caixa lateral, `grow="true"` dá o resto ao conteúdo, e `hide-below="lg"`
deixa uma dica só para telas largas.

<<< @/../examples/cookbook/screens/responsive-layout/components/index.q{xml}

O `quantum test` lê o texto da página, não o layout, então confere o
conteúdo:

<<< @/../examples/cookbook/screens/responsive-layout/tests/layout.test.q{xml}

<<< @/../examples/cookbook/screens/responsive-layout/output/test-report.txt{text}

O empilhamento em si é conferido no console, onde um teste consegue medi-lo:
com 80 colunas `#main` está empilhado, com 140 fica lado a lado e `#side` tem
220 / 8 = 27 colunas de largura
([`tests/docs/test_cookbook_console.py`](https://github.com/danielgregorio/quantum/blob/main/tests/docs/test_cookbook_console.py)). A regra:
[UI-2](../../../reference/spec.md#UI-2).
