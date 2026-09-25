---
source: guide/components.md
source_hash: 1a0d2d913b73
---

# Componentes

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/components).
:::

Los componentes son los bloques fundamentales de las aplicaciones Quantum. Encapsulan lógica, procesamiento de datos y generación de salida en unidades modulares y reutilizables.

Los ejemplos de esta página se ejecutan en cada cambio: los que tienen un
**Output:** tal como se muestran, y los demás — los que reciben parámetros, y la
página que usa una tarjeta — en `tests/docs/test_guide_components.py`.

## Estructura básica {#basic-structure}

Todo componente de Quantum sigue esta estructura:

```xml
<q:component name="ComponentName" xmlns:q="https://quantum.lang/ns">
  <!-- Component logic here -->
  <q:return value="output" />
</q:component>
```

**Output:** `"output"`

### Elementos obligatorios {#required-elements}

| Elemento | Descripción |
|---------|-------------|
| `q:component` | Elemento raíz |
| atributo `name` | El nombre del componente (PascalCase) |
| `xmlns:q` | Declaración del espacio de nombres de Quantum |

## Componentes simples {#simple-components}

### Hola mundo {#hello-world}

```xml
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello, World!" />
</q:component>
```

**Output:** `"Hello, World!"`

### Terminar antes {#returning-early}

`q:return` termina el componente: el primero que se ejecuta es el resultado, y
lo que viene después no se ejecuta. Dentro de un `q:if`, termina el componente
solo cuando su rama se ejecuta.

```xml
<q:component name="Stock" xmlns:q="https://quantum.lang/ns">
  <q:set name="stock" value="0" type="number" />

  <q:if condition="stock == 0">
    <q:return value="Sold out" />
  </q:if>
  <q:return value="{stock} in stock" />
</q:component>
```

**Output:** `"Sold out"`

