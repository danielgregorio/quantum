<q:component name="AdminApplications" require_auth="true" require_role="admin" login_url="/admin/login">
  <!--
    Aplicações. A lógica está em quantum_admin/services/projects.py
    (admin.projects.*); esta tela só chama os serviços e mostra o resultado.
    Os dados ficam no banco do admin — antes, em settings/projects.yaml.
  -->
  <q:import component="AdminShell" from="admin/_layout" />

  <q:action name="createProject" method="POST">
    <q:param name="name" type="string" required="true" minlength="2" />
    <q:param name="description" type="string" />
    <q:param name="source_path" type="string" />
    <q:invoke name="criado" service="admin.projects.create" onerror="continue">
      <q:param name="name" value="{name}" />
      <q:param name="description" value="{form.description}" />
      <q:param name="source_path" value="{form.source_path}" />
    </q:invoke>
    <q:if condition="criado_result.success">
      <q:redirect url="/admin/applications" flash="Application {criado.name} created" />
    </q:if>
    <q:flash type="error" message="{criado_result.error.message}" />
    <q:redirect url="/admin/applications" />
  </q:action>

  <q:action name="deleteProject" method="POST">
    <q:param name="project_id" type="integer" required="true" />
    <q:invoke name="removido" service="admin.projects.delete">
      <q:param name="project_id" value="{project_id}" type="integer" />
    </q:invoke>
    <q:redirect url="/admin/applications" flash="Application record removed (files were kept)" />
  </q:action>

  <q:action name="syncProjects" method="POST">
    <q:invoke name="sincronia" service="admin.projects.sync" />
    <q:redirect url="/admin/applications" flash="{len(sincronia.created)} new application(s) found on disk" />
  </q:action>

  <q:action name="importYaml" method="POST">
    <q:invoke name="importacao" service="admin.import.run" />
    <q:redirect url="/admin/applications" flash="{len(importacao.projects)} application(s) imported; database backup at {importacao.backup}" />
  </q:action>

  <!-- query.search pode não existir: a referência pura vale '' (EXPR-3) -->
  <q:set name="busca" value="{query.search}" />
  <q:invoke name="apps" service="admin.projects.list">
    <q:param name="search" value="{busca}" />
  </q:invoke>
  <q:invoke name="totais" service="admin.projects.summary" />
  <q:invoke name="pendentes" service="admin.import.pending" />

  <AdminShell title="Applications" active="applications" flash="{flash}" flashType="{flashType}">

    <q:if condition="len(pendentes.projects) &gt; 0">
      <div class="qa-card qa-mb-6">
        <div class="qa-card-body">
          <p class="qa-text-sm">
            {len(pendentes.projects)} application(s) exist only in the old settings/projects.yaml:
            <span class="qa-font-mono">{join(pendentes.projects)}</span>.
            Importing copies them into the admin database (a backup of the database is made first; the YAML file is not changed).
          </p>
          <form method="POST" action="/admin/applications">
            <input type="hidden" name="action" value="importYaml" />
            <button type="submit" class="qa-btn qa-btn-primary qa-btn-sm">Import</button>
          </form>
        </div>
      </div>
    </q:if>

    <div class="qa-grid qa-grid-4 qa-mb-6">
      <div class="qa-stat-card"><div class="qa-stat-label">Total Apps</div><div class="qa-stat-value">{totais.total}</div></div>
      <div class="qa-stat-card"><div class="qa-stat-label">Active</div><div class="qa-stat-value">{totais.active}</div></div>
      <div class="qa-stat-card"><div class="qa-stat-label">Running</div><div class="qa-stat-value">{totais.running}</div></div>
      <div class="qa-stat-card"><div class="qa-stat-label">Connectors</div><div class="qa-stat-value">{totais.connectors}</div></div>
    </div>

    <div style="display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap;">
      <form method="GET" action="/admin/applications" style="flex: 1; min-width: 200px;">
        <div class="qa-search-bar">
          <input type="text" name="search" placeholder="Search applications..." value="{busca}" aria-label="Search applications" />
        </div>
      </form>
      <form method="POST" action="/admin/applications">
        <input type="hidden" name="action" value="syncProjects" />
        <button type="submit" class="qa-btn qa-btn-secondary qa-btn-sm">Sync from Disk</button>
      </form>
    </div>

    <div class="qa-card qa-mb-6">
      <div class="qa-card-header">
        <div>
          <div class="qa-card-title">New Application</div>
          <div class="qa-card-subtitle">Create a new Quantum project</div>
        </div>
      </div>
      <div class="qa-card-body">
        <form method="POST" action="/admin/applications">
          <input type="hidden" name="action" value="createProject" />
          <div class="qa-form-row qa-mb-4">
            <div class="qa-form-group">
              <label class="qa-label" for="name">Name</label>
              <input id="name" type="text" name="name" class="qa-input" placeholder="my-app" required="" minlength="2" />
            </div>
            <div class="qa-form-group">
              <label class="qa-label" for="source_path">Source Path</label>
              <input id="source_path" type="text" name="source_path" class="qa-input" placeholder="projects/my-app (optional)" />
            </div>
          </div>
          <div class="qa-form-group qa-mb-4">
            <label class="qa-label" for="description">Description</label>
            <input id="description" type="text" name="description" class="qa-input" placeholder="Brief description of the application" />
          </div>
          <button type="submit" class="qa-btn qa-btn-primary">Create Application</button>
        </form>
      </div>
    </div>

    <q:if condition="len(apps) &gt; 0">
      <div class="qa-card qa-mb-6">
        <div class="qa-card-body" style="padding: 0;">
          <q:loop type="array" var="proj" items="{apps}">
            <div class="qa-app-card">
              <div class="qa-app-card-icon">{proj.initial}</div>
              <div style="flex: 1; min-width: 0;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 2px;">
                  <a href="/admin/app/{proj.name}" style="font-weight: 600; color: var(--q-text-primary); font-size: 0.9375rem;">{proj.name}</a>
                  <span class="{'qa-badge qa-badge-success' if proj.status == 'active' else ('qa-badge qa-badge-danger' if proj.status == 'error' else 'qa-badge qa-badge-gray')}" style="font-size: 0.65rem;">{proj.status}</span>
                  <span class="{'qa-process-running' if proj.running else 'qa-process-stopped'}">{'Running' if proj.running else 'Stopped'}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 10px;">
                  <span class="qa-font-mono qa-text-xs qa-text-muted">{proj.source_path}</span>
                  <span class="qa-text-xs qa-text-muted qa-truncate" style="max-width: 300px;">{proj.description or 'No description'}</span>
                </div>
              </div>
              <div class="qa-app-metrics">
                <div class="qa-app-metric"><span class="qa-app-metric-value">{proj.component_count}</span><span class="qa-app-metric-label">Comps</span></div>
                <div class="qa-app-metric"><span class="qa-app-metric-value">{proj.connector_count}</span><span class="qa-app-metric-label">Conns</span></div>
                <div class="qa-app-metric"><span class="qa-app-metric-value">{proj.port or '-'}</span><span class="qa-app-metric-label">Port</span></div>
              </div>
              <form method="POST" action="/admin/applications" style="flex-shrink: 0; margin: 0;" onsubmit="return confirm('Remove this application record? Files on disk will NOT be deleted.');">
                <input type="hidden" name="action" value="deleteProject" />
                <input type="hidden" name="project_id" value="{proj.id}" />
                <button type="submit" class="qa-btn qa-btn-ghost qa-btn-sm" style="color: var(--q-danger);" title="Remove record" aria-label="Remove {proj.name}">Remove</button>
              </form>
            </div>
          </q:loop>
        </div>
      </div>
    </q:if>

    <q:if condition="len(apps) == 0">
      <div class="qa-card qa-mb-6">
        <div class="qa-empty">
          <div class="qa-empty-title">{'No Results' if busca else 'No Applications Found'}</div>
          <div class="qa-empty-text">{'No applications match your search.' if busca else 'Use Sync from Disk to discover existing projects, or create one above.'}</div>
        </div>
      </div>
    </q:if>

  </AdminShell>
</q:component>
