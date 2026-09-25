---
source: guide/authentication.md
source_hash: 6718120df989
---
# Autenticação

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/authentication). O código é o mesmo do original.
:::

A autenticação no Quantum são três peças que já existem no núcleo:
**atributos de página** que exigem um login, a **sessão** que lembra quem
entrou, e **funções de senha** para conferir um login com honestidade. Não
há servidor de autenticação à parte nem JavaScript.

## Proteger uma página {#protecting-a-page}

```xml
<q:component name="dashboard" require_auth="true" require_role="admin"
             xmlns:q="https://quantum.lang/ns">
  <html><body>
    <p>Hello, {session.userName}</p>
  </body></html>
</q:component>
```

| Visitante | Resultado |
|---------|--------|
| não entrou | redirecionado para `/login` |
| sessão expirada | redirecionado para `/login?expired=true` |
| entrou, mas `session.userRole` não é `admin` | `403 Forbidden` |
| entrou como `admin` | a página |

`require_role` aceita vários papéis separados por vírgulas:
`require_role="admin,editor"`.

As `q:action` da página também são protegidas: um POST sem sessão é
redirecionado e a ação não roda.

### Guardas {#guards}

Um `q:if` no topo da página cujo ramo tem um `q:redirect` é uma *guarda*.
Ela roda antes da página e antes de cada uma das suas ações:

```xml
<q:component name="login" xmlns:q="https://quantum.lang/ns">
  <!-- Already logged in? Go to the dashboard. -->
  <q:if condition="session.authenticated">
    <q:redirect url="/dashboard" />
  </q:if>
  <html><body><p>Please sign in.</p></body></html>
</q:component>
```

Uma chave de sessão que ainda não existe é lida como vazia numa condição,
então `not session.authenticated` é verdadeiro para um visitante que não
entrou.

Duas regras impedem uma guarda de falhar aberta:

- Numa página com ações, uma guarda só pode ler o que existe antes de a
  página rodar — `session`, `query`, `form`, `cookie`, segmentos da rota —
  não uma variável que a página define. Uma ação não roda as instruções da
  página, então essa variável não existiria ali. Isso é um erro de parse.
- Uma condição de guarda que não pode ser avaliada
  (`not session.user.is_admin` quando não há `session.user`) é um erro, não
  "falso".

Para proteger uma página, prefira `require_auth` / `require_role`: eles dizem
o que querem dizer.

## Entrar {#logging-in}

Um login procura o usuário, confere a senha contra o hash guardado e abre a
sessão. A tabela aqui é `users (id, email, name, role, password_hash)`, numa
fonte de dados chamada `db` declarada no `quantum.config.yaml`.

Salve como `components/login.q`:

```xml
<q:component name="login" xmlns:q="https://quantum.lang/ns">
  <q:action name="signIn" method="POST">
    <q:param name="email" type="email" required="true" />
    <q:param name="password" required="true" />

    <q:query name="user" datasource="db">
      SELECT id, name, role, password_hash FROM users WHERE email = :email
      <q:param name="email" value="{email}" type="string" />
    </q:query>

    <q:if condition="user.length == 1 and verifyPassword(password, user[0].password_hash)">
      <q:set name="session.authenticated" value="true" type="boolean" />
      <q:set name="session.userId" value="{user[0].id}" />
      <q:set name="session.userName" value="{user[0].name}" />
      <q:set name="session.userRole" value="{user[0].role}" />
      <q:set name="session.sessionExpiry" value="{dateAdd('h', 8)}" />
      <q:redirect url="/dashboard" />
    </q:if>

    <q:flash type="error" message="Invalid e-mail or password" />
    <q:redirect url="/login" />
  </q:action>

  <html><body>
    <q:if condition="flash"><p class="{flashType}">{flash}</p></q:if>
    <form method="POST" action="/login">
      <input name="email" type="email" />
      <input name="password" type="password" />
      <button>Sign in</button>
    </form>
  </body></html>
</q:component>
```

- Uma senha errada e um e-mail desconhecido recebem a **mesma** mensagem,
  então o formulário não revela quais e-mails têm conta.
- `session.sessionExpiry` é **obrigatória**. Uma sessão sem ela conta como
  expirada — a verificação falha fechada. `dateAdd('h', 8)` quer dizer daqui
  a oito horas.
- `session.authenticated`, `session.userRole` e `session.sessionExpiry` são os
  nomes que `require_auth` e `require_role` leem.

## Criar uma conta {#creating-an-account}

Guarde o hash, nunca a senha:

```xml
<q:action name="createAccount" method="POST">
  <q:param name="email" type="email" required="true" />
  <q:param name="name" required="true" />
  <q:param name="password" required="true" minlength="10" />

  <q:query name="created" datasource="db">
    INSERT INTO users (email, name, role, password_hash)
    VALUES (:email, :name, 'user', :hash)
    <q:param name="email" value="{email}" type="string" />
    <q:param name="name" value="{name}" type="string" />
    <q:param name="hash" value="{hashPassword(password)}" type="string" />
  </q:query>

  <q:redirect url="/login" flash="Account created. Sign in with your e-mail." />
</q:action>
```

`hashPassword` usa bcrypt, com um salt novo a cada chamada. `verifyPassword`
retorna falso — nunca um erro — para uma senha vazia, um hash que falta ou
qualquer coisa que não seja um hash válido.

## Sair {#logging-out}

```xml
<q:action name="signOut" method="POST">
  <q:set name="session.authenticated" value="false" type="boolean" />
  <q:set name="session.userRole" value="" />
  <q:redirect url="/login" />
</q:action>
```

## Próximos passos {#next-steps}

- [Sessions & Scopes](/guide/sessions) — os valores de sessão usados acima (em inglês)
- [Ações e formulários](/pt/guide/actions) — como os campos do formulário de login são declarados
- [Consultas ao banco](/pt/guide/query) — declarar a fonte de dados `db`
