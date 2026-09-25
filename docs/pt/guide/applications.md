---
source: guide/applications.md
source_hash: 508e483fc213
---
# q:application

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/applications). O código é o mesmo do original.
:::

Uma **aplicação web** no Quantum não é uma `q:application`: é uma pasta de
páginas em `components/`, servida pelo `quantum start`. Veja
[Primeiros passos](/pt/guide/getting-started) e o
[Início rápido](/pt/guide/quick-start).

`q:application` é o elemento raiz de programas que **não** são páginas web.
Nenhum deles faz parte do núcleo suportado (veja `SUPPORT_TIERS.md`):

| `type` | Nível | O que o `quantum run app.q` faz |
|--------|------|-------------------------------|
| `game` | Laboratório | gera um jogo 2D (`--engine pixi` ou `--engine godot`) |
| `terminal` | Experimental | gera uma interface de terminal |
| `ui` | Experimental | gera uma interface, só o layout (`--target html` ou `textual`; `mobile` é Laboratório) |

Rodar uma aplicação experimental ou do Laboratório mostra um aviso, uma vez,
dizendo isso. As tags e a saída delas podem mudar em qualquer versão.

## Removidos: `type="html"`, `type="api"`, `type="microservices"` {#removed-type-html-type-api-type-microservices}

Versões antigas documentavam servidores web e APIs JSON declarados como
`q:application` com blocos `q:route`. Eles nunca executaram as suas rotas —
`html` falhava ao iniciar, e `api` respondia com o texto literal do primeiro
`q:return` — e foram removidos na 0.11. `q:application` sem `type` queria
dizer `type="html"`, então também é recusada. `type="testing"` (o motor `qtest:`)
foi removido na 0.22; o que o substitui é o [`quantum test`](/pt/guide/testing).

O parser agora para com instruções:

```text
<q:application> type="html" was removed in Quantum 0.11: it never ran its
routes. Build a web app as pages in components/ (components/index.q is /) and
run `quantum start`. See https://quantumframework.net/guide/getting-started
```

No que cada rota se transforma:

| Antes | Agora |
|--------|-----|
| `<q:route path="/about" method="GET">` | `components/about.q` |
| `<q:route path="/" method="GET">` | `components/index.q` |
| `<q:route path="/users" method="POST">` | uma [`q:action`](/pt/guide/actions) em `components/users.q` |
| rota de API JSON | não disponível |
