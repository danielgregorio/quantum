---
source: guide/state-management.md
source_hash: abd4da66d07f
---

# Manejo de estado (`q:set`)

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/state-management).
:::

`q:set` guarda una variable: convierte el valor a un `type`, lo verifica y lo
cambia en su lugar con una `operation`. Cada atributo, con sus valores y sus
valores por defecto, está en la [Referencia](/reference/tags#q-set); las reglas son
[SET-1 a SET-5](/reference/spec#SET-1).

Cada ejemplo de esta página se ejecuta en CI, y muestra lo que devuelve.

## Guardar un valor {#storing-a-value}

```xml
<q:set name="counter" type="number" value="10" />
<q:return value="{counter}" />
```

**Output:** `10`

### Tipos {#types}

`type` convierte el valor: `string`, `number`, `decimal`, `boolean`, `array`,
`object`, `json` (y los alias que lista la Referencia).

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

### Sin `type` {#without-type}

Un `value` que es exactamente una expresión conserva el tipo de lo que calcula,
como en `q:return` y en las props de un componente; cualquier otra cosa es texto (SET-5):

```xml
<q:set name="tags" value="{['new', 'sale']}" />
<q:set name="count" value="{len(tags)}" />
<q:set name="label" value="{count} tags" />
<q:set name="code" value="007" />
<q:return value="{[tags, count, label, code]}" />
```

**Output:** `[["new", "sale"], 2, "2 tags", "007"]`

`tags` es la lista, `count` el número 2, `label` y `code` son texto. Antes de la
1.0, todo `q:set` sin `type` guardaba texto, así que `len(tags)` contaba los
caracteres de `['new', 'sale']`. Escribe `type="string"` donde quieras texto.

### Un valor por defecto {#a-default}

`default` se guarda cuando `value` no resulta en nada: falta, es `null` o es
texto vacío (SET-1). En una primera visita, `session.clicks` todavía no existe:

```xml
<q:set name="clicks" value="{session.clicks}" default="0" />
<q:return value="Visits: {clicks}" />
```

**Output:** `Visits: 0`

## Operaciones {#operations}

`operation` cambia la variable en su lugar (SET-3). La operación por defecto es `assign`.

### Números {#numbers}

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

`decrement` funciona como `increment`. Una variable que no existe empieza en
0, y `append` sobre una que no existe empieza una lista:

```xml
<q:set name="hits" operation="increment" />
<q:set name="items" operation="append" value="first" />
<q:return value="{[hits, items]}" />
```

**Output:** `[1, ["first"]]`

### Listas {#lists}

```xml
<q:set name="list" type="array" value="[]" />
<q:set name="list" operation="append" value="apple" />
<q:set name="list" operation="append" value="banana" />
<q:set name="list" operation="prepend" value="orange" />
<q:return value="{list}" />
```

**Output:** `["orange", "apple", "banana"]`

`remove` quita el primer elemento igual a `value`; `removeAt`, el elemento en
`index`, contando desde 0:

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

### Objetos {#objects}

```xml
<q:set name="user" type="object" value="{}" />
<q:set name="user" operation="merge" value='{"name": "Daniel"}' />
<q:set name="user" operation="merge" value='{"age": 30}' />
<q:return value="{user}" />
```

**Output:** `{"name": "Daniel", "age": 30}`

`setProperty` y `deleteProperty` reciben una `key`. Un `value` que es texto
literal queda como texto:

```xml
<q:set name="config" type="object" value="{}" />
<q:set name="config" operation="setProperty" key="debug" value="true" />
<q:set name="config" operation="setProperty" key="port" value="8080" />
<q:set name="config" operation="deleteProperty" key="debug" />
<q:return value="{config}" />
```

**Output:** `{"port": "8080"}`

`clone` guarda una copia de la variable nombrada en `source`; cambiar la copia
no toca el original:

```xml
<q:set name="original" type="object" value='{"x": 1}' />
<q:set name="copy" operation="clone" source="original" />
<q:set name="copy" operation="setProperty" key="x" value="2" />
<q:return value="{[original, copy]}" />
```

**Output:** `[{"x": 1}, {"x": "2"}]`

### Texto {#text}

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

`format` guarda `value` con sus expresiones completadas:

```xml
<q:set name="name" value="Ana" />
<q:set name="greeting" operation="format" value="Hello, {name}!" />
<q:return value="{greeting}" />
```

**Output:** `Hello, Ana!`

### Un valor del tipo equivocado {#the-wrong-kind-of-value}

Una operación sobre un valor del tipo equivocado es un error que nombra la variable:

```xml
<q:set name="x" value="1" />
<q:set name="x" operation="append" value="2" />
```

**Error:** `Set execution error for 'x': Cannot perform array operation on non-array`

Una operación que no existe es un error de análisis (PARSE-5):

```xml
<q:set name="x" value="1" operation="explode" />
```

**Error:** `operation="explode" does not exist`

## Con bucles {#with-loops}

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

## Validación {#validation}

`q:set` verifica el valor que guarda (SET-4). Un valor que pasa se guarda:

```xml
<q:set name="code" type="string" value="ABC1234" pattern="^[A-Z]{3}\d{4}$" />
<q:set name="status" type="string" value="active" enum="pending,active,inactive" />
<q:set name="score" type="number" value="87" min="0" max="100" />
<q:set name="age" type="number" value="25" range="18..120" />
<q:set name="username" type="string" value="ana" minlength="3" maxlength="20" />
<q:return value="{[code, status, score, age, username]}" />
```

**Output:** `["ABC1234", "active", 87, 25, "ana"]`

Un valor que no pasa es un error que nombra la variable y dice por qué:

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

### Validadores con nombre {#named-validators}

`validate` acepta `email`, `url`, `phone`, `cep`, `cpf`, `cnpj`, `uuid`,
`creditcard`, `ipv4` o `ipv6` — o una expresión regular que empieza con `^`:

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

`cpf` y `cnpj` (identificadores fiscales de Brasil) verifican los dígitos, no solo la forma:

```xml
<q:set name="cpf" type="string" value="123.456.789-00" validate="cpf" />
```

**Error:** `Set execution error for 'cpf': Invalid CPF check digit`

## Ámbitos {#scopes}

Una variable vive donde dice `scope`: `local` (por defecto), `function`,
`component`, `session`, `application` o `request` (SET-3). El nombre también
puede decirlo: `session.cart` es el `cart` de la sesión del usuario. Las
variables de una página viven en el servidor, durante una solicitud (SET-2); lo
que deba durar más que la solicitud va en `session` o en la base de datos. Las
sesiones están en [Sesiones](/guide/sessions).

```xml
<q:function name="calculate">
  <q:set name="result" type="number" value="0" scope="function" />
  <q:set name="result" operation="add" value="42" />
  <q:return value="{result}" />
</q:function>
<q:return value="{calculate()}" />
```

**Output:** `42`

## Un ejemplo completo {#a-complete-example}

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

## Ver también {#see-also}

- [Bucles (`q:loop`)](/guide/loops)
- [Enlace de datos](/guide/databinding)
- [Componentes (`q:component`)](/es/guide/components)
- [`q:set` en la Referencia](/reference/tags#q-set)
