# State Management (`q:set`)

`q:set` is the fundamental tag for state management in Quantum, letting you create, modify and validate variables in a declarative, type-safe way.

## 🎯 Basic Concepts

### Simple Syntax

```xml
<q:set name="variableName" type="string" value="initialValue" />
```

### Required Attributes

| Attribute | Description | Example |
|----------|-----------|---------|
| `name` | Variable name | `name="counter"` |

### Optional Attributes

| Attribute | Description | Default | Example |
|----------|-----------|--------|---------|
| `type` | Data type | `string` | `type="number"` |
| `value` | Initial value | `null` | `value="10"` |
| `default` | Default value | `null` | `default="0"` |
| `scope` | Variable scope | `local` | `scope="component"` |
| `operation` | Operation to perform | `assign` | `operation="increment"` |

## 📦 Data Types

### Primitive Types

```xml
<!-- String (default) -->
<q:set name="message" type="string" value="Hello World" />

<!-- Number (integer or float) -->
<q:set name="age" type="number" value="25" />

<!-- Decimal (float) -->
<q:set name="price" type="decimal" value="19.99" />

<!-- Boolean -->
<q:set name="isActive" type="boolean" value="true" />

<!-- A date: ISO text, or the date an expression computes (no type, SET-5) -->
<q:set name="birthdate" value="1990-01-01" />
<q:set name="created" value="{now()}" />
```

### Structured Types

```xml
<!-- Array -->
<q:set name="fruits" type="array" value='["apple", "banana", "orange"]' />

<!-- Object -->
<q:set name="user" type="object" value='{"name": "Daniel", "age": 30}' />

<!-- JSON -->
<q:set name="config" type="json" value='{"debug":true,"port":8080}' />
```

### Without `type`

A `value` that is exactly one expression keeps the type of what it computes,
as in `q:return` and in a component's props; anything else is text:

```xml
<q:set name="tags" value="{['new', 'sale']}" />   <!-- the list -->
<q:set name="count" value="{len(tags)}" />        <!-- the number 2 -->
<q:set name="label" value="{count} tags" />       <!-- the text "2 tags" -->
<q:set name="code" value="007" />                 <!-- the text "007" -->
```

```xml
<q:set name="tags" value="{['new', 'sale']}" />
<q:set name="count" value="{len(tags)}" />
<q:return value="{count} tags" />
```

**Output:** `2 tags`

Up to Quantum 0.22 every `q:set` without `type` stored text, so `{tags}` above
was the text `['new', 'sale']` and `len(tags)` counted its 15 characters. Write
`type="string"` where you want the text.

## 🔧 Operations

### Basic Assignment

```xml
<q:component name="BasicAssignment" xmlns:q="https://quantum.lang/ns">
  <q:set name="x" type="number" value="10" />
  <q:return value="x = {x}" />
</q:component>
```

**Output:** `x = 10`

### Arithmetic Expressions

```xml
<q:component name="ArithmeticExpressions" xmlns:q="https://quantum.lang/ns">
  <q:set name="a" type="number" value="5" />
  <q:set name="b" type="number" value="3" />
  <q:set name="sum" type="number" value="{a + b}" />
  <q:return value="Sum: {sum}" />
</q:component>
```

**Output:** `Sum: 8`

### Increment/Decrement

```xml
<q:component name="Counter" xmlns:q="https://quantum.lang/ns">
  <q:set name="counter" type="number" value="0" />

  <!-- Increments by 1 -->
  <q:set name="counter" operation="increment" />
  <q:set name="counter" operation="increment" />
  <q:set name="counter" operation="increment" />

  <q:return value="Counter: {counter}" />
</q:component>
```

**Output:** `Counter: 3`

#### Increment with Step

```xml
<q:set name="counter" value="0" />
<q:set name="counter" operation="increment" step="5" />
<q:return value="counter = {counter}" />
```

**Output:** `counter = 5`

### Arithmetic Operations

```xml
<q:component name="ArithmeticOps" xmlns:q="https://quantum.lang/ns">
  <q:set name="total" type="number" value="10" />

  <!-- Adds 5 -->
  <q:set name="total" operation="add" value="5" />

  <!-- Multiplies by 2 -->
  <q:set name="total" operation="multiply" value="2" />

  <q:return value="Total: {total}" />
</q:component>
```

**Output:** `Total: 30` (10 + 5 = 15, 15 * 2 = 30)

## 📚 Array Operations

### Append/Prepend

```xml
<q:component name="ArrayOperations" xmlns:q="https://quantum.lang/ns">
  <q:set name="list" type="array" value="[]" />

  <!-- Adds at the end -->
  <q:set name="list" operation="append" value="apple" />
  <q:set name="list" operation="append" value="banana" />

  <!-- Adds at the start -->
  <q:set name="list" operation="prepend" value="orange" />

  <q:return value="{list}" />
</q:component>
```

