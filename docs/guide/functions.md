# Function Definitions (`q:function`)

Functions in Quantum provide reusable logic blocks that can accept parameters, perform computations, and return values. Functions are called via databinding or used internally within components.

## Table of Contents

- [Basic Function Syntax](#basic-function-syntax)
- [Parameters](#parameters)
- [Return Values](#return-values)
- [Function Scopes](#function-scopes)
- [Access Control](#access-control)
- [Function Features](#function-features)
- [Validation](#validation)
- [Performance Optimization](#performance-optimization)
- [Event System](#event-system)
- [Examples](#examples)

---

## Basic Function Syntax

A simple function definition:

```xml
<q:function name="add" returnType="number">
  <q:param name="a" type="number" required="true" />
  <q:param name="b" type="number" required="true" />

  <q:set name="result" type="number" value="{a + b}" />
  <q:return value="{result}" />
</q:function>
```

**Calling the function:**

```xml
<q:set name="sum" value="{add(5, 3)}" />
<!-- sum = 8 -->
```

---

## Parameters

### Required Parameters

```xml
<q:param name="username" type="string" required="true" />
```

### Optional Parameters with Defaults

```xml
<q:param name="greeting" type="string" default="Hello" />
```

### Parameter Types

Supported types: `string`, `number`, `boolean`, `array`, `object`, `any`, `binary`

```xml
<q:function name="greet" returnType="string">
  <q:param name="name" type="string" required="true" />
  <q:param name="greeting" type="string" default="Hello" />

  <q:return value="{greeting}, {name}!" />
</q:function>
```

**Usage:**

```xml
<q:set name="msg1" value="{greet('Alice', 'Hi')}" />
<!-- Result: "Hi, Alice!" -->

<q:set name="msg2" value="{greet('Bob')}" />
<!-- Result: "Hello, Bob!" -->
```

## Return Values

### Simple Return

```xml
<q:return value="{result}" />
```

### Conditional Returns

```xml
<q:function name="checkNumber" returnType="string">
  <q:param name="num" type="number" required="true" />

  <q:if condition="{num > 0}">
    <q:return value="positive" />
  </q:if>

  <q:if condition="{num < 0}">
    <q:return value="negative" />
  </q:if>

  <q:return value="zero" />
</q:function>
```

---

## Function Scopes

### Component Scope (Default)

Functions are accessible only within the same component:

```xml
<q:function name="myFunction" scope="component">
  <!-- Only accessible within this component -->
</q:function>
```

### Global Scope

Functions accessible from any component using qualified names:

```xml
<q:function name="utilityFunction" scope="global">
  <q:param name="data" type="string" required="true" />
  <q:return value="[UTILITY] {data}" />
</q:function>
```

**Calling from another component:**

```xml
<q:set name="result" value="{ComponentName.utilityFunction('test')}" />
```

## Access Control

### Public Functions

Accessible from anywhere (default):

```xml
<q:function name="publicAPI" access="public">
  <!-- Accessible everywhere -->
</q:function>
```

### Private Functions

Only accessible within the same component:

```xml
<q:function name="privateHelper" access="private">
  <!-- Only callable from within this component -->
</q:function>
```

**Note:** Functions starting with underscore (`_`) are automatically private:

```xml
<q:function name="_internalHelper">
  <!-- Automatically private -->
</q:function>
```

### Protected Functions

Accessible within component and child components (future feature):

```xml
<q:function name="protectedMethod" access="protected">
  <!-- Accessible in component hierarchy -->
</q:function>
```

---

## Function Features

### Documentation

Add descriptions and hints for better code documentation:

```xml
<q:function name="calculateDiscount"
            returnType="number"
            description="Calculates discount price based on percentage"
            hint="Returns final price after applying discount">
  <q:param name="price" type="number" required="true" />
  <q:param name="discountPercent" type="number" required="true" />

  <q:set name="discount" type="number" value="{price * discountPercent / 100}" />
  <q:set name="finalPrice" type="number" value="{price - discount}" />

  <q:return value="{finalPrice}" />
</q:function>
```

### Pure Functions

Functions with no side effects (always return same output for same input):

```xml
<q:function name="add" pure="true">
  <q:param name="a" type="number" required="true" />
  <q:param name="b" type="number" required="true" />
  <q:return value="{a + b}" />
</q:function>
```

### Async Functions

For asynchronous operations (future feature):

```xml
<q:function name="fetchData" async="true">
  <!-- Async implementation -->
</q:function>
```

---

## REST API Integration

::: warning Not implemented
`q:function` accepts `endpoint`, `method`, `produces`, `consumes` and `source`
attributes, and the parser reads them — but the server never exposes the
function as an HTTP endpoint. Do not rely on them. To handle an HTTP request,
write a page in `components/` with a [`q:action`](/guide/actions).
:::

## Validation

### Parameter Validation

Enable automatic validation:

```xml
<q:function name="registerUser" validate="true">
  <q:param name="email" type="string" required="true" validate="email" />
  <q:param name="age" type="number" required="true" min="18" max="100" />
  <q:param name="role" type="string" required="true" enum="admin,user,guest" />

  <q:return value="User {email} registered as {role}" />
</q:function>
```

### Built-in Validators

- `email` - Valid email address
- `cpf` - Brazilian CPF validation
- `cnpj` - Brazilian CNPJ validation
- `url` - Valid URL
- `phone` - Phone number validation
- `uuid` - UUID format validation
- `date` - Date format validation
- `json` - Valid JSON validation

### Range and Pattern Validation

```xml
<q:param name="score" type="number" min="0" max="100" />
<q:param name="code" type="string" pattern="^[A-Z]{3}[0-9]{3}$" />
<q:param name="password" type="string" minlength="8" maxlength="128" />
```

---

## Performance Optimization

### Caching

Cache function results for specified duration:

```xml
<!-- Cache for 60 seconds -->
<q:function name="expensiveOperation" cache="60s">
  <!-- Computation -->
</q:function>

<!-- Simple cache (default TTL) -->
<q:function name="getData" cache="true">
  <!-- Computation -->
</q:function>
```

### Memoization

Automatically cache results based on input arguments:

```xml
<q:function name="fibonacci" memoize="true">
  <q:param name="n" type="number" required="true" />
  <!-- Recursive computation with automatic memoization -->
</q:function>
```

### Retry Logic

Automatically retry on failure:

```xml
<q:function name="apiCall" retry="3" timeout="5000ms">
  <!-- Will retry up to 3 times with 5 second timeout -->
</q:function>
```

---

## Event System

### Dispatching Events

Publish events from within functions:

```xml
<q:function name="processOrder">
  <q:param name="orderId" type="string" required="true" />

  <!-- Process order logic -->
  <q:set name="status" value="completed" />

  <!-- Dispatch event -->
  <q:dispatchEvent event="order.completed"
                   data="{ orderId: '{orderId}', status: '{status}' }"
                   priority="high" />

  <q:return value="Order {orderId} processed" />
</q:function>
```

### Event Handlers

Subscribe to events:

```xml
<q:onEvent event="order.completed" concurrent="5" prefetch="10">
  <!-- Handle order completion -->
  <q:set name="orderId" value="{event.data.orderId}" />
  <q:set name="status" value="{event.data.status}" />

  <!-- Send notification, update database, etc. -->
</q:onEvent>
```

---

## Examples

### Example 1: Simple Addition

```xml
<q:component name="MathExample" xmlns:q="https://quantum.lang/ns">
  <q:function name="add" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:return value="{a + b}" />
  </q:function>

  <q:set name="result" value="{add(10, 20)}" />
  <q:return value="Sum: {result}" />
</q:component>
```

### Example 2: String Formatting

```xml
<q:component name="StringExample" xmlns:q="https://quantum.lang/ns">
  <q:function name="formatName" returnType="string">
    <q:param name="firstName" type="string" required="true" />
    <q:param name="lastName" type="string" required="true" />
    <q:param name="title" type="string" default="Mr." />

    <q:return value="{title} {firstName} {lastName}" />
  </q:function>

  <q:set name="fullName" value="{formatName('John', 'Doe', 'Dr.')}" />
  <q:return value="{fullName}" />
</q:component>
```

### Example 3: Conditional Logic

```xml
<q:component name="ConditionalExample" xmlns:q="https://quantum.lang/ns">
  <q:function name="calculateGrade" returnType="string">
    <q:param name="score" type="number" required="true" />

    <q:if condition="{score >= 90}">
      <q:return value="A" />
    </q:if>
    <q:if condition="{score >= 80}">
      <q:return value="B" />
    </q:if>
    <q:if condition="{score >= 70}">
      <q:return value="C" />
    </q:if>
    <q:if condition="{score >= 60}">
      <q:return value="D" />
    </q:if>
    <q:return value="F" />
  </q:function>

  <q:set name="grade" value="{calculateGrade(85)}" />
  <q:return value="Grade: {grade}" />
</q:component>
```

### Example 4: Recursive Function

```xml
<q:component name="RecursionExample" xmlns:q="https://quantum.lang/ns">
  <q:function name="factorial" returnType="number">
    <q:param name="n" type="number" required="true" />

    <q:if condition="{n <= 1}">
      <q:return value="1" />
    </q:if>

    <q:set name="nMinus1" type="number" value="{n}" operation="decrement" />
    <q:set name="recursiveResult" value="{factorial(nMinus1)}" />
    <q:return value="{n * recursiveResult}" />
  </q:function>

  <q:set name="fact5" value="{factorial(5)}" />
  <q:return value="Factorial(5) = {fact5}" />
</q:component>
```

### Example 5: Array Processing

```xml
<q:component name="ArrayExample" xmlns:q="https://quantum.lang/ns">
  <q:function name="sumArray" returnType="number">
    <q:param name="numbers" type="array" required="true" />

    <q:set name="total" type="number" value="0" />

    <q:loop type="array" items="{numbers}" var="num">
      <q:set name="total" type="number" value="{total}" operation="add" operand="{num}" />
    </q:loop>

    <q:return value="{total}" />
  </q:function>

  <q:set name="numbers" type="array" value="[10, 20, 30, 40]" />
  <q:set name="sum" value="{sumArray(numbers)}" />
  <q:return value="Sum: {sum}" />
</q:component>
```

## Best Practices

1. **Keep functions small and focused** - Each function should do one thing well
2. **Use meaningful parameter names** - Clear names improve code readability
3. **Add documentation** - Use `description` and `hint` attributes
4. **Validate inputs** - Use parameter validation for production code
5. **Mark pure functions** - Use `pure="true"` for functions without side effects
6. **Consider caching** - Use `cache` or `memoize` for expensive operations
7. **Use appropriate scopes** - Component scope for internal logic, global for utilities
8. **Handle errors gracefully** - Use conditional returns and validation
9. **Test thoroughly** - Create test files for all function scenarios

---

## Related Documentation

- [State Management (`q:set`)](./state-management.md)
- [Conditionals (`q:if`)](./conditionals.md) · [Loops (`q:loop`)](./loops.md)
- [Databinding Expressions](./databinding.md)
- [Component Architecture](./components.md)

---

Generated with ❤️ by Quantum Language Team
