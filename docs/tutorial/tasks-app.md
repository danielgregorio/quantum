# Build the tasks app

This tutorial builds a complete app from an empty folder: a task list with
validated forms, finish and delete buttons, a filter, a sortable table you
edit in place, an edit page with the history of every change, and a test
suite. It is the English twin of
[`projects/tarefas`](https://github.com/danielgregorio/quantum/tree/main/projects/tarefas),
one of the apps Quantum's own CI runs, and it ends with the same code.

You write no JavaScript and no Python. Every step is a complete, working app,
and the code on this page is run by Quantum's test suite exactly as shown
(`tests/docs/test_tutorial_tasks_app.py`): what you read is what runs.

## 1. Install and start the project

You need Python 3.12 or newer.

```bash
pip install quantum-framework
mkdir tasks && cd tasks
```

An app is a folder with a `quantum.config.yaml`. This one says where the pages
and the database migrations live, and declares a SQLite database named `db`.

Save as `quantum.config.yaml`:

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

The table comes from a migration: plain SQL files in `migrations/`, applied in
order. The `CHECK` constraint matters later: Quantum reads it and refuses a
priority outside the list, in the edit form and in the table editor, without
you writing that rule again.

Save as `migrations/V001_tasks.sql`:

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

Create the database (it lands in `data/tasks.db`):

```bash
quantum migrate up
```

### The first page

A file in `components/` is a page: `components/index.q` answers `/`. Two
queries read the database, and the `ui:*` tags lay out the result: a side
panel with the counts, and the list, one row per task.

Save as `components/index.q`:

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

Open http://127.0.0.1:8080: three tasks and their counts. On a narrow screen
the panel stacks above the list ([UI](/guide/ui)).

## 2. Create tasks, with validation

A form sends its fields to a `q:action`. The action's `q:param`s are its
rules: `title` is required and between 3 and 200 characters, `priority` is one
of three values. A value that breaks a rule never reaches the SQL: the page
comes back with the message on the field and what was typed
([Actions and forms](/guide/actions)).

After the insert, `q:redirect` sends the browser back to the list with a flash
message, shown once by the `q:if condition="flash"` block. The form draws its
fields from the action it submits to: `ui:input bind="title"` becomes a
required text field with `minlength="3"`, taken from the rule.

Save as `components/index.q`:

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

Try an empty title, then a single letter: the form says what is wrong, next to
the field.

## 3. Finish and delete

Two more actions, each called by a button in the row. `with="id={tasks.id}"`
sends the row's id, and `type="integer"` on the `q:param` refuses anything
that is not a number before the `UPDATE` or the `DELETE` runs.

Save as `components/index.q`:

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

## 4. Filter the list

The page reads `?show=` from the address with `q:set` and gives it to the
query as a parameter, never pasted into the SQL. The side panel gets three
links, the `toggle` action keeps the current filter when it redirects, and an
empty list says so.

Save as `components/index.q`:

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

`http://127.0.0.1:8080/?show=done` now lists only the finished task.

## 5. A table that sorts and edits itself

A second page, `components/sheet.q`, answers `/sheet`. The query is `sortable`
and paginated, and `ui:table` with `edit="tasks"` turns every cell into a small
form that saves one column of one row. You write no action: the table's schema
is the rule, so a priority outside the `CHECK` list is refused, and the cell
says why ([UI](/guide/ui)).

Save as `components/sheet.q`:

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

Link it from the side panel:

Save as `components/index.q`:

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

## 6. An edit page with history

Turn on the change history for the database: every write an action makes is
recorded, with who made it and what changed.

Save as `quantum.config.yaml`:

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

The edit page is `components/task/[id].q`: the `[id]` in the file name answers
`/task/1`, `/task/2`… and gives the page an `id` variable.

Its action names a table and columns instead of declaring `q:param`s, so the
rules come from the schema (`title` is `NOT NULL`, `priority` is in the `CHECK`
list). `ui:form`, with no fields of its own, draws one field per column filled
with the task's values, and `ui:history` lists every change made to this task.

Save as `components/task/[id].q`:

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

And an *Edit* link in each row:

Save as `components/index.q`:

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

That is the whole app: 151 lines of `.q`, 13 of SQL, 0 of JavaScript.

## 7. Test it

A Quantum app is tested in its own language ([Testing an App](/guide/testing)).
Each `q:test` starts from a fresh database built by your migrations, visits
pages, submits actions, and checks the redirect, the flash, the error on a
field, the rows in the table and the history.

Save as `tests/tasks.test.q`:

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

Tests can also live next to the page they test:

Save as `components/sheet.test.q`:

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

Run them:

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

`quantum test` exits with `1` when a test fails, so it runs as is in CI.

## 8. The same app, elsewhere

The `ui:*` pages are not only HTML:

```bash
quantum console    # the same pages in the terminal
quantum desktop    # in a desktop window (pip install "quantum-framework[desktop]")
```

## Where to go next

- [Actions and forms](/guide/actions): every rule a `q:param` accepts
- [Queries](/guide/query): parameters, pagination and history
- [UI](/guide/ui): the `ui:*` tags
- [Testing an App](/guide/testing): every `test:` step
