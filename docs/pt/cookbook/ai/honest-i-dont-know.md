---
order: 2
title: "Quando os documentos não sabem"
description: "minRelevance deixa de fora os trechos que não têm relação; sem nenhum, o modelo não é chamado e a página diz isso."
source: cookbook/ai/honest-i-dont-know.md
source_hash: 2f44458e4a17
---

# Quando os documentos não sabem

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/ai/honest-i-dont-know). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** quando os documentos não cobrem uma pergunta, dizer isso — em vez
de deixar o modelo responder de memória.

<<< @/../examples/cookbook/ai/honest-i-dont-know/quantum.config.yaml{yaml}

Os mesmos três documentos de [Respostas com as suas fontes](./answer-with-sources.md).
Sem `minRelevance`, os trechos mais próximos sempre voltam, tenham relação com
a pergunta ou não. Com ele, um trecho menos relevante que o piso é descartado;
quando não sobra nenhum, `answer_result.found` é falso e o modelo nunca é
chamado.

<<< @/../examples/cookbook/ai/honest-i-dont-know/components/index.q{xml}

<<< @/../examples/cookbook/ai/honest-i-dont-know/tests/honest.test.q{xml}

<<< @/../examples/cookbook/ai/honest-i-dont-know/output/test-report.txt{text}

O piso depende do modelo de embedding e do tamanho dos trechos. Mostre
`s.relevance` para algumas perguntas que os seus documentos respondem, e
algumas que não respondem, e coloque o piso entre elas — por isso a página
acima o mostra ao lado de cada fonte.

*Testado:* no CI estes testes rodam contra um servidor de modelos substituto, que responde a partir da primeira fonte que recebe; antes de cada versão eles rodam contra um modelo de verdade (`tests/live_ai/test_cookbook_ai.py`). Por isso eles conferem a estrutura — qual fonte, qual ferramenta, o que a página mostra quando algo falha — e nunca as palavras do modelo.

Veja [IA-9](../../../reference/spec.md#IA-9).
