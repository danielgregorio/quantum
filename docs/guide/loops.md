# Loop Structures

Quantum provides powerful loop structures inspired by ColdFusion's `cfloop` but designed for modern declarative programming. All loops support variable databinding and can be nested.

## Loop Types

Quantum has four loop types — `range`, `array`, `list` and `query` — and each
`q:return` inside a loop adds an item to the list the loop returns (LOOP-1).
Every attribute is in the [Reference](../reference/tags#q-loop); the rules are
[LOOP-1 to LOOP-6](../reference/spec#LOOP-1).

### Range Loop (`type="range"`)

Iterates over a numeric range with optional step.

```xml
<q:component name="RangeExample" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="5">
    <q:return value="Number {i}" />
  </q:loop>
</q:component>
```

**Output:** `["Number 1", "Number 2", "Number 3", "Number 4", "Number 5"]`

#### With Step

```xml
<q:loop type="range" var="i" from="1" to="10" step="2">
  <q:return value="Odd: {i}" />
</q:loop>
```

**Output:** `["Odd: 1", "Odd: 3", "Odd: 5", "Odd: 7", "Odd: 9"]`

### Array Loop (`type="array"`)

Iterates over JSON arrays with optional index tracking.

```xml
<q:component name="ArrayExample" xmlns:q="https://quantum.lang/ns">
  <q:loop type="array" var="fruit" items='["apple", "banana", "orange"]'>
    <q:return value="Fruit: {fruit}" />
  </q:loop>
</q:component>
```

**Output:** `["Fruit: apple", "Fruit: banana", "Fruit: orange"]`

#### With Index

```xml
<q:loop type="array" var="fruit" index="idx" items='["apple", "banana", "orange"]'>
  <q:return value="{idx}: {fruit}" />
</q:loop>
```

**Output:** `["0: apple", "1: banana", "2: orange"]`

### List Loop (`type="list"`)

Iterates over delimited strings.

```xml
<q:component name="ListExample" xmlns:q="https://quantum.lang/ns">
  <q:loop type="list" var="color" items="red,green,blue">
    <q:return value="Color: {color}" />
  </q:loop>
</q:component>
```

**Output:** `["Color: red", "Color: green", "Color: blue"]`

#### Custom Delimiter

```xml
<q:loop type="list" var="name" items="João|Maria|Pedro" delimiter="|">
  <q:return value="Name: {name}" />
</q:loop>
```

**Output:** `["Name: João", "Name: Maria", "Name: Pedro"]`

## Advanced Features

### Arithmetic in Databinding

All loops support arithmetic expressions in variable databinding:

```xml
<q:loop type="range" var="i" from="1" to="3">
  <q:return value="Item {i}, Next: {i + 1}, Double: {i * 2}" />
</q:loop>
```

**Output:** `["Item 1, Next: 2, Double: 2", "Item 2, Next: 3, Double: 4", "Item 3, Next: 4, Double: 6"]`

### Nested Loops

Loops can be nested for complex data processing:

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

### Integration with Conditionals

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

## Query Loop (`query="name"`)

Goes over the rows of a `q:query`; each row is reached by the query's name.
The example database is the one in [Database Queries](./query):

```xml
<q:query name="users" datasource="db">
  SELECT name FROM users WHERE status = 'active' ORDER BY name
</q:query>
<q:loop query="users">
  <q:return value="{users.name}" />
</q:loop>
```

**Output:** `["Ana", "Bruno"]`

A query that returned no rows runs the body zero times (LOOP-4).

## Details

A loop without `type` is an array loop when it has `items`, and a range loop
otherwise (LOOP-5):

```xml
<q:loop var="x" items="{[10, 20]}">
  <q:return value="{x}" />
</q:loop>
```

**Output:** `[10, 20]`

A list loop trims the spaces around each item:

```xml
<q:loop type="list" var="c" items=" red , green ">
  <q:return value="[{c}]" />
</q:loop>
```

**Output:** `["[red]", "[green]"]`

With `from` above `to`, a range loop runs zero times, and a loop that returned
nothing lets execution go on (LOOP-2):

```xml
<q:loop type="range" var="i" from="5" to="1">
  <q:return value="{i}" />
</q:loop>
<q:return value="none" />
```

**Output:** `none`

## Errors

An array loop over something that is not a list says what it got (LOOP-6):

```xml
<q:set name="n" value="{5}" />
<q:loop type="array" var="x" items="{n}">
  <q:return value="{x}" />
</q:loop>
```

**Error:** `needs a list`

A `type` that does not exist is a parse error (PARSE-5):

```xml
<q:loop type="while" var="x">
</q:loop>
```

**Error:** `<q:loop type="while"> does not exist`

## See also

- [`q:loop` in the Reference](../reference/tags#q-loop)
- [State Management (`q:set`)](./state-management.md)
- [Conditionals (`q:if`)](./conditionals.md)
