<q:component name="AdminApplications">

  <!-- Action: Create a new project -->
  <q:action name="createProject" method="POST">
    <q:param name="name" type="string" required="true" />
    <q:param name="description" type="string" />
    <q:param name="source_path" type="string" />

    <q:python>
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, save_yaml, gen_id, now_iso
import yaml

name = q.form.get('name', '').strip()
description = q.form.get('description', '').strip()
source_path = q.form.get('source_path', '').strip()

if not name or len(name) &lt; 2:
    pass  # skip, redirect will happen anyway
else:
    projects = load_yaml('projects.yaml')

    # Check unique name
    existing = [p for p in projects if p.get('name', '').lower() == name.lower()]
    if not existing:
        if not source_path:
            source_path = 'projects/' + name

        proj_dir = os.path.join(os.getcwd(), source_path)

        # Scaffold project directory
        os.makedirs(os.path.join(proj_dir, 'components'), exist_ok=True)
        os.makedirs(os.path.join(proj_dir, 'static'), exist_ok=True)

        # Create quantum.config.yaml if not exists
        config_path = os.path.join(proj_dir, 'quantum.config.yaml')
        if not os.path.isfile(config_path):
            default_config = {
                'server': {'port': 8080, 'host': '0.0.0.0', 'debug': True},
                'paths': {'components': './components', 'static': './static'},
            }
            with open(config_path, 'w', encoding='utf-8') as fh:
                yaml.dump(default_config, fh, default_flow_style=False, sort_keys=False)

        # Read config snapshot
        config_snapshot = {}
        try:
            with open(config_path, 'r', encoding='utf-8') as fh:
                config_snapshot = yaml.safe_load(fh) or {}
        except:
            pass

        project = {
            'id': gen_id(),
            'name': name,
            'description': description,
            'status': 'active',
            'source_path': source_path,
            'created_at': now_iso(),
            'updated_at': now_iso(),
            'config': config_snapshot.get('server', {}),
            'environments': [],
        }
        projects.append(project)
        save_yaml('projects.yaml', projects)
    </q:python>

    <q:redirect url="/admin/applications?flash=Application+created" />
  </q:action>

  <!-- Action: Delete a project record (does NOT delete files) -->
  <q:action name="deleteProject" method="POST">
    <q:param name="project_id" type="string" required="true" />

    <q:python>
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, save_yaml

pid = q.form.get('project_id', '').strip()
projects = load_yaml('projects.yaml')
projects = [p for p in projects if p.get('id') != pid]
save_yaml('projects.yaml', projects)
    </q:python>

    <q:redirect url="/admin/applications?flash=Application+removed" />
  </q:action>

  <!-- Action: Sync projects from disk -->
  <q:action name="syncProjects" method="POST">
    <q:python>
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, save_yaml, gen_id, now_iso
import yaml

projects = load_yaml('projects.yaml')
projects_dir = os.path.join(os.getcwd(), 'projects')

# Index existing by source_path
existing_paths = {p.get('source_path', ''): p for p in projects}

