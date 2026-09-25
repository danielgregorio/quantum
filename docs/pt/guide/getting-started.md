---
source: guide/getting-started.md
source_hash: e67760de8b10
---
# Primeiros passos

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/getting-started). O código é o mesmo do original.
:::

Bem-vindo ao Quantum! Este guia ajuda você a ter o framework Quantum rodando
em poucos minutos. O código está em inglês, como no original.

## O que é o Quantum? {#what-is-quantum}

O Quantum é um **framework declarativo full-stack** para aplicações web
escritas em XML. Ele foi pensado com a filosofia de "simplicidade acima de
configuração": tornar tarefas complexas simples, mantendo a linguagem limpa e
legível.

### Principais vantagens {#key-benefits}

- **Nenhum JavaScript necessário** - construa aplicações interativas só com XML e SQL
- **IA como tags** - chamadas a modelos, RAG e agentes com ferramentas, sem cola em Python
- **Full-stack** - consultas ao banco, formulários, sessões e autenticação embutidos
- **Entrada validada** - os parâmetros declarados têm o tipo verificado antes de o seu código rodar

## Pré-requisitos {#prerequisites}

- **Python 3.12+**
- **pip**

## Instalação {#installation}

```bash
pip install quantum-framework
quantum --version
```

Os extras opcionais (PostgreSQL/MySQL, RAG, jobs, websockets) e a dependência
extra do alvo desktop estão listados em [Instalação](/pt/guide/installation).

## Seu primeiro componente {#your-first-component}

Crie um arquivo chamado `hello.q`:

```xml
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello World!" />
</q:component>
```

**Saída:** `Hello World!`

Rode:

```bash
quantum run hello.q
```

## Acrescentando conteúdo dinâmico {#adding-dynamic-content}

Vamos deixar mais interessante com variáveis e loops:

```xml
<q:component name="Greetings" xmlns:q="https://quantum.lang/ns">
  <!-- Define a variable -->
  <q:set name="greeting" value="Hello" />

  <!-- Loop through a list -->
  <q:loop type="list" var="name" items="Alice,Bob,Charlie">
    <q:return value="{greeting} {name}!" />
  </q:loop>
</q:component>
```

**Saída:**
```
["Hello Alice!", "Hello Bob!", "Hello Charlie!"]
```

## Usando condicionais {#using-conditionals}

```xml
<q:component name="AgeCheck" xmlns:q="https://quantum.lang/ns">
  <q:set name="age" value="25" />

  <q:if condition="age >= 18">
    <q:return value="You are an adult" />
  </q:if>
  <q:else>
    <q:return value="You are a minor" />
  </q:else>
</q:component>
```

**Saída:** `You are an adult`

## Criando funções {#creating-functions}

```xml
<q:component name="Calculator" xmlns:q="https://quantum.lang/ns">
  <q:function name="add" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:set name="result" value="{a + b}" />
    <q:return value="{result}" />
  </q:function>

  <q:set name="sum" value="{add(5, 3)}" />
  <q:return value="5 + 3 = {sum}" />
</q:component>
```

**Saída:** `5 + 3 = 8`

## Aplicações web {#web-applications}

As páginas são componentes numa pasta `components/`, e o nome do arquivo é a
URL. Crie `components/index.q`:

```xml
<q:component name="index" xmlns:q="https://quantum.lang/ns">
  <html><body>
    <h1>Welcome to My App</h1>
    <p>Now: {dateFormat(now(), '%H:%M')}</p>
  </body></html>
</q:component>
```

**Mostra:** `Welcome to My App`

Inicie o servidor a partir da pasta que contém `components/`:

```bash
quantum start
```

Abra `http://localhost:8080`. O [Início rápido](/pt/guide/quick-start) continua
com um banco de dados e um formulário.

::: warning `q:application type="html"`
Páginas mais antigas descrevem aplicações web como uma
`q:application type="html"` com blocos `q:route`. Essa forma nunca executou
as suas rotas e foi removida na 0.11 — use `components/` como acima. Veja
[q:application](/guide/applications) (em inglês).
:::

## Modo de depuração {#debug-mode}

Para informações detalhadas da execução:

```bash
quantum run hello.q --debug
```

Isso mostra:
- Detalhes do parse do arquivo
- Informações da geração da AST
- Etapas de validação
- O fluxo de execução

## Próximos passos {#next-steps}

- [Instalação](/pt/guide/installation) - o guia de instalação completo
- [Project Structure](/guide/project-structure) - como organizar o seu código (em inglês)
- [Componentes](/pt/guide/components) - os componentes a fundo
- [AI](/guide/ai) - chamadas a LLM, RAG e agentes como tags (em inglês)
- [Receitas](/pt/cookbook/) - receitas testadas, uma tarefa cada
