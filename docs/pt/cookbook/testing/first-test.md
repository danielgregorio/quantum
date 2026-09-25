---
order: 1
title: "Um primeiro teste com quantum test"
description: "Teste uma página e a sua ação no próprio Quantum — visitar, enviar, conferir a mensagem flash, a tabela e o erro de campo."
source: cookbook/testing/first-test.md
source_hash: 0285b0b6d11f
---

# Um primeiro teste com `quantum test`

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/testing/first-test). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** conferir que uma página lista o que está no banco, que a sua ação
grava uma linha e avisa, e que recusa uma entrada ruim — sem escrever Python.

Uma aplicação pequena: uma tabela, uma página que a lista e uma ação que
acrescenta a ela.

<<< @/../examples/cookbook/testing/first-test/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/testing/first-test/migrations/V001_notes.sql{sql}

<<< @/../examples/cookbook/testing/first-test/components/index.q{xml}

Os testes ficam ao lado, em `tests/`. Cada `q:test` começa de um banco novo
construído a partir de `migrations/`, então um não depende do outro:

<<< @/../examples/cookbook/testing/first-test/tests/notes.test.q{xml}

Rode a partir da pasta da aplicação:

```bash
quantum test
```

<<< @/../examples/cookbook/testing/first-test/output/test-report.txt{text}

`test:visit` abre a página; `test:submit` envia uma ação com os outros
atributos como campos; `test:expect` confere o que aconteceu — o status, o
redirecionamento e a mensagem flash, um texto na página, linhas numa tabela,
ou o campo em que uma entrada foi recusada. O vocabulário completo está no
guia [Testing an App](../../../guide/testing.md) (em inglês).

*Testado:* esta página importa os arquivos de
`examples/cookbook/testing/first-test/`, e o resultado acima é o relatório de
rodá-los.
