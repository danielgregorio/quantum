---
order: 3
title: "Transmitir uma resposta"
description: "Um q:llm transmitido e ui:stream: a página aparece na hora, e a resposta surge enquanto é escrita."
source: cookbook/ai/stream-an-answer.md
source_hash: 5dbf53d20a59
---

# Transmitir uma resposta

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/ai/stream-an-answer). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** um modelo pode levar segundos para responder; mostrar a página na
hora e a resposta conforme ela chega.

<<< @/../examples/cookbook/ai/stream-an-answer/quantum.config.yaml{yaml}

Com `stream="true"`, o `q:llm` não espera: a recuperação já foi feita, então
as fontes estão na página, e `<ui:stream for="answer">` preenche a resposta
enquanto o modelo a escreve — pelo script do próprio framework, sem
JavaScript a escrever. Sem JavaScript ele é um link, e o `quantum console`
também mostra a resposta chegando.

<<< @/../examples/cookbook/ai/stream-an-answer/components/index.q{xml}

<<< @/../examples/cookbook/ai/stream-an-answer/tests/stream.test.q{xml}

<<< @/../examples/cookbook/ai/stream-an-answer/output/test-report.txt{text}

A transmissão pertence ao visitante que perguntou, é lida uma vez e expira em
dez minutos.

*Testado:* no CI estes testes rodam contra um servidor de modelos substituto, que responde a partir da primeira fonte que recebe; antes de cada versão eles rodam contra um modelo de verdade (`tests/live_ai/test_cookbook_ai.py`). Por isso eles conferem a estrutura — qual fonte, qual ferramenta, o que a página mostra quando algo falha — e nunca as palavras do modelo.

Veja [IA-7](../../../reference/spec.md#IA-7).
