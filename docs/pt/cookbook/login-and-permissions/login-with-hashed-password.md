---
order: 1
title: "Login com senha em hash"
description: "Confira uma senha contra o seu hash bcrypt com verifyPassword, abra a sessão e mantenha uma página só para quem entrou."
source: cookbook/login-and-permissions/login-with-hashed-password.md
source_hash: 76e6db18e085
---

# Login com senha em hash

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/login-and-permissions/login-with-hashed-password). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** deixar um usuário entrar com e-mail e senha, com o banco guardando
só um hash da senha, e mostrar uma página só para quem entrou.

A tabela guarda um hash bcrypt (feito com `hashPassword`, como na
[receita de cadastro](./sign-up.md)), nunca a senha:

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/migrations/V001_users.sql{sql}

A ação de login procura o usuário e confere a senha com `verifyPassword`. O
resultado é falso, nunca um erro, para uma senha errada, um usuário que não
existe ou um campo vazio. Quando dá certo, ela define as variáveis de sessão
que `require_auth` e `require_role` leem. `session.sessionExpiry` é
obrigatória: uma sessão sem ela conta como expirada.

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/components/login.q{xml}

A página inicial pede uma sessão de quem entrou com `require_auth="true"`:

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/components/index.q{xml}

Um endereço errado e uma senha errada recebem a mesma mensagem, então o
formulário não conta a um estranho quais endereços têm conta:

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/tests/login.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/output/test-report.txt{text}

Mais no guia [Authentication](../../../guide/authentication.md) (em inglês).
