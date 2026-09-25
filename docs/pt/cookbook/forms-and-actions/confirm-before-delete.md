---
order: 7
title: "Confirmar antes de apagar"
description: "Uma página que pergunta primeiro, aberta por um link, e o apagar como POST pelo botão dela; sem JavaScript."
source: cookbook/forms-and-actions/confirm-before-delete.md
source_hash: 8e2ffc39c3d9
---

# Confirmar antes de apagar

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/forms-and-actions/confirm-before-delete). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** perguntar "tem certeza?" antes de apagar, sem JavaScript.

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/migrations/V001_contacts.sql{sql}

A lista tem um link, não um botão. Abrir um link só lê, então ele só pode
perguntar:

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/components/index.q{xml}

A pergunta é uma página própria, `components/delete/[id].q`. O botão dela
envia para a ação `remove`, que apaga e volta para a lista. Se o contato já
não existe (uma segunda aba, um recarregamento), a página diz isso em vez de
perguntar.

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/components/delete/[id].q{xml}

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/tests/delete.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/output/test-report.txt{text}
