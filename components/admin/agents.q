<q:component name="AdminAgents" require_auth="true" require_role="admin" login_url="/admin/login">
  <!--
    q:agent e q:team declarados em components/, examples/ e projects/
    (admin.agents.list). A contagem de providers é a dos que as declarações
    usam — antes somava ollama/openai/anthropic mesmo sem nenhum agente.
  -->
  <q:import component="AdminShell" from="admin/_layout" />

  <q:invoke name="ia" service="admin.agents.list" />

  <AdminShell title="Agents" active="agents" flash="{flash}" flashType="{flashType}">

    <div class="qa-grid qa-grid-4 qa-mb-6">
      <div class="qa-stat-card">
        <div class="qa-stat-label">Agent Definitions</div>
        <div class="qa-stat-value">{len(ia.agents)}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">q:agent tags found</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Team Definitions</div>
        <div class="qa-stat-value">{len(ia.teams)}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">q:team tags found</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Source Files</div>
        <div class="qa-stat-value">{len(ia.sources)}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">files with agents or teams</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Providers</div>
        <div class="qa-stat-value">{len(ia.providers)}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">{join(ia.providers, ', ') if ia.providers else 'none declared'}</span></div>
      </div>
    </div>

    <q:if condition="len(ia.agents) &gt; 0">
      <div class="qa-card qa-mb-4">
        <div class="qa-card-header">
          <div class="qa-card-title">Agent Definitions</div>
        </div>
        <div class="qa-card-body qa-p-0" style="overflow-x: auto;">
          <table class="qa-table">
            <thead><tr><th>Name</th><th>Model</th><th>Provider</th><th>Source File</th></tr></thead>
            <tbody>
              <q:loop type="array" var="agente" items="{ia.agents}">
                <tr>
                  <td><span class="qa-font-mono">{agente.name or '-'}</span></td>
                  <td><span class="qa-badge qa-badge-info">{agente.model or '-'}</span></td>
                  <td><span class="qa-badge qa-badge-primary">{agente.provider or '-'}</span></td>
                  <td><a href="/admin/source?file={agente.source}" class="qa-font-mono qa-text-sm">{agente.source}</a></td>
                </tr>
              </q:loop>
            </tbody>
          </table>
        </div>
      </div>
    </q:if>

    <q:if condition="len(ia.teams) &gt; 0">
      <div class="qa-card qa-mb-4">
        <div class="qa-card-header">
          <div class="qa-card-title">Team Definitions</div>
        </div>
        <div class="qa-card-body qa-p-0" style="overflow-x: auto;">
          <table class="qa-table">
            <thead><tr><th>Team</th><th>Supervisor</th><th>Source File</th></tr></thead>
            <tbody>
              <q:loop type="array" var="time" items="{ia.teams}">
                <tr>
                  <td><span class="qa-font-mono">{time.name or '-'}</span></td>
                  <td><span class="qa-badge qa-badge-warning">{time.supervisor or '-'}</span></td>
                  <td><a href="/admin/source?file={time.source}" class="qa-font-mono qa-text-sm">{time.source}</a></td>
                </tr>
              </q:loop>
            </tbody>
          </table>
        </div>
      </div>
    </q:if>

    <q:if condition="ia.llm">
      <div class="qa-card qa-mb-4">
        <div class="qa-card-header">
          <div>
            <div class="qa-card-title">LLM Configuration</div>
            <div class="qa-card-subtitle">llm section of quantum.config.yaml</div>
          </div>
        </div>
        <div class="qa-card-body">
          <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Base URL</span><span class="qa-font-mono">{ia.llm.base_url or '-'}</span></div>
          <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Default Model</span><span class="qa-font-mono">{ia.llm.default_model or '-'}</span></div>
          <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Timeout</span><span class="qa-font-mono">{ia.llm.timeout}s</span></div>
        </div>
      </div>
    </q:if>

    <q:if condition="len(ia.agents) == 0 and len(ia.teams) == 0">
      <div class="qa-card">
        <div class="qa-empty">
          <div class="qa-empty-title">No Agents Found</div>
          <div class="qa-empty-text">No q:agent or q:team was found in components/, examples/ or projects/.</div>
        </div>
      </div>
    </q:if>

  </AdminShell>
</q:component>
