---
order: 1
title: "Respostas com as suas fontes"
description: "Responda perguntas a partir dos seus próprios documentos com q:knowledge e q:llm knowledge=, e liste as fontes."
source: cookbook/ai/answer-with-sources.md
source_hash: f578e2c9daff
---

# Respostas com as suas fontes

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/ai/answer-with-sources). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** uma página que responde perguntas sobre uma loja a partir dos
documentos de política dela, e mostra de qual documento veio cada resposta.

<<< @/../examples/cookbook/ai/answer-with-sources/quantum.config.yaml{yaml}

Três arquivos Markdown em `knowledge/`:

<<< @/../examples/cookbook/ai/answer-with-sources/knowledge/returns.md{md}

`q:knowledge` lê a pasta, a divide em trechos e calcula os embeddings deles.
`q:llm knowledge="docs"` recupera os trechos mais próximos da pergunta e os
envia numerados ao modelo, com a instrução de responder só a partir deles e
citá-los como `[1]`. `answer_result.sources` lista o que foi recuperado;
`answer_result.grounded` diz se a resposta cita algum deles.

<<< @/../examples/cookbook/ai/answer-with-sources/components/index.q{xml}

<<< @/../examples/cookbook/ai/answer-with-sources/tests/ask.test.q{xml}

<<< @/../examples/cookbook/ai/answer-with-sources/output/test-report.txt{text}

*Testado:* no CI estes testes rodam contra um servidor de modelos substituto, que responde a partir da primeira fonte que recebe; antes de cada versão eles rodam contra um modelo de verdade (`tests/live_ai/test_cookbook_ai.py`). Por isso eles conferem a estrutura — qual fonte, qual ferramenta, o que a página mostra quando algo falha — e nunca as palavras do modelo.

Veja [IA-2](../../../reference/spec.md#IA-2), [IA-6](../../../reference/spec.md#IA-6) e
[o guia de IA](../../../guide/ai.md#answers-that-cite-their-sources) (em inglês).
