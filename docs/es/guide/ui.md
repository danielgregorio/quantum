---
source: guide/ui.md
source_hash: 238a9346dd15
---

# Una aplicación, varias pantallas

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/ui).
:::

Una página escrita con los elementos del UI Engine — `ui:window`, `ui:panel`,
`ui:table`, `ui:form`… — es a la vez una página web, una aplicación de terminal
y una ventana de escritorio. Hay un solo entorno de ejecución: las consultas,
las acciones y las reglas de la página se ejecutan una vez, en el servidor, y
cada renderizador solo **dibuja** el resultado.

| Ábrela con | Obtienes |
|---|---|
| `quantum start` | la página en un navegador |
| `quantum console` | la misma página en la terminal (Textual) |
| `quantum desktop` | la misma página en una ventana nativa (pywebview) |

Nada de la lógica de la página se traduce a otro lenguaje, así que una regla que
escribes una vez — una validación, un inicio de sesión, una consulta — se
comporta igual en todas las pantallas.

## Una primera pantalla {#a-first-screen}

Guárdala como `components/index.q` en un proyecto (una carpeta con un
`quantum.config.yaml`) y ejecuta `quantum start`:

```xml
<q:component name="Counter">
  <q:action name="add" method="POST">
    <q:set name="current" value="{session.clicks}" default="0" type="number" />
    <q:set name="session.clicks" value="{current + 1}" />
    <q:redirect url="/" />
  </q:action>

  <q:set name="clicks" value="{session.clicks}" default="0" />

  <ui:window title="Counter">
    <ui:panel title="Clicks">
      <ui:text>You clicked {clicks} times.</ui:text>
      <ui:button on-click="add" variant="primary">Add</ui:button>
    </ui:panel>
  </ui:window>
</q:component>
```

**Shows:** `Clicks` · `You clicked 0 times.` · `Add`

Ahora ejecuta `quantum console` en la misma carpeta: el mismo panel, el mismo
texto y el mismo botón, en la terminal. Presionar **Add** ahí envía el mismo
`q:action`, con una sesión propia, igual que un navegador.

`quantum desktop` la abre en una ventana. Necesita un paquete adicional:

```bash
pip install "quantum-framework[desktop]"
quantum desktop            # the home page
quantum desktop /reports   # another page, --width/--height to size the window
```

El título de la ventana es el `title` del primer `ui:window` — el mismo título
que muestran la pestaña del navegador y la consola.

## Los eventos son acciones {#events-are-actions}

Un botón o un formulario no llama código en el navegador: envía datos a un
`q:action` de la página. La acción valida, hace su trabajo y redirige, como
cualquier formulario en Quantum (ver [Acciones y formularios](/es/guide/actions)).

- `<ui:button on-click="save">` envía a `<q:action name="save">`.
- `with="id={t.id}, filter={filter}"` agrega campos a ese envío — así un botón
  en una fila dice qué fila es.
- `<ui:form on-submit="create">` envía sus campos: `<ui:input bind="title">` es
  el campo `title`.

Un evento que no nombra ninguna acción de la página es un error que lista las
acciones de la página — nunca un botón que no hace nada en silencio.

## Tablas y listas a partir de datos {#tables-and-lists-from-data}

`source=` recibe una lista — un `q:query` o un array — y dibuja una fila por
elemento. La variable de la fila se nombra con `as=` (por defecto `row` para una
tabla, `item` para una lista), exactamente como un `q:loop`:

```xml
<q:component name="People">
  <q:action name="delete" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:redirect url="/" flash="Deleted person {id}" />
  </q:action>

  <q:set name="people" type="array"
         value='[{"id": 1, "name": "Ana", "age": 30}, {"id": 2, "name": "Bia", "age": 25}]' />

  <ui:window title="People">
    <ui:table source="{people}" as="p">
      <ui:column key="name" label="Name" />
      <ui:column key="age" label="Age" align="right" />
      <ui:column label="">
        <ui:button on-click="delete" with="id={p.id}" variant="danger">Delete {p.name}</ui:button>
      </ui:column>
    </ui:table>

    <ui:list source="{people}" as="p">
      <ui:item><ui:text>{p.name} is {p.age} years old</ui:text></ui:item>
    </ui:list>
  </ui:window>
</q:component>
```

**Shows:** `Name` · `Age` · `Ana` · `30` · `Delete Bia` · `Bia is 25 years old`

- `<ui:column key="name">` muestra ese campo de la fila, escapado.
- Una columna con contenido lo dibuja una vez por fila — botones, enlaces, insignias.
- Un `source` que no es una lista, o una `key` que la fila no tiene, es un error
  que lo dice (con los campos de la fila) — nunca una tabla vacía.

