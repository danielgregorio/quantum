# Hot Reload

While you write an app, `quantum start --hot-reload` reloads the pages open in
the browser whenever you save a component or a static file. You do not restart
the server or press F5.

```bash
quantum start --hot-reload
```

The server prints its address as usual. Open a page, edit a `.q` file under
`components/`, save, and the page shows the change.

## What happens on a change

The server watches two folders from `quantum.config.yaml`: `paths.components`
and `paths.static`. Each page it serves opens a WebSocket to the watcher.

| You save | The open pages |
|---|---|
| A `.q`, `.html`, `.js`, `.yaml` or `.yml` file | Reload. What was typed in their forms is kept |
| Only `.css` files | Fetch the stylesheets again, without reloading |
| A `.q` file that no longer parses | Do not reload. They show the file and the parse error on top of the page until you fix it |

Changes are grouped: saving several files at once gives one reload.

Pages are read again after a change, even with `performance.cache_templates`
on. Python code (services, `q:python`) is not reloaded: for that, set
`server.reload: true`, which restarts the server when a `.py` file changes.

## Options

| Flag | Meaning |
|---|---|
| `--hot-reload` | Watch the project and reload the open pages |
| `--hot-reload-port N` | Port of the WebSocket the pages connect to. Default `35729` |

Without `--hot-reload`, nothing is watched and nothing is added to the pages.
Hot reload is for your machine: the pages connect to `localhost`.

## Troubleshooting

**The page does not reload.** Open the browser console: the client logs
`[Hot Reload] Connected to dev server` when it connects. If it keeps trying to
reconnect, another program may be using port 35729. Start with
`--hot-reload-port` and a free port.

**A change is not picked up.** Only files under `paths.components` and
`paths.static` are watched. Check those paths in `quantum.config.yaml`.

The rule behind this page is DEV-4 in the specification.

## Related

- [CLI Commands](/tools/cli) - `quantum start` and the other commands
- [Development panel](/tools/dev-panel) - What each request did (`server.debug: true`)
- [Project Structure](/guide/project-structure) - Where components and static files live
