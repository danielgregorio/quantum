---
source: guide/loops.md
source_hash: 0d3575e1e5eb
---

# Estructuras de bucle

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/loops).
:::

Quantum ofrece estructuras de bucle potentes inspiradas en el `cfloop` de ColdFusion, pero pensadas para la programación declarativa moderna. Todos los bucles admiten enlace de datos con variables y se pueden anidar.

## Tipos de bucle {#loop-types}

Quantum tiene cuatro tipos de bucle — `range`, `array`, `list` y `query` — y cada
`q:return` dentro de un bucle agrega un elemento a la lista que devuelve el bucle (LOOP-1).
Cada atributo está en la [Referencia](/reference/tags#q-loop); las reglas son
[LOOP-1 a LOOP-6](/reference/spec#LOOP-1).

### Bucle de rango (`type="range"`) {#range-loop-type-range}

Recorre un rango numérico, con un paso opcional.

```xml
<q:component name="RangeExample" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="5">
    <q:return value="Number {i}" />
  </q:loop>
</q:component>
```

**Output:** `["Number 1", "Number 2", "Number 3", "Number 4", "Number 5"]`

#### Con paso

```xml
<q:loop type="range" var="i" from="1" to="10" step="2">
  <q:return value="Odd: {i}" />
</q:loop>
```

**Output:** `["Odd: 1", "Odd: 3", "Odd: 5", "Odd: 7", "Odd: 9"]`

### Bucle de array (`type="array"`) {#array-loop-type-array}

Recorre arrays JSON, con seguimiento opcional del índice.

```xml
<q:component name="ArrayExample" xmlns:q="https://quantum.lang/ns">
  <q:loop type="array" var="fruit" items='["apple", "banana", "orange"]'>
    <q:return value="Fruit: {fruit}" />
  </q:loop>
</q:component>
```

**Output:** `["Fruit: apple", "Fruit: banana", "Fruit: orange"]`

#### Con índice

```xml
<q:loop type="array" var="fruit" index="idx" items='["apple", "banana", "orange"]'>
  <q:return value="{idx}: {fruit}" />
</q:loop>
```

**Output:** `["0: apple", "1: banana", "2: orange"]`

### Bucle de lista (`type="list"`) {#list-loop-type-list}

Recorre textos con delimitadores.

```xml
<q:component name="ListExample" xmlns:q="https://quantum.lang/ns">
  <q:loop type="list" var="color" items="red,green,blue">
    <q:return value="Color: {color}" />
  </q:loop>
</q:component>
```

**Output:** `["Color: red", "Color: green", "Color: blue"]`

#### Delimitador personalizado

```xml
<q:loop type="list" var="name" items="João|Maria|Pedro" delimiter="|">
  <q:return value="Name: {name}" />
</q:loop>
```

**Output:** `["Name: João", "Name: Maria", "Name: Pedro"]`

## Funciones avanzadas {#advanced-features}

### Aritmética en el enlace de datos {#arithmetic-in-databinding}

Todos los bucles admiten expresiones aritméticas en el enlace de datos de las variables:

```xml
<q:loop type="range" var="i" from="1" to="3">
  <q:return value="Item {i}, Next: {i + 1}, Double: {i * 2}" />
</q:loop>
```

**Output:** `["Item 1, Next: 2, Double: 2", "Item 2, Next: 3, Double: 4", "Item 3, Next: 4, Double: 6"]`

### Bucles anidados {#nested-loops}

Los bucles se pueden anidar para procesar datos complejos:

```xml
<q:component name="NestedExample" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="x" from="1" to="2">
    <q:loop type="range" var="y" from="1" to="2">
      <q:return value="({x},{y})" />
    </q:loop>
  </q:loop>
</q:component>
```

**Output:** `["(1,1)", "(1,2)", "(2,1)", "(2,2)"]`

### Integración con condicionales {#integration-with-conditionals}

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

**Output:** `["1 is odd", "2 is even", "3 is odd", "4 is even", "5 is odd"]`

## Bucle de consulta (`query="name"`) {#query-loop-query-name}

Recorre las filas de un `q:query`; a cada fila se llega por el nombre de la
consulta. La base de datos de ejemplo es la de [Consultas a la base de datos](/guide/query):

```xml
<q:query name="users" datasource="db">
  SELECT name FROM users WHERE status = 'active' ORDER BY name
</q:query>
<q:loop query="users">
  <q:return value="{users.name}" />
</q:loop>
```

**Output:** `["Ana", "Bruno"]`

Una consulta que no devolvió filas ejecuta el cuerpo cero veces (LOOP-4).

## Detalles {#details}

Un bucle sin `type` es un bucle de array cuando tiene `items`, y un bucle de rango
en caso contrario (LOOP-5):

```xml
<q:loop var="x" items="{[10, 20]}">
  <q:return value="{x}" />
</q:loop>
```

**Output:** `[10, 20]`

Un bucle de lista quita los espacios alrededor de cada elemento:

```xml
<q:loop type="list" var="c" items=" red , green ">
  <q:return value="[{c}]" />
</q:loop>
```

**Output:** `["[red]", "[green]"]`

Con `from` mayor que `to`, un bucle de rango se ejecuta cero veces, y un bucle que
no devolvió nada deja que la ejecución siga (LOOP-2):

```xml
<q:loop type="range" var="i" from="5" to="1">
  <q:return value="{i}" />
</q:loop>
<q:return value="none" />
```

**Output:** `none`

## Errores {#errors}

Un bucle de array sobre algo que no es una lista dice qué recibió (LOOP-6):

```xml
<q:set name="n" value="{5}" />
<q:loop type="array" var="x" items="{n}">
  <q:return value="{x}" />
</q:loop>
```

**Error:** `needs a list`

Un `type` que no existe es un error de análisis (PARSE-5):

```xml
<q:loop type="while" var="x">
</q:loop>
```

**Error:** `<q:loop type="while"> does not exist`

## Ver también {#see-also}

- [`q:loop` en la Referencia](/reference/tags#q-loop)
- [Manejo de estado (`q:set`)](/es/guide/state-management)
- [Condicionales (`q:if`)](/es/guide/conditionals)
