---
source: tools/dev-panel.md
source_hash: aba77ca68e49
---

# O painel `/_dev`

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/tools/dev-panel).
:::

Enquanto você escreve uma aplicação, o `/_dev` mostra o que as últimas
requisições fizeram: qual componente respondeu, qual `q:action` rodou, cada
consulta com seus parâmetros, tempo e linhas, as variáveis com que cada escopo
terminou, o redirecionamento e a mensagem flash.

Ative-o no `quantum.config.yaml`:

```yaml
server:
  debug: true
  host: 127.0.0.1
```

O `quantum start` mostra o endereço (`Dev panel: http://localhost:8080/_dev`).
Use a aplicação e depois abra `/_dev`: a requisição mais recente é mostrada, e
cada linha da lista abre a sua própria requisição (`/_dev/12`).

| Seção | O que mostra |
|---|---|
| Component, Action | o arquivo `.q` que respondeu e a ação que um POST executou |
| Redirect, Flash | para onde uma ação mandou o navegador, e a mensagem para a próxima página |
| Queries | fonte de dados, SQL, parâmetros, linhas (ou o erro do banco), tempo |
| action / page | as variáveis com que a ação ou a página terminou |
| session / application | os escopos como estavam no fim da requisição |

Um valor com mais de 300 caracteres é cortado. Tudo é escapado: uma variável
que contém HTML aparece como texto.

## Ele só existe durante o desenvolvimento {#it-exists-only-while-developing}
- Com `debug: false` nada é registrado e `/_dev` é um 404.
- Ele só responde a requisições da própria máquina (`127.0.0.1` / `::1`): o
  painel mostra sessões e parâmetros de consultas, então de qualquer outro
  endereço ele não existe — mesmo que a configuração diga `debug: true` atrás de
  um bind público.
- Ele guarda as últimas 30 requisições do processo do servidor, em memória.
