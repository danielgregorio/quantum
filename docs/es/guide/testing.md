---
source: guide/testing.md
source_hash: d3d9fb557d8b
---

# Probar una aplicación (`quantum test`)

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/testing).
:::

Una aplicación Quantum se prueba en su propio lenguaje. Un archivo `*.test.q`
contiene pruebas que visitan páginas, envían acciones y verifican lo que pasó —
la redirección, el mensaje flash, las filas en la base de datos, el error junto
a un campo — con las mismas palabras que la aplicación ya usa. `quantum test`
las ejecuta contra el servidor real, cada prueba con una base de datos nueva, y
termina con `1` cuando una falla.

Sin Python, sin navegador, sin selectores CSS.

## Una primera prueba {#a-first-test}

Una pequeña aplicación de notas. Guárdalo como `quantum.config.yaml`:

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/notes.db
    history: true
```

Guárdalo como `migrations/V001_notes.sql`:

```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'idea' CHECK (kind IN ('idea', 'todo')),
    created_at TEXT DEFAULT (datetime('now'))
);
INSERT INTO notes (title) VALUES ('Read the guide');
```

Guárdalo como `components/index.q`:

```xml
<q:component name="Notes">
  <q:action name="add" method="POST">
    <q:param name="title" required="true" minlength="3" />
    <q:param name="kind" default="idea" enum="idea,todo" />
    <q:query name="added" datasource="db">
      INSERT INTO notes (title, kind) VALUES (:title, :kind)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="kind" value="{kind}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Added: {title}" />
  </q:action>

  <q:query name="notes" datasource="db">SELECT title, kind FROM notes ORDER BY id</q:query>

  <ui:window title="Notes">
    <ui:vbox gap="md" padding="lg">
      <q:if condition="flash"><ui:alert variant="success">{flash}</ui:alert></q:if>
      <ui:form on-submit="add">
        <ui:input bind="title" />
        <ui:button variant="primary">Add</ui:button>
      </ui:form>
      <ui:text>{notes_result.recordCount} notes</ui:text>
      <q:loop query="notes"><ui:text>{notes.title} ({notes.kind})</ui:text></q:loop>
    </ui:vbox>
  </ui:window>
</q:component>
```

Y sus pruebas. Guárdalas como `tests/notes.test.q`:

```xml
<q:test name="the list" page="/">
  <test:visit />
  <test:expect text="1 notes" />
  <test:expect text="Read the guide (idea)" />
</q:test>

<q:test name="add a note" page="/">
  <test:submit action="add" title="Buy bread" kind="todo" />
  <test:expect redirect="/" flash="Added: Buy bread" />
  <test:expect table="notes" count="1" where="title = 'Buy bread' AND kind = 'todo'" />
  <test:expect text="2 notes" />
  <test:expect history="notes" action="add" op="insert" count="1" />
</q:test>

<q:test name="a title needs three letters" page="/">
  <test:submit action="add" title="x" />
  <test:expect error="title" message="Must be at least 3 characters" />
  <test:expect table="notes" count="1" />
</q:test>
```

Ejecútalas desde la carpeta de la aplicación:

```bash
quantum test
```

<!-- report: pass -->
```text
tests/notes.test.q
  PASS  the list  (31 ms)
  PASS  add a note  (38 ms)
  PASS  a title needs three letters  (27 ms)
3 passed, 0 failed
```

Cada prueba empieza desde el mismo lugar: una base de datos nueva construida
por `migrations/`, que tiene solo `Read the guide`. Lo que escribió `add a note`
ya no está cuando empieza `a title needs three letters`.

## Cuando una prueba falla {#when-a-test-fails}

Cambia el mensaje flash de `add a note` a `flash="Added: Buy milk"` y ejecuta
de nuevo. El informe nombra el paso que falló, con su línea, y lo que hizo la
aplicación en su lugar:

<!-- report: fail -->
```text
tests/notes.test.q
  PASS  the list  (29 ms)
  FAIL  add a note  (35 ms)
        tests/notes.test.q:9  <test:expect redirect="/" flash="Added: Buy milk"/>
        expected flash "Added: Buy milk", got "Added: Buy bread"
  PASS  a title needs three letters  (26 ms)
2 passed, 1 failed
```

`quantum test` termina con `1`, así que un job de CI falla con él.

Cuando la propia página falla — una expresión que no se evalúa, un SQL que la
base de datos rechaza — el paso que hizo la solicitud falla con el error y
también con la línea de la **página**:

```text
        tests/bill.test.q:2  <test:visit/>
        the server answered 500: ComponentExecutionError: …
        page: components/bill.q:4
