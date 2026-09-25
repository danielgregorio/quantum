---
order: 7
title: "Respostas a partir de uma tabela"
description: "Uma fonte de q:knowledge que é uma consulta: as linhas da sua tabela de perguntas frequentes, recuperadas como documentos."
source: cookbook/ai/knowledge-from-a-table.md
source_hash: f7b220a49066
---

# Respostas a partir de uma tabela

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/ai/knowledge-from-a-table). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** responder perguntas sobre a conta a partir de perguntas
frequentes guardadas no banco.

<<< @/../examples/cookbook/ai/knowledge-from-a-table/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/ai/knowledge-from-a-table/migrations/V001_faq.sql{sql}

Uma fonte `type="query"` transforma cada linha num texto a indexar. Tudo o
que está nela é compartilhado por todos os usuários da aplicação — qualquer
pergunta pode recuperar qualquer linha — então indexe só o que todos podem
ler.

<<< @/../examples/cookbook/ai/knowledge-from-a-table/components/index.q{xml}

<<< @/../examples/cookbook/ai/knowledge-from-a-table/tests/faq.test.q{xml}

<<< @/../examples/cookbook/ai/knowledge-from-a-table/output/test-report.txt{text}

*Testado:* no CI estes testes rodam contra um servidor de modelos substituto, que responde a partir da primeira fonte que recebe; antes de cada versão eles rodam contra um modelo de verdade (`tests/live_ai/test_cookbook_ai.py`). Por isso eles conferem a estrutura — qual fonte, qual ferramenta, o que a página mostra quando algo falha — e nunca as palavras do modelo.

Veja [IA-8](../../../reference/spec.md#IA-8) e [IA-9](../../../reference/spec.md#IA-9).
