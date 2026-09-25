---
source: guide/components.md
source_hash: 1a0d2d913b73
---
# Componentes

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/components). O código é o mesmo do original.
:::

Os componentes são os blocos fundamentais das aplicações Quantum. Eles
encapsulam lógica, processamento de dados e geração de saída em unidades
modulares e reutilizáveis.

Os exemplos desta página rodam a cada mudança: os que têm uma **Saída:**
exatamente como aparecem, e os outros — os que recebem parâmetros, e a página
que usa um card — por `tests/docs/test_guide_components.py`.

## Estrutura básica {#basic-structure}

Todo componente Quantum segue esta estrutura:

```xml
<q:component name="ComponentName" xmlns:q="https://quantum.lang/ns">
  <!-- Component logic here -->
  <q:return value="output" />
</q:component>
```

**Saída:** `"output"`

### Elementos obrigatórios {#required-elements}

| Elemento | Descrição |
|---------|-------------|
| `q:component` | Elemento raiz |
| atributo `name` | O nome do componente (PascalCase) |
| `xmlns:q` | Declaração do namespace do Quantum |

## Componentes simples {#simple-components}

### Hello World {#hello-world}

```xml
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello, World!" />
</q:component>
```

**Saída:** `"Hello, World!"`

### Retornar antes {#returning-early}

`q:return` termina o componente: o primeiro que roda é o resultado, e o que
vem depois não roda. Dentro de um `q:if`, ele só termina o componente quando o
seu ramo roda.

```xml
<q:component name="Stock" xmlns:q="https://quantum.lang/ns">
  <q:set name="stock" value="0" type="number" />

  <q:if condition="stock == 0">
    <q:return value="Sold out" />
  </q:if>
  <q:return value="{stock} in stock" />
</q:component>
```

**Saída:** `"Sold out"`