Con una base de datos, el origen es una consulta. Los ejemplos de aquí en
adelante usan esta base de datos (CI la construye a partir de este bloque):

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    done INTEGER NOT NULL DEFAULT 0
);
INSERT INTO tasks (title, priority) VALUES ('Write the guide', 'high'), ('Review it', 'low');

CREATE TABLE posts (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL);
WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 12)
INSERT INTO posts (title) SELECT 'Post ' || i FROM n;
```

```xml
<q:component name="Tasks">
  <q:query name="tasks" datasource="db">
    SELECT id, title FROM tasks ORDER BY id
  </q:query>
  <ui:window title="Tasks">
    <ui:table source="{tasks}">
      <ui:column key="title" label="Task" />
    </ui:table>
  </ui:window>
</q:component>
```

**Shows:** `Task` · `Write the guide` · `Review it`

## Páginas de una lista larga {#pages-of-a-long-list}

Una consulta con `paginate="true"` devuelve una página; la página es el
`?page=` de la URL. `<ui:pager>` dibuja los enlaces:

```xml
<q:component name="Blog">
  <q:query name="posts" datasource="db" paginate="true" page_size="10">
    SELECT title FROM posts ORDER BY id DESC
  </q:query>
  <ui:window title="Blog">
    <ui:list source="{posts}" as="p"><ui:item><ui:text>{p.title}</ui:text></ui:item></ui:list>
    <ui:pager for="posts" />
  </ui:window>
</q:component>
```

**Shows:** `Post 12` · `Post 3`

Las 12 publicaciones forman dos páginas: la primera muestra de `Post 12` a `Post 3`.

- Anterior, los números alrededor de la página actual (el primero y el último
  siempre, `…` donde se salta), siguiente. En los extremos, anterior/siguiente
  no son enlaces; con una sola página no se dibuja nada.
- Los enlaces conservan los demás parámetros de la URL: en `/?tag=news&page=2`
  van a `/?tag=news&page=3`.
- `?page=abc` o `?page=-1` es la página 1, nunca un error.
- `window="1"` muestra menos números; `param="p"` (con `page="{query.p}"` en la
  consulta) cuando una página tiene dos listas paginadas.

`projects/blog` pagina su página de inicio de esta forma.

## Buscar mientras escribes {#search-as-you-type}

```xml
<q:component name="Search">
  <q:set name="term" value="{query.q}" default="" />
  <q:query name="found" datasource="db">
    SELECT title FROM posts WHERE title LIKE :p
    <q:param name="p" value="%{term}%" type="string" />
  </q:query>
  <ui:window title="Search">
    <ui:input bind="q" search="results" placeholder="Search" />
    <ui:vbox id="results">
      <ui:list source="{found}" as="a"><ui:item><ui:text>{a.title}</ui:text></ui:item></ui:list>
    </ui:vbox>
  </ui:window>
</q:component>
```

**Shows:** `Post 1` · `Post 12`

- Cada pausa al escribir (`delay`, 300 ms por defecto) pide la misma página con
  `?q=…` y reemplaza solo `#results` — la búsqueda la hacen las propias
  consultas de la página. La URL lo acompaña, así que el resultado se puede
  compartir o recargar.
- Por debajo es un formulario GET común: sin JavaScript, Enter busca.
- Los demás parámetros de la URL se conservan; `page` se descarta, así que una
  búsqueda nueva empieza en la página 1 de un `<ui:pager>`.
- En la consola, lo mismo: después de una pausa se vuelve a pedir la página, y
  el campo conserva el foco.
- Un destino que no está en la página es un error — nunca un campo que no
  reemplaza nada.

`projects/blog` busca de esta forma (`components/search.q`).

## Una tabla que se ordena y se edita sola {#a-table-that-sorts-and-edits-itself}

```xml
<q:component name="Sheet">
  <q:query name="tasks" datasource="db" sortable="true">
    SELECT id, title, priority FROM tasks
  </q:query>
  <ui:window title="Tasks">
    <ui:table source="{tasks}" sort="true" edit="tasks" datasource="db">
      <ui:column key="title" label="Title" />
      <ui:column key="priority" label="Priority" />
    </ui:table>
  </ui:window>
</q:component>
```

**Shows:** `Title` · `Priority` · `low` · `medium` · `high`

Cada celda es un pequeño formulario: los títulos están en sus campos, y cada
prioridad es un select con la lista del `CHECK`.

- `sort="true"`: cada encabezado es un enlace que ordena la consulta **en SQL**
  (`sortable="true"` en la consulta) según `?sort=` y `?dir=` — así que funciona
  con un `<ui:pager>`. Una columna en la URL que la consulta no devuelve se ignora.
