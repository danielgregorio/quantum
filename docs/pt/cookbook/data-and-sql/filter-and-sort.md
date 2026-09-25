---
order: 4
title: "Filtrar e ordenar uma tabela"
description: "Links que filtram as linhas e cabeçalhos que as ordenam — os dois no SQL, os dois na URL."
source: cookbook/data-and-sql/filter-and-sort.md
source_hash: 2fd626dc0a23
---

# Filtrar e ordenar uma tabela

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/data-and-sql/filter-and-sort). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** uma tabela de tarefas que quem lê filtra (abertas, feitas, todas)
e ordena clicando num cabeçalho.

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/migrations/V001_tasks.sql{sql}

O filtro é `?show=`, passado à consulta como parâmetro. `sortable="true"` na
consulta e `sort="true"` na tabela transformam cada cabeçalho num link que
ordena a consulta no SQL por `?sort=` e `?dir=` — então continua funcionando
numa consulta paginada. Uma coluna que a consulta não devolve é ignorada.

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/tests/tasks.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/filter-and-sort/output/test-report.txt{text}

Veja [UI-13](../../../reference/spec.md#UI-13).
