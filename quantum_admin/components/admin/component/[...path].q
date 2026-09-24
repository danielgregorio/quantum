<q:component name="AdminComponentDetail" require_auth="true" require_role="admin" login_url="/admin/login">
  <!--
    Detail of a component: /admin/component/components/shop.q.
    admin.components.get reads; admin.tests.generate and admin.tests.run act.
    `path` comes from the URL inside the actions too (ROUTE-2) — before it went in a
    hidden form field. Running tests only accepts test_*.py of
    tests/ (the previous version ran pytest on any absolute path), and
    generating does not overwrite an existing test without the Regenerate button.
  -->
  <q:import component="AdminShell" from="admin/_layout" />

  <q:action name="generateTests" method="POST">
    <q:param name="overwrite" type="boolean" default="false" />
    <q:invoke name="generated" service="admin.tests.generate" onerror="continue">
      <q:param name="comp_path" value="{path}" />
      <q:param name="overwrite" value="{overwrite}" type="boolean" />
    </q:invoke>
    <q:if condition="generated_result.success">
      <q:redirect url="/admin/component/{path}?tab=tests" flash="{generated.test_file} {'regenerated' if generated.overwritten else 'created'}" />
    </q:if>
    <q:flash type="error" message="{generated_result.error.message}" />
    <q:redirect url="/admin/component/{path}?tab=tests" />
  </q:action>

  <q:action name="runTests" method="POST">
    <q:invoke name="target" service="admin.components.get">
      <q:param name="path" value="{path}" />
    </q:invoke>
    <q:invoke name="test_run" service="admin.tests.run" onerror="continue">
      <q:param name="test_file" value="{target.test_file or ''}" />
    </q:invoke>
    <q:if condition="not test_run_result.success">
      <q:flash type="error" message="{test_run_result.error.message}" />
      <q:redirect url="/admin/component/{path}?tab=tests" />
    </q:if>
    <q:if condition="test_run.passed">
      <q:redirect url="/admin/component/{path}?tab=tests" flash="{test_run.summary.passed} passed in {test_run.summary.duration}s" />
    </q:if>
    <q:flash type="error" message="{test_run.summary.failed} failed, {test_run.summary.errors} errors, {test_run.summary.passed} passed" />
    <q:redirect url="/admin/component/{path}?tab=tests" />
  </q:action>

  <q:set name="tab" value="{query.tab}" />
  <q:invoke name="comp" service="admin.components.get" onerror="continue">
    <q:param name="path" value="{path}" />
  </q:invoke>

  <AdminShell title="Component" active="components" flash="{flash}" flashType="{flashType}">

    <q:if condition="not comp_result.success">
      <div class="qa-card">
        <div class="qa-empty">
          <div class="qa-empty-title">Cannot Load Component</div>
          <div class="qa-empty-text">{comp_result.error.message}</div>
          <a href="/admin/components" class="qa-text-sm">Back to Components</a>
        </div>
      </div>
    </q:if>

    <q:if condition="comp_result.success">
      <div class="qa-flex qa-items-center qa-mb-4" style="gap: 12px; flex-wrap: wrap;">
        <span class="qa-font-medium">{comp.name}</span>
        <span class="qa-font-mono qa-text-sm qa-text-muted">{comp.path}</span>
        <span class="qa-badge qa-badge-primary">{comp.type}</span>
        <a href="/admin/components" class="qa-text-sm">Back to Components</a>
      </div>

      <q:if condition="tab == 'tests'">
        <input type="radio" name="cdtabs" id="cdtab-general" class="qa-tab-radio" />
        <input type="radio" name="cdtabs" id="cdtab-tests" class="qa-tab-radio" checked="checked" />
      <q:else>
        <input type="radio" name="cdtabs" id="cdtab-general" class="qa-tab-radio" checked="checked" />
        <input type="radio" name="cdtabs" id="cdtab-tests" class="qa-tab-radio" />
      </q:else>
      </q:if>
      <div class="qa-tabs-bar">
        <label for="cdtab-general" class="qa-tab-label">General</label>
        <label for="cdtab-tests" class="qa-tab-label">Tests</label>
      </div>

      <div class="qa-tabs-content">
        <div class="qa-panel-cd-general">
          <div class="qa-card qa-mb-6">
            <div class="qa-card-header"><div class="qa-card-title">Metadata</div></div>
            <div class="qa-card-body">
              <div class="qa-grid qa-grid-3" style="gap: 20px;">
                <div><div class="qa-text-xs qa-text-muted">Size</div><div class="qa-text-sm">{comp.size}</div></div>
                <div><div class="qa-text-xs qa-text-muted">Lines</div><div class="qa-text-sm">{comp.lines}</div></div>
                <div><div class="qa-text-xs qa-text-muted">Last Modified</div><div class="qa-text-sm">{comp.modified}</div></div>
              </div>
            </div>
          </div>

          <q:if condition="len(comp.actions) &gt; 0">
            <div class="qa-card qa-mb-6">
              <div class="qa-card-header"><div class="qa-card-title">Actions</div></div>
              <div class="qa-card-body">
                <div class="qa-flex" style="flex-wrap: wrap; gap: 8px;">
                  <q:loop type="array" var="action_name" items="{comp.actions}">
                    <span class="qa-badge qa-badge-info qa-font-mono">{action_name}</span>
                  </q:loop>
                </div>
              </div>
            </div>
          </q:if>

          <q:if condition="len(comp.queries) &gt; 0">
            <div class="qa-card qa-mb-6">
              <div class="qa-card-header"><div class="qa-card-title">Queries</div></div>
              <div class="qa-card-body">
                <div class="qa-flex" style="flex-wrap: wrap; gap: 8px;">
                  <q:loop type="array" var="query_name" items="{comp.queries}">
                    <span class="qa-badge qa-badge-info qa-font-mono">{query_name}</span>
                  </q:loop>
                </div>
              </div>
            </div>
          </q:if>

          <q:if condition="len(comp.feature_tags) &gt; 0">
            <div class="qa-card qa-mb-6">
              <div class="qa-card-header"><div class="qa-card-title">Tags Used</div></div>
              <div class="qa-card-body">
                <div class="qa-flex" style="flex-wrap: wrap; gap: 8px;">
                  <q:loop type="array" var="tag" items="{comp.feature_tags}">
                    <span class="qa-badge qa-badge-primary">q:{tag}</span>
                  </q:loop>
                </div>
              </div>
            </div>
          </q:if>

          <a href="/admin/source?file={comp.path}" class="qa-text-sm">View Full Source</a>
        </div>

        <div class="qa-panel-cd-tests">
          <div class="qa-card qa-mb-6">
            <div class="qa-card-header">
              <div>
                <div class="qa-card-title">Tests</div>
                <div class="qa-card-subtitle qa-font-mono">{comp.test_file or 'no test file yet'}</div>
              </div>
              <div class="qa-flex qa-items-center" style="gap: 8px;">
                <q:if condition="comp.test_file">
                  <form method="POST" action="/admin/component/{comp.path}" style="margin: 0;"
                        onsubmit="return confirm('Replace the test file? Changes made by hand will be lost.');">
                    <input type="hidden" name="action" value="generateTests" />
                    <input type="hidden" name="overwrite" value="true" />
                    <button type="submit" class="qa-btn qa-btn-ghost qa-btn-sm">Regenerate</button>
                  </form>
                  <form method="POST" action="/admin/component/{comp.path}" style="margin: 0;">
                    <input type="hidden" name="action" value="runTests" />
                    <button type="submit" class="qa-btn qa-btn-primary qa-btn-sm">Run Tests</button>
                  </form>
                <q:else>
                  <form method="POST" action="/admin/component/{comp.path}" style="margin: 0;">
                    <input type="hidden" name="action" value="generateTests" />
                    <button type="submit" class="qa-btn qa-btn-primary qa-btn-sm">Generate Tests</button>
                  </form>
                </q:else>
                </q:if>
              </div>
            </div>
          </div>

          <q:if condition="comp.last_run">
            <div class="qa-grid qa-grid-4 qa-mb-6">
              <div class="qa-stat-card"><div class="qa-stat-label">Passed</div><div class="qa-stat-value" style="color: var(--q-success);">{comp.last_run.summary.passed}</div></div>
              <div class="qa-stat-card"><div class="qa-stat-label">Failed</div><div class="qa-stat-value" style="color: var(--q-danger);">{comp.last_run.summary.failed + comp.last_run.summary.errors}</div></div>
              <div class="qa-stat-card"><div class="qa-stat-label">Skipped</div><div class="qa-stat-value" style="color: var(--q-warning);">{comp.last_run.summary.skipped}</div></div>
              <div class="qa-stat-card"><div class="qa-stat-label">Ran at</div><div class="qa-text-sm">{comp.last_run.ran_at}</div></div>
            </div>
          </q:if>

          <q:if condition="len(comp.test_status) &gt; 0">
            <div class="qa-card qa-mb-6">
              <div class="qa-card-body qa-p-0">
                <table class="qa-table">
                  <thead><tr><th style="width: 110px;">Status</th><th>Test</th></tr></thead>
                  <tbody>
                    <q:loop type="array" var="test_case" items="{comp.test_status}">
                      <tr>
                        <td><span class="{'qa-badge qa-badge-success' if test_case.status == 'PASSED' else ('qa-badge qa-badge-danger' if test_case.status in ['FAILED', 'ERROR'] else 'qa-badge qa-badge-gray')}">{test_case.status}</span></td>
                        <td><span class="qa-font-mono qa-text-sm">{test_case.name}</span></td>
                      </tr>
                    </q:loop>
                  </tbody>
                </table>
              </div>
            </div>
            <a href="/admin/source?file={comp.test_file}" class="qa-text-sm">View test source</a>
          </q:if>

          <q:if condition="comp.last_run">
            <details class="qa-card qa-mb-6">
              <summary class="qa-text-sm" style="padding: 12px 16px; cursor: pointer;">Raw pytest output</summary>
              <pre class="qa-log-viewer">{comp.last_run.output}</pre>
            </details>
          </q:if>
        </div>
      </div>
    </q:if>

  </AdminShell>
</q:component>
