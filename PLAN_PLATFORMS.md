# One application, every version — web, desktop, TUI and terminal by one parameter

> Status: approved 2026-10-23 (the goal, the proof application, the TUI drawn by Godot, and that it comes
> before PandaFoot's Phase 2). A REST API of the application's own (`q:endpoint`) is designed below and left for
> later: not the focus of this plan. The page's runtime does not change: one runtime, renderers that draw its
> view tree (UI-3).
>
> Phase 1 done 2026-10-23: `projects/kanban`, tested end to end in `tests/apps/test_kanban.py`; what it found
> in the runtime is below, each fixed with its rule and test. Phase 2 under way: the parameter and the
> guarantee are in (`quantum run <app> --on web|desktop|terminal`, UI-18; the Kanban's script in each version,
> `tests/apps/test_kanban_everywhere.py`); the transitions are next.

## The goal

Take an application and have its versions — **web, desktop and TUI** — by changing one parameter, with every one
of its features working in all of them, and CI saying so; and the terminal itself, for SSH and machines
without a screen. An application with a database, REST
services it calls, and the AI tags (and, later, a REST API of its own). As faithful as each platform allows: the same
`ui:*` tags meaning the same everywhere, laid out the same wherever there are pixels, with the same look.

## Where it stands

| It needs | Today | |
|---|---|---|
| A database | `q:query`, `q:transaction`, `q:action table=` | Core |
| To call REST services | `q:invoke url=` (bearer, apikey, basic) | Core |
| AI | `q:llm`, `q:knowledge`, `q:agent`, `ui:stream` | AI |
| A REST API of its own | none but the page's view for the renderers (UI-3) and `/health`: "JSON API route: not available" (the routes documented before 0.11 never ran and were removed) | later (below) |
| The versions | `quantum start`, `quantum desktop` (a pywebview over the browser), `quantum console` (Textual, in the terminal, with a terminal's limits: its colours, its cells, no mouse to speak of, nothing that moves) | three commands, no TUI |
| The same `ui:*` everywhere | about 40 of ~70 tags (the Core set); the other ~30 only in the browser | |

## Rules

Those of the Core tier for what enters it (`SUPPORT_TIERS.md`: a SPEC rule with a test that cites it, an
example that runs, a guide page, a line in `FEATURE_STATUS.md`), and of every `ui:*` renderer (UI-7). A map,
`UI_PARITY.md`, of every tag against every renderer, kept by a check. A tag a renderer cannot draw is said,
never drawn as something else. Fidelity is checked at three levels: **meaning** (every renderer: the parity
script), **layout** (every renderer with pixels: the same boxes for the same page at the same size), **look**
(the same design tokens for the browser's CSS and Godot's theme).

## Phase 1 — Kanban, as it should read

`projects/kanban`, written first, as it should read (the method of the games: what the runtime refuses is
the phase's list):

- **A Kanban manager in the database**: many boards, each with columns of its own (and a limit of cards in
  progress, WIP, that a column says when it is passed), cards with a title, description, who, due date and
  labels, moved between columns, edited, archived and deleted by actions; filters by who, label and due
  date; every change in the history (DB-11), and the board's flow measured from it (how long a card takes
  from start to done); members, viewers and an admin of each board (`require_auth`, `require_role`).
- **REST it calls**: a repository's open issues imported as cards (`q:invoke`, a fake service in the tests),
  and a webhook told when a card is done.
- **AI**: a card split into subtasks (`q:llm`, JSON), the board's summary written as it is read
  (`ui:stream`), questions about the cards answered with the cards they come from (`q:knowledge`), and an
  agent that says what is late and who has it (`q:agent`, its tools over the database).

### What Phase 1 found

The Kanban was written as it should read; what did not work as it read was the runtime's to fix:

| The Kanban wrote | What happened | Now |
|---|---|---|
| `<q:action require_role="admin,member">` so that viewers read and members change | accepted and ignored: a viewer moved cards | enforced, `403` for the others (AUTH-8) |
| `<ui:table edit="columns">` inside `<q:if condition="session.userRole == 'admin'">` | the generated `__edit` edited any row of the table, by its key, for anyone who could open the page | each cell is signed for the session it was shown to (UI-13) |
| a knowledge base of the board's cards, `name="cards{id}"` and `WHERE board_id = …` | the name was taken as written (one base for every board), and `{id}` in a query source went into its SQL as written | `q:param`s in a query source, `{…}` in its SQL refused, the name an expression (IA-10) |
| `UPDATE cards … RETURNING board_id` | taken for a `SELECT`: never committed by itself, missing from the history, and with history on, a syntax error | committed and recorded (DB-11) |
| `<q:param name="webhook_url" type="url" default="" />` | `''` is not a URL: the settings were never saved | `default=""` is empty, whatever the type (ACT-2) |
| a webhook body `{"event": "card.done", "board": "{hook[0].board}", …}` | the first expression after the JSON object's brace was sent as written | evaluated (EXPR-4) |
| `<q:function name="tellWebhook" params="card">` | ignored: the function had no parameter | a parse error that says to write `q:param` (FN-2) |

## Phase 2 — One parameter, and the guarantee

`quantum run <app> --on web|desktop|tui|terminal`:

| `--on` | What | |
|---|---|---|
| `web` | the browser | `quantum start` |
| `desktop` | the browser in a window of its own (pywebview), as today: the web exactly, no second layout engine | `quantum desktop` (UI-4) |
| `tui` | a text screen drawn by Godot (Phase 3): a grid of characters, box borders, a terminal's look, without a terminal's limits | new |
| `terminal` | the terminal itself (Textual), for SSH and machines without a screen | `quantum console` (UI-3) |

The Kanban's end-to-end script — a card created, moved and split by the AI, the board asked a question,
issues imported, the webhook told — runs on every version in CI. A feature that fails in any of them turns
CI red.

### Transitions, the same everywhere

Nothing elaborate, the same behaviour on every platform — three kinds, two speeds:

- **fade**, **slide** (from a side; between pages, forward and back by the way the user went) and
  **expand** (something that opens: a tab's content, a section, an item added to a list);
- `fast` (150 ms) and `normal` (250 ms), from the design tokens, with one easing (ease-out);
- where: the page that changes (`ui:window transition="fade|slide"`), what appears or leaves
  (`ui:animate type= on="enter|leave"`), the flash, the tab that opens, the Kanban's card that leaves one
  column and enters another;
- drawn by each renderer with what it has: the browser's CSS transitions (the web and the desktop), Godot's
  tweens (the TUI, Phase 3), Textual's animations in the terminal (opacity, offset and height, in its
  cells);
- one switch turns them all off everywhere (the system's reduced motion, `prefers-reduced-motion` in the
  browser, `ui.motion: off` in the configuration).

The check: the same steps on the same page, and each renderer reports the transitions it ran (kind,
speed, what) — the same list on every one, and the same end state.

## Phase 3 — The TUI drawn by Godot

A text screen as PandaFoot's is — a grid of characters in a monospaced font, box borders, a terminal's
colours and look — drawn by Godot, so that none of a terminal's limits apply: any colour, boxes and
columns laid out exactly, the mouse, scrolling that glides, the transitions above, wide characters and
images where the page has them. It lays the view tree out in its cells as the terminal and the Hive's
screen do, speaks to the server as they do (the view as JSON, the same posts a browser sends, a cookie
jar), and draws the Core set: the flash, the tabs, search as you type, the field errors, the editable
table, the file field with a dialog of its own. The parity script gains a TUI driver (the play protocol,
as the games' agents use it), and a layout check compares its cells with the terminal's. It is a window,
so it comes with an installer (the games' export pipeline), and it runs in the browser too.

## Phase 4 — Every `ui:*` tag everywhere

The ~30 tags only the browser draws (accordion, modal, toast, tooltip, dropdown, menu, tree, chart,
calendar, date picker, stepper, carousel, breadcrumb, markdown, avatar, skeleton…) in the TUI, and in the
terminal in the form it can (a chart in bars of characters, a modal as a layer, a toast as a line);
each enters the Core set when it passes in every renderer; charts drawn natively.

## Phase 5 — An installer

`quantum package <app> --on desktop|tui --target linux|windows|macos`: the server frozen (Python, Quantum and
the application) beside the client and started by it — the TUI exported with the games' pipeline, the
desktop as its window — one file to hand someone. CI builds the Kanban's Linux packages and runs its script
against them; size and time to the first page are measured.

## Phase 6 — The phone, and a hosted application

`--server https://...`: the TUI and the desktop as clients of a hosted application, no Python on the
machine; and the phone (`--target android|ios`), the TUI's renderer with a look for a touch screen. The React
Native target can then leave.

## Later — `q:endpoint`: a REST API in the Core

```xml
<!-- components/api/cards.q: GET and POST /api/cards -->
<q:component name="cards">
  <q:endpoint method="GET">
    <q:query name="rows" datasource="db">SELECT id, title, column_id FROM cards</q:query>
    <q:respond json="{rows}" />
  </q:endpoint>
  <q:endpoint method="POST" require_role="member">
    <q:param name="title" type="string" required="true" maxlength="120" />
    <q:query name="added" datasource="db">INSERT INTO cards (title) VALUES (:title) RETURNING id</q:query>
    <q:respond status="201" json="{ {'id': added[0].id} }" />
  </q:endpoint>
</q:component>
```

A component's `q:endpoint` per method (GET, POST, PUT, PATCH, DELETE) on the component's path (path
parameters as pages have them, `[id].q`); its `q:param`s from the JSON body or the query string, validated
as an action's (ACT-2), a refusal a 422 with each field's error; its guards (AUTH-6); `q:respond json=
status=`; a JSON error for anything that fails, never a page; `/api/openapi.json` generated from the
endpoints and their parameters; `quantum check` knows them. Its SPEC rules, tests, guide page and example.
Chosen on 2026-10-23 among four designs (the page answering JSON to whoever asks, a component of
`type="api"`, `q:action` answering JSON): the one with a contract a third party can rely on, every method and
status, and an OpenAPI for free. When it comes, the Kanban gains its API and its script a card created
through it and seen on the board.

## Risks

- **Accessibility**: Godot 4.4 does not speak to screen readers; the web and the desktop do, and the
  terminal is read by the terminal's own.
- **Size**: a Godot export is tens of megabytes, a frozen Python server about as much again.
- **Layouts that drift**: the TUI and the terminal lay out the same tree in cells; the layout check is the
  guard, as the parity script is for the meaning.
