---
order: 5
title: "Um formulário a partir da tabela"
description: "q:action table= pega os seus parâmetros do esquema; um ui:form sem campos desenha um campo por coluna."
source: cookbook/forms-and-actions/form-from-table.md
source_hash: 8dcaa96980a9
---

# Um formulário a partir da tabela

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/forms-and-actions/form-from-table). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** um formulário para uma tabela sem escrever de novo cada campo e
cada regra.

<<< @/../examples/cookbook/forms-and-actions/form-from-table/quantum.config.yaml{yaml}

O esquema já diz do que um livro precisa:

<<< @/../examples/cookbook/forms-and-actions/form-from-table/migrations/V001_library.sql{sql}

`<q:action table="books" datasource="db">` o lê e faz um `q:param` de cada
coluna menos a chave, na ordem da tabela:

| Coluna | Vira |
|---|---|
| `title VARCHAR(120) NOT NULL` | obrigatório, no máximo 120 caracteres |
| `author_id ... REFERENCES authors(id)` | um inteiro que precisa nomear um autor existente |
| `genre ... CHECK (genre IN (...))` | um dos três |
| `pages INTEGER` (aceita NULL) | um inteiro; deixado em branco, chega à ação como `None` |
| `lent BOOLEAN` | uma caixa |

Um `ui:form` sem campos próprios desenha um por parâmetro, com o rótulo tirado
do nome (`author_id` vira "Author"). O campo do autor é uma lista com os
nomes dos autores. `null="true"` no parâmetro `pages` da consulta grava um
campo em branco como `NULL`.

<<< @/../examples/cookbook/forms-and-actions/form-from-table/components/index.q{xml}

<<< @/../examples/cookbook/forms-and-actions/form-from-table/tests/books.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/form-from-table/output/test-report.txt{text}

Um `q:param` escrito na ação vence o do esquema, e `columns="a,b"` fica só com
essas colunas. Veja [UI-10](../../../reference/spec.md#UI-10).
