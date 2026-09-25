---
source: tutorial/tasks-app.md
source_hash: 0b96f8323cd6
---

# Construye la aplicación de tareas

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/tutorial/tasks-app).
:::

Este tutorial construye una aplicación completa a partir de una carpeta vacía:
una lista de tareas con formularios validados, botones para terminar y
eliminar, un filtro, una tabla ordenable que editas en el lugar, una página de
edición con el historial de cada cambio, y un conjunto de pruebas. Es el
gemelo en inglés de
[`projects/tarefas`](https://github.com/danielgregorio/quantum/tree/main/projects/tarefas),
una de las aplicaciones que ejecuta el propio CI de Quantum, y termina con el
mismo código. El código de esta página está en inglés, como en el original.

No escribes JavaScript ni Python. Cada paso es una aplicación completa que
funciona, y el conjunto de pruebas de Quantum ejecuta el código de esta página
exactamente como se muestra (`tests/docs/test_tutorial_tasks_app.py`): lo que
lees es lo que se ejecuta.

## 1. Instala e inicia el proyecto

Necesitas Python 3.12 o más reciente.

```bash
pip install quantum-framework
mkdir tasks && cd tasks
```

Una aplicación es una carpeta con un `quantum.config.yaml`. Este dice dónde
viven las páginas y las migraciones de la base de datos, y declara una base
de datos SQLite llamada `db`.

Guarda como `quantum.config.yaml`:

```yaml
server:
  port: 8080
  host: 127.0.0.1

paths:
  components: ./components
  migrations: ./migrations

datasources:
  db:
    driver: sqlite
    database: ./data/tasks.db
```

La tabla viene de una migración: archivos SQL simples en `migrations/`,
aplicados en orden. La restricción `CHECK` importa más adelante: Quantum la
lee y rechaza una prioridad fuera de la lista, en el formulario de edición y
en el editor de la tabla, sin que escribas esa regla otra vez.

Guarda como `migrations/V001_tasks.sql`:

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    done INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

INSERT INTO tasks (title, priority) VALUES
    ('Read the Quantum guide', 'high'),
    ('Write the first page', 'medium');
INSERT INTO tasks (title, priority, done) VALUES
    ('Install Quantum', 'low', 1);
```

Crea la base de datos (queda en `data/tasks.db`):

```bash
quantum migrate up
```

### La primera página

Un archivo en `components/` es una página: `components/index.q` responde a
`/`. Dos consultas leen la base de datos, y las etiquetas `ui:*` organizan el
resultado: un panel lateral con los conteos, y la lista, una fila por tarea.

Guarda como `components/index.q`:

```xml
<q:component name="Tasks">
  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
          </ui:hbox>
        </q:loop>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

```bash
quantum start
```

Abre http://127.0.0.1:8080: tres tareas y sus conteos. En una pantalla
angosta el panel se apila encima de la lista ([UI](/guide/ui)).

## 2. Crea tareas, con validación

Un formulario envía sus campos a una `q:action`. Los `q:param` de la acción son
sus reglas: `title` es obligatorio y tiene entre 3 y 200 caracteres,
`priority` es uno de tres valores. Un valor que rompe una regla nunca llega al
SQL: la página vuelve con el mensaje en el campo y lo que se escribió
([Actions and forms](/guide/actions)).

Después de la inserción, `q:redirect` envía el navegador de vuelta a la lista
con un mensaje flash, que el bloque `q:if condition="flash"` muestra una sola
vez. El formulario dibuja sus campos a partir de la acción a la que envía:
`ui:input bind="title"` se convierte en un campo de texto obligatorio con
`minlength="3"`, tomado de la regla.

Guarda como `components/index.q`:

```xml
<q:component name="Tasks">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title, priority) VALUES (:title, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Created: {title}" />
  </q:action>

  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:if condition="flash">
          <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="create">
          <ui:hbox gap="sm">
            <ui:input bind="title" placeholder="What needs to be done?" required="true" grow="true" />
            <ui:select bind="priority" options="medium,high,low" />
            <ui:button variant="primary">Create</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
          </ui:hbox>
        </q:loop>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

Prueba un título vacío, y luego una sola letra: el formulario dice qué está
mal, junto al campo.

## 3. Terminar y eliminar

Dos acciones más, cada una llamada por un botón en la fila.
`with="id={tasks.id}"` envía el id de la fila, y `type="integer"` en el
`q:param` rechaza cualquier cosa que no sea un número antes de que se ejecute
el `UPDATE` o el `DELETE`.

Guarda como `components/index.q`:

```xml
<q:component name="Tasks">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title, priority) VALUES (:title, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Created: {title}" />
  </q:action>

  <q:action name="toggle" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="toggled" datasource="db">
      UPDATE tasks SET done = 1 - done WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" />
  </q:action>

  <q:action name="delete" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="removed" datasource="db">
      DELETE FROM tasks WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Task deleted." />
  </q:action>

  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:if condition="flash">
          <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="create">
          <ui:hbox gap="sm">
            <ui:input bind="title" placeholder="What needs to be done?" required="true" grow="true" />
            <ui:select bind="priority" options="medium,high,low" />
            <ui:button variant="primary">Create</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
            <ui:button on-click="toggle" with="id={tasks.id}">{'Reopen' if tasks.done else 'Finish'}</ui:button>
            <ui:button on-click="delete" with="id={tasks.id}" variant="danger">Delete</ui:button>
          </ui:hbox>
        </q:loop>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

## 4. Filtra la lista

La página lee `?show=` de la dirección con `q:set` y se lo da a la consulta
como parámetro, nunca pegado en el SQL. El panel lateral recibe tres enlaces,
la acción `toggle` conserva el filtro actual cuando redirige, y una lista
vacía lo dice.

Guarda como `components/index.q`:

```xml
<q:component name="Tasks">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title, priority) VALUES (:title, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Created: {title}" />
  </q:action>

  <q:action name="toggle" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:param name="show" default="all" enum="all,open,done" />
    <q:query name="toggled" datasource="db">
      UPDATE tasks SET done = 1 - done WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/?show={show}" />
  </q:action>

  <q:action name="delete" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="removed" datasource="db">
      DELETE FROM tasks WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Task deleted." />
  </q:action>

  <q:set name="show" value="{query.show}" default="all" />

  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    WHERE :show = 'all' OR (:show = 'open' AND done = 0) OR (:show = 'done' AND done = 1)
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
    <q:param name="show" value="{show}" type="string" />
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
        <ui:panel title="Show">
          <ui:vbox gap="sm">
            <ui:link to="/?show=all">All</ui:link>
            <ui:link to="/?show=open">Open</ui:link>
            <ui:link to="/?show=done">Done</ui:link>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:if condition="flash">
          <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="create">
          <ui:hbox gap="sm">
            <ui:input bind="title" placeholder="What needs to be done?" required="true" grow="true" />
            <ui:select bind="priority" options="medium,high,low" />
            <ui:button variant="primary">Create</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
            <ui:button on-click="toggle" with="id={tasks.id}, show={show}">{'Reopen' if tasks.done else 'Finish'}</ui:button>
            <ui:button on-click="delete" with="id={tasks.id}" variant="danger">Delete</ui:button>
          </ui:hbox>
        </q:loop>

        <q:if condition="tasks_result.recordCount == 0">
          <ui:text>No tasks here.</ui:text>
        </q:if>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

`http://127.0.0.1:8080/?show=done` ahora lista solo la tarea terminada.

## 5. Una tabla que se ordena y se edita sola

Una segunda página, `components/sheet.q`, responde a `/sheet`. La consulta es
`sortable` y paginada, y `ui:table` con `edit="tasks"` convierte cada celda en
un pequeño formulario que guarda una columna de una fila. No escribes ninguna
acción: el esquema de la tabla es la regla, así que una prioridad fuera de la
lista del `CHECK` se rechaza, y la celda dice por qué ([UI](/guide/ui)).

Guarda como `components/sheet.q`:

```xml
<q:component name="Sheet">
  <q:query name="tasks" datasource="db" sortable="true" paginate="true" page_size="20">
    SELECT id, title, priority, done FROM tasks ORDER BY id
  </q:query>

  <ui:window title="Task sheet">
    <ui:vbox gap="md" padding="lg">
      <ui:hbox gap="md">
        <ui:link to="/">Back</ui:link>
        <ui:text>Click a header to sort; edit a cell and confirm with ✓ (or Enter).</ui:text>
      </ui:hbox>
      <q:if condition="flash">
        <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
      </q:if>
      <ui:table source="{tasks}" sort="true" edit="tasks" datasource="db">
        <ui:column key="title" label="Title" />
        <ui:column key="priority" label="Priority" />
        <ui:column key="done" label="Done" />
      </ui:table>
      <ui:pager for="tasks" />
    </ui:vbox>
  </ui:window>
</q:component>
```

Enlázala desde el panel lateral:

Guarda como `components/index.q`:

```xml
<q:component name="Tasks">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title, priority) VALUES (:title, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Created: {title}" />
  </q:action>

  <q:action name="toggle" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:param name="show" default="all" enum="all,open,done" />
    <q:query name="toggled" datasource="db">
      UPDATE tasks SET done = 1 - done WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/?show={show}" />
  </q:action>

  <q:action name="delete" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="removed" datasource="db">
      DELETE FROM tasks WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Task deleted." />
  </q:action>

  <q:set name="show" value="{query.show}" default="all" />

  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    WHERE :show = 'all' OR (:show = 'open' AND done = 0) OR (:show = 'done' AND done = 1)
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
    <q:param name="show" value="{show}" type="string" />
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
        <ui:panel title="Show">
          <ui:vbox gap="sm">
            <ui:link to="/?show=all">All</ui:link>
            <ui:link to="/?show=open">Open</ui:link>
            <ui:link to="/?show=done">Done</ui:link>
            <ui:link to="/sheet">Sheet</ui:link>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:if condition="flash">
          <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="create">
          <ui:hbox gap="sm">
            <ui:input bind="title" placeholder="What needs to be done?" required="true" grow="true" />
            <ui:select bind="priority" options="medium,high,low" />
            <ui:button variant="primary">Create</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
            <ui:button on-click="toggle" with="id={tasks.id}, show={show}">{'Reopen' if tasks.done else 'Finish'}</ui:button>
            <ui:button on-click="delete" with="id={tasks.id}" variant="danger">Delete</ui:button>
          </ui:hbox>
        </q:loop>

        <q:if condition="tasks_result.recordCount == 0">
          <ui:text>No tasks here.</ui:text>
        </q:if>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

## 6. Una página de edición con historial

Activa el historial de cambios de la base de datos: cada escritura que hace
una acción queda registrada, con quién la hizo y qué cambió.

Guarda como `quantum.config.yaml`:

```yaml
server:
  port: 8080
  host: 127.0.0.1

paths:
  components: ./components
  migrations: ./migrations

datasources:
  db:
    driver: sqlite
    database: ./data/tasks.db
    history: true          # every change made by an action is recorded
```

La página de edición es `components/task/[id].q`: el `[id]` en el nombre del
archivo responde a `/task/1`, `/task/2`… y le da a la página una variable `id`.

Su acción nombra una tabla y columnas en lugar de declarar `q:param`, así que
las reglas vienen del esquema (`title` es `NOT NULL`, `priority` está en la
lista del `CHECK`). `ui:form`, sin campos propios, dibuja un campo por
columna con los valores de la tarea, y `ui:history` lista cada cambio hecho a
esta tarea.

Guarda como `components/task/[id].q`:

```xml
<q:component name="EditTask">
  <q:action name="save" method="POST" table="tasks" datasource="db" columns="title,priority">
    <q:query name="saved" datasource="db">
      UPDATE tasks SET title = :title, priority = :priority WHERE id = :id
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Saved: {title}" />
  </q:action>

  <q:query name="task" datasource="db">
    SELECT id, title, priority FROM tasks WHERE id = :id
    <q:param name="id" value="{id}" type="integer" />
  </q:query>

  <ui:window title="Edit task">
    <ui:vbox gap="md" padding="lg">
      <ui:link to="/">Back</ui:link>
      <q:if condition="task_result.recordCount == 0">
        <ui:alert variant="danger">That task does not exist.</ui:alert>
      </q:if>
      <q:else>
        <ui:form on-submit="save" values="{task}" submit="Save" />
        <ui:section title="History">
          <ui:history table="tasks" key="{id}" datasource="db" />
        </ui:section>
      </q:else>
    </ui:vbox>
  </ui:window>
</q:component>
```

Y un enlace *Edit* en cada fila:

Guarda como `components/index.q`:

```xml
<q:component name="Tasks">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title, priority) VALUES (:title, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Created: {title}" />
  </q:action>

  <q:action name="toggle" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:param name="show" default="all" enum="all,open,done" />
    <q:query name="toggled" datasource="db">
      UPDATE tasks SET done = 1 - done WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/?show={show}" />
  </q:action>

  <q:action name="delete" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="removed" datasource="db">
      DELETE FROM tasks WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Task deleted." />
  </q:action>

  <q:set name="show" value="{query.show}" default="all" />

  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    WHERE :show = 'all' OR (:show = 'open' AND done = 0) OR (:show = 'done' AND done = 1)
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
    <q:param name="show" value="{show}" type="string" />
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
        <ui:panel title="Show">
          <ui:vbox gap="sm">
            <ui:link to="/?show=all">All</ui:link>
            <ui:link to="/?show=open">Open</ui:link>
            <ui:link to="/?show=done">Done</ui:link>
            <ui:link to="/sheet">Sheet</ui:link>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:if condition="flash">
          <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="create">
          <ui:hbox gap="sm">
            <ui:input bind="title" placeholder="What needs to be done?" required="true" grow="true" />
            <ui:select bind="priority" options="medium,high,low" />
            <ui:button variant="primary">Create</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
            <ui:link to="/task/{tasks.id}">Edit</ui:link>
            <ui:button on-click="toggle" with="id={tasks.id}, show={show}">{'Reopen' if tasks.done else 'Finish'}</ui:button>
            <ui:button on-click="delete" with="id={tasks.id}" variant="danger">Delete</ui:button>
          </ui:hbox>
        </q:loop>

        <q:if condition="tasks_result.recordCount == 0">
          <ui:text>No tasks here.</ui:text>
        </q:if>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

Esa es toda la aplicación: 151 líneas de `.q`, 13 de SQL, 0 de JavaScript.

## 7. Pruébala

Una aplicación de Quantum se prueba en su propio lenguaje
([Testing an App](/guide/testing)). Cada `q:test` empieza con una base de
datos nueva construida por tus migraciones, visita páginas, envía acciones, y
verifica la redirección, el mensaje flash, el error en un campo, las filas de
la tabla y el historial.

Guarda como `tests/tasks.test.q`:

```xml
<q:test name="the list shows the summary and the tasks" page="/">
  <test:visit />
  <test:expect text="Total: 3" />
  <test:expect text="Open: 2" />
  <test:expect text="Done: 1" />
  <test:expect text="Write the first page" />
</q:test>

<q:test name="create a task" page="/">
  <test:submit action="create" title="Test the UI" priority="high" />
  <test:expect status="302" redirect="/" flash="Created: Test the UI" />
  <test:expect table="tasks" count="1" where="title = 'Test the UI' AND priority = 'high'" />
  <test:expect text="Total: 4" />
</q:test>

<q:test name="a title that is too short is refused on its field" page="/">
  <test:submit action="create" title="x" />
  <test:expect redirect="/" />
  <test:expect error="title" />
  <test:expect text="at least 3 characters" />
  <test:expect table="tasks" count="3" />
</q:test>

<q:test name="a priority outside the list is refused" page="/">
  <test:submit action="create" title="With a wrong priority" priority="urgent" />
  <test:expect error="priority" />
  <test:expect table="tasks" count="0" where="title = 'With a wrong priority'" />
</q:test>

<q:test name="finish a task and show the open ones" page="/">
  <test:given table="tasks" title="Buy bread" />
  <test:expect table="tasks" count="1" where="title = 'Buy bread' AND done = 0" />
  <test:submit action="toggle" id="4" show="open" />
  <test:expect redirect="/?show=open" />
  <test:expect table="tasks" count="1" where="id = 4 AND done = 1" />
  <test:expect no-text="Buy bread" />
  <test:expect text="Read the Quantum guide" />
</q:test>

<q:test name="delete a task" page="/">
  <test:submit action="delete" id="2" />
  <test:expect redirect="/" flash="Task deleted." />
  <test:expect table="tasks" count="0" where="id = 2" />
  <test:expect text="Total: 2" />
</q:test>

<q:test name="the page runs a fixed number of queries" page="/">
  <test:given table="tasks" />
  <test:given table="tasks" />
  <test:visit />
  <test:expect queries="2" />
  <test:expect var="show" value="all" />
</q:test>

<q:test name="the filter comes from the query string" page="/">
  <test:visit show="done" />
  <test:expect var="show" value="done" />
  <test:expect text="Install Quantum" />
  <test:expect no-text="Read the Quantum guide" />
</q:test>
```

Las pruebas también pueden vivir junto a la página que prueban:

Guarda como `components/sheet.test.q`:

```xml
<q:test name="a cell edit is saved and recorded in the history" page="/sheet">
  <test:submit action="__edit" __table="tasks" __key="1" __column="priority" value="low" />
  <test:expect redirect="/sheet" flash="Saved: priority" />
  <test:expect table="tasks" count="1" where="id = 1 AND priority = 'low'" />
  <test:expect history="tasks" count="1" op="update" where="id = 1" />
</q:test>

<q:test name="a cell refuses a value the schema does not allow" page="/sheet">
  <test:submit action="__edit" __table="tasks" __key="1" __column="priority" value="urgent" />
  <test:expect table="tasks" count="1" where="id = 1 AND priority = 'high'" />
  <test:expect history="tasks" count="0" />
</q:test>

<q:test name="the edit form validates with the schema's rules" page="/task/1">
  <test:submit action="save" title="" priority="urgent" />
  <test:expect error="title" message="Required" />
  <test:expect error="priority" message="Must be one of: low, medium, high" />
  <test:expect table="tasks" count="1" where="id = 1 AND title = 'Read the Quantum guide'" />
</q:test>

<q:test name="an edit is saved and shows in the task's history" page="/task/1">
  <test:as user="ana" />
  <test:submit action="save" title="Read the whole guide" priority="low" />
  <test:expect redirect="/" flash="Saved: Read the whole guide" />
  <test:expect table="tasks" count="1" where="id = 1 AND title = 'Read the whole guide' AND priority = 'low'" />
  <test:expect history="tasks" action="save" op="update" user="ana" where="id = 1" count="1" />
  <test:visit path="/task/1" />
  <test:expect text="title: Read the Quantum guide → Read the whole guide" />
</q:test>

<q:test name="a task that does not exist" page="/task/99">
  <test:visit />
  <test:expect text="That task does not exist" />
</q:test>
```

Ejecútalas:

```bash
quantum test
```

<!-- report: pass -->
```text
components/sheet.test.q
  PASS  a cell edit is saved and recorded in the history  (304 ms)
  PASS  a cell refuses a value the schema does not allow  (32 ms)
  PASS  the edit form validates with the schema's rules  (35 ms)
  PASS  an edit is saved and shows in the task's history  (55 ms)
  PASS  a task that does not exist  (33 ms)
tests/tasks.test.q
  PASS  the list shows the summary and the tasks  (29 ms)
  PASS  create a task  (47 ms)
  PASS  a title that is too short is refused on its field  (34 ms)
  PASS  a priority outside the list is refused  (33 ms)
  PASS  finish a task and show the open ones  (39 ms)
  PASS  delete a task  (34 ms)
  PASS  the page runs a fixed number of queries  (33 ms)
  PASS  the filter comes from the query string  (26 ms)
13 passed, 0 failed
```

`quantum test` termina con `1` cuando una prueba falla, así que funciona tal
cual en CI.

## 8. La misma aplicación, en otros lugares

Las páginas `ui:*` no son solo HTML:

```bash
quantum console    # the same pages in the terminal
quantum desktop    # in a desktop window (pip install "quantum-framework[desktop]")
```

## Adónde ir después

- [Actions and forms](/guide/actions): cada regla que acepta un `q:param`
- [Queries](/guide/query): parámetros, paginación e historial
- [UI](/guide/ui): las etiquetas `ui:*`
- [Testing an App](/guide/testing): cada paso `test:`
