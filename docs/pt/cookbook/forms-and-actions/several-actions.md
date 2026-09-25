---
order: 4
title: "Vários formulários numa página"
description: "Cada formulário e botão envia o nome da sua ação; um nome que a página não tem responde 400."
source: cookbook/forms-and-actions/several-actions.md
source_hash: 50553f79a7ea
---

# Vários formulários numa página

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/forms-and-actions/several-actions). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** acrescentar, remover e esvaziar a partir de uma página, cada um
com a sua ação.

<<< @/../examples/cookbook/forms-and-actions/several-actions/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/several-actions/migrations/V001_cart.sql{sql}

Cada `ui:form on-submit` e cada `ui:button on-click` envia o nome da sua ação
num campo chamado `action`; a página roda essa ação e nenhuma outra.
`with="id={cart.id}"` envia o id da linha junto com o botão.

<<< @/../examples/cookbook/forms-and-actions/several-actions/components/index.q{xml}

Numa página com mais de uma ação, um envio cujo `action` falta ou não nomeia
nenhuma delas responde `400` e lista as ações que existem. Nada roda no lugar,
como o último teste confere:

<<< @/../examples/cookbook/forms-and-actions/several-actions/tests/cart.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/several-actions/output/test-report.txt{text}

Veja [ACT-5](../../../reference/spec.md#ACT-5).
