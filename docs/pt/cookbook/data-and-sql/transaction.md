---
order: 5
title: "Escritas que acontecem juntas"
description: "Uma q:transaction: o débito, o crédito e a linha de registro são confirmados juntos, ou nenhum deles é."
source: cookbook/data-and-sql/transaction.md
source_hash: 3bce037be24a
---

# Escritas que acontecem juntas

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/data-and-sql/transaction). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** transferir dinheiro entre duas contas de um jeito que ele nunca
possa sair de uma sem entrar na outra.

<<< @/../examples/cookbook/data-and-sql/transaction/quantum.config.yaml{yaml}

A tabela de registro recusa uma transferência acima de 1000 — o que o último
teste usa para fazer a terceira escrita falhar:

<<< @/../examples/cookbook/data-and-sql/transaction/migrations/V001_accounts.sql{sql}

A página verifica o que ela sabe explicar (dinheiro insuficiente) e diz isso
com uma mensagem flash. As três escritas ficam dentro de `q:transaction`: se
qualquer uma falhar, as anteriores são desfeitas e a página para com o erro.

<<< @/../examples/cookbook/data-and-sql/transaction/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/transaction/tests/transfer.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/transaction/output/test-report.txt{text}

Veja [DB-4](../../../reference/spec.md#DB-4).
