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
| `quantum pixel` | the same page on the Hive's screen, the console of a Quantum OS machine (keyboard only) |
| `quantum run <app> --on tui` | the same page on a text screen drawn by Godot: a terminal's look, with the mouse, colours and motion |

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

### One parameter

The whole application, in the version you ask for — give it the application's folder:

```bash
quantum run projects/kanban --on web        # the browser (quantum start)
quantum run projects/kanban --on desktop    # a window of its own (quantum desktop)
quantum run projects/kanban --on tui        # a text screen drawn by Godot (below)
quantum run projects/kanban --on terminal   # the terminal (quantum console)
```

`--page /board/1` opens on another page, `--port` sets the web's port. The repository's
Kanban runs one script — sign in, cards moved, a card another program adds through its API, the
AI's subtasks, issues imported, a viewer who changes nothing — in every version, in CI
(`tests/apps/test_kanban_everywhere.py`).

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
  with the error. `edit="false"` on a column keeps it read-only. Each cell is
  signed for the session it was shown to: a table inside a `q:if` that was
  false for this person, or a row their query left out, cannot be edited by a
  form made by hand.
- The rows must include the primary key (`SELECT id, …`).
- What it does shows in [`/_dev`](/tools/dev-panel) like any action.

`projects/tasks` has one at `/sheet`.

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

`projects/tasks` edits a task this way (`components/task/[id].q`).

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

## Motion

Three kinds of motion — `fade`, `slide`, `expand` — at two speeds — `fast` (150 ms) and `normal`
(250 ms, the default) — the same in the browser, the desktop and the terminal:

```xml
<q:component name="Board">
  <q:set name="moved" value="{query.moved}" default="2" type="number" />
  <q:set name="cards" type="array" value='[{"id": 1, "title": "Fonts"}, {"id": 2, "title": "Domain"}]' />
  <ui:window title="Board" transition="slide">
    <q:loop items="{cards}" var="card">
      <ui:card title="{card.title}" enter="{card.id == moved and 'slide' or ''}" />
    </q:loop>
    <ui:animate type="expand" speed="fast">
      <ui:text>Opens quickly</ui:text>
    </ui:animate>
  </ui:window>
</q:component>
```

**Shows:** `Fonts` · `Domain` · `Opens quickly`

- `transition` on `ui:window` (`fade` or `slide`): the page enters that way each time it is shown.
- `enter` on any element, an expression too: the element enters that way when its page is shown;
  `''` is no motion. `<ui:animate type="fade|slide|expand">` is the same around what it holds.
- A tab's content opens with `expand` when the user changes the tab.
- `speed="fast"` on any of them.

`ui.motion: off` in `quantum.config.yaml` turns every motion off; the browser also stops them for the
system's reduced-motion setting. Each renderer records the motions it ran (`window.quantumMotions` in the
browser), so a test can check that every version moved the same way. `ui:animate`'s other types
(`bounce`, `scale`…) are the browser's only; elsewhere the content shows without them.

## The core set

These elements are drawn with the same meaning by the browser, the console,
the desktop window, the Hive's screen and the TUI, and one test script — see,
fill, check, choose, click — runs unchanged in a real browser, in the console,
on the screen and in the TUI:

