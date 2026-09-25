---
order: 5
title: "Quando o modelo falha"
description: "onerror no q:llm: um modelo fora do ar ou lento demais não derruba a página junto."
source: cookbook/ai/when-the-model-fails.md
source_hash: 2fc39501021e
---

# Quando o modelo falha

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/ai/when-the-model-fails). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** uma página que usa um modelo deve continuar funcionando — e dizer
o que aconteceu — quando o servidor de modelos está fora do ar, lento, ou sem
o modelo.

<<< @/../examples/cookbook/ai/when-the-model-fails/quantum.config.yaml{yaml}

Sem `onerror`, uma falha de IA para a página com um erro que nomeia o
servidor e a causa. Com `onerror="continue"`, a página segue:
`summary_result.success` é falso, `summary_result.error.message` diz o
motivo, e `summary` fica vazio. O exemplo aponta `endpoint=` para um servidor
que não está rodando, então falha do mesmo jeito em qualquer lugar.

<<< @/../examples/cookbook/ai/when-the-model-fails/components/index.q{xml}

<<< @/../examples/cookbook/ai/when-the-model-fails/tests/failure.test.q{xml}

<<< @/../examples/cookbook/ai/when-the-model-fails/output/test-report.txt{text}

`onerror` funciona igual em `q:llm`, `q:knowledge`, `q:agent` e `q:query`.
Veja [IA-5](../../../reference/spec.md#IA-5).
