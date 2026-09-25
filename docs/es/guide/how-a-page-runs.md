---
source: guide/how-a-page-runs.md
source_hash: ac6cc77dd1e5
---

# Cómo se ejecuta una página

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/how-a-page-runs).
:::

Una página `.q` tiene dos tipos de partes: las **sentencias** (`q:set`, `q:query`,
`q:invoke`, `q:action`…), que hacen cosas, y el **marcado** (HTML, elementos
`ui:*`, `{expressions}`), que muestra cosas. Conocer el orden en que se ejecutan
explica cada regla que al principio parece sorprendente — y los mensajes de
error de esas reglas enlazan aquí.

## Un GET, en orden {#a-get-in-order}

1. La **ruta** elige el componente: `components/index.q` es `/`,
   `components/loja/[id].q` es `/loja/41`.
2. `require_auth` / `require_role` deciden si se abre o no.
3. Se ejecutan las **guardas**: un `q:if` de nivel superior cuya rama tiene un `q:redirect`.
4. Se ejecutan las **sentencias** de la página, de arriba abajo.
5. Se renderiza el **marcado** con las variables que dejaron las sentencias:
   las `{expressions}`, los `q:loop` y `q:if` dentro del marcado, los elementos
   `ui:*` y los componentes llamados desde él.

```xml
<q:component name="InOrder">
  <q:set name="items" type="array" value='["a", "b", "c"]' />
  <q:set name="total" value="{len(items)}" type="number" />
  <p>Total: {total}</p>
  <q:loop type="array" items="{items}" var="i">
    <p>Item {i}</p>
  </q:loop>
</q:component>
```

**Shows:** `Total: 3` · `Item a` · `Item c`

El marcado solo **renderiza**. Nunca ejecuta una sentencia — así que una
sentencia puesta dentro de él nunca se ejecutaría, y Quantum la rechaza en lugar
de ignorarla:

```xml
<q:component name="Wrong">
  <div>
    <q:set name="x" value="1" />
  </div>
</q:component>
```

**Error:** `never runs (PARSE-2): statements run before the page is rendered`

Mueve el `q:set` por encima del marcado. Por la misma razón, un `q:set` dentro de
un `q:loop` del marcado cuyo valor leen las filas es un error: el bucle se
ejecuta para cada elemento antes de que se dibuje cualquier fila, así que cada
fila mostraría el último valor. Calcúlalo en la expresión: `{item.price * item.qty}`.

Los `q:function` de una página están disponibles en toda la página, y en sus
acciones, dondequiera que estén escritos:

```xml
<q:set name="doubled" value="{double_it(21)}" type="number" />
<q:function name="double_it">
  <q:param name="n" type="number" />
  <q:return value="{n * 2}" />
</q:function>
<q:return value="{doubled}" />
```

**Output:** `42`

## Un POST: la acción, y después una redirección {#a-post-the-action-then-a-redirect}

Un formulario envía a la página un campo `action` que nombra uno de sus
`q:action`. Los pasos 1–3 se ejecutan como en un GET; después se ejecuta **solo
esa acción** — no las sentencias de la página. Valida sus `q:param`, hace su
trabajo y termina en un `q:redirect`: el navegador entonces pide la página con
un GET, que se ejecuta como arriba.

Como las sentencias de la página no se ejecutan en una acción, una variable que
define la página no existe ahí:

```xml
<q:component name="Order">
  <q:set name="total" value="42" type="number" />

  <q:action name="pay" method="POST">
    <!-- {total} does not exist here: the page's q:set did not run. -->
    <q:redirect url="/order" flash="Paid {total}." />
  </q:action>

  <p>Total: {total}</p>
</q:component>
```

La página muestra `Total: 42`; enviar `pay` es un error, y su mensaje dice
exactamente esto:

```text
q:action 'pay' failed: {total} could not be evaluated: variable 'total' is not defined (in scope: form). A q:action does not run the page's statements (ACT-9): query or compute what it needs inside the action.
```

La acción consulta o calcula por sí misma lo que necesita.

Las guardas son la excepción: se ejecutan antes de la página **y** antes de cada
una de sus acciones, así que una guarda que redirige también detiene la acción.
Por eso, además, una guarda no puede leer una variable que define la página — en
la acción no existiría, y la guarda dejaría pasar el envío. Las guardas leen los
ámbitos (`session.x`) directamente; `require_auth` y `require_role` resuelven el
caso común por ti.

Una acción que no termina en `q:redirect` responde con la página misma (sus
sentencias se ejecutan después de la acción, como en un GET). La respuesta es un
200 a un POST, y recargarla vuelve a enviar el formulario — termina las acciones
con `q:redirect`.

## Cuánto vive cada cosa {#how-long-things-live}

| Qué | Vive | Lo ve |
|---|---|---|
| una variable de la página (`q:set name="x"`) | una solicitud | esa solicitud |
| `flash` | la página siguiente, una vez | ese visitante |
| `session.x` | entre solicitudes, en la cookie de sesión firmada | un visitante |
| `application.x` | mientras el proceso del servidor se ejecuta | todos los visitantes de ese proceso |

Cada solicitud se ejecuta en su propio entorno de ejecución, así que dos
solicitudes nunca ven las variables de la otra. `application.x` es memoria del
proceso del servidor: desaparece después de un reinicio, y con
`gunicorn --workers 4` cada worker tiene la suya. Guarda en la base de datos todo
lo que deba durar o compartirse.
