---
order: 2
title: "Dados de teste com test:given"
description: "Coloque no banco novo de um teste as linhas de que ele precisa com test:given, e entre como um usuário com test:as."
source: cookbook/testing/test-data.md
source_hash: 96b9d6f6e931
---

# Dados de teste com `test:given`

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/testing/test-data). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** testar uma página que depende de dados e de quem está olhando —
sem arquivo de fixtures e sem senha.

A página lista as tarefas abertas do usuário que entrou:

<<< @/../examples/cookbook/testing/test-data/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/testing/test-data/migrations/V001_tasks.sql{sql}

<<< @/../examples/cookbook/testing/test-data/components/index.q{xml}

Cada teste começa de um banco vazio construído por `migrations/`.
`test:given` coloca as linhas de que o teste precisa — passando pelas regras
do esquema, então uma linha que a aplicação nunca poderia ter gravado (um
`done` fora do `CHECK (… IN …)`, uma coluna obrigatória que ele não consegue
preencher) faz o passo falhar em vez de entrar escondida. `test:as` faz um
usuário entrar do jeito que um login faz:

<<< @/../examples/cookbook/testing/test-data/tests/tasks.test.q{xml}

<<< @/../examples/cookbook/testing/test-data/output/test-report.txt{text}

`no-text` confere o que *não* pode estar na página — aqui, a tarefa de outro
usuário e uma concluída. O vocabulário completo está no guia
[Testing an App](../../../guide/testing.md) (em inglês).

*Testado:* esta página importa os arquivos de
`examples/cookbook/testing/test-data/`, e o resultado acima é o relatório de
rodá-los.
