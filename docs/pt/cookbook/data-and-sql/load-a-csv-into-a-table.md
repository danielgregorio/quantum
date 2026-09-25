---
order: 9
title: "Carregar um CSV numa tabela"
description: "Insira cada linha de um arquivo numa transação — uma linha que falha não deixa nada para trás."
source: cookbook/data-and-sql/load-a-csv-into-a-table.md
source_hash: 74e71bd4db57
---

# Carregar um CSV numa tabela

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/data-and-sql/load-a-csv-into-a-table). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** carregar uma lista de produtos no banco, tudo ou nada.

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/migrations/V001_products.sql{sql}

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/import/products.csv{text}

A ação lê o arquivo com `q:data` e depois insere cada linha dentro de uma
`q:transaction`; as consultas dentro dela, também as do loop, usam a fonte de
dados dela.

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/components/index.q{xml}

O segundo teste carrega o arquivo quando um dos produtos já está lá: a
segunda linha falha, e a primeira, já inserida, é desfeita.

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/tests/load.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/load-a-csv-into-a-table/output/test-report.txt{text}

Veja [DATA-1](../../../reference/spec.md#DATA-1) e [DB-4](../../../reference/spec.md#DB-4).
