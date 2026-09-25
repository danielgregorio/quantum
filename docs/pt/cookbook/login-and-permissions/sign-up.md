---
order: 2
title: "Cadastro com o hash da senha"
description: "Crie uma conta com hashPassword, para o banco nunca guardar a senha, com regras em cada campo."
source: cookbook/login-and-permissions/sign-up.md
source_hash: f0ed6cc4abc2
---

# Cadastro com o hash da senha

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/login-and-permissions/sign-up). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** criar uma conta sem nunca guardar a própria senha.

<<< @/../examples/cookbook/login-and-permissions/sign-up/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/login-and-permissions/sign-up/migrations/V001_users.sql{sql}

`hashPassword(password)` devolve um hash bcrypt com um salt novo a cada vez;
o `INSERT` guarda isso. As regras dos `q:param` rodam antes de tudo: uma
senha com menos de 12 caracteres nunca chega à consulta.

<<< @/../examples/cookbook/login-and-permissions/sign-up/components/index.q{xml}

Os testes olham na tabela: a linha tem um hash bcrypt (começa com `$2b$`) e
nenhuma linha guarda a senha como foi digitada:

<<< @/../examples/cookbook/login-and-permissions/sign-up/tests/signup.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/sign-up/output/test-report.txt{text}

Para entrar com esse hash, veja [Login com senha em hash](./login-with-hashed-password.md).
