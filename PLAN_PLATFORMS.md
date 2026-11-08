# One application, every version — web, desktop, TUI and terminal by one parameter

> Status: approved 2026-10-23 (the goal, the proof application, the TUI drawn by Godot, and that it comes
> before PandaFoot's Phase 2). A REST API of the application's own (`q:endpoint`) is designed below and left for
> later: not the focus of this plan. The page's runtime does not change: one runtime, renderers that draw its
> view tree (UI-3).
>
> Phase 1 done 2026-10-23: `projects/kanban`, tested end to end in `tests/apps/test_kanban.py`; what it found
> in the runtime is below, each fixed with its rule and test. Phase 2 done the same day: `quantum run <app>
> --on web|desktop|terminal` (UI-18), the Kanban's script in each version (`tests/apps/test_kanban_everywhere.py`),
> and motion the same everywhere (UI-19), checked by that script. Phase 3 done 2026-11-08: `--on tui`, the TUI
> drawn by Godot (UI-20; its record is under Phase 3). Next: Phase 4.

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
| A REST API of its own | `q:endpoint` (API-1 to API-6) and its OpenAPI document, `/api/openapi.json` (API-7) | Core |
| The versions | `quantum run <app> --on web\|desktop\|tui\|terminal` (UI-18): the browser, a pywebview window, the TUI drawn by Godot (UI-20) and the terminal (Textual, with a terminal's limits) | one parameter |
| The same `ui:*` everywhere | 67 of 67 tags (the Core set, `UI_PARITY.md`) | Phase 4 done |
| One file to hand someone | `quantum package <app>` for Linux, Windows, macOS, a browser tab and a phone, a server beside it or a hosted one's client (UI-22) | Phases 5 and 6 done |

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

**Done 2026-11-08.** `quantum/runtime/tui/` is a Godot project (`tui.gd`, `layout.gd`, DejaVu Sans Mono) and
`quantum/runtime/ui_tui.py` opens it: `quantum run <app> --on tui` serves the application on a local port and opens
the window on it, fetching the pinned Godot into the cache the first time. The TUI speaks HTTP to the server itself
(`HTTPClient`: the view as JSON, form posts and `multipart/form-data`, a cookie jar, redirects followed by hand so
the session set on a redirect is kept), lays the view tree out in cells (`layout.gd`: boxes, rows of fields, tables
in columns sized by their content, an `hbox` and a `grid` by the breakpoints in columns, wide characters in two
cells) and draws them with the browser's design tokens. The Core set is drawn — the flash, the tabs (UI-17, and
`expand` when the user opens one), search as you type (UI-12, the field keeping its focus and cursor), the field
errors (UI-9), the editable table (UI-13: a cell sent with Enter, or when its box or option changes), the file field
with a dialog of its own (UI-14), progress, images fetched and drawn in their cells, streams read as they are
written (IA-7) — and anything else says `[ui:kind is not drawn in the TUI]`. The mouse clicks, hovers and scrolls
(gliding); the motions of UI-19 run and are recorded as the browser records them. Its play protocol (`--play`,
headless; `TuiSession`) is the driver of `tests/apps/ui_drivers.py`'s `Tui`: the parity script
(`tests/apps/test_ui_parity_script.py`) and the Kanban's whole script — the API step and the motions included —
pass in it, and `tests/tui/test_tui.py` covers what they do not reach. The CI's test job installs Godot for them.

What changed from the plan. The layout check compares the TUI's cells with **reference frames** of its own
(`tests/tui/frames/`, written again with `UPDATE_FRAMES=1`) and checks that no element sits on another or past the
right edge, rather than with the terminal's cells: the terminal is Textual, whose widgets (a button three rows tall,
its own paddings) are not cells of the same boxes, so equal cells would only measure Textual. What both show is
compared where it means something, by the same scripts. The TUI's installer and its version in the browser use the
games' export pipeline and are Phase 5's (an exported TUI in a browser cannot speak `HTTPClient` or keep its own
cookies; it needs the browser's fetch).

## Phase 4 — Every `ui:*` tag everywhere

The ~30 tags only the browser draws (accordion, modal, toast, tooltip, dropdown, menu, tree, chart,
calendar, date picker, stepper, carousel, breadcrumb, markdown, avatar, skeleton…) in the TUI, and in the
terminal in the form it can (a chart in bars of characters, a modal as a layer, a toast as a line);
each enters the Core set when it passes in every renderer; charts drawn natively.

**4a done 2026-11-08: the tags the server can say whole.** `quantum/runtime/ui_more.py` works out what each
means once — an avatar's initials, which crumb is the current page, a Markdown text's blocks (escaped, links
only to http, https, mailto or a path), a chart's bars and their share, a tree's rows and the lines beside
them, a log's last lines, a pagination's pages — and the view tree sends it (`as` naming the Core kind a
composition is drawn as: a breadcrumb is a row of links, a date picker a date field); the browser's page
draws its HTML from the same functions. The console, the Hive's screen (in Rust, its bars and a tree's lines in
pixels: its font is ASCII and Latin-1) and the TUI draw them, and thirteen tags enter the Core set: breadcrumb,
menu, avatar, markdown, chart, tree, log, dividedbox, pagination, skeleton, loading, date-picker and animate
(SPEC.md UI-21). A second script (`tests/apps/showcase/components/more.q`) runs in the four renderers, and
`UI_PARITY.md`, written from `quantum/runtime/ui_parity.py`, maps every tag against every renderer: a page
with every tag checks that each says "not drawn" for exactly what the map says. On the way: the browser's
page drew `ui:tree` and `ui:log` empty, `ui:markdown` raw, a bar chart squashed (its class was one bar's) and
a date picker that could not pick; the screen lost what was inside a `ui:animate`; the page's HTML lost the
space after an inline element.

What changed from the plan: "charts drawn natively" is the browser's SVG and CSS and bars in the three
others; the TUI could draw them in pixels and does not yet. Left for 4b, the tags with state of their own:
accordion, modal, tooltip, dropdown, toast, carousel, stepper, calendar — and `ui:validator` and `ui:theme`,
which a page leaves out today in every renderer, the browser too (UI_PARITY.md says so).

**4b done 2026-11-08: the tags with a state of their own.** Accordion, modal, tooltip, dropdown, toast (and
its container), carousel (and its slides) and stepper (and its steps) keep their state in the renderer, the
same way in each (SPEC.md UI-21): a fold open or closed, a modal closed, a toast gone after its duration, a tip
while pointed at or focused, a dropdown's options open, which slide, which step. The browser's page gets
the scripts only a standalone build had (a carousel's arrows, a stepper's steps and a toast's going did
nothing in a page), an accordion and a dropdown as `<details>`, a stepper's Back and Next, and a modal that
opens by an expression (`open="{...}"` was read as a boolean when parsed and never opened); `on-change`,
`on-complete`, `bind` and a toast's `on-close`, which call a standalone build's script, are errors in a page.
The console (Textual: a ModalScreen, Collapsibles, layers for toasts and tips), the TUI (layers drawn over
the page, which take the clicks) and the Hive's screen (keyboard only: a modal takes the keys, a tooltip
shows its tip while focused) draw them; a third script (`tests/apps/showcase/components/state.q`) runs in the
four renderers. 63 of the 67 tags are drawn by every renderer. Left: `ui:calendar`, and `ui:validator` and
`ui:theme`, which a page leaves out in every renderer.

