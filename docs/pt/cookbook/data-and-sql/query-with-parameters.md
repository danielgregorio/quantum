---
order: 1
title: "Uma consulta com parâmetros"
description: "Filtre por um valor da URL, ligado como um q:param — o valor nunca vira SQL."
source: cookbook/data-and-sql/query-with-parameters.md
source_hash: b54ace8bb289
---

# Uma consulta com parâmetros

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/data-and-sql/query-with-parameters). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** listar os produtos cujo nome contém o que a URL pede
(`/?name=mouse`), com segurança.

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/migrations/V001_products.sql{sql}

Cada `:name` no SQL é ligado ao `q:param` de mesmo nome: o valor vai para o
banco separado do texto do SQL, convertido antes pelo seu `type`. Um `:name`
sem `q:param` não passa pelo parser, então não há como colar um valor no SQL
sem querer.

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/components/index.q{xml}

O último teste manda SQL na URL. É só um texto a procurar: nenhum produto o
tem no nome, e a tabela fica intacta.

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/tests/products.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/output/test-report.txt{text}

Veja [DB-1](../../../reference/spec.md#DB-1).
