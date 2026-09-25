# One App, Many Screens

A page written with the UI Engine's elements — `ui:window`, `ui:panel`,
`ui:table`, `ui:form`… — is a web page, a terminal app and a desktop window at
the same time. There is one runtime: the page's queries, actions and rules run
once, on the server, and each renderer only **draws** the result.

| Open it with | You get |
|---|---|
| `quantum start` | the page in a browser |
| `quantum console` | the same page in the terminal (Textual) |
| `quantum desktop` | the same page in a native window (pywebview) |

Nothing of the page's logic is translated to another language, so a rule you
write once — a validation, a login, a query — behaves the same on every screen.

## A first screen

Save as `components/index.q` in a project (a folder with a `quantum.config.yaml`)
and run `quantum start`:

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

Now run `quantum console` in the same folder: the same panel, text and button,
in the terminal. Pressing **Add** there posts the same `q:action`, with a
session of its own, just as a browser does.

`quantum desktop` opens it in a window. It needs one extra package:

```bash
pip install "quantum-framework[desktop]"
quantum desktop            # the home page
quantum desktop /reports   # another page, --width/--height to size the window
```

The window's title is the first `ui:window`'s `title` — the same title the
browser tab and the console show.

## Events are actions

A button or a form does not call code in the browser: it posts to a
`q:action` of the page. The action validates, does its work and redirects,
like any form in Quantum (see [Actions & Forms](/guide/actions)).

- `<ui:button on-click="save">` posts to `<q:action name="save">`.
- `with="id={t.id}, filter={filter}"` adds fields to that post — how a button
  in a row says which row it is.
- `<ui:form on-submit="create">` posts its fields: `<ui:input bind="title">` is
  the field `title`.

An event that names no action of the page is an error that lists the page's
actions — never a button that silently does nothing.

## Tables and lists from data

`source=` takes a list — a `q:query` or an array — and draws one row per item.
The row's variable is named by `as=` (default `row` for a table, `item` for a
list), exactly like a `q:loop`:

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

