<q:component name="AdminComponents" require_auth="true" require_role="admin" login_url="/admin/login">
  <!-- Os .q de components/ (admin.components.list). -->
  <q:import component="AdminShell" from="admin/_layout" />

  <q:invoke name="lista" service="admin.components.list" />

  <AdminShell title="Components" active="components" flash="{flash}" flashType="{flashType}">

    <div class="qa-grid qa-grid-3 qa-mb-6">
      <div class="qa-stat-card">
        <div class="qa-stat-label">Total Components</div>
        <div class="qa-stat-value">{len(lista.components)}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">.q files in components/</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Directories</div>
        <div class="qa-stat-value">{lista.directories}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">component groups</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Examples</div>
        <div class="qa-stat-value">{lista.examples}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">.q files in examples/</span></div>
      </div>
    </div>

    <q:if condition="len(lista.components) &gt; 0">
      <div class="qa-card">
        <div class="qa-card-body qa-p-0" style="overflow-x: auto;">
          <table class="qa-table">
            <thead><tr><th>Path</th><th>Lines</th><th>Size</th><th>Group</th><th>Tags</th><th></th></tr></thead>
            <tbody>
              <q:loop type="array" var="comp" items="{lista.components}">
                <tr>
                  <td><a class="qa-font-mono" href="/admin/component/components/{comp.path}">{comp.path}</a></td>
                  <td style="font-variant-numeric: tabular-nums;">{comp.lines}</td>
                  <td>{comp.size}</td>
                  <td><span class="qa-badge qa-badge-info">{comp.group}</span></td>
                  <td><span class="qa-text-sm qa-text-muted">{join(comp.feature_tags, ', ') if comp.feature_tags else '-'}</span></td>
                  <td><a href="/admin/source?file=components/{comp.path}" class="qa-text-sm">Source</a></td>
                </tr>
              </q:loop>
            </tbody>
          </table>
        </div>
      </div>
    </q:if>

    <q:if condition="len(lista.components) == 0">
      <div class="qa-card">
        <div class="qa-empty">
          <div class="qa-empty-title">No Components</div>
          <div class="qa-empty-text">There is no .q file under components/ in the project root.</div>
        </div>
      </div>
    </q:if>

  </AdminShell>
</q:component>