**4c done 2026-11-08: Phase 4 is done, every tag in every renderer.** A form's `ui:validator`s are checked by
the server when it is sent, before its action, and the error comes back by its field as the action's own rules
do (`quantum/runtime/ui_validators.py`); a page's `ui:theme` gives the browser its CSS variables and the
console and the TUI their colours (the view's `tokens`), and the Hive's screen keeps its palette. A
`ui:calendar` in a page is a date field of its form shown as a month: the server says its month, bounds and
days that cannot be picked (`ui_more.calendar_of`), and each renderer moves it from month to month and picks
a day with the mouse or the keys (the screen: arrows, PgUp and PgDn, Enter); the day sent comes back in it,
with its error. The STATE script picks a day the validator refuses, sees the error by the calendar, then
books another, in the four renderers. 67 of the 67 tags are drawn by every renderer and every tag is in the
Core set; the "not drawn" tests now use a kind no renderer knows. On the way: the browser's calendar arrows
sent its form (no `type="button"`), and its picked day never reached the form.

What changed from the plan: the screen and the TUI leave the days of the months around the shown one blank
(as `cal` does), where the browser and the console show them dim; the TUI still draws charts in characters,
not pixels.

## Phase 5 — An installer

`quantum package <app> --on desktop|tui --target linux|windows|macos`: the server frozen (Python, Quantum and
the application) beside the client and started by it — the TUI exported with the games' pipeline, the
desktop as its window — one file to hand someone. The TUI exported for the browser too (from Phase 3), its requests
through the browser's fetch. CI builds the Kanban's Linux packages and runs its script
against them; size and time to the first page are measured.

**5a done 2026-11-08: the TUI's package.** `quantum package <app> --on tui --target linux|windows|macos`
(`quantum/runtime/package.py`, SPEC.md UI-22) makes one file: the TUI exported with the games' pipeline (now
`quantum/runtime/godot_export.py`, which both use) and, beside it, `server/` — python-build-standalone's Python for
the target, the server's libraries installed by pip for that system (wheels only, pinned to the versions this
Quantum runs with), Quantum itself and the application. Any target is made on any system. The exported TUI is the
program: with no `--url` it reads `server/package.json`, starts the server with the package's Python
(`OS.execute_with_pipe`), shows the first page when the server's line says where it listens, and holds the server's
input open, so the server (`quantum/runtime/packaged_server.py`) ends when its input does — however the TUI ends.
The server writes only to a folder of the user's: its configuration is the package's with the application's paths
pointing into the package, its SQLite databases are made by the application's migrations at each start (the
package leaves yours out unless `--with-data`), and everything it prints goes to `server.log` there, so the pipes
the TUI does not read never fill. CI's `package` job makes the Kanban's three packages and runs its whole script in
the Linux one through the TUI's play protocol (`TuiSession(program=...)`), the board's answer from its cards aside
(chromadb, which the Kanban's package does not carry). Measured: 61 MB for Linux, 78 MB for macOS (Godot's
universal binary), the first page in about 1.5 s, the package made in about 35 s once the cache is warm.

