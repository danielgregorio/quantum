---
order: 3
title: "Uma página só para um papel"
description: "require_role reserva uma página aos administradores: um membro recebe 403, e quem não entrou é mandado para o login."
source: cookbook/login-and-permissions/page-for-one-role.md
source_hash: 8674b9cce0ea
---

# Uma página só para um papel

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/login-and-permissions/page-for-one-role). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** mostrar uma página só para administradores.

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/quantum.config.yaml{yaml}

`require_auth="true"` pede uma sessão de quem entrou; `require_role`, um dos
papéis listados em `session.userRole` (vários são separados por vírgulas,
`require_role="admin,editor"`):

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/components/reports.q{xml}

Sem sessão, a resposta redireciona para `/login` (mude com
`security.login_url`):

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/components/login.q{xml}

`test:as` faz a sessão do teste entrar com um papel, sem senha:

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/tests/reports.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/output/test-report.txt{text}