**Output:** `['orange', 'apple', 'banana']`

### Remove/RemoveAt

```xml
<q:set name="list" type="array" value='["a", "b", "c", "d"]' />

<!-- Remove by value -->
<q:set name="list" operation="remove" value="b" />

<!-- Remove by index -->
<q:set name="list" operation="removeAt" index="2" />
```

### Other Operations

```xml
<!-- Clear the array -->
<q:set name="list" operation="clear" />

<!-- Sort -->
<q:set name="list" operation="sort" />

<!-- Reverse -->
<q:set name="list" operation="reverse" />

<!-- Remove duplicates -->
<q:set name="list" operation="unique" />
```

## 🗂️ Object Operations

### Merge

```xml
<q:component name="ObjectMerge" xmlns:q="https://quantum.lang/ns">
  <q:set name="user" type="object" value="{}" />

  <q:set name="user" operation="merge" value='{"name":"Daniel"}' />
  <q:set name="user" operation="merge" value='{"age":30}' />
  <q:set name="user" operation="merge" value='{"email":"daniel@example.com"}' />

  <q:return value="{user}" />
</q:component>
```

**Output:** `{'name': 'Daniel', 'age': 30, 'email': 'daniel@example.com'}`

### SetProperty/DeleteProperty

```xml
<q:set name="config" type="object" value="{}" />

<!-- Set a property -->
<q:set name="config" operation="setProperty" key="debug" value="true" />

<!-- Delete a property -->
<q:set name="config" operation="deleteProperty" key="debug" />
```

### Clone

```xml
<q:set name="original" type="object" value='{"x":1}' />
<q:set name="copy" operation="clone" source="original" />
```

## 🔤 String Transformations

```xml
<q:set name="text" value="Hello World" />

<!-- Uppercase -->
<q:set name="text" operation="uppercase" />
<!-- Result: HELLO WORLD -->

<!-- Lowercase -->
<q:set name="text" operation="lowercase" />
<!-- Result: hello world -->

<!-- Trim -->
<q:set name="text" value="  spaces  " />
<q:set name="text" operation="trim" />
<!-- Result: spaces -->
```

## 🔄 Use with Loops

```xml
<q:component name="LoopAccumulator" xmlns:q="https://quantum.lang/ns">
  <q:set name="total" type="number" value="0" />

  <q:loop type="range" var="i" from="1" to="5">
    <q:set name="total" operation="add" value="{i}" />
  </q:loop>

  <q:return value="Total: {total}" />
</q:component>
```

**Output:** `Total: 15` (1+2+3+4+5)

### Array Builder with a Loop

```xml
<q:component name="ArrayBuilder" xmlns:q="https://quantum.lang/ns">
  <q:set name="results" type="array" value="[]" />

  <q:loop type="range" var="i" from="1" to="3">
    <q:set name="results" operation="append" value="{i * 2}" />
  </q:loop>

  <q:return value="{results}" />
</q:component>
```

**Output:** `[2, 4, 6]`

## ✅ Validation

### Required & Nullable

```xml
<!-- Required field -->
<q:set name="email" type="string" required="true" />

<!-- Does not accept null -->
<q:set name="age" type="number" nullable="false" />
```

### Built-in Validators

```xml
<!-- Email -->
<q:set name="email" type="string" value="daniel@example.com" validate="email" />

<!-- URL -->
<q:set name="website" type="string" validate="url" />

<!-- CPF (with check-digit verification) -->
<q:set name="cpf" type="string" value="123.456.789-09" validate="cpf" />

<!-- CNPJ (with check-digit verification) -->
<q:set name="cnpj" type="string" validate="cnpj" />

<!-- Brazilian phone number -->
<q:set name="phone" type="string" validate="phone" />

<!-- CEP (Brazilian postal code) -->
<q:set name="cep" type="string" validate="cep" />

<!-- UUID -->
<q:set name="id" type="string" validate="uuid" />

<!-- Credit card -->
<q:set name="card" type="string" validate="creditcard" />

<!-- IP v4 -->
<q:set name="ip" type="string" validate="ipv4" />

<!-- IP v6 -->
<q:set name="ip" type="string" validate="ipv6" />
```

### Regex Pattern

```xml
<!-- Custom pattern -->
<q:set name="code" type="string" pattern="^[A-Z]{3}\d{4}$" />
```

### Range

```xml
<!-- Numeric range -->
<q:set name="age" type="number" value="25" range="18..120" />
```

### Enum

```xml
<q:set name="status" type="string" value="active" enum="pending,active,inactive" />
```

### Min/Max

```xml
<!-- Numbers -->
<q:set name="score" type="number" min="0" max="100" />

<!-- String length -->
<q:set name="username" type="string" minlength="3" maxlength="20" />
```

## 🔐 Complete Example: Sign-up Form

