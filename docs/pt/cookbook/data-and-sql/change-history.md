---
order: 6
title: "Histórico de mudanças"
description: "history: true registra quem mudou qual linha, e como; ui:history mostra isso na página."
source: cookbook/data-and-sql/change-history.md
source_hash: c1de2e8e5d97
---

# Histórico de mudanças

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/data-and-sql/change-history). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** saber quem mudou uma página de um wiki, quando, e o que mudou.

`history: true` na fonte de dados é toda a configuração:

<<< @/../examples/cookbook/data-and-sql/change-history/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/change-history/migrations/V001_pages.sql{sql}

Cada escrita que uma ação faz é registrada numa tabela `quantum_history` do
mesmo banco, na mesma transação: quando, o usuário da sessão, a ação, a
linha, e a linha antes e depois. `ui:history` lista as mudanças de uma linha,
as mais novas primeiro, com cada coluna alterada como `antigo → novo`.

<<< @/../examples/cookbook/data-and-sql/change-history/components/index.q{xml}

`test:as` faz o teste entrar; `history=` confere o que foi registrado. Uma
escrita recusada, ou desfeita, não deixa histórico:

<<< @/../examples/cookbook/data-and-sql/change-history/tests/history.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/change-history/output/test-report.txt{text}

Veja [DB-11](../../../reference/spec.md#DB-11).
