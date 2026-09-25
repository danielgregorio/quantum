---
source: guide/sessions.md
source_hash: 51e837228e46
---
# Sessões e escopos

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/sessions). O código é o mesmo do original.
:::

Um `q:set` simples vive por uma requisição (SET-2). Três escopos com prefixo
guardam valores por mais tempo, ou expõem a própria requisição:

| Escopo | Vive | Compartilhado com |
|-------|-------|-------------|
| `session.` | entre requisições, para um visitante | só aquele visitante |
| `application.` | enquanto o processo do servidor roda | todo visitante daquele processo |
| `request.` | uma requisição | — |

`application.` é memória no processo do servidor: some depois de um
reinício, e com `gunicorn --workers 4` cada worker tem a sua. Guarde no banco
o que precisa durar — veja [Como uma página roda](/pt/guide/how-a-page-runs).

As sessões ficam num cookie assinado pelo servidor web, então funcionam com o
`quantum start` sem configurar nada. Quando for publicar, defina
`QUANTUM_SECRET_KEY` (ou `security.secret_key` na configuração): sem ela,
cada processo assina com uma chave própria, e um reinício desconecta todo
mundo.

Os exemplos desta página rodam no CI (`tests/docs/test_guide_sessions.py`).

## Contar visitas {#counting-visits}

Salve como `components/visits.q`:

```xml
<q:component name="visits" xmlns:q="https://quantum.lang/ns">
  <q:set name="session.mine" operation="increment" />
  <q:set name="application.everyone" operation="increment" />

  <html><body>
    <p>Your visits: {session.mine}</p>
    <p>Everyone's visits: {application.everyone}</p>
    <p>{request.method} {request.path}</p>
  </body></html>
</q:component>
```

Dois visitantes abrindo `/visits`, um depois do outro, veem:

| Requisição | `session.mine` | `application.everyone` |
|---------|------------------|---------------------|
| visitante A, 1ª | 1 | 1 |
| visitante A, 2ª | 2 | 2 |
| visitante B, 1ª | 1 | 3 |

e a última linha diz `GET /visits`. `operation="increment"` começa do zero
quando a variável ainda não existe (SET-3).

## Um valor que ainda não existe {#a-value-that-does-not-exist-yet}

Fazer contas com um valor de sessão que nunca foi definido é um erro que diz
isso e aponta a correção (EXPR-3):

```xml
<q:set name="session.visits" value="{session.visits + 1}" />
```

**Erro:** `session value used in 'session.visits + 1' is not set`

Use `operation="increment"` para um contador, ou dê um `default` ao valor
(SET-1):

```xml
<q:set name="session.visits" operation="increment" />
<q:return value="Visits: {session.visits}" />
```

**Saída:** `Visits: 1`

A referência sozinha não é um erro: um `{session.name}` que não existe
renderiza vazio (uma página renderiza antes do login), e numa condição é
falso:

```xml
<q:return value="Hello, {session.name}!" />
```

**Saída:** `Hello, !`

Isso faz de "o visitante entrou?" uma linha só. Salve como
`components/welcome.q`:

```xml
<q:component name="welcome" xmlns:q="https://quantum.lang/ns">
  <q:if condition="session.authenticated">
    <p>Welcome back!</p>
    <q:else><a href="/login">Sign in</a></q:else>
  </q:if>
</q:component>
```

Um visitante novo vê **Sign in**; depois que uma ação definiu
`session.authenticated`, a mesma página diz **Welcome back!**

## Escrever a partir de uma ação {#writing-from-an-action}

As ações escrevem em `session.` do mesmo jeito, e a mudança é salva antes do
redirecionamento — veja [Ações e formulários](/pt/guide/actions) e
[Autenticação](/pt/guide/authentication).

## Valores da requisição {#request-values}

| Variável | Contém |
|----------|----------|
| `request.method` | `GET`, `POST`… |
| `request.path` | o caminho, sem a query string |
| `request.url` | a URL inteira, com a query string |

A própria query string está em `query.` (`{query.page}`), e um formulário
enviado em `form.`.
