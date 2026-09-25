---
order: 6
title: "A mesma página num terminal"
description: "Uma página ui:*, servida ao navegador pelo quantum start e desenhada num terminal pelo quantum console."
source: cookbook/screens/browser-and-console.md
source_hash: 0ceede109e4d
---

# A mesma página num terminal

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/screens/browser-and-console). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** usar a mesma página a partir de um navegador e de um terminal.

<<< @/../examples/cookbook/screens/browser-and-console/quantum.config.yaml{yaml}

Uma página feita de tags `ui:*` do Núcleo não está presa ao HTML. O
`quantum start` a serve a um navegador; o `quantum console` a desenha no
terminal, e o `quantum desktop` numa janela local. O console pede ao mesmo
servidor a árvore de visualização da página e envia as mesmas ações: a regra
de `name`, a mensagem flash e a sessão funcionam do mesmo jeito, sem nada
traduzido.

<<< @/../examples/cookbook/screens/browser-and-console/components/index.q{xml}

No navegador, `quantum test`:

<<< @/../examples/cookbook/screens/browser-and-console/tests/guests.test.q{xml}

<<< @/../examples/cookbook/screens/browser-and-console/output/test-report.txt{text}

No console, [`tests/docs/test_cookbook_console.py`](https://github.com/danielgregorio/quantum/blob/main/tests/docs/test_cookbook_console.py) abre a mesma
aplicação no renderizador do console. Ele confere que cada texto que esta
suíte espera numa visita simples está na tela do console, depois digita um
nome curto demais e um que está bom, e aperta **Sign**: o console mostra o
erro do campo, depois a mensagem flash e o novo nome.

```bash
quantum start      # http://localhost:8080
quantum console    # the same page in this terminal
```

Veja [UI-3](../../../reference/spec.md#UI-3) e [UI-7](../../../reference/spec.md#UI-7).
