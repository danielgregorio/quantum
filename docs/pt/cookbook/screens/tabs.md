---
order: 3
title: "Abas"
description: "ui:tabpanel com uma ui:tab por seção de uma página."
source: cookbook/screens/tabs.md
source_hash: d1171ed5c0b9
---

# Abas

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/screens/tabs). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** dividir uma página em seções, uma visível de cada vez.

<<< @/../examples/cookbook/screens/tabs/quantum.config.yaml{yaml}

Cada `ui:tab` é uma seção com um `title`; a primeira abre com a página. O
conteúdo de todas as abas está na página, então uma aba escondida continua lá
para a busca e para os testes.

<<< @/../examples/cookbook/screens/tabs/components/index.q{xml}

<<< @/../examples/cookbook/screens/tabs/tests/tabs.test.q{xml}

<<< @/../examples/cookbook/screens/tabs/output/test-report.txt{text}

`ui:tabpanel` faz parte do conjunto do Núcleo desenhado pelo navegador, pelo
console e pela janela de desktop: [UI-7](../../../reference/spec.md#UI-7).