if os.path.isdir(projects_dir):
    for entry in sorted(os.listdir(projects_dir)):
        proj_path = os.path.join(projects_dir, entry)
        if not os.path.isdir(proj_path) or entry.startswith('.') or entry.startswith('_'):
            continue

        rel_path = 'projects/' + entry

        if rel_path in existing_paths:
            # Update config snapshot for existing
            existing = existing_paths[rel_path]
            config_path = os.path.join(proj_path, 'quantum.config.yaml')
            if os.path.isfile(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as fh:
                        cfg = yaml.safe_load(fh) or {}
                    existing['config'] = cfg.get('server', {})
                except:
                    pass
                existing['updated_at'] = now_iso()
        else:
            # Create new record
            config_snapshot = {}
            config_path = os.path.join(proj_path, 'quantum.config.yaml')
            if os.path.isfile(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as fh:
                        cfg = yaml.safe_load(fh) or {}
                    config_snapshot = cfg.get('server', {})
                except:
                    pass

            project = {
                'id': gen_id(),
                'name': entry,
                'description': '',
                'status': 'active',
                'source_path': rel_path,
                'created_at': now_iso(),
                'updated_at': now_iso(),
                'config': config_snapshot,
                'environments': [],
            }
            projects.append(project)

save_yaml('projects.yaml', projects)
    </q:python>

    <q:redirect url="/admin/applications?flash=Applications+synced" />
  </q:action>

  <!-- Collect project data -->
  <q:python>
import sys, os, datetime
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, get_process_status

projects = load_yaml('projects.yaml')
connectors = load_yaml('connectors.yaml')

base = os.getcwd()
total_active = 0
total_running = 0
total_with_config = 0
total_connectors = len(connectors)

# Search filter
search_term = ''
try:
    from flask import request as flask_request
    search_term = flask_request.args.get('search', '').strip().lower()
    q.flash_message = flask_request.args.get('flash', '')
except:
    q.flash_message = ''
q.search_term = search_term if search_term else ''

display_projects = []
for p in projects:
    # Search filter
    if search_term:
        name_match = search_term in p.get('name', '').lower()
        desc_match = search_term in (p.get('description', '') or '').lower()
        if not name_match and not desc_match:
            continue

    dp = dict(p)
    source = p.get('source_path', '')
    proj_dir = os.path.join(base, source)

    # Status
    status = p.get('status', 'active')
    if status == 'active':
        total_active += 1
    dp['status_badge'] = {
        'active': 'qa-badge-success',
        'archived': 'qa-badge-gray',
        'error': 'qa-badge-danger',
    }.get(status, 'qa-badge-info')

    # Process status (runtime)
    proc_status = get_process_status(p.get('name', ''))
    dp['runtime_running'] = 'yes' if proc_status['running'] else 'no'
    dp['runtime_badge'] = 'qa-process-running' if proc_status['running'] else 'qa-process-stopped'
    dp['runtime_label'] = 'Running' if proc_status['running'] else 'Stopped'
    if proc_status['running']:
        total_running += 1

    # Config
    config = p.get('config', {})
    dp['port'] = str(config.get('port', '-'))
    dp['debug'] = str(config.get('debug', '-'))

    # Check config file exists on disk
    config_path = os.path.join(proj_dir, 'quantum.config.yaml')
    dp['has_config'] = 'yes' if os.path.isfile(config_path) else 'no'
    if dp['has_config'] == 'yes':
        total_with_config += 1

    # Count components
    comp_dir = os.path.join(proj_dir, 'components')
    comp_count = 0
    if os.path.isdir(comp_dir):
        for root, dirs, files in os.walk(comp_dir):
            for f in files:
                if f.endswith('.q'):
                    comp_count += 1
    dp['component_count'] = str(comp_count)

    # Count connectors scoped to this project
    pid = p.get('id', '')
    proj_connectors = [c for c in connectors if str(c.get('application_id', '')) == str(pid)]
    dp['connector_count'] = str(len(proj_connectors))

    # Name initial (for icon)
    dp['initial'] = p.get('name', '?')[0].upper()

    # Last modified
    try:
        if os.path.isdir(proj_dir):
            mtime = os.path.getmtime(proj_dir)
            dt = datetime.datetime.fromtimestamp(mtime)
            dp['last_modified'] = dt.strftime('%Y-%m-%d %H:%M')
        else:
            dp['last_modified'] = '-'
    except:
        dp['last_modified'] = '-'

    dp['description'] = p.get('description', '') or 'No description'

    display_projects.append(dp)

q.projects = display_projects
q.total_apps = str(len(projects))
q.total_displayed = str(len(display_projects))
q.total_active = str(total_active)
q.total_running = str(total_running)
q.with_config = str(total_with_config)
q.total_connectors = str(total_connectors)
  </q:python>

  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Applications - Quantum Admin</title>
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
            <a href="/admin/applications" class="qa-sidebar-link active">
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
            <a href="/admin/agents" class="qa-sidebar-link">
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
          <h1 class="qa-header-title">Applications</h1>
          <div class="qa-header-actions">
            <form method="POST" action="/admin/applications" style="display: inline;">
              <input type="hidden" name="action" value="syncProjects" />
              <button type="submit" class="qa-btn qa-btn-secondary qa-btn-sm">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6"/><path d="M2.5 22v-6h6"/><path d="M2 11.5a10 10 0 0 1 18.8-4.3"/><path d="M22 12.5a10 10 0 0 1-18.8 4.2"/></svg>
                Sync from Disk
              </button>
            </form>
          </div>
        </header>

        <!-- Content -->
        <div class="qa-content">

          <!-- Flash Message -->
          <q:if condition="{flash_message} != ''">
            <div style="padding: 12px 16px; margin-bottom: 24px; border-radius: 8px; background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); color: var(--q-success);">
              <span class="qa-text-sm qa-font-medium">{flash_message}</span>
            </div>
          </q:if>

          <!-- Stats Row -->
          <div class="qa-grid qa-grid-4 qa-mb-6">
            <div class="qa-stat-card">
              <div class="qa-stat-label">Total Apps</div>
              <div class="qa-stat-value">{total_apps}</div>
            </div>
            <div class="qa-stat-card">
              <div class="qa-stat-label">Active</div>
              <div class="qa-stat-value">{total_active}</div>
            </div>
            <div class="qa-stat-card">
              <div class="qa-stat-label">Running</div>
              <div class="qa-stat-value">{total_running}</div>
            </div>
            <div class="qa-stat-card">
              <div class="qa-stat-label">Connectors</div>
              <div class="qa-stat-value">{total_connectors}</div>
            </div>
          </div>

          <!-- Search + Create Row -->
          <div style="display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap;">
            <!-- Search -->
            <form method="GET" action="/admin/applications" style="flex: 1; min-width: 200px;">
              <div class="qa-search-bar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                <input type="text" name="search" placeholder="Search applications..." value="{search_term}" />
              </div>
            </form>
          </div>

          <!-- New Application — card form -->
          <div class="qa-card qa-mb-6">
            <div class="qa-card-header">
              <div>
                <div class="qa-card-title">New Application</div>
                <div class="qa-card-subtitle">Create a new Quantum project</div>
              </div>
            </div>
            <div class="qa-card-body">
              <form method="POST" action="/admin/applications">
                <input type="hidden" name="action" value="createProject" />
                <div class="qa-form-row qa-mb-4">
                  <div class="qa-form-group">
                    <label class="qa-label">Name</label>
                    <input type="text" name="name" class="qa-input" placeholder="my-app" required="" minlength="2" />
                    <div class="qa-input-hint">Unique identifier for the application</div>
                  </div>
                  <div class="qa-form-group">
                    <label class="qa-label">Source Path</label>
                    <input type="text" name="source_path" class="qa-input" placeholder="projects/my-app (optional)" />
                    <div class="qa-input-hint">Defaults to projects/{name}</div>
                  </div>
                </div>
                <div class="qa-form-group qa-mb-4">
                  <label class="qa-label">Description</label>
                  <input type="text" name="description" class="qa-input" placeholder="Brief description of the application" />
                </div>
                <button type="submit" class="qa-btn qa-btn-primary">Create Application</button>
              </form>
            </div>
          </div>

          <!-- Application List -->
          <q:if condition="{total_displayed} != '0'">
            <div class="qa-card qa-mb-6">
              <div class="qa-card-body" style="padding: 0;">
                <q:loop type="array" var="proj" items="{projects}">
                  <a href="/admin/app/{proj.name}" class="qa-app-card">

                    <!-- Icon -->
                    <div class="qa-app-card-icon">{proj.initial}</div>

                    <!-- Name + status + description -->
                    <div style="flex: 1; min-width: 0;">
                      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 2px;">
                        <span style="font-weight: 600; color: var(--q-text-primary); font-size: 0.9375rem;">{proj.name}</span>
                        <span class="qa-badge {proj.status_badge}" style="font-size: 0.65rem;">{proj.status}</span>
                        <span class="{proj.runtime_badge}">{proj.runtime_label}</span>
                      </div>
                      <div style="display: flex; align-items: center; gap: 10px;">
                        <span class="qa-font-mono qa-text-xs qa-text-muted">{proj.source_path}</span>
                        <span class="qa-text-xs qa-text-muted qa-truncate" style="max-width: 300px;">{proj.description}</span>
                      </div>
                    </div>

                    <!-- Metrics -->
                    <div class="qa-app-metrics">
                      <div class="qa-app-metric">
                        <span class="qa-app-metric-value">{proj.component_count}</span>
                        <span class="qa-app-metric-label">Comps</span>
                      </div>
                      <div class="qa-app-metric">
                        <span class="qa-app-metric-value">{proj.connector_count}</span>
                        <span class="qa-app-metric-label">Conns</span>
                      </div>
                      <div class="qa-app-metric">
                        <span class="qa-app-metric-value">{proj.port}</span>
                        <span class="qa-app-metric-label">Port</span>
                      </div>
                    </div>

                    <!-- Delete -->
                    <form method="POST" action="/admin/applications" style="flex-shrink: 0; margin: 0;" onclick="event.stopPropagation(); event.preventDefault();" onsubmit="event.stopPropagation(); return confirm('Remove this application record? Files on disk will NOT be deleted.');">
                      <input type="hidden" name="action" value="deleteProject" />
                      <input type="hidden" name="project_id" value="{proj.id}" />
                      <button type="submit" class="qa-btn qa-btn-ghost qa-btn-sm" style="color: var(--q-danger); opacity: 0.4;" title="Remove record" onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.4'">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                      </button>
                    </form>

                  </a>
                </q:loop>
              </div>
            </div>
          </q:if>

          <!-- Empty State -->
          <q:if condition="{total_apps} == '0'">
            <div class="qa-card qa-mb-6">
              <div class="qa-empty">
                <div class="qa-empty-icon">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                </div>
                <div class="qa-empty-title">No Applications Found</div>
                <div class="qa-empty-text">Click "Sync from Disk" to discover existing projects, or use the form above to create one.</div>
              </div>
            </div>
          </q:if>

          <!-- No search results -->
          <q:if condition="{search_term} != ''">
            <q:if condition="{total_displayed} == '0'">
              <div class="qa-card qa-mb-6">
                <div class="qa-empty">
                  <div class="qa-empty-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                  </div>
                  <div class="qa-empty-title">No Results</div>
                  <div class="qa-empty-text">No applications match your search. Try a different term or clear the search.</div>
                  <div class="qa-empty-action">
                    <a href="/admin/applications" class="qa-btn qa-btn-secondary qa-btn-sm">Clear Search</a>
                  </div>
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
