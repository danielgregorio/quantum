---
order: 8
title: "Ler um arquivo CSV"
description: "q:data transforma um CSV em registros tipados, filtrados e ordenados — sem banco de dados."
source: cookbook/data-and-sql/read-a-csv.md
source_hash: 6de028735194
---

# Ler um arquivo CSV

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/data-and-sql/read-a-csv). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** mostrar os clientes ativos de um arquivo CSV, os mais antigos
primeiro.

<<< @/../examples/cookbook/data-and-sql/read-a-csv/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/read-a-csv/import/customers.csv{text}

As colunas declaradas são tipadas (`true`, `1`, `yes` e `on` são um boolean
verdadeiro); as outras chegam como texto. `q:transform` roda as suas
operações em ordem.

<<< @/../examples/cookbook/data-and-sql/read-a-csv/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/read-a-csv/tests/customers.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/read-a-csv/output/test-report.txt{text}

Veja [DATA-1](../../../reference/spec.md#DATA-1) e [DATA-3](../../../reference/spec.md#DATA-3), e
[Data Import](../../../guide/data-import.md) (em inglês).
