---
order: 1
title: "Cada erro no seu campo"
description: "Escreva as regras uma vez no q:param da ação; o formulário as lê e mostra cada recusa ao lado do seu campo."
source: cookbook/forms-and-actions/field-errors.md
source_hash: 25cb71a331e3
---

# Cada erro no seu campo

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/forms-and-actions/field-errors). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** recusar um formulário ruim e dizer, ao lado de cada campo, o que
está errado nele.

<<< @/../examples/cookbook/forms-and-actions/field-errors/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/field-errors/migrations/V001_guests.sql{sql}

As regras são escritas uma vez, nos `q:param` da ação. O `ui:form` as lê e
as coloca nos seus campos (`required`, `minlength`, `type="number"`,
`min`...), então o navegador verifica primeiro. O servidor verifica de novo,
todos os campos de uma vez: quando um falha, a ação não roda, a página volta
e cada campo mostra a sua própria mensagem.

<<< @/../examples/cookbook/forms-and-actions/field-errors/components/index.q{xml}

`error="campo"` num teste confere que o campo foi recusado, e `message=` o
texto mostrado ao lado dele:

<<< @/../examples/cookbook/forms-and-actions/field-errors/tests/guests.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/field-errors/output/test-report.txt{text}

As regras e as mensagens: [ACT-2](../../../reference/spec.md#ACT-2) e [UI-9](../../../reference/spec.md#UI-9).
