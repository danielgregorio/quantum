---
source: guide/loops.md
source_hash: 0d3575e1e5eb
---
# Estruturas de loop

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/loops). O código é o mesmo do original.
:::

O Quantum oferece estruturas de loop inspiradas no `cfloop` do ColdFusion,
mas pensadas para a programação declarativa. Todos os loops aceitam
databinding de variáveis e podem ser aninhados.

## Tipos de loop {#loop-types}

O Quantum tem quatro tipos de loop — `range`, `array`, `list` e `query` — e
cada `q:return` dentro de um loop acrescenta um item à lista que o loop
retorna (LOOP-1). Cada atributo está na [Referência](../../reference/tags#q-loop)
(em inglês); as regras são [LOOP-1 a LOOP-6](../../reference/spec#LOOP-1).

### Loop de intervalo (`type="range"`) {#range-loop-type-range}

Percorre um intervalo numérico, com passo opcional.

```xml
<q:component name="RangeExample" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="5">
    <q:return value="Number {i}" />
  </q:loop>
</q:component>
```

**Saída:** `["Number 1", "Number 2", "Number 3", "Number 4", "Number 5"]`

#### Com passo {#with-step}

```xml
<q:loop type="range" var="i" from="1" to="10" step="2">
  <q:return value="Odd: {i}" />
</q:loop>
```

**Saída:** `["Odd: 1", "Odd: 3", "Odd: 5", "Odd: 7", "Odd: 9"]`

### Loop de array (`type="array"`) {#array-loop-type-array}

Percorre arrays JSON, com o índice opcional.

```xml
<q:component name="ArrayExample" xmlns:q="https://quantum.lang/ns">
  <q:loop type="array" var="fruit" items='["apple", "banana", "orange"]'>
    <q:return value="Fruit: {fruit}" />
  </q:loop>
</q:component>
```

**Saída:** `["Fruit: apple", "Fruit: banana", "Fruit: orange"]`

#### Com índice {#with-index}

```xml
<q:loop type="array" var="fruit" index="idx" items='["apple", "banana", "orange"]'>
  <q:return value="{idx}: {fruit}" />
</q:loop>
```

**Saída:** `["0: apple", "1: banana", "2: orange"]`

### Loop de lista (`type="list"`) {#list-loop-type-list}

Percorre textos com delimitador.

```xml
<q:component name="ListExample" xmlns:q="https://quantum.lang/ns">
  <q:loop type="list" var="color" items="red,green,blue">
    <q:return value="Color: {color}" />
  </q:loop>
</q:component>
```

**Saída:** `["Color: red", "Color: green", "Color: blue"]`

#### Delimitador próprio {#custom-delimiter}

```xml
<q:loop type="list" var="name" items="João|Maria|Pedro" delimiter="|">
  <q:return value="Name: {name}" />
</q:loop>
```

**Saída:** `["Name: João", "Name: Maria", "Name: Pedro"]`

## Recursos avançados {#advanced-features}

### Aritmética no databinding {#arithmetic-in-databinding}

Todos os loops aceitam expressões aritméticas no databinding de variáveis:

```xml
<q:loop type="range" var="i" from="1" to="3">
  <q:return value="Item {i}, Next: {i + 1}, Double: {i * 2}" />
</q:loop>
```

**Saída:** `["Item 1, Next: 2, Double: 2", "Item 2, Next: 3, Double: 4", "Item 3, Next: 4, Double: 6"]`

### Loops aninhados {#nested-loops}

Os loops podem ser aninhados para processar dados mais complexos:

```xml
<q:component name="NestedExample" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="x" from="1" to="2">
    <q:loop type="range" var="y" from="1" to="2">
      <q:return value="({x},{y})" />
    </q:loop>
  </q:loop>
</q:component>
```

**Saída:** `["(1,1)", "(1,2)", "(2,1)", "(2,2)"]`

### Junto com condicionais {#integration-with-conditionals}

```xml
<q:loop type="range" var="i" from="1" to="5">
  <q:if condition="i % 2 == 0">
    <q:return value="{i} is even" />
  <q:else>
    <q:return value="{i} is odd" />
  </q:else>
  </q:if>
</q:loop>
```

**Saída:** `["1 is odd", "2 is even", "3 is odd", "4 is even", "5 is odd"]`

## Loop de consulta (`query="name"`) {#query-loop-query-name}

Percorre as linhas de uma `q:query`; cada linha é acessada pelo nome da
consulta. O banco do exemplo é o de [Database Queries](./query):

```xml
<q:query name="users" datasource="db">
  SELECT name FROM users WHERE status = 'active' ORDER BY name
</q:query>
<q:loop query="users">
  <q:return value="{users.name}" />
</q:loop>
```

**Saída:** `["Ana", "Bruno"]`

Uma consulta que não devolveu linhas roda o corpo zero vezes (LOOP-4).

## Detalhes {#details}

Um loop sem `type` é um loop de array quando tem `items`, e um loop de
intervalo caso contrário (LOOP-5):

```xml
<q:loop var="x" items="{[10, 20]}">
  <q:return value="{x}" />
</q:loop>
```

**Saída:** `[10, 20]`

Um loop de lista tira os espaços em volta de cada item:

```xml
<q:loop type="list" var="c" items=" red , green ">
  <q:return value="[{c}]" />
</q:loop>
```

**Saída:** `["[red]", "[green]"]`

Com `from` acima de `to`, um loop de intervalo roda zero vezes, e um loop que
não retornou nada deixa a execução seguir (LOOP-2):

```xml
<q:loop type="range" var="i" from="5" to="1">
  <q:return value="{i}" />
</q:loop>
<q:return value="none" />
```

**Saída:** `none`

## Erros {#errors}

Um loop de array sobre algo que não é uma lista diz o que recebeu (LOOP-6):

```xml
<q:set name="n" value="{5}" />
<q:loop type="array" var="x" items="{n}">
  <q:return value="{x}" />
</q:loop>
```

**Erro:** `needs a list`

Um `type` que não existe é um erro de parse (PARSE-5):

```xml
<q:loop type="while" var="x">
</q:loop>
```

**Erro:** `<q:loop type="while"> does not exist`

## Veja também {#see-also}

- [`q:loop` na Referência](../../reference/tags#q-loop) (em inglês)
- [Gerenciamento de estado (`q:set`)](./state-management.md)
- [Condicionais (`q:if`)](./conditionals.md)
