---
order: 2
title: "Variáveis e expressões"
description: "q:set guarda um valor, as chaves calculam com ele, e default preenche o que falta."
source: cookbook/basics/variables.md
source_hash: 103530a1b6f1
---

# Variáveis e expressões

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/basics/variables). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** guardar valores em variáveis e calcular com eles.

<<< @/../examples/cookbook/basics/variables/quantum.config.yaml{yaml}

`q:set` guarda um valor com um nome. As chaves calculam com ele: num atributo
`q:` e no HTML. `type="number"` transforma texto em número, e um valor que é
uma única expressão mantém o seu tipo, então `total` é um número.
`operation="increment"` muda uma variável no lugar, e a página roda de cima
para baixo: `total` foi calculado antes de `quantity` crescer. O `default` é
guardado quando o valor está vazio ou falta, como o `?note=` numa visita
simples.

<<< @/../examples/cookbook/basics/variables/components/index.q{xml}

<<< @/../examples/cookbook/basics/variables/tests/receipt.test.q{xml}

<<< @/../examples/cookbook/basics/variables/output/test-report.txt{text}

Veja [SET-1](../../../reference/spec.md#SET-1), [SET-3](../../../reference/spec.md#SET-3)
e [SET-5](../../../reference/spec.md#SET-5).
