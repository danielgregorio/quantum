---
order: 5
title: "Sair"
description: "Uma página de logout que limpa a sessão e redireciona; as páginas protegidas se fecham de novo."
source: cookbook/login-and-permissions/sign-out.md
source_hash: 86548aa4610b
---

# Sair

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/login-and-permissions/sign-out). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** encerrar a sessão do usuário.

<<< @/../examples/cookbook/login-and-permissions/sign-out/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/login-and-permissions/sign-out/components/index.q{xml}

Uma página pode mudar a sessão e depois redirecionar: o que ela escreveu na
sessão antes do `q:redirect` continua escrito.

<<< @/../examples/cookbook/login-and-permissions/sign-out/components/logout.q{xml}

<<< @/../examples/cookbook/login-and-permissions/sign-out/components/login.q{xml}

O teste entra, sai, e confere que a página inicial pede o login de novo:

<<< @/../examples/cookbook/login-and-permissions/sign-out/tests/logout.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/sign-out/output/test-report.txt{text}
