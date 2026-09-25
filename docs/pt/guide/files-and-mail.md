---
source: guide/files-and-mail.md
source_hash: 03999c32bb66
---
# Arquivos e e-mail

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/files-and-mail). O código é o mesmo do original.
:::

Um formulário pode receber um arquivo, uma página pode devolver um, e uma
ação pode mandar e-mail. O `projects/helpdesk` usa os três: chamados com um
anexo, um e-mail para a equipe de suporte e para quem abriu o chamado.

## Receber um arquivo {#taking-a-file}

Declare o arquivo como um parâmetro da ação. `accept` e `maxsize` são regras
como `minlength`: um arquivo que as quebra nunca chega à ação, e o formulário
mostra o motivo ao lado do campo.

```xml
<q:action name="open" method="POST">
  <q:param name="title" required="true" minlength="5" />
  <q:param name="attachment" type="file" maxsize="5MB" accept=".png,.jpg,.pdf" />

  <q:if condition="attachment">
    <q:file action="upload" file="{attachment}" result="saved" />
    <!-- saved.filename, saved.original_filename, saved.size, saved.mimetype -->
  </q:if>
  <q:redirect url="/" flash="Ticket opened: {title}" />
</q:action>

<ui:form on-submit="open" submit="Open ticket">
  <ui:input bind="title" />
  <ui:input bind="attachment" />
</ui:form>
```

O formulário sabe que a ação recebe um arquivo: ele envia
`multipart/form-data`, e `attachment` é um campo de arquivo que oferece
`.png,.jpg,.pdf`. Você não escreve nenhum dos dois.

O arquivo é salvo em `paths.uploads` (`./uploads`, a menos que a configuração
diga outra coisa), com um nome seguro; `destination="invoices"` o coloca numa
pasta lá dentro. Guarde o `saved.filename` — é como você acha o arquivo de
novo.

`q:file action` é `upload`, `delete` ou `send` (abaixo); qualquer outra coisa
não passa pelo parser:

```xml
<q:file action="copy" file="{attachment}" />
```

**Erro:** `<q:file action="copy">: use upload, delete or send`

Um campo de várias linhas é `<ui:input bind="description" rows="6" />`.

## Devolver um arquivo {#handing-a-file-back}

Os uploads **não** são servidos como arquivos estáticos: qualquer um com a
URL poderia lê-los. Uma página envia um, e decide quem pode recebê-lo:

```xml
<!-- components/attachment/[id].q -->
<q:component name="Attachment">
  <q:query name="ticket" datasource="db">
    SELECT attachment, attachment_name FROM tickets WHERE id = :id AND attachment IS NOT NULL
    <q:param name="id" value="{id}" type="integer" />
  </q:query>
  <q:if condition="ticket_result.recordCount == 1">
    <q:file action="send" file="{ticket[0].attachment}" name="{ticket[0].attachment_name}" />
  </q:if>
  <p>There is no attachment for ticket #{id}.</p>
</q:component>
```

`q:file action="send"` termina a página com o arquivo como download. O nome
guardado vem do banco, nunca da URL; um caminho fora de `paths.uploads` é
recusado, e um arquivo que falta responde 404. Coloque uma guarda na página
(`require_auth`, ou um `q:if` com `q:redirect`) e só as pessoas certas o
recebem.

## Mandar e-mail {#sending-mail}

Uma ação manda uma mensagem com `q:mail`; o servidor é a seção `mail:` do
`quantum.config.yaml`. Da receita
[E-mail em desenvolvimento](../cookbook/files-and-mail/mail-in-development.md),
testada como aparece:

<<< @/../examples/cookbook/files-and-mail/mail-in-development/components/index.q{xml}

<<< @/../examples/cookbook/files-and-mail/mail-in-development/quantum.config.yaml{yaml}

`host: log` grava cada mensagem no log em vez de enviá-la — use em
desenvolvimento. Sem uma seção `mail:`, o `q:mail` é um erro que diz isso; ele
nunca finge enviar:

```xml
<q:mail to="ana@example.com" subject="Welcome">Hello, Ana!</q:mail>
```

**Erro:** `q:mail needs a mail server`

### Quando o servidor diz não {#when-the-server-says-no}

Uma mensagem que o servidor não aceita para a ação com o motivo do servidor.
Quando o resto da ação precisa acontecer mesmo assim, diga
`onerror="continue"` e confira `<name>_result.success` — da receita
[Quando o servidor de e-mail diz não](../cookbook/files-and-mail/mail-server-refuses.md),
em que o pedido é salvo mesmo quando a confirmação não pode ser enviada:

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/components/index.q{xml}

O helpdesk (`projects/helpdesk`) faz o mesmo: salva o chamado primeiro e diz,
na sua mensagem, quando um e-mail não pôde ser enviado.

## Regras {#rules}

[FILE-1, FILE-2, MAIL-1, MAIL-2 e UI-14](https://github.com/danielgregorio/quantum/blob/main/SPEC.md)
na SPEC.
