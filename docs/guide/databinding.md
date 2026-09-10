# Expressions & Databinding

Anything between curly braces is an expression: `{total * 2}`. Quantum evaluates
it against the variables in scope and puts the result in place.

Every example on this page runs as shown — `tests/docs` executes each block and
compares it with the **Output** below it.

## A value, or text with values in it

When an attribute is **exactly one expression**, you get the value with its
type. When there is anything else around it, you get text:

```xml
<q:component name="Pedido" xmlns:q="https://quantum.lang/ns">
  <q:set name="preco" value="9.5" type="number" />
  <q:set name="qtd" value="3" type="number" />
  <q:return value="{preco * qtd}" />
</q:component>
```

**Output:** `28.5`

```xml
<q:component name="Resumo" xmlns:q="https://quantum.lang/ns">
  <q:set name="preco" value="9.5" type="number" />
  <q:set name="qtd" value="3" type="number" />
  <q:return value="{qtd} items, total {preco * qtd}" />
</q:component>
```

**Output:** `"3 items, total 28.5"`

## Operators

| Kind | Operators |
|------|-----------|
| Arithmetic | `+` `-` `*` `/` `//` (integer division) `%` `**` |
| Comparison | `==` `!=` `<` `<=` `>` `>=` `in` `not in` |
| Logic | `and` `or` `not` — or `&&` `\|\|` `!` |
| Choice | `value if condition else other` |

Values that arrive as text — a form field, a query parameter, a tool argument
from an LLM — are treated as numbers when they look like numbers, so `+` adds:

```xml
<q:component name="Soma" xmlns:q="https://quantum.lang/ns">
  <q:set name="a" value="17" />
  <q:set name="b" value="25" />
  <q:return value="{a + b}" />
</q:component>
```

**Output:** `42`

```xml
<q:component name="Idade" xmlns:q="https://quantum.lang/ns">
  <q:set name="idade" value="20" type="number" />
  <q:set name="convite" value="false" type="boolean" />
  <q:return value="{'entra' if idade >= 18 && !convite else 'fila'}" />
</q:component>
```

**Output:** `"entra"`

## Reading lists and records

```xml
<q:component name="Leitura" xmlns:q="https://quantum.lang/ns">
  <q:set name="user" type="object" value='{"name": "Ana", "tags": ["admin", "dev"]}' />
  <q:return value="{user.name} has {user.tags.length} tags, first {user.tags[0]}, last {user.tags[-1]}" />
</q:component>
```

**Output:** `"Ana has 2 tags, first admin, last dev"`

`true`, `false` and `null` are literals. Strings use single quotes inside a
double-quoted attribute: `{status == 'ativo'}`.

## Functions

| Function | Example | Result |
|----------|---------|--------|
| `upper(s)`, `lower(s)`, `trim(s)` | `upper('ana')` | `ANA` |
| `replace(s, old, new)` | `replace('a-b', '-', '+')` | `a+b` |
| `split(s, sep=',')` | `split('a,b')` | `['a', 'b']` |
| `contains(s, part)` | `contains('quantum', 'ant')` | `true` |
| `len(x)`, `first(x)`, `last(x)` | `len(itens)` | number of items |
| `join(list, sep=', ')`, `sort(list)` | `join(sort(tags), ' / ')` | text |
| `round(n, digits=0)`, `abs`, `min`, `max` | `round(2.567, 2)` | `2.57` |
| `int(x)`, `float(x)`, `str(x)` | `int('42')` | `42` |
| `now()` | `now()` | current date and time |
| `dateAdd(unit, n, start=now)` | `dateAdd('d', 7)` | a week from now |
| `dateDiff(unit, start, end)` | `dateDiff('h', a, b)` | whole hours |
| `dateFormat(date, pattern)` | `dateFormat(now(), '%d/%m/%Y')` | `10/09/2026` |
| `hashPassword(s)`, `verifyPassword(s, hash)` | see [Authentication](/guide/authentication) | |

Units for the date functions: `s`, `n` (minutes), `h`, `d`, `w`. A
`q:function` declared in the component is called the same way: `{dobro(preco)}`.

```xml
<q:component name="Funcoes" xmlns:q="https://quantum.lang/ns">
  <q:function name="dobro">
    <q:param name="x" type="number" />
    <q:return value="{x * 2}" />
  </q:function>
  <q:set name="tags" value='["dev", "admin"]' type="array" />
  <q:return value="{upper(join(sort(tags), ' / '))} {dobro(21)}" />
</q:component>
```

**Output:** `"ADMIN / DEV 42"`

## Scoped variables

`session.`, `application.`, `request.`, `form.`, `query.` and `cookie.` read
from their scope. A page often renders before the value exists — before login,
say — so reading one that is not set gives empty text:

```xml
<q:component name="Ola" xmlns:q="https://quantum.lang/ns">
  <q:return value="[{session.nome}]" />
</q:component>
```

**Output:** `"[]"`

Doing arithmetic with a value that is not set is an error, not an empty
result. For a counter, use `operation="increment"`, which starts from zero:

```xml
<q:component name="Visitas" xmlns:q="https://quantum.lang/ns">
  <q:set name="session.visitas" operation="increment" />
  <q:return value="{session.visitas}" />
</q:component>
```

**Output:** `1`

## When an expression fails

In a `q:` attribute, an expression that cannot be evaluated stops the component
with an error that names it — nothing is silently replaced:

```xml
<q:component name="Erro" xmlns:q="https://quantum.lang/ns">
  <q:set name="total" value="3" type="number" />
  <q:return value="{totl + 1}" />
</q:component>
```

**Error:** `{totl + 1} could not be evaluated: variable 'totl' is not defined, did you mean 'total'?`

The same holds for a failed evaluation (`{10 / zero}`) and for arithmetic on a
scoped value that is not set.

Two places are deliberately more forgiving:

- **Conditions test for presence.** A name, key or attribute that does not
  exist makes a `condition` false, so `<q:if condition="flash">` works before
  there is a flash message. Anything else — a syntax error, a function that
  does not exist — is still an error.
- **HTML content keeps the text.** An expression in page content that does not
  resolve is rendered as written and logged once. Page content also holds code
  samples and stray braces, and those must not break the page.

```xml
<q:component name="Presenca" xmlns:q="https://quantum.lang/ns">
  <q:if condition="flash">
    <q:return value="tem" />
  </q:if>
  <q:return value="nao tem" />
</q:component>
```

**Output:** `"nao tem"`

## Braces that are not expressions

A JSON object and a regular-expression quantifier are left alone:

```xml
<q:component name="Literais" xmlns:q="https://quantum.lang/ns">
  <q:set name="padrao" value="[0-9]{10,11}" />
  <q:set name="dados" value='[{"a": 1}, {"b": 2}]' type="array" />
  <q:return value="{padrao} {len(dados)}" />
</q:component>
```

**Output:** `"[0-9]{10,11} 2"`

## Reference

The rules on this page are `EXPR-1` to `EXPR-5` in
[SPEC.md](https://github.com/danielgregorio/quantum/blob/main/SPEC.md).
