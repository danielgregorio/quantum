---
source: guide/state-management.md
source_hash: abd4da66d07f
---
# Gerenciamento de estado (`q:set`)

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/state-management). O código é o mesmo do original.
:::

O `q:set` guarda uma variável: ele converte o valor para um `type`, o
verifica, e o muda no lugar com uma `operation`. Cada atributo, com os seus
valores e padrões, está na [Referência](../../reference/tags#q-set) (em
inglês); as regras são [SET-1 a SET-5](../../reference/spec#SET-1).

Cada exemplo desta página roda no CI e mostra o que retorna.

## Guardar um valor {#storing-a-value}

```xml
<q:set name="counter" type="number" value="10" />
<q:return value="{counter}" />
```

**Saída:** `10`

### Tipos {#types}

`type` converte o valor: `string`, `number`, `decimal`, `boolean`, `array`,
`object`, `json` (e os apelidos que a Referência lista).

```xml
<q:set name="message" type="string" value="Hello World" />
<q:set name="age" type="number" value="25" />
<q:set name="price" type="decimal" value="19.99" />
<q:set name="isActive" type="boolean" value="true" />
<q:return value="{[message, age, price, isActive]}" />
```

**Saída:** `["Hello World", 25, 19.99, true]`

```xml
<q:set name="fruits" type="array" value='["apple", "banana", "orange"]' />
<q:set name="user" type="object" value='{"name": "Daniel", "age": 30}' />
<q:set name="config" type="json" value='{"debug": true, "port": 8080}' />
<q:return value="{[fruits, user, config]}" />
```

**Saída:** `[["apple", "banana", "orange"], {"name": "Daniel", "age": 30}, {"debug": true, "port": 8080}]`

### Sem `type` {#without-type}

Um `value` que é exatamente uma expressão mantém o tipo do que ela calcula,
como no `q:return` e nas props de um componente; qualquer outra coisa é texto
(SET-5):

```xml
<q:set name="tags" value="{['new', 'sale']}" />
<q:set name="count" value="{len(tags)}" />
<q:set name="label" value="{count} tags" />
<q:set name="code" value="007" />
<q:return value="{[tags, count, label, code]}" />
```

**Saída:** `[["new", "sale"], 2, "2 tags", "007"]`

`tags` é a lista, `count` o número 2, `label` e `code` são texto. Até o
Quantum 0.22, todo `q:set` sem `type` guardava texto, então
`len(tags)` contava os caracteres de `['new', 'sale']`. Escreva
`type="string"` onde você quer texto.

### Um valor padrão {#a-default}

O `default` é guardado quando o `value` não resulta em nada: faltando, `null`
ou texto vazio (SET-1). Numa primeira visita, `session.clicks` ainda não
existe:

```xml
<q:set name="clicks" value="{session.clicks}" default="0" />
<q:return value="Visits: {clicks}" />
```

**Saída:** `Visits: 0`

## Operações {#operations}

`operation` muda a variável no lugar (SET-3). O padrão é `assign`.

### Números {#numbers}

```xml
<q:set name="counter" type="number" value="0" />
<q:set name="counter" operation="increment" />
<q:set name="counter" operation="increment" />
<q:set name="counter" operation="increment" step="5" />
<q:return value="Counter: {counter}" />
```

**Saída:** `Counter: 7`

```xml
<q:set name="total" type="number" value="10" />
<q:set name="total" operation="add" value="5" />
<q:set name="total" operation="multiply" value="2" />
<q:return value="Total: {total}" />
```

**Saída:** `Total: 30`

`decrement` funciona como `increment`. Uma variável que não existe começa em
0, e `append` numa que não existe começa uma lista:

```xml
<q:set name="hits" operation="increment" />
<q:set name="items" operation="append" value="first" />
<q:return value="{[hits, items]}" />
```

**Saída:** `[1, ["first"]]`

### Listas {#lists}

```xml
<q:set name="list" type="array" value="[]" />
<q:set name="list" operation="append" value="apple" />
<q:set name="list" operation="append" value="banana" />
<q:set name="list" operation="prepend" value="orange" />
<q:return value="{list}" />
```

**Saída:** `["orange", "apple", "banana"]`

`remove` tira o primeiro item igual a `value`; `removeAt`, o item no `index`,
contando a partir de 0:

```xml
<q:set name="list" type="array" value='["a", "b", "c", "d"]' />
<q:set name="list" operation="remove" value="b" />
<q:set name="list" operation="removeAt" index="2" />
<q:return value="{list}" />
```

**Saída:** `["a", "c"]`

```xml
<q:set name="list" type="array" value='["pear", "apple", "pear", "fig"]' />
<q:set name="list" operation="unique" />
<q:set name="list" operation="sort" />
<q:set name="list" operation="reverse" />
<q:return value="{list}" />
```

**Saída:** `["pear", "fig", "apple"]`

```xml
<q:set name="list" type="array" value='["a", "b"]' />
<q:set name="list" operation="clear" />
<q:return value="{list}" />
```

**Saída:** `[]`

### Objetos {#objects}

```xml
<q:set name="user" type="object" value="{}" />
<q:set name="user" operation="merge" value='{"name": "Daniel"}' />
<q:set name="user" operation="merge" value='{"age": 30}' />
<q:return value="{user}" />
```

**Saída:** `{"name": "Daniel", "age": 30}`

`setProperty` e `deleteProperty` recebem uma `key`. Um `value` que é texto
literal continua texto:

```xml
<q:set name="config" type="object" value="{}" />
<q:set name="config" operation="setProperty" key="debug" value="true" />
<q:set name="config" operation="setProperty" key="port" value="8080" />
<q:set name="config" operation="deleteProperty" key="debug" />
<q:return value="{config}" />
```

**Saída:** `{"port": "8080"}`

`clone` guarda uma cópia da variável nomeada por `source`; mudar a cópia não
mexe no original:

```xml
<q:set name="original" type="object" value='{"x": 1}' />
<q:set name="copy" operation="clone" source="original" />
<q:set name="copy" operation="setProperty" key="x" value="2" />
<q:return value="{[original, copy]}" />
```

**Saída:** `[{"x": 1}, {"x": "2"}]`

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

**Saída:** `["Hello World", "HELLO WORLD", "hello world"]`

`format` guarda o `value` com as expressões preenchidas:

```xml
<q:set name="name" value="Ana" />
<q:set name="greeting" operation="format" value="Hello, {name}!" />
<q:return value="{greeting}" />
```

**Saída:** `Hello, Ana!`

### O tipo errado de valor {#the-wrong-kind-of-value}

Uma operação sobre um valor do tipo errado é um erro que nomeia a variável:

```xml
<q:set name="x" value="1" />
<q:set name="x" operation="append" value="2" />
```

**Erro:** `Set execution error for 'x': Cannot perform array operation on non-array`

Uma operação que não existe é um erro de parse (PARSE-5):

```xml
<q:set name="x" value="1" operation="explode" />
```

**Erro:** `operation="explode" does not exist`

## Com loops {#with-loops}

```xml
<q:set name="total" type="number" value="0" />
<q:loop type="range" var="i" from="1" to="5">
  <q:set name="total" operation="add" value="{i}" />
</q:loop>
<q:return value="Total: {total}" />
```

**Saída:** `Total: 15`

```xml
<q:set name="results" type="array" value="[]" />
<q:loop type="range" var="i" from="1" to="3">
  <q:set name="results" operation="append" value="{i * 2}" />
</q:loop>
<q:return value="{results}" />
```

**Saída:** `[2, 4, 6]`

## Validação {#validation}

O `q:set` verifica o valor que guarda (SET-4). Um valor que passa é guardado:

```xml
<q:set name="code" type="string" value="ABC1234" pattern="^[A-Z]{3}\d{4}$" />
<q:set name="status" type="string" value="active" enum="pending,active,inactive" />
<q:set name="score" type="number" value="87" min="0" max="100" />
<q:set name="age" type="number" value="25" range="18..120" />
<q:set name="username" type="string" value="ana" minlength="3" maxlength="20" />
<q:return value="{[code, status, score, age, username]}" />
```

**Saída:** `["ABC1234", "active", 87, 25, "ana"]`

Um valor que não passa é um erro que nomeia a variável e diz por quê:

```xml
<q:set name="email" type="string" value="" required="true" />
```

**Erro:** `Set execution error for 'email': This field cannot be empty`

```xml
<q:set name="age" type="number" value="{null}" nullable="false" />
```

**Erro:** `Set execution error for 'age': Variable 'age' cannot be null`

```xml
<q:set name="status" type="string" value="archived" enum="pending,active,inactive" />
```

**Erro:** `Set execution error for 'status': Value must be one of: pending, active, inactive`

```xml
<q:set name="age" type="number" value="15" range="18..120" />
```

**Erro:** `Set execution error for 'age': Value must be between 18 and 120`

```xml
<q:set name="score" type="number" value="120" min="0" max="100" />
```

**Erro:** `Set execution error for 'score': Value must be at most 100`

```xml
<q:set name="username" type="string" value="al" minlength="3" maxlength="20" />
```

**Erro:** `Set execution error for 'username': Value must be at least 3 characters`

### Validadores com nome {#named-validators}

`validate` aceita `email`, `url`, `phone`, `cep`, `cpf`, `cnpj`, `uuid`,
`creditcard`, `ipv4` ou `ipv6` — ou uma expressão regular que começa com `^`:

```xml
<q:set name="website" type="string" value="https://quantumframework.net" validate="url" />
<q:set name="id" type="string" value="7c9e6679-7425-40de-944b-e07fc1f90ae7" validate="uuid" />
<q:set name="ip" type="string" value="192.168.0.1" validate="ipv4" />
<q:return value="valid" />
```

**Saída:** `valid`

```xml
<q:set name="email" value="invalid" validate="email" />
```

**Erro:** `Set execution error for 'email': Invalid email format`

`cpf` e `cnpj` conferem os dígitos, não só o formato:

```xml
<q:set name="cpf" type="string" value="123.456.789-00" validate="cpf" />
```

**Erro:** `Set execution error for 'cpf': Invalid CPF check digit`

## Escopos {#scopes}

Uma variável vive onde o `scope` diz: `local` (o padrão), `function`,
`component`, `session`, `application` ou `request` (SET-3). O nome também
pode dizer: `session.cart` é o `cart` na sessão do usuário. As variáveis de
uma página vivem no servidor, por uma requisição (SET-2); o que precisa
sobreviver à requisição vai para `session` ou para o banco. As sessões estão
em [Sessions](/guide/sessions) (em inglês).

```xml
<q:function name="calculate">
  <q:set name="result" type="number" value="0" scope="function" />
  <q:set name="result" operation="add" value="42" />
  <q:return value="{result}" />
</q:function>
<q:return value="{calculate()}" />
```

**Saída:** `42`

## Um exemplo completo {#a-complete-example}

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

**Saída:** `Total: 22.0`

## Veja também {#see-also}

- [Loops (`q:loop`)](./loops.md)
- [Databinding](./databinding.md)
- [Componentes (`q:component`)](./components.md)
- [`q:set` na Referência](../../reference/tags#q-set) (em inglês)
