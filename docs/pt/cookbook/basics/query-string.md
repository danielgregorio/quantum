---
order: 7
title: "Ler a query string"
description: "query.name lê o ?name= do endereço; default cobre um que falta; urlencode monta um link."
source: cookbook/basics/query-string.md
source_hash: 04f0affeada2
---

# Ler a query string

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/basics/query-string). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** filtrar e ordenar uma lista a partir de valores no endereço.

<<< @/../examples/cookbook/basics/query-string/quantum.config.yaml{yaml}

`query.q` é o valor de `?q=` no endereço, e fica vazio quando o endereço não
tem nenhum, então o `default` lhe dá um valor. Um formulário GET preenche o
endereço para você. `urlencode()` deixa um valor digitado seguro dentro de um
link.

<<< @/../examples/cookbook/basics/query-string/components/index.q{xml}

<<< @/../examples/cookbook/basics/query-string/tests/search.test.q{xml}

<<< @/../examples/cookbook/basics/query-string/output/test-report.txt{text}

Veja [SET-1](../../../reference/spec.md#SET-1) e [EXPR-12](../../../reference/spec.md#EXPR-12).
