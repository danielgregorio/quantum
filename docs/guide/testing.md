# Testing an App (`quantum test`)

A Quantum app is tested in its own language. A `*.test.q` file holds tests
that visit pages, submit actions and check what happened — the redirect, the
flash message, the rows in the database, the error next to a field — in the
words the app already uses. `quantum test` runs them against the real server,
each test with a fresh database, and exits with `1` when one fails.

No Python, no browser, no CSS selectors.

## A first test

A small notes app. Save as `quantum.config.yaml`:

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/notes.db
    history: true
```

Save as `migrations/V001_notes.sql`:

```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'idea' CHECK (kind IN ('idea', 'todo')),
    created_at TEXT DEFAULT (datetime('now'))
);
INSERT INTO notes (title) VALUES ('Read the guide');
```

Save as `components/index.q`:

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

And its tests. Save as `tests/notes.test.q`:

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

Run them from the app's folder:

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

Each test starts from the same place: a new database built by
`migrations/`, holding only `Read the guide`. What `add a note` wrote is gone
when `a title needs three letters` starts.

## When a test fails

Change the flash in `add a note` to `flash="Added: Buy milk"` and run again.
The report names the step that failed, with its line, and what the app did
instead:

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

`quantum test` exits with `1`, so a CI job fails with it.

When a page itself fails — an expression that does not evaluate, SQL the
database refuses — the step that made the request fails with the error and the
**page's** line as well:

```text
        tests/bill.test.q:2  <test:visit/>
        the server answered 500: ComponentExecutionError: …
        page: components/bill.q:4
```

A step whose request answers an error status (`400` or more) fails, unless
the very next step says it expects it — `<test:expect status="404"/>` after
visiting a page that should not exist.

## Where tests live

`quantum test` searches the folder it is given (the current one by default)
for `*.test.q`:

- **next to a page** — `components/admin/index.test.q` tests
  `components/admin/index.q`. A `.test.q` is never served as a page and makes
  no route; `quantum check` reads it as a test file.
- **in `tests/`** — suites about the whole app, like `tests/signin.test.q`.

A test file belongs to the app of the nearest `quantum.config.yaml` above it.
`quantum test projects/blog tests/one.test.q` runs several places at once.

## The steps

A `q:test` has a `name` and the `page` it starts on (`/` by default). Its
steps run in order.

| Step | What it does |
|---|---|
| `<test:given table="notes" title="Draft"/>` | Inserts a row, checked against the schema |
| `<test:as user="Ana" role="admin" id="1"/>` | Signs in without a password |
| `<test:visit/>` | Opens the page — or `path="/other"` — with the other attributes as the query string |
| `<test:submit action="add" title="…"/>` | Posts the action with the other attributes as fields |
| `<test:expect …/>` | Checks what happened |

### `test:given` — rows the test needs

```xml
<test:given table="notes" title="Draft" kind="todo" />
```

The row goes into the test's database through the schema's rules: a table or
column that does not exist, a value outside a `CHECK (… IN …)` list, text in
an `INTEGER` column, a foreign key pointing at nothing — each fails the step
with a message, instead of inserting something the app could never have
written. Required columns the step leaves out are filled in: the first
allowed value of a `CHECK … IN`, the first row of the table a foreign key
points at, a number, or `"<column> <n>"` for text. With several datasources,
`datasource="…"` says which.

### `test:as` — who is using the app

```xml
<test:as user="Ana" role="admin" id="1" plan="pro" />
```

Sets the session as a sign-in does: `session.userName` is `Ana`,
`session.userRole` is `admin`, `session.userId` is `1`, and pages with
`require_auth` and `require_role` let the test in. Any other attribute is a
session variable (`session.plan` above). To test the sign-in form itself,
submit it like a person would.

### `test:visit` and `test:submit` — what a browser does

`test:submit` posts to the page the test is on, the way the form on that page
would: through the page's guards, the action's `q:param` rules, the history,
the redirect and the flash. Both steps follow redirects like a browser, and
the test is then on the page it ended at — so the next `test:submit` posts
there. After a redirect to the login page, for example, the test is on
`/login`.

A page with a single `q:action` runs it whatever name is posted; if the page
ran another action than the one the step names, the step fails — the test
would otherwise pass while testing the wrong action.

## What `test:expect` checks

Each attribute is one assertion; several on one `test:expect` must all hold.

| Assertion | Holds when |
|---|---|
| `status="302"` | The request answered this status (before any redirect was followed) |
| `redirect="/?added=1"` | It redirected here: path, query and `#fragment` |
| `flash="Added: Buy bread"` | It set exactly this flash message |
| `text="2 notes"` | The page the test is on shows this text (tags removed, spaces collapsed) |
| `no-text="Draft"` | … does not show it |
| `error="title"` | The submit was refused with an error on this field; `message="…"` checks the message |
| `var="filter" value="open"` | The page (or the action) ended with this variable's value, compared as text |
| `queries="2"`, `queries="at most 3"` | The request ran this many database queries |
| `table="notes"` | The database has rows in this table — `where="…"` filters, `count="N"` checks how many |
| `history="notes"` | `history: true` recorded changes to this table — with `action`, `op` (`insert`, `update`, `delete`), `user`, `where`, `count` |

`queries` catches the page that runs one query per row: a list of 3 rows and
a list of 300 should both say `queries="2"`.

## Nothing outside the vocabulary

The steps and assertions above are the whole language. A tag that is not
one of them, an assertion that does not exist, a `count` with no `table` or
`history` to count — each is a parse error with its line, never a step that
quietly does nothing:

```text
tests/notes.test.q: <test:click> is not a test step. The steps are: test:given, test:as, test:visit, test:submit, test:expect
  at line 4: <test:click text="Add" />
```

## In CI

`quantum test` exits with `0` when every test passed and `1` otherwise —
including when a file does not parse, a path does not exist or no test is
found. Run it in the app's folder as a CI step:

```bash
quantum test
```

## Limits for now

- Only `sqlite` datasources: each test builds its own SQLite database.
- With several datasources and a `migrations/` folder, the migrations would
  have to say which datasource they build; the test fails saying so.
- Clicking through the screen (`test:click`, `test:fill`), running one test
  on the web and the console, tests derived from the actions' rules, recorded
  AI answers and coverage are planned, not built.

See also: [Actions & Forms](./actions.md), [Database Queries](./query.md),
[Authentication](./authentication.md).
