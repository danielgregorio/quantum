---
order: 6
title: "Uma página por URL"
description: "components/product/[id].q responde em /product/1, /product/2...; o segmento é uma variável."
source: cookbook/basics/page-per-url.md
source_hash: b03561c27215
---

# Uma página por URL

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/basics/page-per-url). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** um arquivo que responde a uma URL para cada item.

<<< @/../examples/cookbook/basics/page-per-url/quantum.config.yaml{yaml}

Um segmento `[name]` no nome de um arquivo ou pasta aceita qualquer valor, e
a página o recebe como a variável `name`. Ele chega como texto;
`type="integer"` num `q:set` o transforma em número.

<<< @/../examples/cookbook/basics/page-per-url/components/product/[id].q{xml}

<<< @/../examples/cookbook/basics/page-per-url/tests/product.test.q{xml}

<<< @/../examples/cookbook/basics/page-per-url/output/test-report.txt{text}

Com um banco de dados, a página lê a linha com aquele id: veja
[Editar uma linha](../forms-and-actions/edit-a-row.md). A regra:
[ROUTE-1](../../../reference/spec.md#ROUTE-1).
