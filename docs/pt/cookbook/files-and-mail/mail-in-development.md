---
order: 1
title: "E-mail em desenvolvimento"
description: "Envie e-mail de uma ação sem servidor de e-mail enquanto desenvolve — host: log grava cada mensagem no log."
source: cookbook/files-and-mail/mail-in-development.md
source_hash: 6103acae1466
---

# E-mail em desenvolvimento

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/files-and-mail/mail-in-development). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** um formulário de contato que manda e-mail para o suporte — e que
você consegue desenvolver e testar sem um servidor de e-mail.

Com `host: log`, o `q:mail` grava cada mensagem no log em vez de enviá-la. A
configuração lê o host do ambiente, então em produção basta definir
`SMTP_HOST`:

<<< @/../examples/cookbook/files-and-mail/mail-in-development/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/files-and-mail/mail-in-development/components/index.q{xml}

Os testes enviam o formulário e conferem o que o visitante ouve, e que um
endereço ruim é recusado no seu campo antes de qualquer envio:

<<< @/../examples/cookbook/files-and-mail/mail-in-development/tests/contact.test.q{xml}

<<< @/../examples/cookbook/files-and-mail/mail-in-development/output/test-report.txt{text}

E esta é a mensagem que o primeiro teste "enviou" — o que o `host: log`
gravou:

<<< @/../examples/cookbook/files-and-mail/mail-in-development/output/mail.txt{text}

Sem uma seção `mail:`, o `q:mail` é um erro que diz isso — ele nunca finge
enviar. Mais em [Files & Mail](../../../guide/files-and-mail.md) (em inglês).

*Testado:* esta página importa os arquivos de
`examples/cookbook/files-and-mail/mail-in-development/`, e os resultados acima
saíram de rodá-los.
