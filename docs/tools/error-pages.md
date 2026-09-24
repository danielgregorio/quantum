# Error Pages

When a page fails while you develop (`server.debug: true`), the error page
shows **where**: the `.q` file, the lines around the one that failed with that
line marked, the message — which says what to change — and links to the SPEC
rules the message cites (`PARSE-2`, `ACT-9`…). The Python traceback is there
too, folded, for when the problem is in Quantum itself.

The line is the innermost one that failed:

- a parse error points at the tag (`<q:sett>` on line 3);
- a runtime error points at the statement — the `q:set` inside the `q:if`,
  not the `q:if`;
- an error inside a component you called points into **that component's
  file**, not at the `<Card />` that called it.

Parse errors carry the line everywhere, not only on the page: `quantum run`
and the logs print `at line 3: <q:sett name="x" value="1"/>`.

With `debug: false` the page says only that an error happened — no source, no
message details. Everything on an error page is escaped: a message can carry
what the request sent.

## Reloading keeps you logged in

With `debug: true` and `reload: true`, saving a file restarts the server
process. Without a configured `security.secret_key`, each process used to
invent its own session key, so every save logged everyone out. In debug mode
the key is now kept in `.quantum/dev-secret-key` next to your
`quantum.config.yaml` (git-ignore `.quantum/`), and sessions survive reloads.
In production, set `QUANTUM_SECRET_KEY` or `security.secret_key` — the file is
never used with `debug: false`.
