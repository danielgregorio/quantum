---
source: guide/databinding.md
source_hash: 68dae0629ce9
---

# Expresiones y enlace de datos

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/databinding).
:::

Todo lo que está entre llaves es una expresión: `{total * 2}`. Quantum la evalúa
con las variables del ámbito y pone el resultado en su lugar.

Cada ejemplo de esta página se ejecuta tal como se muestra — `tests/docs` ejecuta
cada bloque y lo compara con el **Output** que tiene debajo.

## Un valor, o un texto con valores dentro {#a-value-or-text-with-values-in-it}

Cuando un atributo es **exactamente una expresión**, obtienes el valor con su
tipo. Cuando hay algo más alrededor, obtienes texto:

```xml
<q:component name="Order" xmlns:q="https://quantum.lang/ns">
  <q:set name="price" value="9.5" type="number" />
  <q:set name="qty" value="3" type="number" />
  <q:return value="{price * qty}" />
</q:component>
```

**Output:** `28.5`

```xml
<q:component name="Summary" xmlns:q="https://quantum.lang/ns">
  <q:set name="price" value="9.5" type="number" />
  <q:set name="qty" value="3" type="number" />
  <q:return value="{qty} items, total {price * qty}" />
</q:component>
```

**Output:** `"3 items, total 28.5"`

## Operadores {#operators}

| Tipo | Operadores |
|------|-----------|
| Aritméticos | `+` `-` `*` `/` `//` (división entera) `%` `**` |
| Comparación | `==` `!=` `<` `<=` `>` `>=` `in` `not in` |
| Lógicos | `and` `or` `not` — o `&&` `\|\|` `!` |
| Elección | `value if condition else other` |

Los valores que llegan como texto — un campo de formulario, un parámetro de la
consulta, el argumento de una herramienta de un LLM — se tratan como números
cuando parecen números, así que `+` suma:

```xml
<q:component name="Sum" xmlns:q="https://quantum.lang/ns">
  <q:set name="a" value="17" />
  <q:set name="b" value="25" />
  <q:return value="{a + b}" />
</q:component>
```

**Output:** `42`

```xml
<q:component name="Age" xmlns:q="https://quantum.lang/ns">
  <q:set name="age" value="20" type="number" />
  <q:set name="invited" value="false" type="boolean" />
  <q:return value="{'enters' if age >= 18 && !invited else 'waits'}" />
</q:component>
```

**Output:** `"enters"`

`in` compara como lo hace `==`, así que un valor que llegó como texto igual
encuentra su número en una lista:

```xml
<q:component name="Member" xmlns:q="https://quantum.lang/ns">
  <q:set name="chosen" value="5" />
  <q:set name="allowed" value="[1, 5, 10]" type="array" />
  <q:return value="{chosen in allowed}" />
</q:component>
```

**Output:** `true`

## Leer listas y registros {#reading-lists-and-records}

```xml
<q:component name="Reading" xmlns:q="https://quantum.lang/ns">
  <q:set name="user" type="object" value='{"name": "Ana", "tags": ["admin", "dev"]}' />
  <q:return value="{user.name} has {user.tags.length} tags, first {user.tags[0]}, last {user.tags[-1]}" />
</q:component>
```

**Output:** `"Ana has 2 tags, first admin, last dev"`

`true`, `false` y `null` son literales. Los textos usan comillas simples dentro
de un atributo con comillas dobles: `{status == 'active'}`.

## Funciones {#functions}

| Función | Ejemplo | Resultado |
|----------|---------|--------|
| `upper(s)`, `lower(s)`, `trim(s)` | `upper('ana')` | `ANA` |
| `replace(s, old, new)` | `replace('a-b', '-', '+')` | `a+b` |
| `split(s, sep=',')` | `split('a,b')` | `['a', 'b']` |
| `contains(s, part)` | `contains('quantum', 'ant')` | `true` |
| `len(x)`, `first(x)`, `last(x)` | `len(items)` | cantidad de elementos |
| `get(x, key, default=null)` — una clave o un índice opcional | `get(prefs, 'theme', 'light')` | el valor, o `default` cuando falta |
| `join(list, sep=', ')`, `sort(list)` | `join(sort(tags), ' / ')` | texto |
| `round(n, digits=0)` — las mitades se alejan del cero | `round(2.5)` | `3` |
| `ceil(n)`, `floor(n)`, `abs`, `min`, `max` | `ceil(7 / 3)` | `3` |
| `int(x)`, `float(x)`, `str(x)` | `int('42')` | `42` |
| `now()` | `now()` | la fecha y la hora actuales |
| `dateAdd(unit, n, start=now)` | `dateAdd('d', 7)` | dentro de una semana |
| `dateDiff(unit, start, end)` | `dateDiff('h', a, b)` | horas completas |
| `dateFormat(date, pattern)` | `dateFormat(now(), '%d/%m/%Y')` | `10/09/2026` |
| `hashPassword(s)`, `verifyPassword(s, hash)` | ver [Autenticación](/es/guide/authentication) | |
| `random()`, `random(a, b)` | `random(1, 6)` | un número desde 0 hasta 1; un entero de `a` a `b` |
| `chance(p)`, `pick(list)` | `pick(tips)` | verdadero con probabilidad `p`; un elemento |

