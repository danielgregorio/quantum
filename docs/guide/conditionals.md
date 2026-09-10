# Conditionals (q:if, q:elseif, q:else)

`q:if` runs its body when its `condition` is true. `q:elseif` and `q:else` add
alternatives. Every example on this page with an **Output** is executed by the
test suite.

## If, elseif, else

```xml
<q:component name="Nota" xmlns:q="https://quantum.lang/ns">
  <q:param name="score" type="number" default="85" />

  <q:if condition="score >= 90">
    <q:return value="A" />
  </q:if>
  <q:elseif condition="score >= 80">
    <q:return value="B" />
  </q:elseif>
  <q:else>
    <q:return value="C" />
  </q:else>
</q:component>
```

**Output:** `"B"`

`q:elseif` and `q:else` can also be written **inside** the `q:if`, after its
body. Both spellings mean the same thing, anywhere — in a component, a loop, a
function, an action or an HTML template:

```xml
<q:component name="ParImpar" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="4">
    <q:if condition="i % 2 == 0">
      <q:return value="{i} even" />
      <q:else>
        <q:return value="{i} odd" />
      </q:else>
    </q:if>
  </q:loop>
</q:component>
```

**Output:** `["1 odd", "2 even", "3 odd", "4 even"]`

A `q:else` or `q:elseif` with no `q:if` right before it is a parse error.

## Writing conditions

A condition is an [expression](/guide/databinding), with or without braces:
`condition="age >= 18"` and `condition="{age >= 18}"` are the same.

| | |
|---|---|
| Comparison | `==` `!=` `<` `<=` `>` `>=` `in` |
| Logic | `and` `or` `not`, or `&&` `\|\|` `!` |
| Text | `status == 'active'` — single quotes inside the attribute |

```xml
<q:component name="Filtro" xmlns:q="https://quantum.lang/ns">
  <q:set name="items" type="array" value='[
    {"name": "Apple", "type": "fruit", "price": 1.50},
    {"name": "Carrot", "type": "vegetable", "price": 0.75},
    {"name": "Banana", "type": "fruit", "price": 0.45}
  ]' />

  <q:loop type="array" var="item" items="{items}">
    <q:if condition="item.type == 'fruit' && item.price < 1.00">
      <q:return value="{item.name}: {item.price}" />
    </q:if>
  </q:loop>
</q:component>
```

**Output:** `["Banana: 0.45"]`

### True and false

`false`, `0`, empty text, an empty list and `null` are false; everything else is
true. The **text** `"false"` is not empty, so it is true — declare booleans with
`type="boolean"`:

```xml
<q:component name="Booleanos" xmlns:q="https://quantum.lang/ns">
  <q:set name="texto" value="false" />
  <q:set name="booleano" value="false" type="boolean" />
  <q:set name="r" value="" />
  <q:if condition="texto"><q:set name="r" value="{r}texto " /></q:if>
  <q:if condition="booleano"><q:set name="r" value="{r}booleano" /></q:if>
  <q:return value="[{r}]" />
</q:component>
```

**Output:** `"[texto ]"`

### A condition is a presence test

A name, key or attribute that does not exist makes the condition **false** —
this is what lets a page check for a value that only sometimes exists, like a
flash message:

```xml
<q:component name="Aviso" xmlns:q="https://quantum.lang/ns">
  <q:if condition="flash">
    <q:return value="{flash}" />
  </q:if>
  <q:return value="no message" />
</q:component>
```

**Output:** `"no message"`

Any other failure is an error, never a silent false — an unfinished condition
stops the component:

```xml
<q:component name="Incompleta" xmlns:q="https://quantum.lang/ns">
  <q:set name="age" value="20" type="number" />
  <q:if condition="age >">
    <q:return value="adult" />
  </q:if>
</q:component>
```

**Error:** `condition 'age >' could not be evaluated`

## Returning early

The first `q:return` that runs ends the component or function, so a chain of
checks does not need nesting:

```xml
<q:component name="Pedido" xmlns:q="https://quantum.lang/ns">
  <q:function name="processar">
    <q:param name="pedido" type="string" default="" />
    <q:if condition="!pedido">
      <q:return value="order id required" />
    </q:if>
    <q:return value="order {pedido} processed" />
  </q:function>

  <q:return value="{processar()} / {processar('A7')}" />
</q:component>
```

**Output:** `"order id required / order A7 processed"`

## In a page

In HTML, `q:if` decides what is rendered:

```xml
<q:component name="menu" xmlns:q="https://quantum.lang/ns">
  <nav>
    <q:if condition="session.authenticated">
      <span>Hello, {session.userName}</span>
      <a href="/logout">Logout</a>
    </q:if>
    <q:else>
      <a href="/login">Login</a>
    </q:else>
  </nav>
</q:component>
```

Before login, `session.authenticated` does not exist, so the page shows the
Login link. See [Authentication](/guide/authentication) for the login itself.

## Related

- [Expressions & Databinding](/guide/databinding) — everything a condition can use
- [Loops](/guide/loops)
- [Functions](/guide/functions)
