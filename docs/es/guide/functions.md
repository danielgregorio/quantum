---
source: guide/functions.md
source_hash: 7d723be16710
---

# Funciones (`q:function`)

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/functions).
:::

Un `q:function` es una porción de lógica con nombre dentro de un componente.
Recibe parámetros, ejecuta su cuerpo y devuelve el valor de su `q:return`. Cada
ejemplo de esta página que tiene un **Output** lo ejecuta el conjunto de pruebas.

## Declarar y llamar {#declaring-and-calling}

```xml
<q:component name="Sum" xmlns:q="https://quantum.lang/ns">
  <q:function name="add" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:return value="{a + b}" />
  </q:function>

  <q:return value="Sum: {add(10, 20)}" />
</q:component>
```

**Output:** `"Sum: 30"`

Una función se llama desde cualquier expresión de su componente — un atributo
`q:` o el HTML de la página: `<p>Total: {add(price, tax)}</p>`.

## Parámetros {#parameters}

Los argumentos se vinculan **por posición** o **por nombre**, y `default`
completa lo que falta:

```xml
<q:component name="Name" xmlns:q="https://quantum.lang/ns">
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

En cada llamada, cada argumento se convierte a su `type` y se verifica contra
sus reglas — el mismo `q:param` que en las [acciones](/guide/actions):

| Atributo | Verifica |
|-----------|--------|
| `required="true"` | que se pase el argumento |
| `type` | `string`, `number`, `integer`, `boolean`, `email`, `url`, `array`, `object` |
| `min` / `max` | rango numérico |
| `minlength` / `maxlength` / `pattern` | texto |
| `enum` | uno de una lista separada por comas |
| `range="1..10"` | entre los dos, ambos incluidos |

```xml
<q:component name="SignUp" xmlns:q="https://quantum.lang/ns">
  <q:function name="register">
    <q:param name="email" type="email" required="true" />
    <q:param name="age" type="number" min="18" max="120" />
    <q:return value="{email} ({age})" />
  </q:function>

  <q:return value="{register('ann@example.com', '30')}" />
</q:component>
```

**Output:** `"ann@example.com (30)"`

Un argumento que no pasa detiene la llamada con un error que nombra el
parámetro:

```xml
<q:component name="Smallest" xmlns:q="https://quantum.lang/ns">
  <q:function name="register">
    <q:param name="email" type="email" required="true" />
    <q:param name="age" type="number" min="18" max="120" />
    <q:return value="{email} ({age})" />
  </q:function>

  <q:return value="{register('ann@example.com', 15)}" />
</q:component>
```

**Error:** `Parameter 'age' must be at least 18 (got 15)`

## Devolver {#returning}

El primer `q:return` que se ejecuta termina la función, así que las
verificaciones pueden devolver antes:

```xml
<q:component name="Grade" xmlns:q="https://quantum.lang/ns">
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

`returnType` se verifica en cada retorno: el valor se convierte al tipo (`"7"`
pasa a ser `7` para `number`), y un valor que no es del tipo es un error que
nombra la función. `any` (por defecto) acepta cualquier cosa; `void` significa
que la función no devuelve nada.

## Bucles y recursión {#loops-and-recursion}

El cuerpo de una función puede usar todo lo que puede usar un componente —
`q:set`, `q:loop`, `q:query`, otras funciones, y a sí misma:

```xml
<q:component name="Maths" xmlns:q="https://quantum.lang/ns">
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

## Lo que `q:function` no tiene {#what-q-function-does-not-have}

Versiones anteriores de esta página describían `cache`, `memoize`, `pure`,
`async`, `retry`, `timeout`, `access`, `scope="global"`, endpoints REST y un
sistema de eventos. Se aceptaban y nunca hicieron nada, y se eliminaron en la
0.11: el analizador ahora rechaza esos atributos y lo dice.

Una función pertenece a su componente. Para compartir lógica entre páginas,
ponla en un componente y úsala con [`q:import`](/es/guide/components).

## Relacionado {#related}

- [Expresiones y enlace de datos](/guide/databinding)
- [Condicionales](/es/guide/conditionals) · [Bucles](/es/guide/loops)
- [Manejo de estado (`q:set`)](/es/guide/state-management)