```xml
<q:component name="UserRegistration" xmlns:q="https://quantum.lang/ns">
  <!-- Email with validation -->
  <q:set
    name="email"
    type="string"
    value="daniel@example.com"
    required="true"
    validate="email"
    maxlength="255"
  />

  <!-- Password with strength validation -->
  <q:set
    name="password"
    type="string"
    value="Secure123"
    required="true"
    minlength="8"
    pattern="^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)"
  />

  <!-- CPF -->
  <q:set
    name="cpf"
    type="string"
    value="123.456.789-09"
    required="true"
    validate="cpf"
  />

  <!-- Age -->
  <q:set
    name="age"
    type="number"
    value="25"
    required="true"
    range="18..120"
  />

  <!-- Plan -->
  <q:set
    name="plan"
    type="string"
    value="basic"
    enum="free,basic,premium,enterprise"
    default="free"
  />

  <q:return value="Valid sign-up for {email}" />
</q:component>
```

**Output:** `Valid sign-up for daniel@example.com`

## 🌐 Scopes

### Local (default)

```xml
<q:set name="temp" value="123" scope="local" />
```

The variable exists only in the current block.

### Function

```xml
<q:function name="calculate">
  <q:set name="result" value="0" scope="function" />
</q:function>
```

The variable is visible inside the function.

### Component

```xml
<q:set name="globalCounter" value="0" scope="component" />
```

The variable is visible in the whole component.

### Session

```xml
<q:set name="userData" value="{}" scope="session" />
```

The variable is shared in the session (future).

## 🎯 Practical Examples

### Cart Calculator

```xml
<q:component name="ShoppingCart" xmlns:q="https://quantum.lang/ns">
  <q:param name="price" type="number" default="10" />
  <q:param name="quantity" type="number" default="2" />

  <q:set name="subtotal" type="number" value="{price * quantity}" />
  <q:set name="tax" type="number" value="{subtotal * 0.1}" />
  <q:set name="total" type="number" value="{subtotal + tax}" />

  <q:return value="Total: R$ {total}" />
</q:component>
```

### Progressive Object Builder

```xml
<q:component name="BuildUser" xmlns:q="https://quantum.lang/ns">
  <q:set name="user" type="object" value="{}" />

  <q:set name="user" operation="merge" value='{"name":"Daniel"}' />
  <q:set name="user" operation="merge" value='{"age":30}' />
  <q:set name="user" operation="merge" value='{"role":"admin"}' />

  <q:return value="{user}" />
</q:component>
```

### List Filtering and Processing

```xml
<q:component name="ProcessList" xmlns:q="https://quantum.lang/ns">
  <q:set name="numbers" type="array" value="[5,2,8,1,9]" />

  <!-- Sort -->
  <q:set name="numbers" operation="sort" />

  <!-- Reverse -->
  <q:set name="numbers" operation="reverse" />

  <q:return value="Sorted (desc): {numbers}" />
</q:component>
```

## ⚠️ Error Handling

When a validation fails, Quantum raises a descriptive error:

```xml
<q:set name="email" value="invalid" validate="email" />
```

**Error:** `Set execution error for 'email': Invalid email format`

```xml
<q:set name="age" type="number" value="15" range="18..120" />
```

**Error:** `Set execution error for 'age': Value must be between 18 and 120`

## 📋 Operations Summary

| Operation | Description | Example |
|----------|-----------|---------|
| `assign` | Assignment (default) | `value="10"` |
| `increment` | Increment | `operation="increment"` |
| `decrement` | Decrement | `operation="decrement"` |
| `add` | Addition | `operation="add" value="5"` |
| `multiply` | Multiplication | `operation="multiply" value="2"` |
| `append` | Adds at the end (array) | `operation="append" value="item"` |
| `prepend` | Adds at the start (array) | `operation="prepend" value="item"` |
| `remove` | Removes by value (array) | `operation="remove" value="item"` |
| `removeAt` | Removes by index (array) | `operation="removeAt" index="2"` |
| `clear` | Clears the array | `operation="clear"` |
| `sort` | Sorts the array | `operation="sort"` |
| `reverse` | Reverses the array | `operation="reverse"` |
| `unique` | Removes duplicates | `operation="unique"` |
| `merge` | Merges objects | `operation="merge" value='{...}'` |
| `setProperty` | Sets a property | `operation="setProperty" key="x" value="1"` |
| `deleteProperty` | Removes a property | `operation="deleteProperty" key="x"` |
| `clone` | Clones an object | `operation="clone" source="original"` |
| `uppercase` | Upper case | `operation="uppercase"` |
| `lowercase` | Lower case | `operation="lowercase"` |
| `trim` | Removes spaces | `operation="trim"` |

## 🔗 See Also

- [Loops (`q:loop`)](./loops.md)
- [Databinding](./databinding.md)
- [Components (`q:component`)](./components.md)
