# Components

Components are the fundamental building blocks of Quantum applications. They encapsulate logic, data processing, and output generation in reusable, modular units.

The examples on this page are run on every change: those with an
**Output:** as shown, the others — the ones that take parameters, and the page
that uses a card — by `tests/docs/test_guide_components.py`.

## Basic Structure

Every Quantum component follows this structure:

```xml
<q:component name="ComponentName" xmlns:q="https://quantum.lang/ns">
  <!-- Component logic here -->
  <q:return value="output" />
</q:component>
```

**Output:** `"output"`

### Required Elements

| Element | Description |
|---------|-------------|
| `q:component` | Root element |
| `name` attribute | The component's name (PascalCase) |
| `xmlns:q` | Quantum namespace declaration |

## Simple Components

### Hello World

```xml
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello, World!" />
</q:component>
```

**Output:** `"Hello, World!"`

### Returning early

`q:return` ends the component: the first one that runs is the result, and what
comes after it does not run. Inside a `q:if`, it ends the component only when
its branch runs.

```xml
<q:component name="Stock" xmlns:q="https://quantum.lang/ns">
  <q:set name="stock" value="0" type="number" />

  <q:if condition="stock == 0">
    <q:return value="Sold out" />
  </q:if>
  <q:return value="{stock} in stock" />
</q:component>
```

**Output:** `"Sold out"`

