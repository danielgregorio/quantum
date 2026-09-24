<q:component name="AdminTests" require_auth="true" require_role="admin" login_url="/admin/login">
  <!-- The test_*.py files of tests/ (admin.tests.list). Running them is on the component detail page. -->
  <q:import component="AdminShell" from="admin/_layout" />

  <q:invoke name="suite" service="admin.tests.list" />

  <AdminShell title="Tests" active="tests" flash="{flash}" flashType="{flashType}">

    <div class="qa-grid qa-grid-3 qa-mb-6">
      <div class="qa-stat-card">
        <div class="qa-stat-label">Test Files</div>
        <div class="qa-stat-value">{len(suite.files)}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">test_*.py files</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Test Functions</div>
        <div class="qa-stat-value">{suite.total_functions}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">def test_ definitions</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Directories</div>
        <div class="qa-stat-value">{len(suite.directories)}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">test groups</span></div>
      </div>
    </div>

    <q:if condition="len(suite.directories) &gt; 0">
      <div class="qa-card qa-mb-6">
        <div class="qa-card-header">
          <div class="qa-card-title">By Directory</div>
        </div>
        <div class="qa-card-body">
          <div class="qa-grid qa-grid-3">
            <q:loop type="array" var="folder" items="{suite.directories}">
              <div class="qa-stat-card">
                <div class="qa-stat-label qa-font-mono">{folder.name}</div>
                <div class="qa-text-sm"><strong>{folder.files}</strong> files · <strong>{folder.functions}</strong> tests</div>
              </div>
            </q:loop>
          </div>
        </div>
      </div>

      <div class="qa-card">
        <div class="qa-card-body qa-p-0" style="overflow-x: auto;">
          <table class="qa-table">
            <thead><tr><th>File</th><th>Functions</th><th>Directory</th><th></th></tr></thead>
            <tbody>
              <q:loop type="array" var="test_file" items="{suite.files}">
                <tr>
                  <td><span class="qa-font-mono">{test_file.path}</span></td>
                  <td style="font-variant-numeric: tabular-nums;">{test_file.functions}</td>
                  <td><span class="qa-badge qa-badge-info">{test_file.directory}</span></td>
                  <td><a href="/admin/source?file=tests/{test_file.path}" class="qa-text-sm">Source</a></td>
                </tr>
              </q:loop>
            </tbody>
          </table>
        </div>
      </div>
    </q:if>

    <q:if condition="len(suite.files) == 0">
      <div class="qa-card">
        <div class="qa-empty">
          <div class="qa-empty-title">No Tests</div>
          <div class="qa-empty-text">There is no test_*.py under tests/ in the project root. A component's page can generate one.</div>
        </div>
      </div>
    </q:if>

  </AdminShell>
</q:component>
