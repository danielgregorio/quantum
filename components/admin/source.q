<q:component name="AdminSource" require_auth="true" require_role="admin" login_url="/admin/login">
  <!--
    Leitor de código (admin.source.read). O serviço recusa caminhos fora da
    raiz e arquivos que podem ter credenciais (.env, chaves, bancos, os YAML
    de settings) — a versão anterior mostrava todos eles.
  -->
  <q:import component="AdminShell" from="admin/_layout" />

  <q:set name="arquivo" value="{query.file}" />
  <q:invoke name="fonte" service="admin.source.read" onerror="continue">
    <q:param name="path" value="{arquivo}" />
  </q:invoke>

  <AdminShell title="Source" active="" flash="{flash}" flashType="{flashType}">

    <q:if condition="fonte_result.success">
      <div class="qa-flex qa-items-center qa-mb-4" style="gap: 24px; flex-wrap: wrap;">
        <span class="qa-font-mono qa-font-medium">{fonte.path}</span>
        <span class="qa-badge qa-badge-info">{fonte.type}</span>
        <span class="qa-text-sm qa-text-muted">{fonte.lines} lines</span>
        <span class="qa-text-sm qa-text-muted">{fonte.size}</span>
        <span class="qa-text-sm qa-text-muted">modified {fonte.modified}</span>
      </div>
      <div class="qa-card">
        <div class="qa-card-body qa-p-0">
          <div class="qa-source-viewer">
            <div class="qa-source-gutter" id="sourceGutter"></div>
            <pre class="qa-source-code" id="sourceCode">{fonte.content}</pre>
          </div>
        </div>
      </div>
      <script src="/static/quantum-source-highlight.js"></script>
    </q:if>

    <q:if condition="not fonte_result.success">
      <div class="qa-card">
        <div class="qa-empty">
          <div class="qa-empty-title">Cannot Display Source</div>
          <div class="qa-empty-text">{fonte_result.error.message}</div>
        </div>
      </div>
    </q:if>

  </AdminShell>
</q:component>
