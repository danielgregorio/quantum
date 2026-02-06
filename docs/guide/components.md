# Components

Components are the fundamental building blocks of Quantum applications. They encapsulate logic, data processing, and output generation in reusable, modular units.

## Basic Structure

Every Quantum component follows this structure:

```xml
<q:component name="ComponentName" xmlns:q="https://quantum.lang/ns">
  <!-- Component logic here -->
  <q:return value="output" />
</q:component>
```

### Required Elements

| Element | Description |
|---------|-------------|
| `q:component` | Root element |
| `name` attribute | Unique identifier (PascalCase) |
| `xmlns:q` | Quantum namespace declaration |

## Simple Components

### Hello World

```xml
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello, World!" />
</q:component>
```

Output: `"Hello, World!"`

### Multiple Returns

```xml
<q:component name="Colors" xmlns:q="https://quantum.lang/ns">
  <q:return value="Red" />
  <q:return value="Green" />
  <q:return value="Blue" />
</q:component>
```

Output: `["Red", "Green", "Blue"]`

## Component Parameters

Accept input with `q:param`:

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

### Parameter Attributes

| Attribute | Description | Example |
|-----------|-------------|---------|
| `name` | Parameter name | `name="userId"` |
| `type` | Data type | `type="string"` |
| `required` | Required parameter | `required="true"` |
| `default` | Default value | `default="10"` |

### Supported Types

- `string` - Text values
- `number` - Integers and decimals
- `boolean` - true/false
- `array` - JSON arrays
- `object` - JSON objects
- `email` - Valid email format
- `date` - Date strings

## Component State

Use `q:set` for internal variables:

```xml
<q:component name="Counter" xmlns:q="https://quantum.lang/ns">
  <q:set name="count" value="0" type="number" />
  <q:set name="step" value="1" type="number" />

  <q:function name="increment">
    <q:set name="count" value="{count + step}" />
  </q:function>

  <q:return value="Count: {count}" />
</q:component>
```

### Variable Validation

```xml
<q:set name="email"
       type="email"
       value="user@example.com"
       validate="true" />

<q:set name="age"
       type="number"
       value="25"
       min="0"
       max="150" />

<q:set name="status"
       type="string"
       value="active"
       enum="active,inactive,pending" />
```

## Component Functions

Define reusable logic with `q:function`:

```xml
<q:component name="Calculator" xmlns:q="https://quantum.lang/ns">
  <q:function name="add" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:set name="result" value="{a + b}" />
    <q:return value="{result}" />
  </q:function>

  <q:function name="multiply" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:return value="{a * b}" />
  </q:function>

  <!-- Use the functions -->
  <q:set name="sum" value="{add(5, 3)}" />
  <q:set name="product" value="{multiply(4, 7)}" />

  <q:return value="5 + 3 = {sum}" />
  <q:return value="4 * 7 = {product}" />
</q:component>
```

## Loops in Components

### Range Loop

```xml
<q:component name="Numbers" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="5">
    <q:return value="Number {i}" />
  </q:loop>
</q:component>
```

Output: `["Number 1", "Number 2", "Number 3", "Number 4", "Number 5"]`

### Array Loop

```xml
<q:component name="Fruits" xmlns:q="https://quantum.lang/ns">
  <q:set name="fruits" value='["Apple", "Banana", "Cherry"]' />

  <q:loop type="array" var="fruit" items="{fruits}">
    <q:return value="I like {fruit}" />
  </q:loop>
</q:component>
```

### List Loop

```xml
<q:component name="Colors" xmlns:q="https://quantum.lang/ns">
  <q:loop type="list" var="color" items="red,green,blue" delimiter=",">
    <q:return value="Color: {color}" />
  </q:loop>
</q:component>
```

### Loop with Index

```xml
<q:component name="IndexedList" xmlns:q="https://quantum.lang/ns">
  <q:set name="items" value='["First", "Second", "Third"]' />

  <q:loop type="array" var="item" items="{items}" index="i">
    <q:return value="{i + 1}. {item}" />
  </q:loop>
</q:component>
```

Output: `["1. First", "2. Second", "3. Third"]`

## Conditionals

### Basic If/Else

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

### Multiple Conditions

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

## Data Binding

Use `{expression}` for dynamic values:

### Simple Variables

```xml
<q:set name="name" value="Alice" />
<q:return value="Hello, {name}!" />
```

### Object Properties

```xml
<q:set name="user" value='{"name": "Bob", "age": 30}' />
<q:return value="{user.name} is {user.age} years old" />
```

### Expressions

```xml
<q:set name="price" value="100" />
<q:set name="quantity" value="5" />
<q:return value="Total: ${price * quantity}" />
```

### String Functions

```xml
<q:set name="text" value="hello world" />
<q:return value="{text.toUpperCase()}" />
```

## Nested Components

Components can contain nested structures:

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

## Error Handling

### Validation Errors

```xml
<!-- Missing required parameter -->
<q:component name="BadComponent" xmlns:q="https://quantum.lang/ns">
  <q:param name="id" required="true" />
  <!-- Error: 'id' is required but not provided -->
</q:component>
```

### Runtime Errors

```xml
<q:component name="ErrorExample" xmlns:q="https://quantum.lang/ns">
  <q:return value="{undefined_variable}" />
  <!-- Error: undefined_variable is not defined -->
</q:component>
```

### Error Messages

Quantum provides descriptive error messages:

```
[ERROR] Component 'MyComponent' at line 5:
  Variable 'userName' is not defined in this scope.
  Did you mean 'username'?
```

## Best Practices

### 1. Single Responsibility

Each component should have one clear purpose:

```xml
<!-- Good: Focused component -->
<q:component name="UserEmail" xmlns:q="https://quantum.lang/ns">
  <q:param name="email" type="email" required="true" />
  <q:return value="{email}" />
</q:component>
```

### 2. Use Descriptive Names

```xml
<!-- Good -->
<q:component name="ProductPriceFormatter" xmlns:q="https://quantum.lang/ns">

<!-- Avoid -->
<q:component name="PF" xmlns:q="https://quantum.lang/ns">
```

### 3. Document Parameters

```xml
<!--
  Formats a price with currency symbol.

  @param amount - The price amount (required)
  @param currency - Currency code (default: USD)
-->
<q:component name="PriceFormatter" xmlns:q="https://quantum.lang/ns">
  <q:param name="amount" type="number" required="true" />
  <q:param name="currency" type="string" default="USD" />
  ...
</q:component>
```

### 4. Validate Input

```xml
<q:component name="SafeComponent" xmlns:q="https://quantum.lang/ns">
  <q:param name="count" type="number" required="true" />

  <q:if condition="count < 0">
    <q:return value="Error: count must be positive" />
  </q:if>

  <q:loop type="range" var="i" from="1" to="{count}">
    <q:return value="Item {i}" />
  </q:loop>
</q:component>
```

## Next Steps

- [State Management](/guide/state-management) - Advanced variable handling
- [Functions](/guide/functions) - Creating reusable logic
- [Loops](/guide/loops) - Iteration patterns
- [Conditionals](/guide/conditionals) - Control flow