```

Un paso cuya solicitud responde con un estado de error (`400` o más) falla, salvo
que el paso siguiente diga que lo espera — `<test:expect status="404"/>` después
de visitar una página que no debería existir.

## Dónde viven las pruebas {#where-tests-live}

`quantum test` busca `*.test.q` en la carpeta que recibe (por defecto, la actual):

- **junto a una página** — `components/admin/index.test.q` prueba
  `components/admin/index.q`. Un `.test.q` nunca se sirve como página ni crea
  una ruta; `quantum check` lo lee como un archivo de prueba.
- **en `tests/`** — conjuntos sobre toda la aplicación, como `tests/signin.test.q`.

Un archivo de prueba pertenece a la aplicación del `quantum.config.yaml` más
cercano por encima de él. `quantum test projects/blog tests/one.test.q` ejecuta
varios lugares a la vez.

## Los pasos {#the-steps}

Un `q:test` tiene un `name` y la `page` en la que empieza (`/` por defecto). Sus
pasos se ejecutan en orden.

| Paso | Qué hace |
|---|---|
| `<test:given table="notes" title="Draft"/>` | Inserta una fila, verificada contra el esquema |
| `<test:as user="Ana" role="admin" id="1"/>` | Inicia sesión sin contraseña |
| `<test:visit/>` | Abre la página — o `path="/other"` — con los demás atributos como query string |
| `<test:submit action="add" title="…"/>` | Envía la acción con los demás atributos como campos |
| `<test:expect …/>` | Verifica lo que pasó |

### `test:given` — las filas que la prueba necesita {#test-given-—-rows-the-test-needs}

```xml
<test:given table="notes" title="Draft" kind="todo" />
```

La fila entra en la base de datos de la prueba a través de las reglas del
esquema: una tabla o una columna que no existe, un valor fuera de una lista
`CHECK (… IN …)`, un texto en una columna `INTEGER`, una clave foránea que no
apunta a nada — cada uno hace fallar el paso con un mensaje, en lugar de
insertar algo que la aplicación nunca podría haber escrito. Las columnas
obligatorias que el paso deja afuera se completan: el primer valor permitido de
un `CHECK … IN`, la primera fila de la tabla a la que apunta una clave foránea,
un número, o `"<column> <n>"` para el texto. Con varias fuentes de datos,
`datasource="…"` dice cuál.

### `test:as` — quién usa la aplicación {#test-as-—-who-is-using-the-app}

```xml
<test:as user="Ana" role="admin" id="1" plan="pro" />
```

Define la sesión como lo hace un inicio de sesión: `session.userName` es `Ana`,
`session.userRole` es `admin`, `session.userId` es `1`, y las páginas con
`require_auth` y `require_role` dejan entrar a la prueba. Cualquier otro
atributo es una variable de sesión (`session.plan` arriba). Para probar el
propio formulario de inicio de sesión, envíalo como lo haría una persona.

### `test:visit` y `test:submit` — lo que hace un navegador {#test-visit-and-test-submit-—-what-a-browser-does}

`test:submit` envía datos a la página en la que está la prueba, como lo haría el
formulario de esa página: a través de las guardas de la página, las reglas de
los `q:param` de la acción, el historial, la redirección y el mensaje flash.
Los dos pasos siguen las redirecciones como un navegador, y después la prueba
queda en la página en la que terminó — así que el siguiente `test:submit` envía
ahí. Después de una redirección a la página de inicio de sesión, por ejemplo, la
prueba está en `/login`.

Una página con un solo `q:action` lo ejecuta sea cual sea el nombre enviado; si
la página ejecutó otra acción distinta de la que nombra el paso, el paso falla —
de lo contrario la prueba pasaría probando la acción equivocada.

## Qué verifica `test:expect` {#what-test-expect-checks}

Cada atributo es una aserción; varias en un mismo `test:expect` deben cumplirse todas.

| Aserción | Se cumple cuando |
|---|---|
| `status="302"` | La solicitud respondió este estado (antes de seguir cualquier redirección) |
| `redirect="/?added=1"` | Redirigió aquí: ruta, query y `#fragment` |
| `flash="Added: Buy bread"` | Definió exactamente este mensaje flash |
| `text="2 notes"` | La página en la que está la prueba muestra este texto (sin etiquetas, con los espacios unificados) |
| `no-text="Draft"` | … no lo muestra |
| `error="title"` | El envío se rechazó con un error en este campo; `message="…"` verifica el mensaje |
| `var="filter" value="open"` | La página (o la acción) terminó con este valor en la variable, comparado como texto |
| `queries="2"`, `queries="at most 3"` | La solicitud ejecutó esta cantidad de consultas a la base de datos |
| `table="notes"` | La base de datos tiene filas en esta tabla — `where="…"` filtra, `count="N"` verifica cuántas |
| `history="notes"` | `history: true` registró cambios en esta tabla — con `action`, `op` (`insert`, `update`, `delete`), `user`, `where`, `count` |

`queries` detecta la página que ejecuta una consulta por fila: una lista de 3
filas y una de 300 deberían decir las dos `queries="2"`.

## Nada fuera del vocabulario {#nothing-outside-the-vocabulary}

Los pasos y las aserciones de arriba son todo el lenguaje. Una etiqueta que no
es una de ellas, una aserción que no existe, un `count` sin `table` ni `history`
que contar — cada uno es un error de análisis con su línea, nunca un paso que en
silencio no hace nada:

```text
tests/notes.test.q: <test:click> is not a test step. The steps are: test:given, test:as, test:visit, test:submit, test:expect
  at line 4: <test:click text="Add" />
```

## En CI {#in-ci}

`quantum test` termina con `0` cuando todas las pruebas pasaron y con `1` en caso
contrario — también cuando un archivo no pasa el análisis, una ruta no existe o
no se encuentra ninguna prueba. Ejecútalo en la carpeta de la aplicación como un
paso de CI:

```bash
quantum test
```

## Límites por ahora {#limits-for-now}

- Solo fuentes de datos `sqlite`: cada prueba construye su propia base de datos SQLite.
- Con varias fuentes de datos y una carpeta `migrations/`, las migraciones
  tendrían que decir qué fuente de datos construyen; la prueba falla diciéndolo.
- Hacer clic por la pantalla (`test:click`, `test:fill`), ejecutar una prueba en
  la web y en la consola, pruebas derivadas de las reglas de las acciones,
  respuestas de IA grabadas y la cobertura están planeados, no construidos.

Ver también: [Acciones y formularios](/es/guide/actions), [Consultas a la base de datos](/es/guide/query),
[Autenticación](/es/guide/authentication).
