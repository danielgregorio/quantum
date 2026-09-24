<q:component name="AdminDatabase" require_auth="true" require_role="admin" login_url="/admin/login">
  <!--
    SQLite databases under the root and declared datasources (admin.databases.list).
    The databases are opened read-only — the previous version opened them in
    write mode, even databases of running applications.
  -->
  <q:import component="AdminShell" from="admin/_layout" />

  <q:invoke name="listing" service="admin.databases.list" />

  <AdminShell title="Database" active="database" flash="{flash}" flashType="{flashType}">

    <div class="qa-grid qa-grid-3 qa-mb-6">
      <div class="qa-stat-card">
        <div class="qa-stat-label">Database Files</div>
        <div class="qa-stat-value">{len(listing.databases)}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">.db files, opened read-only</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Total Tables</div>
        <div class="qa-stat-value">{listing.total_tables}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">across all databases</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Datasources</div>
        <div class="qa-stat-value">{len(listing.datasources)}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">declared in quantum.config.yaml</span></div>
      </div>
    </div>

    <q:loop type="array" var="db" items="{listing.databases}">
      <div class="qa-card qa-mb-4">
        <div class="qa-card-header">
          <div>
            <div class="qa-card-title"><span class="qa-font-mono">{db.path}</span></div>
            <div class="qa-card-subtitle">{db.size} · modified {db.modified} · {len(db.tables)} tables</div>
          </div>
        </div>
        <q:if condition="db.error">
          <div class="qa-card-body"><span class="qa-text-sm" style="color: var(--q-danger);">Could not be read: {db.error}</span></div>
        </q:if>
        <q:if condition="len(db.tables) &gt; 0">
          <div class="qa-card-body qa-p-0">
            <table class="qa-table">
              <thead><tr><th>Table</th><th>Rows</th></tr></thead>
              <tbody>
                <q:loop type="array" var="table" items="{db.tables}">
                  <tr>
                    <td><span class="qa-font-mono">{table.name}</span></td>
                    <td style="font-variant-numeric: tabular-nums;">{'?' if table.rows == None else table.rows}</td>
                  </tr>
                </q:loop>
              </tbody>
            </table>
          </div>
        </q:if>
      </div>
    </q:loop>

    <q:if condition="len(listing.datasources) &gt; 0">
      <div class="qa-card qa-mb-4">
        <div class="qa-card-header">
          <div>
            <div class="qa-card-title">Declared Datasources</div>
            <div class="qa-card-subtitle">name, driver and database only — credentials are not shown</div>
          </div>
        </div>
        <div class="qa-card-body qa-p-0">
          <table class="qa-table">
            <thead><tr><th>Name</th><th>Driver</th><th>Database</th></tr></thead>
            <tbody>
              <q:loop type="array" var="source" items="{listing.datasources}">
                <tr>
                  <td><span class="qa-font-mono">{source.name}</span></td>
                  <td><span class="qa-badge qa-badge-info">{source.driver or '-'}</span></td>
                  <td><span class="qa-font-mono">{source.database or '-'}</span></td>
                </tr>
              </q:loop>
            </tbody>
          </table>
        </div>
      </div>
    </q:if>

    <q:if condition="len(listing.databases) == 0 and len(listing.datasources) == 0">
      <div class="qa-card">
        <div class="qa-empty">
          <div class="qa-empty-title">No Databases Found</div>
          <div class="qa-empty-text">No .db file under the project root and no datasource in quantum.config.yaml.</div>
        </div>
      </div>
    </q:if>

  </AdminShell>
</q:component>
