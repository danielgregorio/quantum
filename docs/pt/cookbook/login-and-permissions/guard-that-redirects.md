---
order: 4
title: "Uma guarda que redireciona"
description: "Um q:if no topo com q:redirect protege uma página e cada ação dela: um envio sem sessão não grava nada."
source: cookbook/login-and-permissions/guard-that-redirects.md
source_hash: 94e99b99ab2d
---

# Uma guarda que redireciona

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/login-and-permissions/guard-that-redirects). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** mandar quem não entrou para a página de login com uma mensagem, e
garantir que também não consiga enviar para as ações da página.

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/migrations/V001_notes.sql{sql}

Um `q:if` no topo da página cujo ramo tem um `q:redirect` é uma **guarda**.
Ela roda antes da página e antes de cada uma das suas ações, então um envio
mandado direto para `add` também é barrado:

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/components/index.q{xml}

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/components/login.q{xml}

O segundo teste envia para a ação sem sessão e confere que nenhuma linha foi
gravada:

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/tests/guard.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/output/test-report.txt{text}

Uma guarda pode verificar qualquer coisa que a sessão guarda. Para pedir só
um usuário que entrou ou um papel, `require_auth` e `require_role` dizem isso
num atributo ([Uma página só para um papel](./page-for-one-role.md)).
