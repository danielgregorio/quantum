# Variable Databinding

Quantum's variable databinding system enables dynamic content substitution using `{variable}` syntax. This powerful feature transforms static components into dynamic, data-driven applications.

## Basic Syntax

Variable databinding uses curly braces to reference variables in scope:

```xml
<q:component name="BasicBinding" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="3">
    <q:return value="Item number {i}" />
  </q:loop>
</q:component>
```

**Output:** `["Item number 1", "Item number 2", "Item number 3"]`

## Arithmetic Expressions

Databinding supports mathematical expressions within curly braces:

```xml
<q:loop type="range" var="i" from="1" to="3">
  <q:return value="Number: {i}, Double: {i * 2}, Next: {i + 1}" />
</q:loop>
```

**Output:** `["Number: 1, Double: 2, Next: 2", "Number: 2, Double: 4, Next: 3", "Number: 3, Double: 6, Next: 4"]`

### Supported Operators

- **Addition**: `{i + 5}`
- **Subtraction**: `{i - 2}`
- **Multiplication**: `{i * 3}`
- **Division**: `{i / 2}`
- **Modulo**: `{i % 2}`
- **Parentheses**: `{(i + 1) * 2}`

## Variable Scope

Variables are available within their defining scope and nested scopes:

### Loop Variables

```xml
<q:loop type="range" var="x" from="1" to="2">
  <q:loop type="range" var="y" from="1" to="2">
    <q:return value="Point ({x}, {y})" />
  </q:loop>
</q:loop>
```

**Output:** `["Point (1, 1)", "Point (1, 2)", "Point (2, 1)", "Point (2, 2)"]`

### Index Variables

Array and list loops can provide index variables:

```xml
<q:loop type="array" var="fruit" index="idx" items='["apple", "banana"]'>
  <q:return value="Item {idx}: {fruit}" />
</q:loop>
```

**Output:** `["Item 0: apple", "Item 1: banana"]`

## Advanced Patterns

### Complex Expressions

Combine multiple variables and operations:

```xml
<q:loop type="range" var="i" from="1" to="3">
  <q:loop type="range" var="j" from="1" to="2">
    <q:return value="Sum: {i + j}, Product: {i * j}" />
  </q:loop>
</q:loop>
```

### Conditional Expressions

Use databinding with conditional logic:

```xml
<q:loop type="range" var="i" from="1" to="5">
  <q:if condition="i % 2 == 0">
    <q:return value="Even: {i}, Half: {i / 2}" />
  <q:else>
    <q:return value="Odd: {i}, Squared: {i * i}" />
  </q:else>
  </q:if>
</q:loop>
```

## Data Types

Databinding works with different data types:

### Strings

```xml
<q:loop type="list" var="name" items="Alice,Bob,Charlie">
  <q:return value="Hello, {name}!" />
</q:loop>
```

### Numbers

```xml
<q:loop type="array" var="price" items="[10.99, 25.50, 15.75]">
  <q:return value="Price: ${price}, Tax: ${price * 0.1}" />
</q:loop>
```

## Error Handling

Quantum provides helpful error handling for databinding issues:

### Missing Variables

```xml
<!-- This will show an error if 'undefined_var' is not in scope -->
<q:return value="Value: {undefined_var}" />
```

**Error:** `NameError: name 'undefined_var' is not defined in expression: undefined_var`

### Invalid Expressions

```xml
<!-- This will show an error for invalid syntax -->
<q:return value="Invalid: {i +}" />
```

**Error:** `SyntaxError: invalid syntax in expression: i +`

### Safe Fallback

When an expression fails, Quantum provides contextual error information while continuing execution where possible.

## Performance Considerations

- **Expression Evaluation**: Complex expressions are evaluated for each use
- **Variable Lookup**: Variable resolution is optimized for nested scopes
- **String Interpolation**: Multiple variables in one string are processed efficiently

## Best Practices

### Clear Variable Names

```xml
<!-- Good -->
<q:loop type="range" var="userIndex" from="1" to="10">
  <q:return value="User {userIndex}" />
</q:loop>

<!-- Less clear -->
<q:loop type="range" var="i" from="1" to="10">
  <q:return value="User {i}" />
</q:loop>
```

### Avoid Complex Expressions

```xml
<!-- Good - clear and readable -->
<q:loop type="range" var="i" from="1" to="5">
  <q:return value="Number: {i}, Double: {i * 2}" />
</q:loop>

<!-- Harder to read -->
<q:loop type="range" var="i" from="1" to="5">
  <q:return value="Complex: {((i + 1) * 2) - (i / 2)}" />
</q:loop>
```

### Consistent Spacing

```xml
<!-- Consistent spacing makes expressions more readable -->
<q:return value="Result: {i + 1}, Total: {i * factor}" />
```

## Integration Examples

### With Conditionals

```xml
<q:loop type="range" var="score" from="1" to="100" step="25">
  <q:if condition="score >= 90">
    <q:return value="Score {score}: Excellent!" />
  <q:elseif condition="score >= 70">
    <q:return value="Score {score}: Good" />
  <q:else>
    <q:return value="Score {score}: Needs improvement" />
  </q:else>
  </q:if>
</q:loop>
```

### With Multiple Loop Types

```xml
<q:component name="DataMatrix" xmlns:q="https://quantum.lang/ns">
  <q:loop type="array" var="row" index="r" items='[["A", "B"], ["C", "D"]]'>
    <q:loop type="array" var="cell" index="c" items="{row}">
      <q:return value="Cell[{r}][{c}]: {cell}" />
    </q:loop>
  </q:loop>
</q:component>
```

## Syntax Reference

### Basic Pattern
- `{variable}` - Simple variable substitution
- `{expression}` - Arithmetic expression evaluation

### Supported in Expressions
- Variables from current scope
- Basic arithmetic operators (`+`, `-`, `*`, `/`, `%`)
- Parentheses for grouping
- Numeric literals

### Error Handling
- Missing variables: `NameError` with variable name
- Invalid syntax: `SyntaxError` with expression details
- Graceful degradation when possible

## Coming Soon

Future databinding enhancements:

- **String Functions**: `{string.upper()}`, `{string.length}`
- **Date/Time**: `{date.format()}`, `{time.now}`
- **Conditional Operators**: `{condition ? value1 : value2}`
- **Array Access**: `{array[index]}`, `{object.property}`