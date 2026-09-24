# Desktop (`quantum desktop`)

`quantum desktop` opens your application in a native window. It starts the
application's server on a free local port (`127.0.0.1`) and opens a
[pywebview](https://pywebview.flowrl.com/) window on it: the window is a
browser without the browser's chrome, so the pages, `q:action`s, sessions and
responsive layout are exactly the web's. Closing the window stops the server.

```bash
pip install "quantum-framework[desktop]"

quantum desktop                      # the home page
quantum desktop /reports             # another page
quantum desktop --width 800 --height 600
quantum desktop --config other.config.yaml
```

Without the `[desktop]` extra, the command says what to install instead of
failing with an import error.

The window's title follows the page: the first `ui:window`'s `title`, else the
component's name — the same title the browser tab and `quantum console` show.

Platform notes (from pywebview):

- **Windows**: uses Edge WebView2, already present on Windows 10/11.
- **macOS**: uses WebKit, nothing to install.
- **Linux**: needs GTK/WebKit, e.g. `sudo apt install python3-gi gir1.2-webkit2-4.1`.

## Write pages, not a desktop app

There is no separate "desktop version" of a screen. Write the page once, with
`ui:*` elements — see [One App, Many Screens](/guide/ui) — and open it with
`quantum start`, `quantum console` or `quantum desktop`.

## What happened to `--target desktop`

Until 0.15, `quantum run app.q --target desktop` generated a Python file with a
JavaScript bridge that translated `q:set` and `q:function` into its own
reactive state. It was a second implementation of the language, and it
disagreed with the first. It was removed in 0.16 (SPEC `UI-8`); building with
it is an error that points to `quantum desktop`.
