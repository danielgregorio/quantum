---
order: 2
title: "Quando o servidor de e-mail diz não"
description: "Mantenha um pedido mesmo quando o e-mail de confirmação não pode ser enviado — onerror=continue, e avise o visitante."
source: cookbook/files-and-mail/mail-server-refuses.md
source_hash: 9ffe0f1d6c0a
---

# Quando o servidor de e-mail diz não

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/files-and-mail/mail-server-refuses). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** um pedido precisa ser salvo mesmo quando o e-mail de confirmação
não pode ser enviado — e o visitante deve ficar sabendo, não receber uma
página de erro.

Por padrão, um `q:mail` que o servidor não aceita interrompe a ação com o
motivo do servidor. `onerror="continue"` deixa a ação seguir e coloca o
resultado em `<name>_result`: `success`, e `error.message` quando falhou.
Esta receita aponta para um servidor de e-mail que não existe, então toda
mensagem falha — como acontece quando o servidor de verdade está fora do ar:

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/migrations/V001_orders.sql{sql}

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/components/index.q{xml}

O pedido é inserido antes do e-mail, e a mensagem flash diz o que aconteceu.
O teste confere as duas coisas — a linha está lá, e o visitante foi avisado:

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/tests/order.test.q{xml}

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/output/test-report.txt{text}

Em desenvolvimento, [`host: log`](./mail-in-development.md) evita a falha por
completo; `onerror="continue"` é para o dia em que o servidor de verdade
estiver fora do ar. Mais em [Files & Mail](../../../guide/files-and-mail.md) (em inglês).

*Testado:* esta página importa os arquivos de
`examples/cookbook/files-and-mail/mail-server-refuses/`, e o resultado acima
saiu de rodá-los.
