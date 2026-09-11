<q:component name="AdminFeatures" require_auth="true" require_role="admin" login_url="/admin/login">
  <!--
    Features de quantum/core/features, pelo manifest.yaml de cada uma
    (admin.features.list). A versão anterior lia src/core/features, que não
    existe mais, e a tabela vinha vazia.
  -->
  <q:import component="AdminShell" from="admin/_layout" />

  <q:invoke name="catalogo" service="admin.features.list" />

  <AdminShell title="Features" active="features" flash="{flash}" flashType="{flashType}">

    <div class="qa-grid qa-grid-4 qa-mb-6">
      <div class="qa-stat-card">
        <div class="qa-stat-label">Total Features</div>
        <div class="qa-stat-value">{len(catalogo.features)}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">with manifest.yaml</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Active</div>
        <div class="qa-stat-value">{catalogo.summary.active}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">status: active</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Planned</div>
        <div class="qa-stat-value">{catalogo.summary.planned}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">status: planned</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Other</div>
        <div class="qa-stat-value">{catalogo.summary.other}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">experimental, draft or unreadable</span></div>
      </div>
    </div>

    <div class="qa-card">
      <div class="qa-card-header">
        <div>
          <div class="qa-card-title">All Features</div>
          <div class="qa-card-subtitle">status as declared in each manifest</div>
        </div>
      </div>
      <div class="qa-card-body qa-p-0" style="overflow-x: auto;">
        <table class="qa-table">
          <thead>
            <tr><th>Feature</th><th>Description</th><th>Version</th><th>Status</th><th>Category</th><th></th></tr>
          </thead>
          <tbody>
            <q:loop type="array" var="feat" items="{catalogo.features}">
              <tr>
                <td><span class="qa-font-mono">{feat.name}</span><div class="qa-text-xs qa-text-muted">{feat.display_name}</div></td>
                <td class="qa-text-sm">{feat.short_desc}</td>
                <td><span class="qa-font-mono">{feat.version or '-'}</span></td>
                <td><span class="{'qa-badge qa-badge-success' if feat.status == 'active' else ('qa-badge qa-badge-danger' if feat.status == 'error' else ('qa-badge qa-badge-warning' if feat.status == 'planned' else 'qa-badge qa-badge-info'))}">{feat.status}</span></td>
                <td><span class="qa-badge qa-badge-info">{feat.category or '-'}</span></td>
                <td>
                  <q:if condition="feat.source">
                    <a href="/admin/source?file={feat.source}" class="qa-text-sm">Manifest</a>
                  </q:if>
                </td>
              </tr>
            </q:loop>
          </tbody>
        </table>
      </div>
    </div>

  </AdminShell>
</q:component>