What changed from the plan: the server is not frozen into one binary (PyInstaller) but carried with a Python of
its own, which is what makes a Windows or macOS package from Linux possible; the macOS package's Python is Apple
silicon's; the desktop's package (its window as the program) and the TUI in the browser are 5b and 5c. On the way:
an exported Godot does not flush its standard output on each print, which stalled the play protocol
(`run/flush_stdout_on_print`), and the TUI's font is an imported resource once exported. A Windows and a macOS
runner then unpack the packages made on Linux and run the start of the Kanban's script in them
(`tests/package/test_package_runs_here.py`); TuiSession reads Godot's output as UTF-8 for Windows.

**5b done 2026-11-08: the desktop's package.** `quantum package <app> --on desktop --target windows|macos` makes
the same package with a window as its program: the package's Python runs the server and pywebview's window in one
process (`quantum/runtime/packaged_desktop.py`), on the system's web view (WebView2 through pythonnet, WKWebView
through PyObjC), named for each system since pip does not read a library's markers for another one. On Windows the
program is distlib's launcher (the one pip's own scripts use), whose first line runs the `pythonw.exe` beside it on
the zip after it; on a Mac, an `.app` whose program is a script that runs the package's Python. Everything the
process prints goes to the user's `server.log` (a window's Python has no output). `QUANTUM_PACKAGE_CHECK=<file>`
starts it with no window, asks its first page and imports its window's library; CI's Windows and macOS runners run
the Kanban's desktop packages so, the Windows one from a folder whose name has a space. Measured: 27 MB for
Windows.

What changed from the plan: Linux has no desktop package — its window would need Qt WebEngine (PyQt6-WebEngine,
about 550 MB installed) — and says that its package is the TUI. The window itself is not driven in CI (a runner
has no one at it); the check proves the program, its Python, its libraries and its server.

