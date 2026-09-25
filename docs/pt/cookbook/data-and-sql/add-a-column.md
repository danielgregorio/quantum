---
order: 7
title: "Acrescentar uma coluna com uma migração"
description: "Mude o esquema com um novo arquivo de migração; o antigo fica como estava."
source: cookbook/data-and-sql/add-a-column.md
source_hash: b48dec1e9084
---

# Acrescentar uma coluna com uma migração

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/data-and-sql/add-a-column). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** os produtos precisam de uma contagem de estoque, e o banco já existe.

<<< @/../examples/cookbook/data-and-sql/add-a-column/quantum.config.yaml{yaml}

A primeira migração criou a tabela:

<<< @/../examples/cookbook/data-and-sql/add-a-column/migrations/V001_products.sql{sql}

A mudança é um segundo arquivo. As migrações rodam em ordem, cada uma uma
vez, cada uma na sua própria transação; uma migração já aplicada nunca é
editada:

<<< @/../examples/cookbook/data-and-sql/add-a-column/migrations/V002_add_stock.sql{sql}

```bash
quantum migrate up
```

<<< @/../examples/cookbook/data-and-sql/add-a-column/components/index.q{xml}

Cada teste começa de um banco construído pelas migrações, então o teste vê o
esquema que uma instalação nova recebe:

<<< @/../examples/cookbook/data-and-sql/add-a-column/tests/stock.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/add-a-column/output/test-report.txt{text}

Prefere escrever o esquema que você quer e deixar o Quantum escrever a
migração? Veja `quantum migrate plan` em
[Project Structure](../../../guide/project-structure.md) (em inglês). Veja
[DB-6](../../../reference/spec.md#DB-6) e [DB-8](../../../reference/spec.md#DB-8).
