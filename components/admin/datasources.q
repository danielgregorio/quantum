<?xml version="1.0" encoding="UTF-8"?>
<q:component name="AdminDatasources" xmlns:q="http://quantum-framework.org/schema">

  <!--
    Quantum Admin — datasource listing, written in Quantum.

    SATELLITES_AUDIT.md Fase E. The second screen of the chosen core
    (projects + datasources + jobs); components/admin/projects.q was the
    first. The equivalent in quantum_admin/ is a FastAPI route plus an htmx
    partial built by string concatenation inside main.py.

    This one also exists to be used: writing a real screen is what turned up
    the eleven framework frictions listed in DOGFOOD_NOTES.md, and the notes
    below are what this one turned up.

    Run: quantum run components/admin/datasources.q
    Datasource `admin` is declared in quantum.config.yaml.
  -->

  <q:query name="sources" datasource="admin">
    SELECT d.id, d.name, d.type, d.host, d.port, d.database_name,
           d.status, d.health_status, p.name AS project
    FROM datasources d
    LEFT JOIN projects p ON p.id = d.project_id
    ORDER BY d.name
  </q:query>

  <q:set name="total" value="{sources.length}" />

  <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Datasources — Quantum Admin</title>
      <style>
        :root {
          --bg: #fbfaf8; --fg: #1a1a18; --muted: #6b6b63;
          --line: #e5e2db; --card: #ffffff; --accent: #2f6f4f;
          --warn: #a4552b; --dim: #9a978f;
        }
        * { box-sizing: border-box; }
        body {
          margin: 0; background: var(--bg); color: var(--fg);
          font: 15px/1.55 ui-sans-serif, system-ui, -apple-system, sans-serif;
        }
        main { max-width: 60rem; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }
        header { border-bottom: 1px solid var(--line); padding-bottom: 1rem; }
        h1 { font-size: 1.5rem; margin: 0 0 .25rem; letter-spacing: -.01em; }
        .count { color: var(--muted); font-size: .875rem; }
        .empty {
          margin-top: 2rem; padding: 2rem; text-align: center;
          border: 1px dashed var(--line); border-radius: .5rem;
          color: var(--muted);
        }
        .card {
          background: var(--card); border: 1px solid var(--line);
          border-radius: .5rem; padding: 1rem 1.15rem; margin-top: .75rem;
        }
        .row {
          display: flex; align-items: baseline; gap: .6rem;
          justify-content: space-between;
        }
        .name { font-weight: 600; }
        .kind {
          font: 600 .7rem/1 ui-monospace, monospace; letter-spacing: .04em;
          text-transform: uppercase; color: var(--accent);
        }
        .badge {
          font-size: .7rem; padding: .15rem .5rem; border-radius: 999px;
          border: 1px solid var(--line); color: var(--muted);
        }
        .badge.healthy { color: var(--accent); border-color: var(--accent); }
        .badge.unhealthy, .badge.error { color: var(--warn); border-color: var(--warn); }
        .meta {
          color: var(--dim); font-size: .8rem; margin-top: .35rem;
          font-family: ui-monospace, monospace;
        }
        footer {
          margin-top: 2.5rem; padding-top: 1rem;
          border-top: 1px solid var(--line);
          color: var(--dim); font-size: .8rem;
        }
      </style>
    </head>
    <body>
      <main>
        <header>
          <h1>Datasources</h1>
          <div class="count">{total} in the admin database</div>
        </header>

        <q:if condition="{total} == 0">
          <div class="empty">
            No datasources registered. They are created from the project
            screen, or declared directly in <code>quantum.config.yaml</code>.
          </div>
        </q:if>

        <q:loop query="sources" var="d">
          <div class="card">
            <div class="row">
              <span class="name">{d.name}</span>
              <span class="kind">{d.type}</span>
            </div>
            <div class="row">
              <span class="meta">{d.host}:{d.port}/{d.database_name}</span>
              <span class="badge {d.health_status}">{d.health_status}</span>
            </div>
            <div class="meta">#{d.id} · project {d.project} · {d.status}</div>
          </div>
        </q:loop>

        <footer>
          Written in Quantum — one file, one query, no JavaScript.
          The FastAPI equivalent builds this markup by string concatenation
          inside quantum_admin/backend/main.py.
        </footer>
      </main>
    </body>
  </html>
</q:component>