- `edit="tasks"`: cada columna mostrada de esa tabla se convierte en un pequeño
  formulario en su celda (Enter o ✓ guarda). No escribes ninguna acción: el
  servidor acepta solo la tabla y las columnas que declara esta página, ejecuta
  las guardas de la página, valida el valor con las reglas de la columna tomadas
  del esquema (NOT NULL, `CHECK … IN`, tipo) y actualiza una fila por su clave
  primaria. Un valor rechazado vuelve a su celda con el error. `edit="false"` en
  una columna la deja de solo lectura.
- Las filas deben incluir la clave primaria (`SELECT id, …`).
- Lo que hace se muestra en [`/_dev`](/tools/dev-panel) como cualquier acción.

`projects/tarefas` tiene una en `/planilha`.

## Formularios que se abren con valores {#forms-that-open-with-values}

Los campos toman su valor inicial de la página, así que el mismo formulario crea
y edita:

```xml
<q:component name="Profile">
  <q:action name="save" method="POST">
    <q:param name="name" required="true" minlength="2" />
    <q:param name="notices" default="off" />
    <q:param name="plan" default="free" />
    <q:set name="session.name" value="{name}" />
    <q:redirect url="/" flash="Saved: {name}, notices {notices}, plan {plan}" />
  </q:action>

  <q:set name="name" value="{session.name}" default="Ana" />

  <ui:window title="Profile">
    <q:if condition="flash">
      <ui:alert variant="success">{flash}</ui:alert>
    </q:if>
    <ui:form on-submit="save">
      <ui:formitem label="Name">
        <ui:input bind="name" value="{name}" />
      </ui:formitem>
      <ui:checkbox bind="notices" label="Receive notices" checked="true" />
      <ui:radio bind="plan" options="free,pro" value="pro" />
      <ui:select bind="color" options="blue,green" value="green" />
      <ui:button variant="primary">Save</ui:button>
    </ui:form>
  </ui:window>
</q:component>
```

**Shows:** `Name` · `Receive notices` · `free` · `pro` · `Save`

`default=` le da su valor a la primera visita (la sesión todavía no tiene `name`).

- `value=` en `ui:input`, `ui:select` y `ui:radio`; `checked=` en
  `ui:checkbox` y `ui:switch` (`true`, o una expresión).
- Una casilla marcada se envía como `on`; una sin marcar **no se envía** — así lo
  hacen los navegadores. Por eso la acción dice `<q:param name="notices" default="off">`.

## Formularios que conocen las reglas de la acción {#forms-that-know-the-action-s-rules}

Un formulario toma las reglas de cada campo de los `q:param` de la acción a la
que envía, así que las escribes una sola vez:

```xml
<q:component name="SignUp">
  <q:action name="signUp" method="POST">
    <q:param name="name" required="true" minlength="3" />
    <q:param name="age" type="integer" min="18" />
    <q:param name="plan" enum="free,pro" default="free" />
    <q:redirect url="/" flash="Signed up: {name}" />
  </q:action>

  <ui:window title="Sign up">
    <ui:form on-submit="signUp">
      <ui:formitem label="Name"><ui:input bind="name" /></ui:formitem>
      <ui:formitem label="Age"><ui:input bind="age" /></ui:formitem>
      <ui:select bind="plan" />
      <ui:button>Sign up</ui:button>
    </ui:form>
  </ui:window>
</q:component>
```

**Shows:** `Name` · `Age` · `free` · `pro` · `Sign up`

- `name` recibe `required minlength="3"`, `age` recibe `type="number" min="18"`,
  y el select recibe el `enum` como sus opciones — mira el código fuente de la
  página. El navegador los verifica antes de enviar.
- El servidor igual valida cada campo. Cuando rechaza, la página vuelve con los
  valores que se enviaron y **cada error junto a su campo** (también en la
  consola). Una contraseña nunca se devuelve.
- Un atributo que escribes en un campo tiene prioridad; `<ui:form rules="off">`
  desactiva esto.
- Un `pattern` pasa a ser del navegador solo cuando está anclado (`^…$`): el
  navegador compara el valor completo, el servidor busca.

## Formularios a partir de una tabla {#forms-from-a-table}

Cuando una acción escribe en una tabla, puede tomar sus reglas de la propia
tabla — el esquema que ya escribiste en la migración (la tabla `tasks` de arriba):

```xml
<q:component name="EditTask">
  <q:action name="save" method="POST" table="tasks" datasource="db" columns="title,priority">
    <q:param name="id" type="integer" required="true" />
    <q:query name="updated" datasource="db">
      UPDATE tasks SET title = :title, priority = :priority WHERE id = :id
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Saved: {title}" />
  </q:action>

  <q:query name="task" datasource="db">SELECT id, title, priority FROM tasks WHERE id = 1</q:query>

  <ui:window title="Edit task">
    <ui:form on-submit="save" values="{task}" submit="Save" />
  </ui:window>
</q:component>
```

