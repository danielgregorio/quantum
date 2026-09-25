---
order: 3
title: "Redirecionar e dizer o que aconteceu"
description: "Termine uma ação com q:redirect e uma mensagem flash; q:flash para um aviso; a mensagem aparece uma vez na próxima página."
source: cookbook/forms-and-actions/redirect-and-flash.md
source_hash: 1783ffa2ce2e
---

# Redirecionar e dizer o que aconteceu

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/forms-and-actions/redirect-and-flash). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** depois que um formulário é enviado, levar o navegador para uma
página e dizer o que aconteceu, uma vez.

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/migrations/V001_notes.sql{sql}

`q:redirect` termina a ação. O `flash` dele aceita expressões e vira `flash`
na próxima página renderizada, com `flashType` igual a `success`. Para outro
tipo de mensagem, `q:flash type="warning"` define os dois antes do
redirecionamento. A URL pode ser qualquer página da aplicação.

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/components/index.q{xml}

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/components/done.q{xml}

O segundo teste abre a página de novo depois do redirecionamento: a mensagem
sumiu, e `flash` é `''`.

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/tests/notes.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/output/test-report.txt{text}

Veja [ACT-3](../../../reference/spec.md#ACT-3).
