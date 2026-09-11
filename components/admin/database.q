<q:component name="AdminDatabase" require_auth="true" require_role="admin" login_url="/admin/login">
  <!--
    Bancos SQLite da raiz e datasources declarados (admin.databases.list).
    Os bancos são abertos somente leitura — a versão anterior abria em modo
    escrita, inclusive bancos de aplicações rodando.
  -->
  <q:import component="AdminShell" from="admin/_layout" />

  <q:invoke name="dados" service="admin.databases.list" />

  <AdminShell title="Database" active="database" flash="{flash}" flashType="{flashType}">

    <div class="qa-grid qa-grid-3 qa-mb-6">
      <div class="qa-stat-card">
        <div class="qa-stat-label">Database Files</div>
        <div class="qa-stat-value">{len(dados.databases)}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">.db files, opened read-only</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Total Tables</div>
        <div class="qa-stat-value">{dados.total_tables}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">across all databases</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Datasources</div>
        <div class="qa-stat-value">{len(dados.datasources)}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">declared in quantum.config.yaml</span></div>
      </div>
    </div>

    <q:loop type="array" var="banco" items="{dados.databases}">
      <div class="qa-card qa-mb-4">
        <div class="qa-card-header">
          <div>
            <div class="qa-card-title"><span class="qa-font-mono">{banco.path}</span></div>
            <div class="qa-card-subtitle">{banco.size} · modified {banco.modified} · {len(banco.tables)} tables</div>
          </div>
        </div>
        <q:if condition="banco.error">
          <div class="qa-card-body"><span class="qa-text-sm" style="color: var(--q-danger);">Could not be read: {banco.error}</span></div>
        </q:if>
        <q:if condition="len(banco.tables) &gt; 0">
          <div class="qa-card-body qa-p-0">
            <table class="qa-table">
              <thead><tr><th>Table</th><th>Rows</th></tr></thead>
              <tbody>
                <q:loop type="array" var="tabela" items="{banco.tables}">
                  <tr>
                    <td><span class="qa-font-mono">{tabela.name}</span></td>
                    <td style="font-variant-numeric: tabular-nums;">{'?' if tabela.rows == None else tabela.rows}</td>
                  </tr>
                </q:loop>
              </tbody>
            </table>
          </div>
        </q:if>
      </div>
    </q:loop>

    <q:if condition="len(dados.datasources) &gt; 0">
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
              <q:loop type="array" var="fonte" items="{dados.datasources}">
                <tr>
                  <td><span class="qa-font-mono">{fonte.name}</span></td>
                  <td><span class="qa-badge qa-badge-info">{fonte.driver or '-'}</span></td>
                  <td><span class="qa-font-mono">{fonte.database or '-'}</span></td>
                </tr>
              </q:loop>
            </tbody>
          </table>
        </div>
      </div>
    </q:if>

    <q:if condition="len(dados.databases) == 0 and len(dados.datasources) == 0">
      <div class="qa-card">
        <div class="qa-empty">
          <div class="qa-empty-title">No Databases Found</div>
          <div class="qa-empty-text">No .db file under the project root and no datasource in quantum.config.yaml.</div>
        </div>
      </div>
    </q:if>

  </AdminShell>
</q:component>
