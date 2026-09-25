# Why Quantum

**Quantum builds web applications from declarative XML pages — with the
database, forms, sessions and AI in the language itself. No build chain, no
JavaScript, no front-end framework.**

It is for a solo developer or a small team building internal tools,
dashboards, admin screens and applications that use a language model — the
kind of software where a front-end build chain costs more than the product.

## What a page looks like

```xml
<q:component name="Tasks">
  <q:action name="add" method="POST">
    <q:param name="title" required="true" minlength="3" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title) VALUES (:title)
      <q:param name="title" value="{title}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Added: {title}" />
  </q:action>

  <q:query name="tasks" datasource="db">SELECT id, title FROM tasks ORDER BY id</q:query>

  <ui:window title="Tasks">
    <q:if condition="flash"><ui:alert variant="info">{flash}</ui:alert></q:if>
    <ui:form on-submit="add" submit="Add" />
    <ui:table source="{tasks}" />
  </ui:window>
</q:component>
```

That is the whole feature: the form draws its field from the action's
`q:param` (with `required` and `minlength` checked in the browser and on the
server), the query is parameterized by construction, and the same page runs
in a browser (`quantum start`), in a terminal (`quantum console`) and in a
desktop window (`quantum desktop`).

## What is different

- **One file per page, top to bottom.** Guards, actions, queries and the
  screen are in the order they run ([how a page runs](/guide/how-a-page-runs)).
- **The rules live in one place.** A `q:param` says what a field must be; the
  form, the server and `quantum check` all read it.
- **AI is part of the language.** `q:llm` answers from a `q:knowledge` base and
  cites its sources, streams as it writes, and `q:agent` calls tools you write
  as Quantum functions — each with a failure contract the page can handle
  ([AI](/guide/ai)).
- **It does not pretend.** A mail with no server, a knowledge source that
  cannot be read, an attribute a `q:` tag does not have: each is an error that
  says what to do, not a silent success.

## How we know it works

- A [specification](https://github.com/danielgregorio/quantum/blob/main/SPEC.md)
  with numbered rules; the test suite fails when a rule has no test.
- Real applications in `projects/`, each tested end to end in CI: a task list
  (browser, console, desktop), a blog, a dashboard, a helpdesk with uploads and
  e-mail, a docs assistant (RAG) and an agent over a SQLite database. The AI
  apps are also tested against a real model server.
- A release is built only after the whole test suite passes on the tagged
  commit, and this page's example runs in CI as shown.

## What it is not

- **Not a mobile framework.** Phones are out of 1.0; the React Native target
  is an experiment.
- **Not a SPA framework.** Pages are rendered on the server; the browser gets
  HTML, plus small scripts where a page needs them (search as you type,
  streamed answers).
- **Not tied to a model vendor, but not magic either.** A small local model
  answers worse than a large one; Quantum shows the sources so a reader can
  check.
- **SQLite first.** PostgreSQL and MySQL drivers exist but are less
  exercised; migrations, schema plans and `quantum check` are proven on SQLite.

What each part promises is in
[SUPPORT_TIERS.md](https://github.com/danielgregorio/quantum/blob/main/SUPPORT_TIERS.md):
Core and AI are stable; Experimental works without a stability promise; the
Laboratory (games, Godot, AS4) lives in the repository to push the language.
