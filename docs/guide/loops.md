# Loop Structures

Quantum provides powerful loop structures inspired by ColdFusion's `cfloop` but designed for modern declarative programming. All loops support variable databinding and can be nested.

## Loop Types

Quantum supports three main loop types:

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

Loops work seamlessly with conditional logic:

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

## Syntax Reference

### Range Loop Attributes

- `type="range"` - Loop type identifier
- `var="varname"` - Variable name for current iteration value
- `from="start"` - Starting number (inclusive)
- `to="end"` - Ending number (inclusive)
- `step="increment"` - Step size (optional, default: 1)

### Array Loop Attributes

- `type="array"` - Loop type identifier
- `var="varname"` - Variable name for current array item
- `items="[...]"` - JSON array or variable reference
- `index="indexvar"` - Variable name for current index (optional)

### List Loop Attributes

- `type="list"` - Loop type identifier
- `var="varname"` - Variable name for current list item
- `items="item1,item2,..."` - Delimited string or variable reference
- `delimiter=","` - Delimiter character (optional, default: comma)
- `index="indexvar"` - Variable name for current index (optional)

## Error Handling

Quantum provides helpful error messages for common loop issues:

- **Missing variable name**: `Loop requires 'var' attribute`
- **Invalid range**: `Range loop requires 'from' and 'to' attributes`
- **Invalid JSON**: Falls back to string parsing for arrays
- **Empty collections**: Loops with empty data simply don't execute

## Performance Notes

- Range loops are most efficient for numeric iterations
- Array loops support large datasets well
- List loops automatically trim whitespace from items
- Nested loops should be used judiciously for large datasets

## Coming Soon

Future loop enhancements planned:
- Object/Structure loops (`type="object"`)
- Query/Database loops (`type="query"`)
- Conditional loops (`type="while"`)
- Parallel execution options