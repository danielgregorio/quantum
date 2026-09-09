<?xml version="1.0" encoding="UTF-8"?>
<q:component name="AdminProjects" xmlns:q="http://quantum-framework.org/schema">

  <!--
    Quantum Admin — project listing, written in Quantum.

    FRAMEWORK_PLAN.md Fase 4. The equivalent screen in quantum_admin/ is
    FastAPI + a JS fetch + a Jinja template. This is the same screen and the
    same database, so the comparison is direct.

    Run: quantum run apps/admin/projects.q
    Datasource `admin` is declared in quantum.config.yaml.
  -->

  <q:query name="projects" datasource="admin">
    SELECT id, name, description, status, git_branch, updated_at
    FROM projects
    ORDER BY name
  </q:query>

  <!-- ATRITO 6: q:query publica DUAS variáveis — `projects` (as linhas) e
       `projects_result` (os metadados, com recordCount). Escrevi
       {projects.recordCount} e não recebi erro nenhum: a expressão virou texto
       literal, o q:set guardou a string "{projects.recordCount}", e ela foi
       parar na página. `.length` funciona na lista e é o que se espera. -->
  <q:set name="total" value="{projects.length}" />

  <!-- ATRITO 1: <!DOCTYPE html> aqui é erro de parse. Um .q é XML, e um DOCTYPE
       só é válido antes do elemento raiz — mas o elemento raiz é <q:component>.
       Nenhum dos 168 exemplos emite DOCTYPE; a página sai em quirks mode. -->
  <html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Projects — Quantum Admin</title>
    <style>
      :root {
        --bg: #fbfaf8; --fg: #1a1a18; --muted: #6b6b64;
        --line: #e5e3dd; --card: #ffffff; --accent: #b45309;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0; background: var(--bg); color: var(--fg);
        font: 15px/1.55 ui-sans-serif, system-ui, -apple-system, sans-serif;
      }
      .wrap { max-width: 880px; margin: 0 auto; padding: 48px 24px; }
      header { border-bottom: 1px solid var(--line); padding-bottom: 20px; margin-bottom: 28px; }
      h1 { margin: 0 0 4px; font-size: 26px; letter-spacing: -0.01em; }
      .count { color: var(--muted); font-size: 14px; }
      .card {
        background: var(--card); border: 1px solid var(--line); border-radius: 10px;
        padding: 18px 20px; margin-bottom: 12px;
      }
      .row { display: flex; align-items: baseline; gap: 10px; }
      .name { font-weight: 600; font-size: 16px; }
      .desc { color: var(--muted); margin: 6px 0 10px; }
      .meta { color: var(--muted); font-size: 13px; font-variant-numeric: tabular-nums; }
      .badge {
        font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em;
        padding: 2px 8px; border-radius: 999px; border: 1px solid var(--line);
      }
      .badge.active { color: #166534; background: #f0fdf4; border-color: #bbf7d0; }
      .badge.inactive { color: var(--muted); background: #f7f7f5; }
      .empty { color: var(--muted); padding: 40px 0; text-align: center; }
      footer { margin-top: 32px; color: var(--muted); font-size: 13px; }
      code { background: #f2f0ec; padding: 1px 5px; border-radius: 4px; font-size: 13px; }
    </style>
  </head>
  <body>
    <div class="wrap">

      <header>
        <h1>Projects</h1>
        <div class="count">{total} in the admin database</div>
      </header>

      <q:if condition="{total} == 0">
        <div class="empty">No projects yet.</div>
      </q:if>

      <q:loop query="projects" var="p">
        <div class="card">
          <div class="row">
            <span class="name">{p.name}</span>
            <span class="badge {p.status}">{p.status}</span>
          </div>
          <div class="desc">{p.description}</div>
          <div class="meta">#{p.id} · branch {p.git_branch} · updated {p.updated_at}</div>
        </div>
      </q:loop>

      <footer>
        Served by Quantum from <code>components/admin/projects.q</code>.
      </footer>

    </div>
  </body>
  </html>

</q:component>
