---
order: 8
title: "Números e datas"
description: "type=integer, decimal e date no q:param: a ação recebe números verificados e datas de verdade, com min e max."
source: cookbook/forms-and-actions/numbers-and-dates.md
source_hash: be7e0a2f2ba4
---

# Números e datas

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/forms-and-actions/numbers-and-dates). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** receber um valor, uma contagem e uma data, e fazer contas com eles
sem converter nada à mão.

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/migrations/V001_expenses.sql{sql}

Um formulário envia texto. `type="decimal"` e `type="integer"` o transformam
em número antes de a ação rodar, então `amount / people` funciona. `min` e
`max` são verificados sobre esse número. `type="date"` aceita `YYYY-MM-DD` e
um dia que existe, e o mantém como texto, pronto para o banco.

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/components/index.q{xml}

O formulário ganha `type="number"` com os mesmos `min` e `max`, e
`type="date"`, então o navegador verifica primeiro. Os testes enviam direto
para o servidor, como um script faria:

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/tests/split.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/output/test-report.txt{text}

Veja [ACT-2](../../../reference/spec.md#ACT-2) e [UI-9](../../../reference/spec.md#UI-9).
