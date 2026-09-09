<q:component name="AdminAgents">

  <!-- Scan for agent and team definitions in .q files -->
  <q:python>
import os
import re
import yaml

base = os.getcwd()

agents = []
teams = []
scan_dirs = ['components', 'examples', 'projects']
source_files_with_agents = set()

# Regex patterns for agent/team tags
agent_pattern = re.compile(r'<q:agent\s+([^>]*?)/?>', re.DOTALL)
team_pattern = re.compile(r'<q:team\s+([^>]*?)/?>', re.DOTALL)
attr_pattern = re.compile(r'(\w+)\s*=\s*"([^"]*)"')

for scan_dir in scan_dirs:
    full_dir = os.path.join(base, scan_dir)
    if not os.path.isdir(full_dir):
        continue
    for root, dirs, files in os.walk(full_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for f in files:
            if not f.endswith('.q'):
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, base).replace('\\', '/')
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as fh:
                    content = fh.read()
            except:
                continue

            # Find agents
            for match in agent_pattern.finditer(content):
                attrs = dict(attr_pattern.findall(match.group(1)))
                name = attrs.get('name', '-')
                model = attrs.get('model', '-')
                provider = attrs.get('provider', '-')
                endpoint = attrs.get('endpoint', '-')
                agents.append({
                    'name': name,
                    'model': model,
                    'provider': provider,
                    'source': rel_path,
                })
                source_files_with_agents.add(rel_path)

            # Find teams
            for match in team_pattern.finditer(content):
                attrs = dict(attr_pattern.findall(match.group(1)))
                name = attrs.get('name', '-')
                supervisor = attrs.get('supervisor', '-')
                agents_attr = attrs.get('agents', '-')
                teams.append({
                    'name': name,
                    'agents': agents_attr,
                    'supervisor': supervisor,
                    'source': rel_path,
                })

# Collect unique providers
providers = set()
for a in agents:
    if a['provider'] != '-':
        providers.add(a['provider'])
# Add known defaults
providers.update(['ollama', 'openai', 'anthropic'])

# LLM config from quantum.config.yaml
config_path = os.path.join(base, 'quantum.config.yaml')
q.llm_base_url = '-'
q.llm_model = '-'
q.llm_timeout = '-'
q.llm_found = 'no'