Dentro de un bucle es distinto: cada `q:return` agrega un elemento a una lista
(ver [Bucles en componentes](#loops-in-components)).

## Parámetros de componentes {#component-parameters}

Recibe entradas con `q:param`:

```xml
<q:component name="Greeting" xmlns:q="https://quantum.lang/ns">
  <q:param name="name" type="string" required="true" />
  <q:param name="formal" type="boolean" default="false" />

  <q:if condition="formal">
    <q:return value="Good day, {name}." />
  </q:if>
  <q:else>
    <q:return value="Hey {name}!" />
  </q:else>
</q:component>
```

Con `name` = `Ana` devuelve `"Hey Ana!"`; si además `formal` = `true`,
`"Good day, Ana."`. Sin `name` es un error:
`Required parameter 'name' is missing`.

### Atributos de los parámetros {#parameter-attributes}

| Atributo | Descripción | Ejemplo |
|-----------|-------------|---------|
| `name` | Nombre del parámetro | `name="userId"` |
| `type` | Tipo de dato | `type="string"` |
| `required` | Parámetro obligatorio | `required="true"` |
| `default` | Valor por defecto | `default="10"` |

### Tipos {#types}

El `type` de un `q:param` es uno de `string`, `integer`, `number`, `decimal`,
`boolean`, `array`, `object`, `json`, `email`, `url`, `date`, `file` o `any`
(y los alias `text`, `int`, `long`, `numeric`, `float`, `double`, `binary`,
`upload`). Cualquier otro nombre es un error de análisis.

Un valor que no encaja es un error que nombra el parámetro:
`age` de tipo `number` con el valor `abc` detiene el componente con
`Parameter 'age' must be a number, got 'abc'`, y un `email` con el valor
`not-an-email`, con `Parameter 'email' must be a valid email`.

## Estado del componente {#component-state}

Usa `q:set` para las variables internas. Un `q:set` posterior con el mismo
nombre reemplaza el valor:

```xml
<q:component name="Counter" xmlns:q="https://quantum.lang/ns">
  <q:set name="count" value="0" type="number" />
  <q:set name="step" value="1" type="number" />
  <q:set name="count" value="{count + step}" />

  <q:return value="Count: {count}" />
</q:component>
```

**Output:** `"Count: 1"`

### Validación de variables {#variable-validation}

`q:set` puede verificar el valor que guarda — `validate` (`email`, `url`, …),
`range` y `enum`:

```xml
<q:set name="email"
       value="user@example.com"
       validate="email" />

<q:set name="status"
       type="string"
       value="active"
       enum="active,inactive,pending" />

<q:set name="age"
       type="number"
       value="200"
       range="0..150" />
```

**Error:** `Value must be between 0 and 150`

Los dos primeros pasan; el tercero detiene el componente. Un `status` fuera de
la lista lo detiene con `Value must be one of: active, inactive, pending`, y un
correo que no lo es, con `Invalid email format`.

## Funciones del componente {#component-functions}

Define lógica reutilizable con `q:function`, y llámala en una expresión:

```xml
<q:component name="Calculator" xmlns:q="https://quantum.lang/ns">
  <q:function name="add" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:return value="{a + b}" />
  </q:function>

  <q:function name="multiply" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:return value="{a * b}" />
  </q:function>

  <q:set name="sum" value="{add(5, 3)}" />
  <q:set name="product" value="{multiply(4, 7)}" />

  <q:return value="5 + 3 = {sum}, 4 * 7 = {product}" />
</q:component>
```

**Output:** `"5 + 3 = 8, 4 * 7 = 28"`

Más en [Funciones](/guide/functions).

## Bucles en componentes {#loops-in-components}

Un `q:return` dentro de un bucle no lo termina: cada uno agrega un elemento, y
el componente devuelve la lista.

### Bucle de rango {#range-loop}

```xml
<q:component name="Numbers" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="5">
    <q:return value="Number {i}" />
  </q:loop>
</q:component>
```

**Output:** `["Number 1", "Number 2", "Number 3", "Number 4", "Number 5"]`

### Bucle de array {#array-loop}

```xml
<q:component name="Fruits" xmlns:q="https://quantum.lang/ns">
  <q:set name="fruits" value='["Apple", "Banana", "Cherry"]' />

  <q:loop type="array" var="fruit" items="{fruits}">
    <q:return value="I like {fruit}" />
  </q:loop>
</q:component>
```

**Output:** `["I like Apple", "I like Banana", "I like Cherry"]`

### Bucle de lista {#list-loop}

```xml
<q:component name="Colors" xmlns:q="https://quantum.lang/ns">
  <q:loop type="list" var="color" items="red,green,blue" delimiter=",">
    <q:return value="Color: {color}" />
  </q:loop>
</q:component>
```

**Output:** `["Color: red", "Color: green", "Color: blue"]`

### Bucle con índice {#loop-with-index}

`index` nombra la posición, contada desde 0:

```xml
<q:component name="IndexedList" xmlns:q="https://quantum.lang/ns">
  <q:set name="items" value='["First", "Second", "Third"]' />

  <q:loop type="array" var="item" items="{items}" index="i">
    <q:return value="{i + 1}. {item}" />
  </q:loop>
</q:component>
```

**Output:** `["1. First", "2. Second", "3. Third"]`

## Condicionales {#conditionals}

### If/Else básico {#basic-if-else}

```xml
<q:component name="AgeCheck" xmlns:q="https://quantum.lang/ns">
  <q:param name="age" type="number" required="true" />

  <q:if condition="age >= 18">
    <q:return value="Adult" />
  </q:if>
  <q:else>
    <q:return value="Minor" />
  </q:else>
</q:component>
```

Con `age` = `20` devuelve `"Adult"`; con `15`, `"Minor"`.

### Varias condiciones {#multiple-conditions}

```xml
<q:component name="Grade" xmlns:q="https://quantum.lang/ns">
  <q:param name="score" type="number" required="true" />

  <q:if condition="score >= 90">
    <q:return value="A" />
  </q:if>
  <q:elseif condition="score >= 80">
    <q:return value="B" />
  </q:elseif>
  <q:elseif condition="score >= 70">
    <q:return value="C" />
  </q:elseif>
  <q:elseif condition="score >= 60">
    <q:return value="D" />
  </q:elseif>
  <q:else>
    <q:return value="F" />
  </q:else>
</q:component>
```

Con `score` = `85` devuelve `"B"`; con `42`, `"F"`.

## Enlace de datos {#data-binding}

Usa `{expression}` para los valores dinámicos:

### Variables simples {#simple-variables}

```xml
<q:set name="name" value="Alice" />
<q:return value="Hello, {name}!" />
```

**Output:** `"Hello, Alice!"`

### Propiedades de objetos {#object-properties}

```xml
<q:set name="user" type="object" value='{"name": "Bob", "age": 30}' />
<q:return value="{user.name} is {user.age} years old" />
```

**Output:** `"Bob is 30 years old"`

### Expresiones {#expressions}

```xml
<q:set name="price" value="100" />
<q:set name="quantity" value="5" />
<q:return value="Total: ${price * quantity}" />
```

**Output:** `"Total: $500"`

### Funciones de texto {#string-functions}

Las funciones se llaman con el valor como argumento — ver la
[lista de funciones](/guide/databinding#functions):

```xml
<q:set name="text" value="hello world" />
<q:return value="{upper(text)}" />
```

**Output:** `"HELLO WORLD"`

## Bucles anidados {#nested-loops}

Los elementos de un bucle interno van a la lista del bucle externo uno por uno, en orden:

```xml
<q:component name="Report" xmlns:q="https://quantum.lang/ns">
  <q:set name="categories" value='[
    {"name": "Electronics", "items": ["Phone", "Laptop"]},
    {"name": "Clothing", "items": ["Shirt", "Pants"]}
  ]' />

  <q:loop type="array" var="category" items="{categories}">
    <q:return value="Category: {category.name}" />

    <q:loop type="array" var="item" items="{category.items}">
      <q:return value="  - {item}" />
    </q:loop>
  </q:loop>
</q:component>
```

**Output:** `["Category: Electronics", "  - Phone", "  - Laptop", "Category: Clothing", "  - Shirt", "  - Pants"]`

## Usar un componente dentro de otro {#using-one-component-inside-another}

Una página usa otro componente — una tarjeta, un diseño — importándolo y
escribiéndolo como una etiqueta. Guárdalo como `components/_parts/Card.q`:

```xml
<q:component name="Card" xmlns:q="https://quantum.lang/ns">
  <q:param name="title" required="true" />
  <section class="card">
    <h2>{title}</h2>
    <q:slot />
  </section>
</q:component>
```

Guárdalo como `components/index.q`:

```xml
<q:component name="Home" xmlns:q="https://quantum.lang/ns">
  <q:import component="Card" from="_parts" />
  <q:set name="open" value="3" type="number" />

  <Card title="Open tickets: {open}">
    <p>The oldest is from {'Monday'}.</p>
  </Card>
</q:component>
```

Abrir `/` muestra la tarjeta con el título **Open tickets: 3** y, dentro de ella,
**The oldest is from Monday.**

- `q:import` busca el componente en `paths.components` de
  `quantum.config.yaml`, en la carpeta `from` cuando se declara. Una carpeta cuyo
  nombre empieza con `_` no se sirve como páginas, lo que conviene a partes como esta.
- Cada atributo de la etiqueta es un `q:param` del componente, evaluado en la
  página: `title="Open tickets: {open}"` ve el `open` de la página. Un parámetro
  obligatorio que falta es un error.
- Lo que está entre `<Card>` y `</Card>` se dibuja en el ámbito de la página y va
  donde el componente tiene `<q:slot />`.
- El componente usa las fuentes de datos y los servicios de la página y ve los
  mismos `session`, `application` y `request`.
- Un componente que no se encuentra, o que falla, es un error de la página — nunca
  una sección que desaparece en silencio.

## Errores {#errors}

Un componente que no puede hacer lo que dice se detiene con un error que dice por qué.

### Un parámetro que falta {#a-missing-parameter}

```xml
<q:component name="Ticket" xmlns:q="https://quantum.lang/ns">
  <q:param name="id" type="integer" required="true" />
  <q:return value="Ticket {id}" />
</q:component>
```

**Error:** `Required parameter 'id' is missing`

### Una variable que no existe {#a-variable-that-does-not-exist}

```xml
<q:component name="ErrorExample" xmlns:q="https://quantum.lang/ns">
  <q:return value="{undefined_variable}" />
</q:component>
```

**Error:** `variable 'undefined_variable' is not defined`

## Buenas prácticas {#best-practices}

### 1. Una sola responsabilidad {#_1-single-responsibility}

Cada componente debe tener un propósito claro:

```xml
<!-- Good: Focused component -->
<q:component name="UserEmail" xmlns:q="https://quantum.lang/ns">
  <q:param name="email" type="email" required="true" />
  <q:return value="{email}" />
</q:component>
```

### 2. Usa nombres descriptivos {#_2-use-descriptive-names}

Prefiere `<q:component name="ProductPriceFormatter">` a
`<q:component name="PF">`: el nombre es lo que lee una página que lo usa.

### 3. Documenta los parámetros {#_3-document-parameters}

```xml
<!--
  Formats a price with a currency code.

  @param amount - The price amount (required)
  @param currency - Currency code (default: USD)
-->
<q:component name="PriceFormatter" xmlns:q="https://quantum.lang/ns">
  <q:param name="amount" type="decimal" required="true" />
  <q:param name="currency" type="string" default="USD" />
  <q:return value="{currency} {round(amount, 2)}" />
</q:component>
```

Con `amount` = `19.999` devuelve `"USD 20.0"`.

### 4. Valida la entrada {#_4-validate-input}

```xml
<q:component name="SafeComponent" xmlns:q="https://quantum.lang/ns">
  <q:param name="count" type="integer" required="true" />

  <q:if condition="count < 1">
    <q:return value="Error: count must be at least 1" />
  </q:if>

  <q:return value="{count} item(s)" />
</q:component>
```

Con `count` = `3` devuelve `"3 item(s)"`; con `-1`,
`"Error: count must be at least 1"`; con `abc`, el error
`Parameter 'count' must be an integer, got 'abc'`.

## Próximos pasos {#next-steps}

- [Manejo de estado](/es/guide/state-management) - Manejo avanzado de variables
- [Funciones](/guide/functions) - Crear lógica reutilizable
- [Bucles](/guide/loops) - Patrones de iteración
- [Condicionales](/guide/conditionals) - Flujo de control
