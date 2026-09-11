<q:component name="AdminDashboard" require_auth="true" require_role="admin" login_url="/admin/login">
  <!--
    Números do repositório, medidos por admin.dashboard.stats
    (quantum_admin/services/repository.py). A versão anterior procurava
    src/core/... e mostrava 0 features, 0 parsers e 0 executores.
  -->
  <q:import component="AdminShell" from="admin/_layout" />

  <q:invoke name="stats" service="admin.dashboard.stats" />
  <q:invoke name="catalogo" service="admin.features.list" />

  <AdminShell title="Dashboard" active="dashboard" flash="{flash}" flashType="{flashType}">

    <div class="qa-grid qa-grid-4 qa-mb-6">
      <div class="qa-stat-card">
        <div class="qa-stat-label">Components</div>
        <div class="qa-stat-value">{stats.components}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">.q files in components/</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Features</div>
        <div class="qa-stat-value">{stats.features}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">manifests in quantum/core/features/</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Test Files</div>
        <div class="qa-stat-value">{stats.tests}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">test_*.py in tests/</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Examples</div>
        <div class="qa-stat-value">{stats.examples}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">.q files in examples/</span></div>
      </div>
    </div>

    <div class="qa-grid qa-grid-2 qa-mb-6">
      <div class="qa-stat-card">
        <div class="qa-stat-label">Tags with a parser</div>
        <div class="qa-stat-value">{stats.parser_tags}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">registered in the parser registry</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Executors</div>
        <div class="qa-stat-value">{stats.executors}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">registered in the executor registry</span></div>
      </div>
    </div>

    <div class="qa-grid qa-grid-2">
      <div class="qa-card">
        <div class="qa-card-header">
          <div>
            <div class="qa-card-title">Project Components</div>
            <div class="qa-card-subtitle">{stats.components} .q files</div>
          </div>
        </div>
        <div class="qa-card-body" style="max-height: 360px; overflow-y: auto;">
          <q:loop type="array" var="comp" items="{stats.component_list}">
            <div class="qa-activity-item">
              <a class="qa-text-sm qa-font-medium qa-font-mono" href="/admin/component/components/{comp}">{comp}</a>
            </div>
          </q:loop>
        </div>
      </div>

      <div class="qa-card">
        <div class="qa-card-header">
          <div>
            <div class="qa-card-title">Features</div>
            <div class="qa-card-subtitle">{len(catalogo.features)} feature modules</div>
          </div>
        </div>
        <div class="qa-card-body" style="max-height: 360px; overflow-y: auto;">
          <q:loop type="array" var="feat" items="{catalogo.features}">
            <div class="qa-activity-item">
              <span class="qa-text-sm qa-font-medium">{feat.display_name}</span>
              <span class="{'qa-badge qa-badge-success' if feat.status == 'active' else 'qa-badge qa-badge-gray'}">{feat.status}</span>
            </div>
          </q:loop>
        </div>
      </div>
    </div>

  </AdminShell>
</q:component>