- `<ui:column key="name">` shows that field of the row, escaped.
- A column with content draws it once per row — buttons, links, badges.
- A `source` that is not a list, or a `key` the row does not have, is an error
  that says so (with the row's fields) — never an empty table.

With a database, the source is a query. The examples from here on use this
database (CI builds it from this block):

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

## Pages of a long list

A query with `paginate="true"` returns one page; the page is the URL's
`?page=`. `<ui:pager>` draws the links:

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

The 12 posts make two pages: the first shows `Post 12` down to `Post 3`.

- Previous, the numbers around the current page (first and last always, `…`
  where it skips), next. At the ends previous/next are not links; with one page
  nothing is drawn.
- The links keep the other URL parameters: on `/?tag=news&page=2` they go to
  `/?tag=news&page=3`.
- `?page=abc` or `?page=-1` is page 1, never an error.
- `window="1"` shows fewer numbers; `param="p"` (with `page="{query.p}"` on the
  query) when a page has two paginated lists.

`projects/blog` paginates its home page this way.

## Search as you type

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

- Each pause in typing (`delay`, 300 ms by default) asks for the same page with
  `?q=…` and swaps only `#results` — the page's own queries do the search.
  The URL follows, so the result can be shared or reloaded.
- It is a plain GET form underneath: without JavaScript, Enter searches.
- Other URL parameters are kept; `page` is dropped, so a new search starts on
  page 1 of a `<ui:pager>`.
- In the console, the same: after a pause the page is asked again, and the
  field keeps the focus.
- A target that is not on the page is an error — never a field that swaps
  nothing.

`projects/blog` searches this way (`components/search.q`).

## A table that sorts and edits itself

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

Each cell is a small form: the titles are in its fields, and each priority is a
select with the `CHECK` list.

- `sort="true"`: each header is a link that orders the query **in SQL**
  (`sortable="true"` on the query) by `?sort=` and `?dir=` — so it works with a
  `<ui:pager>`. A column in the URL that the query does not return is ignored.
- `edit="tasks"`: each shown column of that table becomes a small form in its
  cell (Enter or ✓ saves). You write no action: the server accepts only the
  table and columns this page declares, runs the page's guards, validates the
  value with the column's rules from the schema (NOT NULL, `CHECK … IN`, type)
  and updates one row by its primary key. A refused value comes back in its cell
  with the error. `edit="false"` on a column keeps it read-only.
- The rows must include the primary key (`SELECT id, …`).
- What it does shows in [`/_dev`](/tools/dev-panel) like any action.

`projects/tarefas` has one at `/planilha`.

## Forms that open with values

Fields take their initial value from the page, so the same form creates and
edits:

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

`default=` gives the first visit its value (the session has no `name` yet).

- `value=` on `ui:input`, `ui:select` and `ui:radio`; `checked=` on
  `ui:checkbox` and `ui:switch` (`true`, or an expression).
- A checked box is sent as `on`; an unchecked one is **not sent** — the way
  browsers do it. That is why the action says `<q:param name="notices" default="off">`.

## Forms that know the action's rules

A form takes each field's rules from the `q:param`s of the action it posts to,
so you write them once:

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

- `name` gets `required minlength="3"`, `age` gets `type="number" min="18"`,
  and the select gets the `enum` as its options — look at the page source.
  The browser checks them before posting.
- The server still validates every field. When it refuses, the page comes
  back with the values that were sent and **each error next to its field**
  (in the console too). A password is never sent back.
- An attribute you write on a field wins; `<ui:form rules="off">` turns this off.
- A `pattern` becomes the browser's only when it is anchored (`^…$`): the
  browser matches the whole value, the server searches.

## Forms from a table

When an action writes one table, it can take its rules from the table itself —
the schema you already wrote in the migration (the `tasks` table above):

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

- `title` is `NOT NULL` → required; `priority` has `CHECK … IN` → a select
  with those options, and the server refuses anything else.
- The form has no fields of its own, so it draws one per column — labels from
  the names (`author_id` → "Author"), a checkbox for `BOOLEAN`, a select for a
  foreign key filled with the referenced table's rows. `values="{task}"`
  opens it with a row's values: an edit form in one line.
- `columns=` picks and orders the columns (default: all but the primary key).
  A `q:param` you write in the action wins over the column's.
- A nullable column left blank reaches the action as `None`, and a foreign key
  must name a row that exists.
- The schema is read from the database, and read again when the database file
  changes — add a column in a migration and the form has it. `quantum check`
  reports a table or column that does not exist.

`projects/tarefas` edits a task this way (`components/tarefa/[id].q`).

## Layout that adapts

Layout is declared, with three breakpoints: `sm` (640 px), `md` (768 px) and
`lg` (1024 px). In the console they are counted in columns (80, 96 and 128).

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

- `stack-below="md"` puts an `ui:hbox`'s children one under the other below
  768 px, and their fixed widths stop applying.
- `grow="true"` takes the rest of the row.
- `ui:grid columns="1 sm:2 lg:3"`: one column, two from `sm`, three from `lg`.
- `hide-below` / `hide-above` hide an element on one side of a breakpoint.

## The core set

These elements are drawn with the same meaning by the browser, the console and
the desktop window, and one test script — see, fill, check, choose, click — runs
unchanged in a real browser and in the console:

| Kind | Elements |
|---|---|
| Layout | `window`, `hbox`, `vbox`, `grid`, `panel`, `section`, `scrollbox`, `spacer`, `rule`, `header`, `footer`, `card` (`card-header`, `card-body`, `card-footer`), `tabpanel` / `tab` |
| Content | `text`, `badge`, `alert`, `link`, `image`, `progress` |
| Data | `table` / `column`, `list` / `item` |
| Forms | `form`, `formitem`, `input`, `checkbox`, `switch`, `radio`, `select` / `option`, `button` |
| Data features | `pager` (pages of a query), `history` (a row's changes), `stream` (an AI answer as it is written) |

Every other `ui:*` element — charts, modals, toasts, date pickers, menus… —
works in the browser only and is **Experimental** (see the
[UI tags reference](/reference/ui)). In the console, such an element shows
`[ui:chart is not drawn in the console]` instead of something else in its
place.

Text directly inside a container is content: `<ui:card-header>Summary</ui:card-header>`.
Plain HTML can sit between `ui:*` elements; the console shows its text.

## Standalone builds

`<q:application type="ui">` with `quantum run app.q --target html` (a single
HTML file) or `--target textual` (a single Python file) draws **layout only**:
there is no runtime in those files, so a `q:set`, `q:function` or any other
command in them is an error that points here. Write the screen as a page to
give it logic.

`--target mobile` (React Native) is **Laboratory**: it translates the logic
to JavaScript on its own, with no stability promise. Phones are not part of
1.0. The old `--target desktop` was removed; `quantum desktop` replaces it.
