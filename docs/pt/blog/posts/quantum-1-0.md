---
title: Quantum 1.0
date: 2026-09-25
description: Aplicações web declarativas em XML, com IA e RAG na linguagem — o que a 1.0 promete, como foi verificada e o que vem a seguir.
source: blog/posts/quantum-1-0.md
source_hash: 83905caaa8ae
---

# Quantum 1.0

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/blog/posts/quantum-1-0).
:::

*2026-09-25*

Saiu o Quantum 1.0. Este post diz o que ele é, o que o número da versão
promete, como verificamos que a promessa se cumpre e o que vem a seguir.

## O que o Quantum é

**Aplicações web declarativas em XML, com IA e RAG na própria linguagem. Sem
cadeia de build, sem JavaScript, sem framework de front-end.**

Uma página é um arquivo `.q`. Estado, SQL parametrizado, formulários e sua
validação, componentes, autenticação, upload de arquivos e e-mail são tags;
também são tags uma chamada a um LLM que responde a partir de uma base de
conhecimento e cita as fontes, e um agente cujas ferramentas são escritas no
próprio Quantum. O `quantum start` serve uma pasta de páginas; não há nada
para compilar.

É para quem desenvolve sozinho e equipes pequenas que fazem ferramentas
internas, dashboards, painéis de administração e aplicações de IA e preferem
não manter uma cadeia de build de front-end. Não é um substituto de uso geral
para um framework JavaScript.

## O que a 1.0 promete

A promessa está escrita nos
[níveis de suporte](https://github.com/danielgregorio/quantum/blob/main/SUPPORT_TIERS.md),
e o engine a impõe:

- **Núcleo** (Core) — componentes, `q:set`, `q:if`, `q:loop`, `q:function`,
  `q:query` e `q:transaction`, `q:action` e formulários, `q:invoke`, `q:data`,
  composição, arquivos, e-mail, o conjunto `ui:*` do Núcleo, autenticação.
- **IA** — `q:llm`, `q:knowledge`, `q:agent`.
- **Experimental** — tags que rodam mas não têm promessa (jobs, mensageria,
  websockets, scripting em Python, o alvo de terminal, …). Uma tag fora do
  Núcleo e da IA mostra um aviso na primeira vez que roda.
- **Laboratório** — o engine de jogos 2D e outros alvos mantidos para
  exercitar a linguagem, sem promessa nenhuma.

A partir da 1.0, **o Núcleo e a IA seguem o versionamento semântico**: uma
versão 1.x não quebra um programa que usa só eles. Uma mudança que quebraria
espera a 2.0. Experimental e Laboratório podem mudar em qualquer versão.

## Como foi verificado

Uma promessa vale o que vale aquilo que a verifica. Quatro coisas verificam:

1. **Uma especificação com IDs de regra.** O [SPEC.md](https://github.com/danielgregorio/quantum/blob/main/SPEC.md)
   diz o que um programa Quantum significa em 137 regras numeradas (`LOOP-2`,
   `DB-4`, `IA-6`…), e está congelado na 1.0. Cada regra é citada por pelo
   menos um teste de conformidade — são 866 — e o CI falha se uma regra não
   tem teste ou se um teste cita uma regra que não existe.
2. **Aplicações que o usam.** O repositório tem aplicações pequenas e reais
   para cada nível: uma lista de tarefas desenhada com `ui:*` no navegador, no
   terminal e numa janela de desktop; um blog; um helpdesk com anexos e
   e-mail; uma transferência bancária dentro de uma `q:transaction`; um
   assistente de documentação e um agente de loja para as tags de IA.
3. **`quantum test`.** As aplicações são testadas na própria linguagem — um
   `*.test.q` visita uma página, envia uma ação e confere o redirecionamento, a
   mensagem flash, as linhas da tabela e o histórico, cada teste num banco
   novo construído a partir das migrações. As suítes das aplicações rodam no
   CI.
4. **Testes de IA ao vivo.** As tags de IA são testadas contra um servidor de
   modelos de verdade antes de cada versão, com verificações estruturais (a
   ferramenta foi chamada, o trecho certo foi recuperado), nunca texto exato.

E a [página de status](/status/) não é escrita à mão: um script roda cada
exemplo e informa o que passa pelo parser e o que executa.

## O que mudou no caminho

O caminho da 0.9 até a 1.0 foi principalmente tornar a promessa verdadeira:
comportamentos que falhavam em silêncio — um nome escrito errado, um atributo
que não fazia nada, uma chave faltando, um campo de consulta que não existe —
agora são erros que apontam a linha. O
[registro de mudanças](/changelog/v1-0-0) tem os detalhes, versão por versão.

## O que vem a seguir

- **O `quantum test` cresce**: mais do que uma aplicação faz deve poder ser
  verificado na própria linguagem.
- **Experimental → Núcleo, uma tag de cada vez**, e só com uma regra na SPEC,
  um teste que a cita, um exemplo que roda e uma página no guia.
- **Este site**: traduções e um domínio próprio.

Bugs, perguntas e ideias são bem-vindos nas
[Issues do GitHub](https://github.com/danielgregorio/quantum/issues). Se o
Quantum é útil para você, a [página de apoio](/pt/sponsor/) diz o que a ajuda
paga.
