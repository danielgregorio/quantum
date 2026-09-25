---
order: 11
title: "Totais a partir de uma consulta"
description: "SQL sobre o resultado de uma consulta, em memória — o banco é consultado uma vez."
source: cookbook/data-and-sql/query-a-result.md
source_hash: 56c2928ad9cd
---

# Totais a partir de uma consulta

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/data-and-sql/query-a-result). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** mostrar os totais de vendas por região sem consultar o banco duas
vezes.

<<< @/../examples/cookbook/data-and-sql/query-a-result/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/query-a-result/migrations/V001_sales.sql{sql}

`q:query source="sales"` roda o seu SQL sobre o resultado da consulta chamada
`sales`, que aparece como uma tabela com esse nome. `queries="1"` no teste
confere que o banco foi consultado uma vez só.

<<< @/../examples/cookbook/data-and-sql/query-a-result/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/query-a-result/tests/totals.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/query-a-result/output/test-report.txt{text}

Veja [DB-3](../../../reference/spec.md#DB-3).
