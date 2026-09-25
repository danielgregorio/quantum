---
order: 10
title: "Ler um arquivo JSON"
description: "Um array JSON como uma lista de registros, com um campo calculado em cada um."
source: cookbook/data-and-sql/read-json.md
source_hash: 19816ee3c86a
---

# Ler um arquivo JSON

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/data-and-sql/read-json). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** mostrar um carrinho a partir de um arquivo JSON, com o subtotal
de cada linha, o maior primeiro.

<<< @/../examples/cookbook/data-and-sql/read-json/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/read-json/import/products.json{json}

Um array JSON é a lista como ela é. `q:compute` acrescenta um campo a cada
registro; `{price}` e `{qty}` são campos do próprio registro.

<<< @/../examples/cookbook/data-and-sql/read-json/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/read-json/tests/cart.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/read-json/output/test-report.txt{text}

Veja [DATA-1](../../../reference/spec.md#DATA-1) e [DATA-3](../../../reference/spec.md#DATA-3).
