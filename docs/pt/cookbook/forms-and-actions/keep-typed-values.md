---
order: 2
title: "Um formulário recusado guarda o que foi digitado"
description: "Depois de uma recusa, o formulário volta preenchido com os valores enviados, uma vez, para ninguém digitar uma mensagem longa duas vezes."
source: cookbook/forms-and-actions/keep-typed-values.md
source_hash: fb01e4e771dc
---

# Um formulário recusado guarda o que foi digitado

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/forms-and-actions/keep-typed-values). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** quando o servidor recusa um formulário, trazê-lo de volta com o
que a pessoa digitou, não vazio.

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/migrations/V001_messages.sql{sql}

Não há nada a escrever para isso. Depois de uma recusa, a próxima
renderização de um `ui:form` preenche cada campo com o valor enviado, uma
vez, como a mensagem flash. Um campo de senha ou de arquivo nunca volta.
`rows="6"` faz da mensagem um campo de várias linhas.

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/components/index.q{xml}

O primeiro teste envia um endereço ruim com uma mensagem boa: o endereço é
recusado e a mensagem continua no seu campo. O segundo abre a página de novo:
os valores sumiram.

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/tests/contact.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/output/test-report.txt{text}

Veja [UI-9](../../../reference/spec.md#UI-9) e, para o campo de várias linhas, [UI-14](../../../reference/spec.md#UI-14).