Inside a loop it is different: each `q:return` adds an item to a list (see
[Loops in Components](#loops-in-components)).

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

With `name` = `Ana` it returns `"Hey Ana!"`; with `formal` = `true` as well,
`"Good day, Ana."`. Without `name` it is an error:
`Required parameter 'name' is missing`.

### Parameter Attributes

| Attribute | Description | Example |
|-----------|-------------|---------|
| `name` | Parameter name | `name="userId"` |
| `type` | Data type | `type="string"` |
| `required` | Required parameter | `required="true"` |
| `default` | Default value | `default="10"` |

### Types

The `type` of a `q:param` is one of `string`, `integer`, `number`, `decimal`,
`boolean`, `array`, `object`, `json`, `email`, `url`, `date`, `file` or `any`
(and the aliases `text`, `int`, `long`, `numeric`, `float`, `double`, `binary`,
`upload`). Any other name is a parse error.

A value that does not fit is an error that names the parameter:
`age` of type `number` given `abc` stops the component with
`Parameter 'age' must be a number, got 'abc'`, and an `email` given
`not-an-email` with `Parameter 'email' must be a valid email`.

## Component State

Use `q:set` for internal variables. A later `q:set` of the same name
replaces the value:

```xml
<q:component name="Counter" xmlns:q="https://quantum.lang/ns">
  <q:set name="count" value="0" type="number" />
  <q:set name="step" value="1" type="number" />
  <q:set name="count" value="{count + step}" />

  <q:return value="Count: {count}" />
</q:component>
```

**Output:** `"Count: 1"`

### Variable Validation

`q:set` can check the value it stores — `validate` (`email`, `url`, …),
`range` and `enum`:

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

**Error:** `Value must be between 0 and 150`

The first two pass; the third stops the component. A `status` outside the
list stops it with `Value must be one of: active, inactive, pending`, and an
e-mail that is not one with `Invalid email format`.

## Component Functions

Define reusable logic with `q:function`, and call it in an expression:

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

**Output:** `"5 + 3 = 8, 4 * 7 = 28"`

More in [Functions](/guide/functions).

## Loops in Components

A `q:return` inside a loop does not end it: each one adds an item, and the
component returns the list.

### Range Loop

```xml
<q:component name="Numbers" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="5">
    <q:return value="Number {i}" />
  </q:loop>
</q:component>
```

**Output:** `["Number 1", "Number 2", "Number 3", "Number 4", "Number 5"]`

### Array Loop

```xml
<q:component name="Fruits" xmlns:q="https://quantum.lang/ns">
  <q:set name="fruits" value='["Apple", "Banana", "Cherry"]' />

  <q:loop type="array" var="fruit" items="{fruits}">
    <q:return value="I like {fruit}" />
  </q:loop>
</q:component>
```

**Output:** `["I like Apple", "I like Banana", "I like Cherry"]`

### List Loop

```xml
<q:component name="Colors" xmlns:q="https://quantum.lang/ns">
  <q:loop type="list" var="color" items="red,green,blue" delimiter=",">
    <q:return value="Color: {color}" />
  </q:loop>
</q:component>
```

**Output:** `["Color: red", "Color: green", "Color: blue"]`

### Loop with Index

`index` names the position, counted from 0:

```xml
<q:component name="IndexedList" xmlns:q="https://quantum.lang/ns">
  <q:set name="items" value='["First", "Second", "Third"]' />

  <q:loop type="array" var="item" items="{items}" index="i">
    <q:return value="{i + 1}. {item}" />
  </q:loop>
</q:component>
```

**Output:** `["1. First", "2. Second", "3. Third"]`

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

With `age` = `20` it returns `"Adult"`; with `15`, `"Minor"`.

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

With `score` = `85` it returns `"B"`; with `42`, `"F"`.

## Data Binding

Use `{expression}` for dynamic values:

### Simple Variables

```xml
<q:set name="name" value="Alice" />
<q:return value="Hello, {name}!" />
```

**Output:** `"Hello, Alice!"`

### Object Properties

```xml
<q:set name="user" type="object" value='{"name": "Bob", "age": 30}' />
<q:return value="{user.name} is {user.age} years old" />
```

**Output:** `"Bob is 30 years old"`

### Expressions

```xml
<q:set name="price" value="100" />
<q:set name="quantity" value="5" />
<q:return value="Total: ${price * quantity}" />
```

**Output:** `"Total: $500"`

### String Functions

Functions are called with the value as an argument — see the
[function list](/guide/databinding#functions):

```xml
<q:set name="text" value="hello world" />
<q:return value="{upper(text)}" />
```

**Output:** `"HELLO WORLD"`

## Nested Loops

The items of an inner loop go into the outer loop's list one by one, in order:

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

**Output:** `["Category: Electronics", "  - Phone", "  - Laptop", "Category: Clothing", "  - Shirt", "  - Pants"]`

## Using one component inside another

A page uses another component — a card, a layout — by importing it and writing
it as a tag. Save as `components/_parts/Card.q`:

```xml
<q:component name="Card" xmlns:q="https://quantum.lang/ns">
  <q:param name="title" required="true" />
  <section class="card">
    <h2>{title}</h2>
    <q:slot />
  </section>
</q:component>
```

Save as `components/index.q`:

```xml
<q:component name="Home" xmlns:q="https://quantum.lang/ns">
  <q:import component="Card" from="_parts" />
  <q:set name="open" value="3" type="number" />

  <Card title="Open tickets: {open}">
    <p>The oldest is from {'Monday'}.</p>
  </Card>
</q:component>
```

Opening `/` shows the card with the title **Open tickets: 3** and, inside it,
**The oldest is from Monday.**

- `q:import` looks the component up in `paths.components` of
  `quantum.config.yaml`, in the `from` folder when declared. A folder whose name
  starts with `_` is not served as pages, which suits parts like this one.
- Each attribute of the tag is a `q:param` of the component, evaluated in the
  page: `title="Open tickets: {open}"` sees the page's `open`. A missing
  required param is an error.
- What is between `<Card>` and `</Card>` is drawn in the page's scope and goes
  where the component has `<q:slot />`.
- The component uses the page's datasources and services and sees the same
  `session`, `application` and `request`.
- A component that is not found, or that fails, is an error of the page — never
  a section that silently disappears.

## Errors

A component that cannot do what it says stops with an error that says why.

### A missing parameter

```xml
<q:component name="Ticket" xmlns:q="https://quantum.lang/ns">
  <q:param name="id" type="integer" required="true" />
  <q:return value="Ticket {id}" />
</q:component>
```

**Error:** `Required parameter 'id' is missing`

### A variable that does not exist

```xml
<q:component name="ErrorExample" xmlns:q="https://quantum.lang/ns">
  <q:return value="{undefined_variable}" />
</q:component>
```

**Error:** `variable 'undefined_variable' is not defined`

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

Prefer `<q:component name="ProductPriceFormatter">` to
`<q:component name="PF">`: the name is what a page that uses it reads.

### 3. Document Parameters

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

With `amount` = `19.999` it returns `"USD 20.0"`.

### 4. Validate Input

```xml
<q:component name="SafeComponent" xmlns:q="https://quantum.lang/ns">
  <q:param name="count" type="integer" required="true" />

  <q:if condition="count < 1">
    <q:return value="Error: count must be at least 1" />
  </q:if>

  <q:return value="{count} item(s)" />
</q:component>
```

With `count` = `3` it returns `"3 item(s)"`; with `-1`,
`"Error: count must be at least 1"`; with `abc`, the error
`Parameter 'count' must be an integer, got 'abc'`.

## Next Steps

- [State Management](/guide/state-management) - Advanced variable handling
- [Functions](/guide/functions) - Creating reusable logic
- [Loops](/guide/loops) - Iteration patterns
- [Conditionals](/guide/conditionals) - Control flow
