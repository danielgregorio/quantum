---
order: 3
title: "Busca enquanto você digita"
description: "Um campo que atualiza os resultados a cada pausa na digitação — a própria consulta da página faz a busca."
source: cookbook/data-and-sql/search-as-you-type.md
source_hash: d5ee5239d914
---

# Busca enquanto você digita

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/data-and-sql/search-as-you-type). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** um campo de busca sobre livros que atualiza a lista enquanto você
digita, e que continua funcionando sem JavaScript.

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/migrations/V001_books.sql{sql}

A busca é um parâmetro GET (`?q=`), lido pela própria consulta da página.
`search="results"` no campo pede a mesma página a cada pausa na digitação e
troca só o elemento com `id="results"`; a URL acompanha, então o resultado
pode ser compartilhado ou recarregado.

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/tests/search.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/output/test-report.txt{text}

Veja [UI-12](../../../reference/spec.md#UI-12).
