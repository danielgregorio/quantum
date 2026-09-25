---
order: 4
title: "Um agente sobre o seu banco de dados"
description: "q:agent com uma ferramenta de consulta só de leitura: o modelo escolhe a ferramenta e os argumentos, nunca o SQL."
source: cookbook/ai/agent-over-your-database.md
source_hash: 144fdb043555
---

# Um agente sobre o seu banco de dados

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/ai/agent-over-your-database). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** deixar um assistente responder "quais produtos estão acabando?" a
partir do banco da loja, sem nunca deixar o modelo escrever SQL.

<<< @/../examples/cookbook/ai/agent-over-your-database/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/ai/agent-over-your-database/migrations/V001_products.sql{sql}

A ferramenta é uma função que você escreve, com uma consulta só de leitura. O
modelo vê o nome, a descrição e o parâmetro dela; ele escolhe chamá-la e com
qual valor, e esse valor é convertido para o tipo do parâmetro antes de a
consulta rodar. `stock_result.actions` lista cada chamada, por extenso.

<<< @/../examples/cookbook/ai/agent-over-your-database/components/index.q{xml}

<<< @/../examples/cookbook/ai/agent-over-your-database/tests/agent.test.q{xml}

No CI, o modelo substituto segue um roteiro curto — chamar a ferramenta, depois
terminar:

<<< @/../examples/cookbook/ai/agent-over-your-database/tests/fake-model.json{json}

<<< @/../examples/cookbook/ai/agent-over-your-database/output/test-report.txt{text}

Uma ferramenta pode fazer tudo o que o corpo dela faz, e um prompt pode levar
o modelo a chamá-la: dê às ferramentas só o acesso de que a tarefa precisa.

*Testado:* no CI estes testes rodam contra um servidor de modelos substituto, que responde a partir da primeira fonte que recebe; antes de cada versão eles rodam contra um modelo de verdade (`tests/live_ai/test_cookbook_ai.py`). Por isso eles conferem a estrutura — qual fonte, qual ferramenta, o que a página mostra quando algo falha — e nunca as palavras do modelo.

Veja [IA-4](../../../reference/spec.md#IA-4) e [IA-5](../../../reference/spec.md#IA-5).