if os.path.isfile(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as fh:
            cfg = yaml.safe_load(fh) or {}
        llm = cfg.get('llm', {})
        if llm:
            q.llm_found = 'yes'
            q.llm_base_url = str(llm.get('base_url', '-'))
            q.llm_model = str(llm.get('default_model', '-'))
            q.llm_timeout = str(llm.get('timeout', 60)) + 's'
    except:
        pass

q.agents = agents
q.teams = teams
q.total_agents = str(len(agents))
q.total_teams = str(len(teams))
q.total_files = str(len(source_files_with_agents))
q.total_providers = str(len(providers))
q.has_agents = 'yes' if agents else 'no'
q.has_teams = 'yes' if teams else 'no'
  </q:python>

  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Agents - Quantum Admin</title>
    <link rel="stylesheet" href="/static/quantum-admin.css" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap" rel="stylesheet" />
  </head>
  <body>
    <div class="qa-layout">

      <!-- ============ SIDEBAR ============ -->
      <aside class="qa-sidebar">
        <div class="qa-sidebar-header">
          <a href="/admin" class="qa-sidebar-logo">
            <div class="qa-sidebar-logo-icon">Q</div>
            <span class="qa-sidebar-logo-text">Quantum<span class="qa-sidebar-version">Admin</span></span>
          </a>
        </div>

        <nav class="qa-sidebar-nav">
          <div class="qa-sidebar-section">
            <div class="qa-sidebar-section-title">Overview</div>
            <a href="/admin/dashboard" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
              Dashboard
            </a>
            <a href="/admin/applications" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
              Applications
            </a>
          </div>

          <div class="qa-sidebar-section">
            <div class="qa-sidebar-section-title">Framework</div>
            <a href="/admin/components" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
              Components
            </a>
            <a href="/admin/features" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
              Features
            </a>
          </div>

          <div class="qa-sidebar-section">
            <div class="qa-sidebar-section-title">Runtime</div>
            <a href="/admin/connectors" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M6 8H5a4 4 0 0 0 0 8h1"/><line x1="6" y1="12" x2="18" y2="12"/></svg>
              Connectors
            </a>
            <a href="/admin/database" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
              Database
            </a>
            <a href="/admin/agents" class="qa-sidebar-link active">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
              Agents
            </a>
            <a href="/admin/jobs" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              Jobs
            </a>
          </div>

          <div class="qa-sidebar-section">
            <div class="qa-sidebar-section-title">System</div>
            <a href="/admin/settings" class="qa-sidebar-link">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
              Settings
            </a>
          </div>
        </nav>

        <div class="qa-sidebar-footer">
          <div class="qa-sidebar-user">
            <div class="qa-sidebar-user-avatar">Q</div>
            <div class="qa-sidebar-user-info">
              <div class="qa-sidebar-user-name">Quantum Admin</div>
              <div class="qa-sidebar-user-role">Native</div>
            </div>
          </div>
        </div>
      </aside>

      <!-- ============ MAIN CONTENT ============ -->
      <main class="qa-main">

        <!-- Header -->
        <header class="qa-header">
          <h1 class="qa-header-title">Agents</h1>
          <div class="qa-header-actions">
            <span class="qa-badge qa-badge-primary">AI</span>
          </div>
        </header>

        <!-- Content -->
        <div class="qa-content">

          <!-- Stat Cards -->
          <div class="qa-grid qa-grid-4 qa-mb-6">
            <div class="qa-stat-card">
              <div class="qa-stat-label">Agent Definitions</div>
              <div class="qa-stat-value">{total_agents}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">q:agent tags found</span>
              </div>
            </div>

            <div class="qa-stat-card">
              <div class="qa-stat-label">Team Definitions</div>
              <div class="qa-stat-value">{total_teams}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">q:team tags found</span>
              </div>
            </div>

            <div class="qa-stat-card">
              <div class="qa-stat-label">Source Files</div>
              <div class="qa-stat-value">{total_files}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">files with agents</span>
              </div>
            </div>

            <div class="qa-stat-card">
              <div class="qa-stat-label">Providers</div>
              <div class="qa-stat-value">{total_providers}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">supported LLM providers</span>
              </div>
            </div>
          </div>

          <!-- Agents Table -->
          <q:if condition="{has_agents} == 'yes'">
            <div class="qa-card qa-mb-4">
              <div class="qa-card-header">
                <div>
                  <div class="qa-card-title">Agent Definitions</div>
                  <div class="qa-card-subtitle">{total_agents} agents discovered across .q files</div>
                </div>
              </div>
              <div class="qa-card-body qa-p-0">
                <table class="qa-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Model</th>
                      <th>Provider</th>
                      <th>Source File</th>
                    </tr>
                  </thead>
                  <tbody>
                    <q:loop type="array" var="agent" items="{agents}">
                      <tr>
                        <td><span class="qa-font-mono">{agent.name}</span></td>
                        <td><span class="qa-badge qa-badge-info">{agent.model}</span></td>
                        <td><span class="qa-badge qa-badge-primary">{agent.provider}</span></td>
                        <td><a href="/admin/source?file={agent.source}" class="qa-font-mono qa-text-sm" style="color: var(--q-primary-400);">{agent.source}</a></td>
                      </tr>
                    </q:loop>
                  </tbody>
                </table>
              </div>
            </div>
          </q:if>

          <!-- Teams Table -->
          <q:if condition="{has_teams} == 'yes'">
            <div class="qa-card qa-mb-4">
              <div class="qa-card-header">
                <div>
                  <div class="qa-card-title">Team Definitions</div>
                  <div class="qa-card-subtitle">{total_teams} teams discovered</div>
                </div>
              </div>
              <div class="qa-card-body qa-p-0">
                <table class="qa-table">
                  <thead>
                    <tr>
                      <th>Team Name</th>
                      <th>Agents</th>
                      <th>Supervisor</th>
                      <th>Source File</th>
                    </tr>
                  </thead>
                  <tbody>
                    <q:loop type="array" var="team" items="{teams}">
                      <tr>
                        <td><span class="qa-font-mono">{team.name}</span></td>
                        <td><span class="qa-text-sm">{team.agents}</span></td>
                        <td><span class="qa-badge qa-badge-warning">{team.supervisor}</span></td>
                        <td><a href="/admin/source?file={team.source}" class="qa-font-mono qa-text-sm" style="color: var(--q-primary-400);">{team.source}</a></td>
                      </tr>
                    </q:loop>
                  </tbody>
                </table>
              </div>
            </div>
          </q:if>

          <!-- LLM Configuration -->
          <q:if condition="{llm_found} == 'yes'">
            <div class="qa-card qa-mb-4">
              <div class="qa-card-header">
                <div class="qa-card-title">LLM Configuration</div>
              </div>
              <div class="qa-card-body">
                <div style="display: flex; flex-direction: column; gap: 12px;">
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Base URL</span>
                    <span class="qa-font-mono">{llm_base_url}</span>
                  </div>
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Default Model</span>
                    <span class="qa-font-mono">{llm_model}</span>
                  </div>
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Timeout</span>
                    <span class="qa-font-mono">{llm_timeout}</span>
                  </div>
                </div>
              </div>
            </div>
          </q:if>

          <!-- Empty State -->
          <q:if condition="{has_agents} != 'yes'">
            <q:if condition="{has_teams} != 'yes'">
              <div class="qa-card">
                <div class="qa-card-body" style="text-align: center; padding: 48px 24px;">
                  <div style="font-size: 3rem; margin-bottom: 16px; opacity: 0.3;">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="display: inline-block;"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                  </div>
                  <div class="qa-text-lg qa-font-medium qa-text-primary" style="margin-bottom: 8px;">No Agents Found</div>
                  <div class="qa-text-sm qa-text-muted">No q:agent or q:team definitions were found in components/ or examples/. Create agents using the &lt;q:agent&gt; tag.</div>
                </div>
              </div>
            </q:if>
          </q:if>

        </div>
      </main>

    </div>
  </body>
  </html>
</q:component>