**Shows:** `Title` · `Priority` · `low` · `high` · `Save`

- `title` es `NOT NULL` → obligatorio; `priority` tiene `CHECK … IN` → un select
  con esas opciones, y el servidor rechaza cualquier otra cosa.
- El formulario no tiene campos propios, así que dibuja uno por columna —
  etiquetas tomadas de los nombres (`author_id` → "Author"), una casilla para
  `BOOLEAN`, un select para una clave foránea completado con las filas de la
  tabla referenciada. `values="{task}"` lo abre con los valores de una fila: un
  formulario de edición en una línea.
- `columns=` elige y ordena las columnas (por defecto: todas menos la clave
  primaria). Un `q:param` que escribes en la acción tiene prioridad sobre el de
  la columna.
- Una columna que acepta nulos y se deja en blanco llega a la acción como
  `None`, y una clave foránea debe nombrar una fila que existe.
- El esquema se lee de la base de datos, y se vuelve a leer cuando cambia el
  archivo de la base de datos — agrega una columna en una migración y el
  formulario la tiene. `quantum check` informa una tabla o columna que no existe.

`projects/tarefas` edita una tarea de esta forma (`components/tarefa/[id].q`).

## Diseño que se adapta {#layout-that-adapts}

El diseño se declara, con tres puntos de quiebre: `sm` (640 px), `md` (768 px) y
`lg` (1024 px). En la consola se cuentan en columnas (80, 96 y 128).

```xml
<q:component name="Dashboard">
  <ui:window title="Dashboard">
    <ui:hbox stack-below="md" gap="md">
      <ui:vbox width="260"><ui:text>Menu</ui:text></ui:vbox>
      <ui:vbox grow="true"><ui:text>Content</ui:text></ui:vbox>
    </ui:hbox>
    <ui:grid columns="1 sm:2 lg:3">
      <ui:text>One</ui:text><ui:text>Two</ui:text><ui:text>Three</ui:text>
    </ui:grid>
    <ui:text hide-below="md">Only on wide screens</ui:text>
  </ui:window>
</q:component>
```

**Shows:** `Menu` · `Content` · `One` · `Three`

- `stack-below="md"` pone los hijos de un `ui:hbox` uno debajo del otro por
  debajo de 768 px, y sus anchos fijos dejan de aplicarse.
- `grow="true"` ocupa el resto de la fila.
- `ui:grid columns="1 sm:2 lg:3"`: una columna, dos desde `sm`, tres desde `lg`.
- `hide-below` / `hide-above` ocultan un elemento a un lado de un punto de quiebre.

## El conjunto del Núcleo {#the-core-set}

Estos elementos los dibujan con el mismo significado el navegador, la consola y
la ventana de escritorio, y un mismo script de prueba — ver, completar, marcar,
elegir, hacer clic — se ejecuta sin cambios en un navegador real y en la consola:

| Tipo | Elementos |
|---|---|
| Diseño | `window`, `hbox`, `vbox`, `grid`, `panel`, `section`, `scrollbox`, `spacer`, `rule`, `header`, `footer`, `card` (`card-header`, `card-body`, `card-footer`), `tabpanel` / `tab` |
| Contenido | `text`, `badge`, `alert`, `link`, `image`, `progress` |
| Datos | `table` / `column`, `list` / `item` |
| Formularios | `form`, `formitem`, `input`, `checkbox`, `switch`, `radio`, `select` / `option`, `button` |
| Funciones de datos | `pager` (páginas de una consulta), `history` (los cambios de una fila), `stream` (una respuesta de IA a medida que se escribe) |

Cualquier otro elemento `ui:*` — gráficos, modales, toasts, selectores de fecha,
menús… — funciona solo en el navegador y es **Experimental** (ver la
[referencia de las etiquetas UI](/reference/ui)). En la consola, un elemento así
muestra `[ui:chart is not drawn in the console]` en lugar de otra cosa en su lugar.

El texto directamente dentro de un contenedor es contenido:
`<ui:card-header>Summary</ui:card-header>`. Puede haber HTML común entre los
elementos `ui:*`; la consola muestra su texto.

## Builds independientes {#standalone-builds}

`<q:application type="ui">` con `quantum run app.q --target html` (un único
archivo HTML) o `--target textual` (un único archivo Python) dibuja **solo el
diseño**: no hay entorno de ejecución en esos archivos, así que un `q:set`, un
`q:function` o cualquier otro comando en ellos es un error que apunta aquí.
Escribe la pantalla como una página para darle lógica.

`--target mobile` (React Native) es **Laboratorio**: traduce la lógica a
JavaScript por su cuenta, sin promesa de estabilidad. Los teléfonos no forman
parte de la 1.0. El antiguo `--target desktop` se eliminó; `quantum desktop` lo reemplaza.
