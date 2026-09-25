---
source: guide/actions.md
source_hash: 2e221351f1c5
---
# Ações e formulários

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/actions). O código é o mesmo do original.
:::

Um formulário envia para uma página, e uma `q:action` dentro dessa página
trata o envio. A ação declara os campos que aceita, os valida, faz o seu
trabalho e redireciona — o ciclo clássico *post / redirect / get*, sem
JavaScript.

## Um formulário e a sua ação {#a-form-and-its-action}

Salve como `components/contact.q` e abra `http://localhost:8080/contact`:

```xml
<q:component name="contact" xmlns:q="https://quantum.lang/ns">
  <q:action name="send" method="POST">
    <q:param name="name" type="string" required="true" minlength="2" />
    <q:set name="session.lastContact" value="{name}" />
    <q:redirect url="/contact" flash="Thank you, {name}!" />
  </q:action>

  <html><body>
    <q:if condition="flash"><p class="{flashType}">{flash}</p></q:if>
    <p>Last contact: {session.lastContact}</p>
    <form method="POST" action="/contact">
      <input name="name" />
      <button>Send</button>
    </form>
  </body></html>
</q:component>
```

O que acontece:

1. O **GET** renderiza a página. A ação não roda.
2. O **POST** com `name=Ana` roda a ação: `name` é validado, guardado na
   sessão, e o navegador é redirecionado para `/contact`.
3. A página depois do redirecionamento mostra `Thank you, Ana!` uma vez.
   `flash` guarda a mensagem e `flashType` o tipo dela (`success`, a menos que
   você diga outra coisa).

## Declarar campos com `q:param` {#declaring-fields-with-q-param}

Cada campo declarado com `q:param` vira uma variável na ação, já validada e
convertida para o tipo declarado. As regras:

| Atributo | Verifica |
|-----------|--------|
| `required="true"` | que o campo está presente e não está vazio |
| `type` | `string`, `number`, `integer`, `boolean`, `email`, `url` |
| `minlength` / `maxlength` | o tamanho do texto |
| `min` / `max` | o intervalo numérico |
| `pattern` | uma expressão regular |
| `enum` | um de uma lista separada por vírgulas |
| `range="1..10"` | entre os dois, ambos incluídos |
| `accept` (com `type="file"`) | o tipo do upload: `image/*`, `.pdf`, `application/pdf` — verificado contra o nome do arquivo e também contra o tipo que o navegador declara |

Quando uma regra falha, a ação **não** roda: o navegador volta para a página
de onde veio, e `flash` traz o motivo com `flashType="error"` — por exemplo
`Parameter 'name' must be at least 2 characters`.

Os valores enviados, crus, também estão disponíveis como `form.<field>` —
como texto, sem validação. Use-os para mostrar; use `q:param` para tudo o que
você guarda ou calcula.

## Várias ações numa página {#several-actions-on-one-page}

Com mais de uma ação, o formulário diz qual quer num campo chamado `action`:

```xml
<q:component name="tasks" xmlns:q="https://quantum.lang/ns">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" />
    <q:redirect url="/tasks" flash="Created: {title}" />
  </q:action>

  <q:action name="clear" method="POST">
    <q:redirect url="/tasks" flash="List cleared" />
  </q:action>

  <html><body>
    <q:if condition="flash"><p>{flash}</p></q:if>
    <form method="POST" action="/tasks">
      <input type="hidden" name="action" value="create" />
      <input name="title" />
      <button>Create</button>
    </form>
    <form method="POST" action="/tasks">
      <input type="hidden" name="action" value="clear" />
      <button>Clear</button>
    </form>
  </body></html>
</q:component>
```

Se `action` falta, ou não nomeia nenhuma ação da página, a requisição é
recusada com `400 Bad Request`, dizendo o que foi pedido e quais ações
existem — nenhuma outra ação roda no lugar.

## Redirecionamentos e mensagens flash {#redirects-and-flash-messages}

`q:redirect` termina a ação. `flash` é opcional e aceita databinding. Para uma
mensagem flash de outro tipo, use `q:flash` antes do redirecionamento:

```xml fragment=action
<q:flash type="error" message="Invalid credentials" />
<q:redirect url="/login" />
```

`q:flash` funciona dentro de uma `q:action`, onde a próxima página a mostra.
Em qualquer outro lugar ela não faria nada, então não passa pelo parser:

```xml
<q:flash type="warning" message="Read the terms first" />
```

**Erro:** `is outside a q:action`

## Proteger uma ação {#protecting-an-action}

Uma ação é protegida pela sua página: `require_auth` / `require_role` no
`q:component`, ou uma guarda (um `q:if` no topo com `q:redirect`), que roda
antes de cada ação da página. A própria `q:action` não aceita atributo de
proteção:

```xml
<q:action name="save" method="POST" require_auth="true">
  <q:redirect url="/" />
</q:action>
```

**Erro:** `require_auth= is not supported`

## Próximos passos {#next-steps}

- [Sessions & Scopes](/guide/sessions) — o que o `session.` guarda entre requisições (em inglês)
- [Autenticação](/pt/guide/authentication) — proteger páginas com um login