Dentro de um loop é diferente: cada `q:return` acrescenta um item a uma lista
(veja [Loops em componentes](#loops-in-components)).

## Parâmetros do componente {#component-parameters}

Receba entradas com `q:param`:

```xml
<q:component name="Greeting" xmlns:q="https://quantum.lang/ns">
  <q:param name="name" type="string" required="true" />
  <q:param name="formal" type="boolean" default="false" />

  <q:if condition="formal">
    <q:return value="Good day, {name}." />
  </q:if>
  <q:else>
    <q:return value="Hey {name}!" />
  </q:else>
</q:component>
```

Com `name` = `Ana` ele retorna `"Hey Ana!"`; com `formal` = `true` também,
`"Good day, Ana."`. Sem `name` é um erro:
`Required parameter 'name' is missing`.

### Atributos do parâmetro {#parameter-attributes}

| Atributo | Descrição | Exemplo |
|-----------|-------------|---------|
| `name` | Nome do parâmetro | `name="userId"` |
| `type` | Tipo de dado | `type="string"` |
| `required` | Parâmetro obrigatório | `required="true"` |
| `default` | Valor padrão | `default="10"` |

### Tipos {#types}

O `type` de um `q:param` é um de `string`, `integer`, `number`, `decimal`,
`boolean`, `array`, `object`, `json`, `email`, `url`, `date`, `file` ou `any`
(e os apelidos `text`, `int`, `long`, `numeric`, `float`, `double`, `binary`,
`upload`). Qualquer outro nome é um erro de parse.

Um valor que não cabe é um erro que nomeia o parâmetro: `age` do tipo
`number` recebendo `abc` para o componente com
`Parameter 'age' must be a number, got 'abc'`, e um `email` recebendo
`not-an-email` com `Parameter 'email' must be a valid email`.

## Estado do componente {#component-state}

Use `q:set` para variáveis internas. Um `q:set` posterior com o mesmo nome
substitui o valor:

```xml
<q:component name="Counter" xmlns:q="https://quantum.lang/ns">
  <q:set name="count" value="0" type="number" />
  <q:set name="step" value="1" type="number" />
  <q:set name="count" value="{count + step}" />

  <q:return value="Count: {count}" />
</q:component>
```

**Saída:** `"Count: 1"`

### Validação de variáveis {#variable-validation}

O `q:set` pode verificar o valor que guarda — `validate` (`email`, `url`, …),
`range` e `enum`:

```xml
<q:set name="email"
       value="user@example.com"
       validate="email" />

<q:set name="status"
       type="string"
       value="active"
       enum="active,inactive,pending" />

<q:set name="age"
       type="number"
       value="200"
       range="0..150" />
```

**Erro:** `Value must be between 0 and 150`

Os dois primeiros passam; o terceiro para o componente. Um `status` fora da
lista o para com `Value must be one of: active, inactive, pending`, e um
e-mail que não é um e-mail com `Invalid email format`.

## Funções do componente {#component-functions}

Defina lógica reutilizável com `q:function` e chame-a numa expressão:

```xml
<q:component name="Calculator" xmlns:q="https://quantum.lang/ns">
  <q:function name="add" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:return value="{a + b}" />
  </q:function>

  <q:function name="multiply" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:return value="{a * b}" />
  </q:function>

  <q:set name="sum" value="{add(5, 3)}" />
  <q:set name="product" value="{multiply(4, 7)}" />

  <q:return value="5 + 3 = {sum}, 4 * 7 = {product}" />
</q:component>
```

**Saída:** `"5 + 3 = 8, 4 * 7 = 28"`

Mais em [Funções](/pt/guide/functions).

## Loops em componentes {#loops-in-components}

Um `q:return` dentro de um loop não o termina: cada um acrescenta um item, e o
componente retorna a lista.

### Loop de intervalo {#range-loop}

```xml
<q:component name="Numbers" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="5">
    <q:return value="Number {i}" />
  </q:loop>
</q:component>
```

**Saída:** `["Number 1", "Number 2", "Number 3", "Number 4", "Number 5"]`

### Loop de array {#array-loop}

```xml
<q:component name="Fruits" xmlns:q="https://quantum.lang/ns">
  <q:set name="fruits" value='["Apple", "Banana", "Cherry"]' />

  <q:loop type="array" var="fruit" items="{fruits}">
    <q:return value="I like {fruit}" />
  </q:loop>
</q:component>
```

**Saída:** `["I like Apple", "I like Banana", "I like Cherry"]`

### Loop de lista {#list-loop}

```xml
<q:component name="Colors" xmlns:q="https://quantum.lang/ns">
  <q:loop type="list" var="color" items="red,green,blue" delimiter=",">
    <q:return value="Color: {color}" />
  </q:loop>
</q:component>
```

**Saída:** `["Color: red", "Color: green", "Color: blue"]`

### Loop com índice {#loop-with-index}

`index` nomeia a posição, contada a partir de 0:

```xml
<q:component name="IndexedList" xmlns:q="https://quantum.lang/ns">
  <q:set name="items" value='["First", "Second", "Third"]' />

  <q:loop type="array" var="item" items="{items}" index="i">
    <q:return value="{i + 1}. {item}" />
  </q:loop>
</q:component>
```

**Saída:** `["1. First", "2. Second", "3. Third"]`

## Condicionais {#conditionals}

### If/Else básico {#basic-if-else}

```xml
<q:component name="AgeCheck" xmlns:q="https://quantum.lang/ns">
  <q:param name="age" type="number" required="true" />

  <q:if condition="age >= 18">
    <q:return value="Adult" />
  </q:if>
  <q:else>
    <q:return value="Minor" />
  </q:else>
</q:component>
```

Com `age` = `20` ele retorna `"Adult"`; com `15`, `"Minor"`.

### Várias condições {#multiple-conditions}

```xml
<q:component name="Grade" xmlns:q="https://quantum.lang/ns">
  <q:param name="score" type="number" required="true" />

  <q:if condition="score >= 90">
    <q:return value="A" />
  </q:if>
  <q:elseif condition="score >= 80">
    <q:return value="B" />
  </q:elseif>
  <q:elseif condition="score >= 70">
    <q:return value="C" />
  </q:elseif>
  <q:elseif condition="score >= 60">
    <q:return value="D" />
  </q:elseif>
  <q:else>
    <q:return value="F" />
  </q:else>
</q:component>
```

Com `score` = `85` ele retorna `"B"`; com `42`, `"F"`.

## Databinding {#data-binding}

Use `{expression}` para valores dinâmicos:

### Variáveis simples {#simple-variables}

```xml
<q:set name="name" value="Alice" />
<q:return value="Hello, {name}!" />
```

**Saída:** `"Hello, Alice!"`

### Propriedades de objetos {#object-properties}

```xml
<q:set name="user" type="object" value='{"name": "Bob", "age": 30}' />
<q:return value="{user.name} is {user.age} years old" />
```

**Saída:** `"Bob is 30 years old"`

### Expressões {#expressions}

```xml
<q:set name="price" value="100" />
<q:set name="quantity" value="5" />
<q:return value="Total: ${price * quantity}" />
```

**Saída:** `"Total: $500"`

### Funções de texto {#string-functions}

As funções são chamadas com o valor como argumento — veja a
[lista de funções](/pt/guide/databinding#functions):

```xml
<q:set name="text" value="hello world" />
<q:return value="{upper(text)}" />
```

**Saída:** `"HELLO WORLD"`

## Loops aninhados {#nested-loops}

Os itens de um loop interno entram na lista do loop externo um a um, em
ordem:

```xml
<q:component name="Report" xmlns:q="https://quantum.lang/ns">
  <q:set name="categories" value='[
    {"name": "Electronics", "items": ["Phone", "Laptop"]},
    {"name": "Clothing", "items": ["Shirt", "Pants"]}
  ]' />

  <q:loop type="array" var="category" items="{categories}">
    <q:return value="Category: {category.name}" />

    <q:loop type="array" var="item" items="{category.items}">
      <q:return value="  - {item}" />
    </q:loop>
  </q:loop>
</q:component>
```

**Saída:** `["Category: Electronics", "  - Phone", "  - Laptop", "Category: Clothing", "  - Shirt", "  - Pants"]`

## Usar um componente dentro de outro {#using-one-component-inside-another}

Uma página usa outro componente — um card, um layout — importando-o e
escrevendo-o como uma tag. Salve como `components/_parts/Card.q`:

```xml
<q:component name="Card" xmlns:q="https://quantum.lang/ns">
  <q:param name="title" required="true" />
  <section class="card">
    <h2>{title}</h2>
    <q:slot />
  </section>
</q:component>
```

Salve como `components/index.q`:

```xml
<q:component name="Home" xmlns:q="https://quantum.lang/ns">
  <q:import component="Card" from="_parts" />
  <q:set name="open" value="3" type="number" />

  <Card title="Open tickets: {open}">
    <p>The oldest is from {'Monday'}.</p>
  </Card>
</q:component>
```

Abrir `/` mostra o card com o título **Open tickets: 3** e, dentro dele,
**The oldest is from Monday.**

- `q:import` procura o componente em `paths.components` do
  `quantum.config.yaml`, na pasta `from` quando declarada. Uma pasta cujo nome
  começa com `_` não é servida como páginas, o que serve bem a partes como
  esta.
- Cada atributo da tag é um `q:param` do componente, avaliado na página:
  `title="Open tickets: {open}"` enxerga o `open` da página. Um parâmetro
  obrigatório que falta é um erro.
- O que está entre `<Card>` e `</Card>` é desenhado no escopo da página e vai
  para onde o componente tem `<q:slot />`.
- O componente usa as fontes de dados e os serviços da página e enxerga os
  mesmos `session`, `application` e `request`.
- Um componente que não é encontrado, ou que falha, é um erro da página —
  nunca uma seção que some em silêncio.

## Erros {#errors}

Um componente que não consegue fazer o que diz para com um erro que diz por
quê.

### Um parâmetro que falta {#a-missing-parameter}

```xml
<q:component name="Ticket" xmlns:q="https://quantum.lang/ns">
  <q:param name="id" type="integer" required="true" />
  <q:return value="Ticket {id}" />
</q:component>
```

**Erro:** `Required parameter 'id' is missing`

### Uma variável que não existe {#a-variable-that-does-not-exist}

```xml
<q:component name="ErrorExample" xmlns:q="https://quantum.lang/ns">
  <q:return value="{undefined_variable}" />
</q:component>
```

**Erro:** `variable 'undefined_variable' is not defined`

## Boas práticas {#best-practices}

### 1. Uma responsabilidade só {#_1-single-responsibility}

Cada componente deve ter um propósito claro:

```xml
<!-- Good: Focused component -->
<q:component name="UserEmail" xmlns:q="https://quantum.lang/ns">
  <q:param name="email" type="email" required="true" />
  <q:return value="{email}" />
</q:component>
```

### 2. Use nomes descritivos {#_2-use-descriptive-names}

Prefira `<q:component name="ProductPriceFormatter">` a
`<q:component name="PF">`: o nome é o que uma página que o usa lê.

### 3. Documente os parâmetros {#_3-document-parameters}

```xml
<!--
  Formats a price with a currency code.

  @param amount - The price amount (required)
  @param currency - Currency code (default: USD)
-->
<q:component name="PriceFormatter" xmlns:q="https://quantum.lang/ns">
  <q:param name="amount" type="decimal" required="true" />
  <q:param name="currency" type="string" default="USD" />
  <q:return value="{currency} {round(amount, 2)}" />
</q:component>
```

Com `amount` = `19.999` ele retorna `"USD 20.0"`.

### 4. Valide a entrada {#_4-validate-input}

```xml
<q:component name="SafeComponent" xmlns:q="https://quantum.lang/ns">
  <q:param name="count" type="integer" required="true" />

  <q:if condition="count < 1">
    <q:return value="Error: count must be at least 1" />
  </q:if>

  <q:return value="{count} item(s)" />
</q:component>
```

Com `count` = `3` ele retorna `"3 item(s)"`; com `-1`,
`"Error: count must be at least 1"`; com `abc`, o erro
`Parameter 'count' must be an integer, got 'abc'`.

## Próximos passos {#next-steps}

- [Gerenciamento de estado](/pt/guide/state-management) - variáveis em detalhe
- [Funções](/pt/guide/functions) - lógica reutilizável
- [Loops](/pt/guide/loops) - padrões de iteração
- [Condicionais](/pt/guide/conditionals) - controle de fluxo
