---
title: Roadmap
source: roadmap/index.md
source_hash: bf70795ae40e
---

# Roadmap

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/roadmap/).
:::

O que o Quantum é hoje, e o que vem a seguir. Não há datas aqui, nem
promessas além dos [níveis de suporte](https://github.com/danielgregorio/quantum/blob/main/SUPPORT_TIERS.md):
um item está pronto quando saiu numa versão e a entrada dele no
[registro de mudanças](/changelog/) diz isso.

Cada item mostra seu estado: **planejado** (aprovado, não começou), **em
desenho** (sendo escrito antes de qualquer código) ou **em andamento** (sendo
construído agora).

## 1.0 — hoje

O Quantum 1.0 é aplicações web declarativas em XML, com IA e RAG na própria
linguagem. O que a 1.0 promete é definido pelos níveis:

- O **Núcleo** (Core: componentes, consultas e transações, ações e
  formulários, arquivos, e-mail, autenticação, o conjunto `ui:*` do Núcleo) e
  a **IA** (`q:llm`, `q:knowledge`, `q:agent`) seguem o versionamento
  semântico: uma versão 1.x não quebra um programa que usa só eles. A IA
  também é testada contra um modelo de verdade antes de cada versão.
- As tags **Experimental** funcionam, sem promessa de estabilidade.
- Os projetos do **Laboratório** ficam no repositório porque pressionam a
  linguagem; não fazem parte do produto e não têm promessa.

O que roda hoje é medido, não declarado: veja o [Status](/status/). Cada tag e
cada regra estão na [Referência](/reference/).

## A seguir

### IA

| Item | Estado |
|---|---|
| Um modelo falso para desenvolvimento: construir e testar páginas de IA sem nenhum modelo rodando, com respostas iguais em toda execução | planejado |
| IA no [painel de desenvolvimento](/tools/dev-panel): cada chamada que uma página fez, com o prompt, as fontes usadas, a resposta, o tempo e os tokens | planejado |
| Orçamentos e remoção de dados: um limite de gastos por aplicação, e dados pessoais removidos antes de irem para o modelo, com o registro de ambos guardado | planejado |
| Conversas que lembram, e um `ui:chat` para guardá-las | planejado |

### Uma aplicação que conhece a si mesma

| Item | Estado |
|---|---|
| `quantum map`: quais páginas e ações leem e escrevem cada tabela | planejado |
| `quantum explain page.q`: o que uma página lê, escreve e de que depende, em texto simples | planejado |
| `q:cache` por tabela: um trecho em cache que é renovado quando uma escrita toca uma das tabelas dele, sem tempo de expiração para adivinhar | planejado |

### Testes

O `quantum test` saiu na 1.0 ([Testing](/guide/testing), em inglês). A seguir:

| Item | Estado |
|---|---|
| Um teste rodando em todas as telas: o navegador e o console | planejado |
| Testes derivados das regras de uma ação, escritos para você | planejado |
| Testes de IA repetidos a partir de uma gravação, para rodarem sem modelo | planejado |
| Cobertura nos termos da própria aplicação: quais páginas, ações e regras uma suíte alcança | planejado |

### O site

| Item | Estado |
|---|---|
| Receitas: receitas curtas, cada uma testada no CI | em andamento |
| O site em mais idiomas | em andamento |
| Um playground: escrever Quantum e rodar no navegador | planejado |
| Benchmarks que qualquer pessoa pode rodar de novo | planejado |

## Laboratório

| Item | Estado |
|---|---|
| Games 2: jogos como uma simulação declarativa determinística, em que as mesmas entradas dão sempre o mesmo jogo, para que um jogo possa ser testado e repetido | em desenho |

O trabalho do Laboratório não tem promessa: pode mudar ou parar a qualquer
momento.
