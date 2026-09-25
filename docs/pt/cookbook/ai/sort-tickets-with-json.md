---
order: 6
title: "Classificar mensagens com respostas em JSON"
description: "responseFormat json: a resposta do modelo é um objeto cujos campos você verifica e guarda."
source: cookbook/ai/sort-tickets-with-json.md
source_hash: 77e549b1b79e
---

# Classificar mensagens com respostas em JSON

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/ai/sort-tickets-with-json). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** arquivar cada mensagem de suporte numa categoria, decidida pelo
modelo, numa tabela.

<<< @/../examples/cookbook/ai/sort-tickets-with-json/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/ai/sort-tickets-with-json/migrations/V001_tickets.sql{sql}

`responseFormat="json"` pede JSON ao modelo e o interpreta: `ticket` é um
objeto. Os campos dele são uma entrada como qualquer outra — a página
verifica a categoria antes de guardá-la, e as próprias regras dos `q:param`
da ação rodam antes de o modelo sequer ser chamado.

<<< @/../examples/cookbook/ai/sort-tickets-with-json/components/index.q{xml}

<<< @/../examples/cookbook/ai/sort-tickets-with-json/tests/tickets.test.q{xml}

<<< @/../examples/cookbook/ai/sort-tickets-with-json/tests/fake-model.json{json}

<<< @/../examples/cookbook/ai/sort-tickets-with-json/output/test-report.txt{text}

*Testado:* no CI estes testes rodam contra um servidor de modelos substituto, que responde a partir da primeira fonte que recebe; antes de cada versão eles rodam contra um modelo de verdade (`tests/live_ai/test_cookbook_ai.py`). Por isso eles conferem a estrutura — qual fonte, qual ferramenta, o que a página mostra quando algo falha — e nunca as palavras do modelo.

Veja [IA-1](../../../reference/spec.md#IA-1).