Unidades de las funciones de fecha: `s`, `n` (minutos), `h`, `d`, `w`. Un
`q:function` declarado en el componente se llama de la misma forma: `{twice(price)}`.

Las funciones se llaman por su nombre, nunca como métodos: `split(title, ' ')`,
no `title.split(' ')`; `ceil(n)`, no `Math.ceil(n)`. El error por una costumbre
de JavaScript nombra la función que hay que usar. `.length` funciona con textos y listas.

```xml
<q:component name="Functions" xmlns:q="https://quantum.lang/ns">
  <q:function name="twice">
    <q:param name="x" type="number" />
    <q:return value="{x * 2}" />
  </q:function>
  <q:set name="tags" value='["dev", "admin"]' type="array" />
  <q:return value="{upper(join(sort(tags), ' / '))} {twice(21)}" />
</q:component>
```

**Output:** `"ADMIN / DEV 42"`

## Variables con ámbito {#scoped-variables}

`session.`, `application.`, `request.`, `form.`, `query.` y `cookie.` leen de su
ámbito. Muchas veces una página se renderiza antes de que exista el valor —
antes del inicio de sesión, por ejemplo — así que leer uno que no está definido
da un texto vacío:

```xml
<q:component name="Hello" xmlns:q="https://quantum.lang/ns">
  <q:return value="[{session.name}]" />
</q:component>
```

**Output:** `"[]"`

Hacer cuentas con un valor que no está definido es un error, no un resultado
vacío. Para un contador, usa `operation="increment"`, que empieza en cero:

```xml
<q:component name="Visits" xmlns:q="https://quantum.lang/ns">
  <q:set name="session.visits" operation="increment" />
  <q:return value="{session.visits}" />
</q:component>
```

**Output:** `1`

## Cuando una expresión falla {#when-an-expression-fails}

En un atributo `q:`, una expresión que no se puede evaluar detiene el
componente con un error que la nombra — nada se reemplaza en silencio:

```xml
<q:component name="Broken" xmlns:q="https://quantum.lang/ns">
  <q:set name="total" value="3" type="number" />
  <q:return value="{totl + 1}" />
</q:component>
```

**Error:** `{totl + 1} could not be evaluated: variable 'totl' is not defined, did you mean 'total'?`

Lo mismo vale para una evaluación que falla (`{10 / zero}`) y para hacer cuentas
con un valor de ámbito que no está definido.

Hay dos lugares que son más tolerantes a propósito:

- **Las condiciones prueban la presencia.** Un nombre, una clave o un atributo
  que no existe hace que una `condition` sea falsa, así que
  `<q:if condition="flash">` funciona antes de que haya un mensaje flash.
  Cualquier otra cosa — un error de sintaxis, una función que no existe — sigue
  siendo un error.
- **El contenido HTML conserva el texto.** Una expresión en el contenido de la
  página que no se resuelve se renderiza tal como está escrita y se registra una
  vez en el log. El contenido de la página también tiene ejemplos de código y
  llaves sueltas, y eso no debe romper la página.

```xml
<q:component name="Presence" xmlns:q="https://quantum.lang/ns">
  <q:if condition="flash">
    <q:return value="there is one" />
  </q:if>
  <q:return value="there is none" />
</q:component>
```

**Output:** `"there is none"`

## Llaves que no son expresiones {#braces-that-are-not-expressions}

Un objeto JSON y un cuantificador de expresión regular se dejan como están:

```xml
<q:component name="Literals" xmlns:q="https://quantum.lang/ns">
  <q:set name="pattern" value="[0-9]{10,11}" />
  <q:set name="rows" value='[{"a": 1}, {"b": 2}]' type="array" />
  <q:return value="{pattern} {len(rows)}" />
</q:component>
```

**Output:** `"[0-9]{10,11} 2"`

## Referencia {#reference}

Las reglas de esta página son de `EXPR-1` a `EXPR-5` en
[SPEC.md](https://github.com/danielgregorio/quantum/blob/main/SPEC.md).
