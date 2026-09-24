<q:component name="AdminAgents" require_auth="true" require_role="admin" login_url="/admin/login">
  <!--
    q:agent and q:team declared in components/, examples/ and projects/
    (admin.agents.list). The provider count is that of the ones the declarations
    use — before, it added ollama/openai/anthropic even without any agent.
  -->
  <q:import component="AdminShell" from="admin/_layout" />

  <q:invoke name="ai" service="admin.agents.list" />

  <AdminShell title="Agents" active="agents" flash="{flash}" flashType="{flashType}">

    <div class="qa-grid qa-grid-4 qa-mb-6">
      <div class="qa-stat-card">
        <div class="qa-stat-label">Agent Definitions</div>
        <div class="qa-stat-value">{len(ai.agents)}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">q:agent tags found</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Team Definitions</div>
        <div class="qa-stat-value">{len(ai.teams)}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">q:team tags found</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Source Files</div>
        <div class="qa-stat-value">{len(ai.sources)}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">files with agents or teams</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Providers</div>
        <div class="qa-stat-value">{len(ai.providers)}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">{join(ai.providers, ', ') if ai.providers else 'none declared'}</span></div>
      </div>
    </div>

    <q:if condition="len(ai.agents) &gt; 0">
      <div class="qa-card qa-mb-4">
        <div class="qa-card-header">
          <div class="qa-card-title">Agent Definitions</div>
        </div>
        <div class="qa-card-body qa-p-0" style="overflow-x: auto;">
          <table class="qa-table">
            <thead><tr><th>Name</th><th>Model</th><th>Provider</th><th>Source File</th></tr></thead>
            <tbody>
              <q:loop type="array" var="agent" items="{ai.agents}">
                <tr>
                  <td><span class="qa-font-mono">{agent.name or '-'}</span></td>
                  <td><span class="qa-badge qa-badge-info">{agent.model or '-'}</span></td>
                  <td><span class="qa-badge qa-badge-primary">{agent.provider or '-'}</span></td>
                  <td><a href="/admin/source?file={agent.source}" class="qa-font-mono qa-text-sm">{agent.source}</a></td>
                </tr>
              </q:loop>
            </tbody>
          </table>
        </div>
      </div>
    </q:if>

    <q:if condition="len(ai.teams) &gt; 0">
      <div class="qa-card qa-mb-4">
        <div class="qa-card-header">
          <div class="qa-card-title">Team Definitions</div>
        </div>
        <div class="qa-card-body qa-p-0" style="overflow-x: auto;">
          <table class="qa-table">
            <thead><tr><th>Team</th><th>Supervisor</th><th>Source File</th></tr></thead>
            <tbody>
              <q:loop type="array" var="team" items="{ai.teams}">
                <tr>
                  <td><span class="qa-font-mono">{team.name or '-'}</span></td>
                  <td><span class="qa-badge qa-badge-warning">{team.supervisor or '-'}</span></td>
                  <td><a href="/admin/source?file={team.source}" class="qa-font-mono qa-text-sm">{team.source}</a></td>
                </tr>
              </q:loop>
            </tbody>
          </table>
        </div>
      </div>
    </q:if>

    <q:if condition="ai.llm">
      <div class="qa-card qa-mb-4">
        <div class="qa-card-header">
          <div>
            <div class="qa-card-title">LLM Configuration</div>
            <div class="qa-card-subtitle">llm section of quantum.config.yaml</div>
          </div>
        </div>
        <div class="qa-card-body">
          <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Base URL</span><span class="qa-font-mono">{ai.llm.base_url or '-'}</span></div>
          <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Default Model</span><span class="qa-font-mono">{ai.llm.default_model or '-'}</span></div>
          <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Timeout</span><span class="qa-font-mono">{ai.llm.timeout}s</span></div>
        </div>
      </div>
    </q:if>

    <q:if condition="len(ai.agents) == 0 and len(ai.teams) == 0">
      <div class="qa-card">
        <div class="qa-empty">
          <div class="qa-empty-title">No Agents Found</div>
          <div class="qa-empty-text">No q:agent or q:team was found in components/, examples/ or projects/.</div>
        </div>
      </div>
    </q:if>

  </AdminShell>
</q:component>
