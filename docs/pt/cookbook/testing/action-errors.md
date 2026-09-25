---
order: 3
title: "Testar o que uma ação recusa"
description: "Teste os erros de campo, a regra de negócio e o sucesso de uma ação — error=, message=, flash= e a tabela."
source: cookbook/testing/action-errors.md
source_hash: 2e4ddc8a6560
---

# Testar o que uma ação recusa

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/cookbook/testing/action-errors). O código e os resultados são
os mesmos do original, importados dos arquivos testados.
:::

**Tarefa:** provar que um formulário recusa o que deve — um campo que quebra a
sua regra, um valor que o negócio não permite — e que nada é gravado quando
isso acontece.

Um cadastro com dois tipos de recusa: as regras dos `q:param` (verificadas
antes de a ação rodar) e uma regra de negócio na própria ação (o endereço já
é de um membro):

<<< @/../examples/cookbook/testing/action-errors/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/testing/action-errors/migrations/V001_members.sql{sql}

<<< @/../examples/cookbook/testing/action-errors/components/index.q{xml}

`error="name"` verifica o campo em que o envio foi recusado, e `message=` o
texto mostrado ao lado dele. Uma recusa que a própria ação decide é um
redirecionamento com mensagem flash, verificado com `flash=`. `table=` com
`count=` prova que nada foi gravado:

<<< @/../examples/cookbook/testing/action-errors/tests/signup.test.q{xml}

<<< @/../examples/cookbook/testing/action-errors/output/test-report.txt{text}

As regras que um `q:param` aceita (`required`, `minlength`, `type="email"`,
`enum`…) estão em [Actions & Forms](../../../guide/actions.md) (em inglês).

*Testado:* esta página importa os arquivos de
`examples/cookbook/testing/action-errors/`, e o resultado acima é o relatório
de rodá-los.