| Kind | Elements |
|---|---|
| Layout | `window`, `hbox`, `vbox`, `grid`, `panel`, `section`, `scrollbox`, `spacer`, `rule`, `header`, `footer`, `card` (`card-header`, `card-body`, `card-footer`), `tabpanel` / `tab` |
| Content | `text`, `badge`, `alert`, `link`, `image`, `progress` |
| Data | `table` / `column`, `list` / `item` |
| Forms | `form`, `formitem`, `input`, `checkbox`, `switch`, `radio`, `select` / `option`, `button` |
| Data features | `pager` (pages of a query), `history` (a row's changes), `stream` (an AI answer as it is written) |
| Beyond the layout | `breadcrumb` / `breadcrumb-item`, `menu`, `avatar`, `markdown`, `chart`, `tree`, `log`, `dividedbox`, `pagination`, `skeleton`, `loading`, `date-picker`, `animate` ([below](#beyond-the-layout)) |
| With a state of their own | `accordion`, `modal`, `tooltip`, `dropdown`, `toast` / `toast-container`, `carousel` / `slide`, `stepper` / `step`, `calendar` ([below](#beyond-the-layout)) |
| Not elements of a page | `validator` (a rule of its form), `theme` / `color` (the page's colours) |

That is every `ui:*` tag. A kind a renderer does not know — a newer server's —
shows `[ui:kind is not drawn in the console]` instead of something else in its
place.

A form's `ui:validator`s are checked by the server when it is sent, in every
renderer the same — the error comes back by its field, as the action's own
rules do:

```xml
<q:component name="Join">
  <q:action name="join" method="POST">
    <q:param name="code" required="true" />
    <q:param name="again" required="true" />
    <q:redirect url="/" flash="Joined with {code}" />
  </q:action>

  <ui:window title="Join">
    <ui:form on-submit="join">
      <ui:validator field="code" pattern="^[A-Z]{3}$" message="Three capital letters" />
      <ui:validator field="again" match="code" message="The codes differ" />
      <ui:input bind="code" />
      <ui:input bind="again" />
      <ui:button>Join</ui:button>
    </ui:form>
  </ui:window>
</q:component>
```

**Shows:** `Join`

A page's `ui:theme` gives its colours — `<ui:theme preset="dark"><ui:color
name="primary" value="#ff00aa" /></ui:theme>` — to the browser, the console
and the TUI; the Hive's screen keeps its palette. [`UI_PARITY.md`](https://github.com/danielgregorio/quantum/blob/main/UI_PARITY.md)
is the map of every tag against every renderer, and a check keeps it true.

Text directly inside a container is content: `<ui:card-header>Summary</ui:card-header>`.
Plain HTML can sit between `ui:*` elements; the console shows its text.

A `ui:tabpanel` opens on its first tab, or on the one its `open` names
(`open="{tab}"`, with `tab` read from the address): a page that comes back
after an action that redirects to `/?tab=Network` opens where the user was
([the Tabs recipe](/cookbook/screens/tabs)). A value that names no tab opens
the first; a literal that names none is a parse error that lists the tabs.

The flash shows where the page draws it, once: the console and the Hive's
screen give it a line of their own only on a page that does not show it.
`variant="{flashType == 'error' and 'danger' or 'success'}"` on its `ui:alert`
draws a refused action's message in red.

## Beyond the layout

A breadcrumb, a menu, an avatar, Markdown, a chart, a tree, a log: each means the
same in every renderer, because the server works out what it means — the
initials of a name, which crumb is the current page, the blocks of a Markdown
text, each bar's share, a tree's rows and the lines beside them — and every
renderer draws that. A terminal draws it in the form it can: a chart in bars of
characters, a skeleton in shaded lines.

```xml
<q:component name="Shelf">
  <q:action name="pick" method="POST">
    <q:param name="value" required="true" />
    <q:redirect url="/" flash="Picked: {value}" />
  </q:action>
  <q:action name="book" method="POST">
    <q:param name="day" type="date" required="true" />
    <q:redirect url="/" flash="Booked: {day}" />
  </q:action>

  <q:set name="sales" type="array" value='[{"label": "Mon", "value": 3}, {"label": "Tue", "value": 6}]' />
  <q:set name="folders" type="array" value='[{"label": "Docs", "children": [
           {"label": "Guide", "value": "guide"}]}]' />
  <q:set name="events" type="array" value='["started", "listening on 8080"]' />

  <ui:window title="Shelf">
    <ui:breadcrumb separator=">">
      <ui:breadcrumb-item label="Home" to="/" />
      <ui:breadcrumb-item label="Shelf" />
    </ui:breadcrumb>
    <ui:menu>
      <ui:option value="new" on-click="pick">New file</ui:option>
    </ui:menu>
    <ui:avatar name="Ana Lima" status="online" />
    <ui:markdown>
      ## Notes
      Some **bold** words and `code`.
    </ui:markdown>
    <ui:chart type="bar" title="Sales" source="{sales}" />
    <ui:chart type="pie" labels="Red,Blue" values="1,3" />
    <ui:tree source="{folders}" on-select="pick" />
    <ui:log max-lines="50" source="{events}" />
    <ui:pagination total="45" page-size="10" show-total="true" />
    <ui:form on-submit="book">
      <ui:date-picker bind="day" />
      <ui:button>Book</ui:button>
    </ui:form>
  </ui:window>
</q:component>
```

**Shows:** `Home` · `Shelf` · `New file` · `AL` · `Notes` · `Sales` · `Mon` · `Red` · `25%` · `Docs` · `Guide` · `listening on 8080` · `45 items`

- A **menu**'s option and a **tree**'s row with an action are links that post
  it, with their `value` as the field `value`; a tree's row with a `to` goes
  there.
- **Markdown** takes headings, paragraphs with **bold**, *italic*, `code` and
  links, lists, code, quotes and rules. Every text is escaped, and a link goes
  only to `http`, `https`, `mailto` or a path.
- A **chart** (`bar`, `line`, `pie`, `doughnut`) takes `labels` and `values`, or
  `source` rows with a `label` and a `value`; a value that is not a number is an
  error that names the chart.
- A **log** shows its text's lines, then its `source`'s, the last `max-lines` of
  them.
- A **pagination** is the pager's links over `total` items: the page is the
  URL's `bind` parameter (`page`), as for `ui:pager`, so `on-change` is an error
  in a page.
- A **date picker** is a date field of its form, YYYY-MM-DD, with the action's
  rules (UI-9).

Some keep a state of their own, in every renderer the same way: an
**accordion**'s sections are folds, the first open; a **modal** shows above the
page while `open` is true (`open="{query.welcome == '1'}"`) until it is closed;
a **toast** shows for its `duration`, while `show` is true; a **tooltip** says
its tip when its content is pointed at or has the focus; a **dropdown** is a
button that opens its options, each posting its action like a menu's; a
**carousel** shows one slide, a **stepper** one step, with controls to move.
Which slide or step is shown is the screen's, not the page's: `on-change`,
`on-complete` and `bind`, which a standalone build's script calls, are an
error in a page.

A **calendar** is a date field of its form shown as a month: the user moves
from month to month and picks a day, which the form sends under its `bind`
(YYYY-MM-DD). `min-date`, `max-date`, `disabled-dates` and `disabled-days`
(0 is Sunday) say the days that cannot be picked; `first-day-of-week` and
`show-week-numbers` how the weeks are laid out. A day the action refuses comes
back picked, with the error by the calendar:

```xml
<q:component name="Visit">
  <q:action name="book" method="POST">
    <q:param name="day" type="date" required="true" />
    <q:redirect url="/" flash="Booked: {day}" />
  </q:action>

  <ui:window title="Visit">
    <ui:form on-submit="book">
      <ui:validator field="day" server-expression="{day != '2026-12-25'}" message="Closed on the 25th" />
      <ui:calendar bind="day" value="2026-12-01" min-date="2026-12-01" disabled-days="0"
                   first-day-of-week="1" show-week-numbers="true" />
      <ui:button>Book</ui:button>
    </ui:form>
  </ui:window>
</q:component>
```

**Shows:** `Book`

`on-change`, `on-month-change` and a `mode` other than `single` call a
standalone build's script, and are an error in a page.

## In the TUI

`quantum run <app> --on tui` opens the pages on a text screen in a window of its own, drawn by
Godot: a grid of characters in one font, boxes with borders, a terminal's look — without a
terminal's limits. It uses the browser's colours (the same design tokens), takes the mouse (a click
acts, a hover marks, the wheel scrolls, and the scrolling glides), runs the motions of the page
(`transition=`, `enter=`, a tab that opens), draws the page's images and wide characters (CJK and
emoji take two cells), and a file field opens a dialog of its own and sends the file with its form.
The first time, the pinned Godot is fetched into your cache.

It is a renderer like the browser: the application's server runs on a local port, the TUI asks it
for each page's view tree and sends the same posts a browser sends, with the cookies the server set
— login, validation, flash and redirects are the web's. The keys are the Hive's screen's (below):
Tab between elements, Enter acts, Space marks, the arrows inside an element, F5 asks the page
again, and Ctrl+Q closes the window; the last line says the keys that apply.

A kind it does not know shows `[ui:kind is not drawn in the TUI]`. Headless, with
`--play`, it is driven one JSON request at a time — click at a cell, type, wait for a text — and
answers with what the screen shows: the parity script and the Kanban's script run in it in CI
(`quantum/runtime/ui_tui.py`, `TuiSession`), and its layout is checked against reference frames of
cells (`tests/tui/frames/`).

### A file to hand someone

`quantum package <app> --on tui --target linux|windows|macos` makes one file of the application
that runs where Quantum is not installed: the TUI as its program, and beside it the application's
server with a Python of its own. Any target is made on any system; the first time, Python's build
for that system, the libraries and Godot's export templates are fetched into your cache.

```bash
quantum package projects/kanban --target windows     # projects/kanban/dist/kanban-windows.zip
```

The person unpacks it and runs `kanban` (`kanban.exe`, or `Kanban.app` on a Mac with Apple
silicon). The TUI starts the server, shows the first page, and the server ends when the window
closes. What the application writes — its SQLite databases, uploads, logs — goes to a folder of
theirs (`~/.local/share/quantum/kanban` on Linux, `%LOCALAPPDATA%\Quantum\kanban` on Windows,
`~/Library/Application Support/Quantum/kanban` on a Mac), not into the package. Your databases
stay with you: the package leaves them out and its migrations make them when it starts, unless
`--with-data` carries them (copied to the person's folder the first time). The Kanban's is about
60 MB and shows its first page in under two seconds; CI makes it for the three systems, runs
the Kanban's whole script in the Linux one, and starts the Windows and macOS ones on those
systems.

With `--on desktop` the program is a window of its own instead, the pages as the browser shows
them (`quantum desktop`, on the system's web view): `Kanban.exe` on Windows, `Kanban.app` on a Mac.
Linux has no desktop package — its window would need Qt WebEngine, about 550 MB — and its package
is the TUI.

### In the browser

`--target web` puts the TUI in a browser tab instead: it is exported into the application's static
folder, and the application's own server serves it with its pages.

```bash
quantum package projects/kanban --target web     # projects/kanban/static/tui/
quantum run projects/kanban --on web             # http://127.0.0.1:8090/static/tui/index.html
```

`/static/tui/index.html` opens the first page, and `?page=/board/1` another. The TUI asks the
same server for the pages through the browser's own requests, so the browser keeps the session's
cookies and follows the redirects — a person signs in once, as in the web version — and a file
field opens the browser's file picker. It is the same TUI: the same cells, the same keys and mouse,
as many columns and rows as the window has room for. Nothing is carried but the TUI (about 44 MB,
most of it Godot's WebAssembly); `--out` puts it elsewhere. CI runs the parity scripts and the
Kanban's whole script in it, in Chromium.

### A client of a hosted application

When the application runs on a server of yours, `--server` makes its client: the program alone,
which asks that server for the pages instead of starting one — no application, no Python beside
the TUI.

```bash
quantum package projects/kanban --server https://kanban.example.com --target windows
quantum package projects/kanban --server https://kanban.example.com --on desktop --target macos
```

The person signs in to the hosted application as on the web, and what they do is in its database.
The TUI's client of the Kanban is about 26 MB; the desktop's carries its window's Python (the
window is pywebview's), but no server. An address that is not `https` is said when the package is
made: the session's cookie would cross the network unencrypted. CI runs the Kanban's whole script
in the Linux client against a hosted Kanban, and the Windows and macOS clients on those systems.


## On the Hive's screen

On a Quantum OS machine the console is the Hive's screen: a pixel-art scene
drawn by `hive-screen` ([the screen](/targets/screen)). `quantum pixel`,
run by any local user, brings a page over that scene, in the screen's own
font, and closes it with Esc — the scene is whole again, and the command
ends. The page's logic runs where it always runs: `quantum pixel` starts
the application's server in its process, as `quantum console` does, asks
each page for its view tree and sends what the user did back as the same
posts a browser sends; the screen only draws and reads the keyboard.

There is no mouse, and no key to learn beyond the console's own:

| Key | Does |
|---|---|
| Tab, Shift+Tab | the next, the previous element that reacts, in the page's order; the one with the focus shows in honey |
| arrows | inside the element: the cursor in a field, the option of a `radio` or `select`, the row and the button of a `table`, the tab of a `tabpanel`, the day of a `calendar` (a week with Up and Down); Up and Down go to the element before and after when what has the focus does not use them (a one-line field, a button, a box) |
| Enter | acts: a button, a link, a row's button; in a field, sends its form; in a `calendar`, picks the day, which its form sends |
| Space | marks: a `checkbox`, a `switch` |
| Esc | closes the page |
| Home, End | the first and the last element (in a field, the ends of its text) |
| Page Up, Page Down | scroll; a bar at the right edge says where in a long page the screen is; in a `calendar`, the month before and after |
| F5 | asks the page again |
| F1 | the Hive's offers in a menu over the page (Enter approves, Del dismisses, Esc shuts it); the status bar says how many wait |

The last line of the screen says the keys that apply to what has the
focus. A search field (`search="true"`) asks the page again after its
pause, as in the browser; a validation error puts the focus on the field
it is about (UI-9). It draws every `ui:*` tag — a chart in bars, a modal
that takes the keys until Esc — and a kind it does not know it says so, as
the console does.

The keyboard is read by the machine's layout: US, or a Brazilian ABNT2
(`XKBLAYOUT="br"` in `/etc/default/keyboard`), where `ç` is its own key
and the accents are dead keys composed with the vowel after them; the
screen's font has every Latin-1 letter. The page is a window over the Hive's
scene: a frame with a bevel and a shadow, a title bar with the Esc key
drawn on it, a status bar with the keys, as tall as the page needs. On a
machine with four cores the screen draws at its fine level and the window
has 100 columns by up to 29 rows instead of 49 by up to 13, so an `hbox`
that stacks on a narrow page sits side by side, as in a terminal 80
columns wide; the page flows again when the level changes and keeps its
focus. The page moves in pixel art, the way the window managers of 2008
did: it opens growing with an overshoot (the jelly), closes bending into
the corner (the lamp), and a page that comes back after an action
replaces the one before through a dither (the curtain); nothing moves on
one core, and `HIVE_SCREEN_MOTION=off` stops it all.

`<q:application type="ui">` with `quantum run app.q --target html` (a single
HTML file) or `--target textual` (a single Python file) draws **layout only**:
there is no runtime in those files, so a `q:set`, `q:function` or any other
command in them is an error that points here. Write the screen as a page to
give it logic.

`--target mobile` (React Native) is **Laboratory**: it translates the logic
to JavaScript on its own, with no stability promise. Phones are not part of
1.0. The old `--target desktop` was removed; `quantum desktop` replaces it.
