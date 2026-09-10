# Functions (`q:function`)

A `q:function` is a named piece of logic inside a component. It takes
parameters, runs its body and gives back the value of its `q:return`. Every
example with an **Output** on this page is executed by the test suite.

## Declaring and calling

```xml
<q:component name="Soma" xmlns:q="https://quantum.lang/ns">
  <q:function name="add" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:return value="{a + b}" />
  </q:function>

  <q:return value="Sum: {add(10, 20)}" />
</q:component>
```

**Output:** `"Sum: 30"`

A function is called from any expression of its component — a `q:` attribute
or the page's HTML: `<p>Total: {add(price, tax)}</p>`.

## Parameters

Arguments bind **by position** or **by name**, and `default` fills in what is
missing:

```xml
<q:component name="Nome" xmlns:q="https://quantum.lang/ns">
  <q:function name="formatName" returnType="string">
    <q:param name="firstName" type="string" required="true" />
    <q:param name="lastName" type="string" required="true" />
    <q:param name="title" type="string" default="Mr." />
    <q:return value="{title} {firstName} {lastName}" />
  </q:function>

  <q:return value="{formatName('John', 'Doe', 'Dr.')} / {formatName(lastName='Lee', firstName='Ann')}" />
</q:component>
```

**Output:** `"Dr. John Doe / Mr. Ann Lee"`

Each argument is converted to its `type` and checked against its rules on
every call — the same `q:param` as in [actions](/guide/actions):

| Attribute | Checks |
|-----------|--------|
| `required="true"` | the argument is given |
| `type` | `string`, `number`, `integer`, `boolean`, `email`, `url`, `array`, `object` |
| `min` / `max` | numeric range |
| `minlength` / `maxlength` / `pattern` | text |
| `enum` | one of a comma-separated list |

```xml
<q:component name="Cadastro" xmlns:q="https://quantum.lang/ns">
  <q:function name="register">
    <q:param name="email" type="email" required="true" />
    <q:param name="age" type="number" min="18" max="120" />
    <q:return value="{email} ({age})" />
  </q:function>

  <q:return value="{register('ann@example.com', '30')}" />
</q:component>
```

**Output:** `"ann@example.com (30)"`

An argument that does not pass stops the call with an error naming the
parameter:

```xml
<q:component name="Menor" xmlns:q="https://quantum.lang/ns">
  <q:function name="register">
    <q:param name="email" type="email" required="true" />
    <q:param name="age" type="number" min="18" max="120" />
    <q:return value="{email} ({age})" />
  </q:function>

  <q:return value="{register('ann@example.com', 15)}" />
</q:component>
```

**Error:** `Parameter 'age' must be at least 18 (got 15)`

## Returning

The first `q:return` that runs ends the function, so checks can return early:

```xml
<q:component name="Nota" xmlns:q="https://quantum.lang/ns">
  <q:function name="grade" returnType="string">
    <q:param name="score" type="number" required="true" />
    <q:if condition="score >= 90"><q:return value="A" /></q:if>
    <q:if condition="score >= 80"><q:return value="B" /></q:if>
    <q:return value="C" />
  </q:function>

  <q:return value="{grade(95)} {grade(85)} {grade(50)}" />
</q:component>
```

**Output:** `"A B C"`

## Loops and recursion

A function body can use everything a component can — `q:set`, `q:loop`,
`q:query`, other functions, and itself:

```xml
<q:component name="Contas" xmlns:q="https://quantum.lang/ns">
  <q:function name="sumArray" returnType="number">
    <q:param name="numbers" type="array" required="true" />
    <q:set name="total" type="number" value="0" />
    <q:loop type="array" items="{numbers}" var="n">
      <q:set name="total" operation="add" value="{n}" />
    </q:loop>
    <q:return value="{total}" />
  </q:function>

  <q:function name="factorial" returnType="number">
    <q:param name="n" type="number" required="true" />
    <q:if condition="n <= 1"><q:return value="{1}" /></q:if>
    <q:return value="{n * factorial(n - 1)}" />
  </q:function>

  <q:set name="numbers" type="array" value="[10, 20, 30, 40]" />
  <q:return value="{sumArray(numbers)} {factorial(5)}" />
</q:component>
```

**Output:** `"100 120"`

## What `q:function` does not have

Earlier versions of this page described `cache`, `memoize`, `pure`, `async`,
`retry`, `timeout`, `access`, `scope="global"`, REST endpoints and an event
system. They were accepted and never did anything, and were removed in 0.11:
the parser now refuses those attributes and says so.

A function belongs to its component. To share logic between pages, put it in a
component and use it with [`q:import`](/guide/components).

## Related

- [Expressions & Databinding](/guide/databinding)
- [Conditionals](/guide/conditionals) · [Loops](/guide/loops)
- [State Management (`q:set`)](/guide/state-management)
