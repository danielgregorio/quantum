---
order: 2
title: "Uma lista paginada"
description: "Uma página de uma lista longa por vez, com o ui:pager desenhando os links para as outras."
source: cookbook/data-and-sql/paginated-list.md
source_hash: 5d55378336e3
---

# Uma lista paginada

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/data-and-sql/paginated-list). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** mostrar 23 posts, dez de cada vez, com links para as outras
páginas.

<<< @/../examples/cookbook/data-and-sql/paginated-list/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/paginated-list/migrations/V001_posts.sql{sql}

`paginate="true"` faz a consulta devolver uma página — a do `?page=` da URL,
ou a primeira — e preenche `posts_result.pagination` com os totais.
`<ui:pager for="posts">` desenha anterior, os números das páginas e próxima,
mantendo os outros parâmetros da URL.

<<< @/../examples/cookbook/data-and-sql/paginated-list/components/index.q{xml}

Um `page` que não é um número positivo é a página 1, nunca um erro:

<<< @/../examples/cookbook/data-and-sql/paginated-list/tests/posts.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/paginated-list/output/test-report.txt{text}

Veja [DB-2](../../../reference/spec.md#DB-2), [DB-9](../../../reference/spec.md#DB-9) e [UI-11](../../../reference/spec.md#UI-11).
