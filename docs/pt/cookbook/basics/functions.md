---
order: 5
title: "Funções"
description: "Uma q:function com parâmetros tipados e verificados, chamada de um q:set e do HTML."
source: cookbook/basics/functions.md
source_hash: ee92d47aaa68
---

# Funções

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/basics/functions). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** escrever um cálculo uma vez e usá-lo onde a página precisar.

<<< @/../examples/cookbook/basics/functions/quantum.config.yaml{yaml}

Uma `q:function` recebe `q:param` como uma ação: cada argumento é convertido
para o seu tipo e verificado contra as suas regras a cada chamada, e
`default` preenche um que ficou de fora. `returnType` verifica o que volta.
Uma função pode ser chamada em qualquer expressão da página, inclusive dentro
de outra chamada.

<<< @/../examples/cookbook/basics/functions/components/index.q{xml}

<<< @/../examples/cookbook/basics/functions/tests/prices.test.q{xml}

<<< @/../examples/cookbook/basics/functions/output/test-report.txt{text}

Veja [FN-1](../../../reference/spec.md#FN-1), [FN-3](../../../reference/spec.md#FN-3)
e [FN-4](../../../reference/spec.md#FN-4).