**5c done 2026-11-08: the TUI in the browser.** `quantum package <app> --target web` exports the TUI with Godot's
templates for the web (threads off, as the games', so the page needs no cross-origin isolation; the canvas the
window's size) into the application's static folder, `<app>/static/tui/` unless `--out` says: the application's
own server serves it at `/static/tui/index.html`, on the page `?page=` names, the same origin as the pages, so the
browser's cookies are the session. Nothing else is made, no Python and no server folder. In a browser
(`OS.has_feature("web")`) the TUI's requests go through the browser's fetch (`quantum/runtime/tui/web.gd`, a helper
installed once by `JavaScriptBridge`, its answers back through callbacks matched by an id): `credentials:
'same-origin'`, the redirects the browser's, the address they end at the page's path; bodies cross as base64 both
ways, so pictures and multipart forms go unchanged; a stream is read with the response's reader as it is written; a
file field opens the browser's own file picker, and the form sends the file it read. The cookie jar, the redirects
followed by hand and the file dialog stay for the window, unchanged. `window.quantumTui.request(json)` is a Promise
of the play protocol's answer, the same requests and answers as stdin and stdout; `TuiInBrowser`
(`quantum/runtime/ui_tui.py`) plays it from a Playwright page with a `TuiSession`'s requests, so the parity driver
`Tui` drives it unchanged. `tests/package/test_tui_in_browser.py` runs in Chromium (WebGL by SwiftShader, as the
games' check) the parity scripts — SCRIPT, MORE and STATE — on the showcase, a file chosen in the browser's picker and
sent, a picture, search as you type and an editable cell on the TUI's own application, and the Kanban's whole script
(signed in and out, its stream, its API, opened on `?page=/login`), each on the application's own server; CI's
`package` job installs Chromium for them, and without the templates or Chromium they are skipped elsewhere.
Measured: 44 MB (Godot's WebAssembly, 43.7 MB of it), exported in about 7 s, the first page in about 2 s in
SwiftShader's Chromium.

What changed from the plan: the TUI in the browser has the window's columns and rows rather than `--cols` and
`--rows`, and its design tokens are its own defaults (the browser's, the same colours): it has no command line. In
the browser Ctrl+Q does nothing (the browser closes its tab), and a shot of the play protocol is the page's
screenshot (`TuiInBrowser.shot`); the observation's `cookies` is empty, as the browser keeps them where the page
cannot read the session's. A package for a system leaves the TUI made for the browser out of the application it
carries (44 MB its program does not need).

## Phase 6 — The phone, and a hosted application

`--server https://...`: the TUI and the desktop as clients of a hosted application, no Python on the
machine; and the phone (`--target android|ios`), the TUI's renderer with a look for a touch screen. The React
Native target can then leave.

**6a done 2026-11-08: a hosted application's client.** `quantum package <app> --server <url>` makes the same
packages as clients: the TUI exported with the address in its project (`quantum/server` in project.godot, with the
colours), which it asks instead of starting a server — the program alone, 26 MB for the Kanban on Linux — or the
desktop's window opening on that address (`packaged_desktop` with `server` in package.json). CI runs the Kanban's
whole script in the Linux client against a hosted Kanban (`quantum run --on web`), and the Windows and macOS runners
run their TUI clients and check their windows against a Kanban they host. An address that is not https is said when
the package is made.

What changed from the plan (6a): the desktop's client still carries a Python of its own — its window is pywebview's,
which is Python — but no server and no application; "no Python on the machine" holds for every package, since
none needs one installed.

**6b done 2026-11-08: the phone.** `quantum package <app> --server <url> --target android|ios` exports the TUI as
a hosted application's client for a phone (Godot's Android and iOS presets, beside the desktops' in
`godot_export.py`): an `.apk` signed with a debug key the JDK's `keytool` makes once (or yours,
`QUANTUM_ANDROID_KEYSTORE`), Godot pointed at the Android SDK and the JDK through its editor settings, and the Xcode
project a Mac builds and signs (95 MB, made on Linux). On a touch screen (a phone, or `--touch`) the TUI sizes its
cells to the screen's width and turns with it; a tap acts where the finger was, a drag scrolls and acts on nothing
(the mouse a touch makes is left aside), and a field with the focus brings up the phone's keyboard of its kind. The
play protocol's `tap` and `drag` drive it (tests/tui/test_tui.py's TestTouch); CI's package job makes the Kanban's
`.apk` and has the SDK's `apksigner` verify it, and makes its Xcode project. The TUI has an icon now (a text screen
and its cursor), which the phones' launchers and iOS's export require.

What changed from the plan (6b): the phone's TUI is not run in an emulator in CI — the touch is driven on the
desktop's TUI with `--touch`, and the phone's package is checked as made and signed.

**6c done 2026-11-08: the React Native target left.** `quantum run --target mobile` (`ui_mobile_adapter.py`,
`ui_mobile_templates.py`, their tests and example, its Laboratory warning) is removed; the builder and the command
line say a phone's application is `quantum package --target android|ios`. **Phase 6 is done, and with it the plan:**
one application, its pages drawn by the browser, the desktop's window, the console, the Hive's screen and the TUI;
packaged for Linux, Windows, macOS and a browser tab; and, as a hosted application's client, for a phone.

## Later — `q:endpoint`: a REST API in the Core

> Brought forward on 2026-10-23 for PandaFoot's beta reports (`PLAN_PANDAFOOT.md`) and built as designed below,
> with what that first API needed: the sites whose pages may call it (`origins=`), `limit=` and `maxsize=`,
> JSON refusals, a credential from the environment (INV-3) and `server.proxies` (SPEC.md API-1 to API-6, CFG-4,
> EXPR-17).
>
> **Done 2026-11-08**: `/api/openapi.json` (API-7), an OpenAPI 3.1 document read from the components as they are
> (`quantum/runtime/openapi.py`): the routes, each endpoint's `description=`, its parameters with their rules,
> the statuses of its `q:respond`s (an object with its keys when `json=` writes a dictionary), the refusals it
> may give and the roles that may call it; `api.title`, `api.version`, `api.openapi: false`; validated by
> `openapi-spec-validator` in `tests/conformance/test_openapi.py`. `quantum check` knows the endpoints (DEV-3):
> it lists them, points out a parameter a route segment replaces, a body with a `204`, an endpoint never served
> and two files at one path, and `--openapi FILE` writes the document. The Kanban's API
> (`projects/kanban/components/api/`): `POST/GET/DELETE /api/session`, `GET /api/boards`, `GET` and `POST
> /api/boards/{id}/cards`, tested in `tests/apps/test_kanban.py`; the Kanban's script, in each version, signs
> another program in through it, adds a card and sees it on the board (`tests/apps/test_kanban_everywhere.py`,
> the step `("api", ...)` of `tests/apps/ui_drivers.py`). A REST API of its own is in the table above now.

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
