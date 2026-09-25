---
source: guide/conditionals.md
source_hash: f186a35fba5d
---

# Condicionales (q:if, q:elseif, q:else)

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/conditionals).
:::

`q:if` ejecuta su cuerpo cuando su `condition` es verdadera. `q:elseif` y `q:else`
agregan alternativas. Cada ejemplo de esta página que tiene un **Output** lo
ejecuta el conjunto de pruebas.

## If, elseif, else {#if-elseif-else}

```xml
<q:component name="Grade" xmlns:q="https://quantum.lang/ns">
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

`q:elseif` y `q:else` también se pueden escribir **dentro** del `q:if`, después de
su cuerpo. Las dos formas significan lo mismo, en cualquier lugar — en un
componente, un bucle, una función, una acción o una plantilla HTML:

```xml
<q:component name="EvenOdd" xmlns:q="https://quantum.lang/ns">
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

Un `q:else` o `q:elseif` sin un `q:if` justo antes es un error de análisis.

## Escribir condiciones {#writing-conditions}

Una condición es una [expresión](/es/guide/databinding), con o sin llaves:
`condition="age >= 18"` y `condition="{age >= 18}"` son lo mismo.

| | |
|---|---|
| Comparación | `==` `!=` `<` `<=` `>` `>=` `in` |
| Lógica | `and` `or` `not`, o `&&` `\|\|` `!` |
| Texto | `status == 'active'` — comillas simples dentro del atributo |

```xml
<q:component name="Filter" xmlns:q="https://quantum.lang/ns">
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

### Verdadero y falso {#true-and-false}

`false`, `0`, el texto vacío, una lista vacía y `null` son falsos; todo lo demás
es verdadero. El **texto** `"false"` no está vacío, así que es verdadero — declara
los booleanos con `type="boolean"`:

```xml
<q:component name="Booleans" xmlns:q="https://quantum.lang/ns">
  <q:set name="as_text" value="false" />
  <q:set name="as_boolean" value="false" type="boolean" />
  <q:set name="r" value="" />
  <q:if condition="as_text"><q:set name="r" value="{r}text " /></q:if>
  <q:if condition="as_boolean"><q:set name="r" value="{r}boolean" /></q:if>
  <q:return value="[{r}]" />
</q:component>
```

**Output:** `"[text ]"`

### Una condición es una prueba de presencia {#a-condition-is-a-presence-test}

Un nombre, una clave o un atributo que no existe hace que la condición sea
**falsa** — esto es lo que permite que una página verifique un valor que solo
existe a veces, como un mensaje flash:

```xml
<q:component name="Notice" xmlns:q="https://quantum.lang/ns">
  <q:if condition="flash">
    <q:return value="{flash}" />
  </q:if>
  <q:return value="no message" />
</q:component>
```

**Output:** `"no message"`

Cualquier otro fallo es un error, nunca un falso silencioso — una condición sin
terminar detiene el componente:

```xml
<q:component name="Unfinished" xmlns:q="https://quantum.lang/ns">
  <q:set name="age" value="20" type="number" />
  <q:if condition="age >">
    <q:return value="adult" />
  </q:if>
</q:component>
```

**Error:** `condition 'age >' could not be evaluated`

## Terminar antes {#returning-early}

El primer `q:return` que se ejecuta termina el componente o la función, así que
una cadena de verificaciones no necesita anidamiento:

```xml
<q:component name="Order" xmlns:q="https://quantum.lang/ns">
  <q:function name="process">
    <q:param name="order_id" type="string" default="" />
    <q:if condition="!order_id">
      <q:return value="order id required" />
    </q:if>
    <q:return value="order {order_id} processed" />
  </q:function>

  <q:return value="{process()} / {process('A7')}" />
</q:component>
```

**Output:** `"order id required / order A7 processed"`

## En una página {#in-a-page}

En HTML, `q:if` decide qué se renderiza:

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

**Shows:** `Login`

Antes del inicio de sesión, `session.authenticated` no existe, así que la página
muestra el enlace Login. Ver [Autenticación](/guide/authentication) para el inicio
de sesión en sí.

## Relacionado {#related}

- [Expresiones y enlace de datos](/es/guide/databinding) — todo lo que puede usar una condición
- [Bucles](/es/guide/loops)
- [Funciones](/es/guide/functions)
