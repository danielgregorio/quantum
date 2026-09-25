# State Management (`q:set`)

`q:set` stores a variable: it converts the value to a `type`, checks it, and
changes it in place with an `operation`. Every attribute, with its values and
defaults, is in the [Reference](../reference/tags#q-set); the rules are
[SET-1 to SET-5](../reference/spec#SET-1).

Each example on this page runs in CI, and shows what it returns.

## Storing a value

```xml
<q:set name="counter" type="number" value="10" />
<q:return value="{counter}" />
```

**Output:** `10`

### Types

`type` converts the value: `string`, `number`, `decimal`, `boolean`, `array`,
`object`, `json` (and the aliases the Reference lists).

```xml
<q:set name="message" type="string" value="Hello World" />
<q:set name="age" type="number" value="25" />
<q:set name="price" type="decimal" value="19.99" />
<q:set name="isActive" type="boolean" value="true" />
<q:return value="{[message, age, price, isActive]}" />
```

**Output:** `["Hello World", 25, 19.99, true]`

```xml
<q:set name="fruits" type="array" value='["apple", "banana", "orange"]' />
<q:set name="user" type="object" value='{"name": "Daniel", "age": 30}' />
<q:set name="config" type="json" value='{"debug": true, "port": 8080}' />
<q:return value="{[fruits, user, config]}" />
```

**Output:** `[["apple", "banana", "orange"], {"name": "Daniel", "age": 30}, {"debug": true, "port": 8080}]`

### Without `type`

A `value` that is exactly one expression keeps the type of what it computes,
as in `q:return` and in a component's props; anything else is text (SET-5):

```xml
<q:set name="tags" value="{['new', 'sale']}" />
<q:set name="count" value="{len(tags)}" />
<q:set name="label" value="{count} tags" />
<q:set name="code" value="007" />
<q:return value="{[tags, count, label, code]}" />
```

**Output:** `[["new", "sale"], 2, "2 tags", "007"]`

`tags` is the list, `count` the number 2, `label` and `code` are text. Up to
Quantum 0.22 every `q:set` without `type` stored text, so `len(tags)` counted
the characters of `['new', 'sale']`. Write `type="string"` where you want text.

### A default

`default` is stored when `value` resolves to nothing: missing, `null` or empty
text (SET-1). On a first visit, `session.clicks` does not exist yet:

```xml
<q:set name="clicks" value="{session.clicks}" default="0" />
<q:return value="Visits: {clicks}" />
```

**Output:** `Visits: 0`

## Operations

`operation` changes the variable in place (SET-3). The default is `assign`.

### Numbers

```xml
<q:set name="counter" type="number" value="0" />
<q:set name="counter" operation="increment" />
<q:set name="counter" operation="increment" />
<q:set name="counter" operation="increment" step="5" />
<q:return value="Counter: {counter}" />
```

**Output:** `Counter: 7`

```xml
<q:set name="total" type="number" value="10" />
<q:set name="total" operation="add" value="5" />
<q:set name="total" operation="multiply" value="2" />
<q:return value="Total: {total}" />
```

**Output:** `Total: 30`

`decrement` works like `increment`. A variable that does not exist starts at
0, and `append` to one that does not exist starts a list:

```xml
<q:set name="hits" operation="increment" />
<q:set name="items" operation="append" value="first" />
<q:return value="{[hits, items]}" />
```

**Output:** `[1, ["first"]]`

### Lists

```xml
<q:set name="list" type="array" value="[]" />
<q:set name="list" operation="append" value="apple" />
<q:set name="list" operation="append" value="banana" />
<q:set name="list" operation="prepend" value="orange" />
<q:return value="{list}" />
```

**Output:** `["orange", "apple", "banana"]`

`remove` takes out the first item equal to `value`; `removeAt` the item at
`index`, counting from 0:

```xml
<q:set name="list" type="array" value='["a", "b", "c", "d"]' />
<q:set name="list" operation="remove" value="b" />
<q:set name="list" operation="removeAt" index="2" />
<q:return value="{list}" />
```

**Output:** `["a", "c"]`

```xml
<q:set name="list" type="array" value='["pear", "apple", "pear", "fig"]' />
<q:set name="list" operation="unique" />
<q:set name="list" operation="sort" />
<q:set name="list" operation="reverse" />
<q:return value="{list}" />
```

**Output:** `["pear", "fig", "apple"]`

```xml
<q:set name="list" type="array" value='["a", "b"]' />
<q:set name="list" operation="clear" />
<q:return value="{list}" />
```

**Output:** `[]`

### Objects

```xml
<q:set name="user" type="object" value="{}" />
<q:set name="user" operation="merge" value='{"name": "Daniel"}' />
<q:set name="user" operation="merge" value='{"age": 30}' />
<q:return value="{user}" />
```

**Output:** `{"name": "Daniel", "age": 30}`

`setProperty` and `deleteProperty` take a `key`. A `value` that is literal
text stays text:

```xml
<q:set name="config" type="object" value="{}" />
<q:set name="config" operation="setProperty" key="debug" value="true" />
<q:set name="config" operation="setProperty" key="port" value="8080" />
<q:set name="config" operation="deleteProperty" key="debug" />
<q:return value="{config}" />
```

**Output:** `{"port": "8080"}`

`clone` stores a copy of the variable named by `source`; changing the copy
leaves the original alone:

```xml
<q:set name="original" type="object" value='{"x": 1}' />
<q:set name="copy" operation="clone" source="original" />
<q:set name="copy" operation="setProperty" key="x" value="2" />
<q:return value="{[original, copy]}" />
```

**Output:** `[{"x": 1}, {"x": "2"}]`

### Text

```xml
<q:set name="text" value="  Hello World  " />
<q:set name="text" operation="trim" />
<q:set name="upper" value="{text}" />
<q:set name="upper" operation="uppercase" />
<q:set name="lower" value="{text}" />
<q:set name="lower" operation="lowercase" />
<q:return value="{[text, upper, lower]}" />
```

**Output:** `["Hello World", "HELLO WORLD", "hello world"]`

`format` stores `value` with its expressions filled in:

```xml
<q:set name="name" value="Ana" />
<q:set name="greeting" operation="format" value="Hello, {name}!" />
<q:return value="{greeting}" />
```

**Output:** `Hello, Ana!`

### The wrong kind of value

An operation on a value of the wrong kind is an error that names the variable:

```xml
<q:set name="x" value="1" />
<q:set name="x" operation="append" value="2" />
```

**Error:** `Set execution error for 'x': Cannot perform array operation on non-array`

An operation that does not exist is a parse error (PARSE-5):

```xml
<q:set name="x" value="1" operation="explode" />
```

**Error:** `operation="explode" does not exist`

## With loops

```xml
<q:set name="total" type="number" value="0" />
<q:loop type="range" var="i" from="1" to="5">
  <q:set name="total" operation="add" value="{i}" />
</q:loop>
<q:return value="Total: {total}" />
```

**Output:** `Total: 15`

```xml
<q:set name="results" type="array" value="[]" />
<q:loop type="range" var="i" from="1" to="3">
  <q:set name="results" operation="append" value="{i * 2}" />
</q:loop>
<q:return value="{results}" />
```

**Output:** `[2, 4, 6]`

## Validation

`q:set` checks the value it stores (SET-4). A value that passes is stored:

```xml
<q:set name="code" type="string" value="ABC1234" pattern="^[A-Z]{3}\d{4}$" />
<q:set name="status" type="string" value="active" enum="pending,active,inactive" />
<q:set name="score" type="number" value="87" min="0" max="100" />
<q:set name="age" type="number" value="25" range="18..120" />
<q:set name="username" type="string" value="ana" minlength="3" maxlength="20" />
<q:return value="{[code, status, score, age, username]}" />
```

**Output:** `["ABC1234", "active", 87, 25, "ana"]`

A value that does not pass is an error that names the variable and says why:

```xml
<q:set name="email" type="string" value="" required="true" />
```

**Error:** `Set execution error for 'email': This field cannot be empty`

```xml
<q:set name="age" type="number" value="{null}" nullable="false" />
```

**Error:** `Set execution error for 'age': Variable 'age' cannot be null`

```xml
<q:set name="status" type="string" value="archived" enum="pending,active,inactive" />
```

**Error:** `Set execution error for 'status': Value must be one of: pending, active, inactive`

```xml
<q:set name="age" type="number" value="15" range="18..120" />
```

**Error:** `Set execution error for 'age': Value must be between 18 and 120`

```xml
<q:set name="score" type="number" value="120" min="0" max="100" />
```

**Error:** `Set execution error for 'score': Value must be at most 100`

```xml
<q:set name="username" type="string" value="al" minlength="3" maxlength="20" />
```

**Error:** `Set execution error for 'username': Value must be at least 3 characters`

### Named validators

`validate` takes `email`, `url`, `phone`, `cep`, `cpf`, `cnpj`, `uuid`,
`creditcard`, `ipv4` or `ipv6` — or a regular expression starting with `^`:

```xml
<q:set name="website" type="string" value="https://quantumframework.net" validate="url" />
<q:set name="id" type="string" value="7c9e6679-7425-40de-944b-e07fc1f90ae7" validate="uuid" />
<q:set name="ip" type="string" value="192.168.0.1" validate="ipv4" />
<q:return value="valid" />
```

**Output:** `valid`

```xml
<q:set name="email" value="invalid" validate="email" />
```

**Error:** `Set execution error for 'email': Invalid email format`

`cpf` and `cnpj` (Brazilian tax IDs) check the digits, not only the shape:

```xml
<q:set name="cpf" type="string" value="123.456.789-00" validate="cpf" />
```

**Error:** `Set execution error for 'cpf': Invalid CPF check digit`

## Scopes

A variable lives where `scope` says: `local` (the default), `function`,
`component`, `session`, `application` or `request` (SET-3). The name can say
it too: `session.cart` is the `cart` in the user's session. A page's variables
live on the server, for one request (SET-2); what must outlive the request goes
in `session` or in the database. Sessions are in [Sessions](./sessions).

```xml
<q:function name="calculate">
  <q:set name="result" type="number" value="0" scope="function" />
  <q:set name="result" operation="add" value="42" />
  <q:return value="{result}" />
</q:function>
<q:return value="{calculate()}" />
```

**Output:** `42`

## A complete example

```xml
<q:component name="ShoppingCart" xmlns:q="https://quantum.lang/ns">
  <q:param name="price" type="number" default="10" />
  <q:param name="quantity" type="number" default="2" />

  <q:set name="subtotal" type="number" value="{price * quantity}" />
  <q:set name="tax" type="number" value="{subtotal * 0.1}" />
  <q:set name="total" type="number" value="{subtotal + tax}" />

  <q:return value="Total: {total}" />
</q:component>
```

**Output:** `Total: 22.0`

## See also

- [Loops (`q:loop`)](./loops.md)
- [Data binding](./databinding.md)
- [Components (`q:component`)](./components.md)
- [`q:set` in the Reference](../reference/tags#q-set)
