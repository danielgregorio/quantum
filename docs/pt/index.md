---
layout: home
title: Quantum
hero:
  name: Quantum
  text: Aplicações web a partir de páginas declarativas
  tagline: Banco de dados, formulários, sessões e IA na linguagem. Sem cadeia de build, sem JavaScript, sem framework de front-end.
  actions:
    - theme: brand
      text: Começar (em inglês)
      link: /guide/getting-started
    - theme: alt
      text: Por que Quantum (em inglês)
      link: /guide/why-quantum
    - theme: alt
      text: Ver no GitHub
      link: https://github.com/danielgregorio/quantum

features:
  - icon: "🎯"
    title: Uma página, de cima a baixo
    details: Guardas, ações, consultas e a tela na ordem em que rodam. Nenhum JavaScript para escrever.
  - icon: "🖥️"
    title: Navegador, terminal, desktop
    details: A mesma página roda num navegador (quantum start), num terminal (quantum console) e numa janela de desktop (quantum desktop).
  - icon: "🧾"
    title: Formulários que conhecem suas regras
    details: Um formulário pega dos q:param da sua ação o obrigatório, os tamanhos, os tipos e as opções — verificados no navegador e no servidor.
  - icon: "🗃️"
    title: SQL em que você pode confiar
    details: Consultas parametrizadas, um plano de esquema declarativo, histórico de mudanças e quantum check contra o seu banco.
  - icon: "🤖"
    title: IA na linguagem
    details: q:llm responde a partir dos seus documentos, com fontes e em streaming; q:agent chama ferramentas que você escreve em Quantum.
  - icon: "✅"
    title: Especificado e testado
    details: Cada regra da SPEC tem um teste; as aplicações de exemplo rodam de ponta a ponta no CI.
source: index.md
source_hash: 15bee710f3f5
---

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada;
correções são bem-vindas no GitHub. Se algo não bater, vale o
[original em inglês](/). Por enquanto, o resto da documentação está em inglês.
:::

# Bem-vindo ao Quantum

O Quantum constrói **aplicações web a partir de páginas XML declarativas** — a
mesma página também roda num terminal e numa janela de desktop. Inspirado no
ColdFusion e no Adobe Flex, ele permite construir ferramentas internas, painéis
e aplicações de IA sem escrever JavaScript.
[Por que Quantum?](/guide/why-quantum) (em inglês)

## Exemplo rápido

Uma página que lista notas de um banco de dados e adiciona uma a partir de um
formulário — com a regra do campo, a inserção e a mensagem depois dela:

<<< @/../examples/cookbook/testing/first-test/components/index.q{xml}

Esta página e o teste dela rodam a cada mudança; veja a receita
[A first test with quantum test](/cookbook/testing/first-test) (em inglês).

## Principais recursos

### A linguagem
- **Componentes**: arquivos `.q` reutilizáveis, com parâmetros e valores de retorno
- **Estado**: `q:set` para variáveis, com validação e verificação de tipos
- **Laços**: iteração sobre intervalos, arrays, listas e consultas com `q:loop`
- **Condicionais**: `q:if`/`q:elseif`/`q:else` completos
- **Funções**: lógica reutilizável com `q:function`

### Telas (`ui:*`)
- **Um conjunto essencial**: janelas, caixas, painéis, tabelas, listas, formulários e campos ([UI](/guide/ui))
- **Três renderizadores**: navegador, terminal e janela de desktop, a partir da mesma página
- **Formulários a partir das ações**: campos, regras e erros vêm dos `q:param` da ação
- **Tabelas a partir das consultas**: paginação, busca enquanto você digita, células ordenáveis e editáveis

### Backend
- **Consultas ao banco**: SQL com parâmetros, planos de esquema, histórico de mudanças, `quantum check`
- **Autenticação**: gestão de sessões e controle de acesso por papéis
- **Importação de dados**: fontes JSON, CSV e XML
- **Arquivos e e-mail**: uploads, downloads protegidos e `q:mail` ([guia](/guide/files-and-mail))
- **IA**: `q:llm` com fontes e streaming, `q:knowledge`, `q:agent` ([guia](/guide/ai))

## Filosofia

> **Simplicidade acima de configuração**

O Quantum prioriza a legibilidade e a facilidade de uso. Se você sabe XML e
SQL, consegue construir aplicações completas.

## Primeiros passos

```bash
pip install quantum-framework
quantum start          # in an application folder; the guide builds one step by step
```

[Leia o guia de primeiros passos](/guide/getting-started) (em inglês)
