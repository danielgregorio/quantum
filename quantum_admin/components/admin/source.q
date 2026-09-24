<q:component name="AdminSource" require_auth="true" require_role="admin" login_url="/admin/login">
  <!--
    Code reader (admin.source.read). The service refuses paths outside the
    root and files that may hold credentials (.env, keys, databases, the
    settings YAML files) — the previous version showed all of them.
  -->
  <q:import component="AdminShell" from="admin/_layout" />

  <q:set name="file_path" value="{query.file}" />
  <q:invoke name="source" service="admin.source.read" onerror="continue">
    <q:param name="path" value="{file_path}" />
  </q:invoke>

  <AdminShell title="Source" active="" flash="{flash}" flashType="{flashType}">

    <q:if condition="source_result.success">
      <div class="qa-flex qa-items-center qa-mb-4" style="gap: 24px; flex-wrap: wrap;">
        <span class="qa-font-mono qa-font-medium">{source.path}</span>
        <span class="qa-badge qa-badge-info">{source.type}</span>
        <span class="qa-text-sm qa-text-muted">{source.lines} lines</span>
        <span class="qa-text-sm qa-text-muted">{source.size}</span>
        <span class="qa-text-sm qa-text-muted">modified {source.modified}</span>
      </div>
      <div class="qa-card">
        <div class="qa-card-body qa-p-0">
          <div class="qa-source-viewer">
            <div class="qa-source-gutter" id="sourceGutter"></div>
            <pre class="qa-source-code" id="sourceCode">{source.content}</pre>
          </div>
        </div>
      </div>
      <script src="/static/quantum-source-highlight.js"></script>
    </q:if>

    <q:if condition="not source_result.success">
      <div class="qa-card">
        <div class="qa-empty">
          <div class="qa-empty-title">Cannot Display Source</div>
          <div class="qa-empty-text">{source_result.error.message}</div>
        </div>
      </div>
    </q:if>

  </AdminShell>
</q:component>
