---
order: 6
title: "Editar uma linha"
description: "Uma página por linha com [id].q, um formulário aberto com os valores da linha e as regras da tabela ao salvar."
source: cookbook/forms-and-actions/edit-a-row.md
source_hash: 5e7078307baa
---

# Editar uma linha

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/forms-and-actions/edit-a-row). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** uma página que edita um livro, aberta a partir da lista.

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/migrations/V001_books.sql{sql}

A lista liga cada livro a `/book/{id}`:

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/components/index.q{xml}

`components/book/[id].q` responde em `/book/2` com `id = 2`. A ação pega
`title` e `genre` da tabela ([Um formulário a partir da tabela](./form-from-table.md))
e `values="{book}"` abre o formulário com os valores da linha. Uma consulta
de uma linha basta.

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/components/book/[id].q{xml}

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/tests/edit.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/output/test-report.txt{text}

Veja [UI-10](../../../reference/spec.md#UI-10).
