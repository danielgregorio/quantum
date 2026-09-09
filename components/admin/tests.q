<q:component name="AdminTests">

  <!-- Collect test data from the filesystem -->
  <q:python>
import os
import re

base = os.getcwd()
test_dir = os.path.join(base, 'tests')

test_files = []
dir_stats = {}
total_functions = 0

if os.path.isdir(test_dir):
    for root, dirs, files in os.walk(test_dir):
        for f in files:
            if f.startswith('test_') and f.endswith('.py'):
                full_path = os.path.join(root, f)
                rel = os.path.relpath(full_path, test_dir).replace('\\', '/')
                group = os.path.relpath(root, test_dir).replace('\\', '/')
                if group == '.':
                    group = 'root'

                # Count test functions
                func_count = 0
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as fh:
                        for line in fh:
                            if re.match(r'\s*def test_', line):
                                func_count += 1
                except:
                    pass

                total_functions += func_count

                if group not in dir_stats:
                    dir_stats[group] = {'files': 0, 'functions': 0}
                dir_stats[group]['files'] += 1
                dir_stats[group]['functions'] += func_count

                test_files.append({
                    'path': rel,
                    'functions': str(func_count),
                    'directory': group,
                })

test_files.sort(key=lambda x: x['path'])

# Build directory breakdown list
dir_list = []
for d in sorted(dir_stats.keys()):
    dir_list.append({
        'name': d,
        'files': str(dir_stats[d]['files']),
        'functions': str(dir_stats[d]['functions']),
    })

q.test_files = test_files
q.dir_list = dir_list
q.total_files = str(len(test_files))
q.total_functions = str(total_functions)
q.total_dirs = str(len(dir_stats))
  </q:python>

  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Tests - Quantum Admin</title>
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
          <h1 class="qa-header-title">Tests</h1>
          <div class="qa-header-actions">
            <span class="qa-badge qa-badge-success">pytest</span>
          </div>
        </header>

        <!-- Content -->
        <div class="qa-content">

          <!-- Stat Cards -->
          <div class="qa-grid qa-grid-3 qa-mb-6">
            <div class="qa-stat-card">
              <div class="qa-stat-label">Test Files</div>
              <div class="qa-stat-value">{total_files}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">test_*.py files</span>
              </div>
            </div>

            <div class="qa-stat-card">
              <div class="qa-stat-label">Test Functions</div>
              <div class="qa-stat-value">{total_functions}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">def test_ definitions</span>
              </div>
            </div>

            <div class="qa-stat-card">
              <div class="qa-stat-label">Directories</div>
              <div class="qa-stat-value">{total_dirs}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">test groups</span>
              </div>
            </div>
          </div>

          <!-- Directory Breakdown -->
          <div class="qa-card qa-mb-6">
            <div class="qa-card-header">
              <div>
                <div class="qa-card-title">Directory Breakdown</div>
                <div class="qa-card-subtitle">Tests organized by directory</div>
              </div>
            </div>
            <div class="qa-card-body">
              <div class="qa-grid qa-grid-3">
                <q:loop type="array" var="dir" items="{dir_list}">
                  <div style="background: var(--q-bg-overlay); border-radius: 8px; padding: 16px; border: 1px solid var(--q-border);">
                    <div class="qa-text-sm qa-text-muted" style="margin-bottom: 4px;">{dir.name}</div>
                    <div class="qa-flex qa-items-center" style="gap: 12px;">
                      <div>
                        <span style="font-size: 1.25rem; font-weight: 700; color: var(--q-text-primary);">{dir.files}</span>
                        <span class="qa-text-sm qa-text-muted"> files</span>
                      </div>
                      <div>
                        <span style="font-size: 1.25rem; font-weight: 700; color: var(--q-primary-400);">{dir.functions}</span>
                        <span class="qa-text-sm qa-text-muted"> tests</span>
                      </div>
                    </div>
                  </div>
                </q:loop>
              </div>
            </div>
          </div>

          <!-- Tests Table -->
          <div class="qa-card">
            <div class="qa-card-header">
              <div>
                <div class="qa-card-title">All Test Files</div>
                <div class="qa-card-subtitle">{total_files} files with {total_functions} test functions</div>
              </div>
            </div>
            <div class="qa-card-body qa-p-0">
              <table class="qa-table">
                <thead>
                  <tr>
                    <th>File Path</th>
                    <th>Functions</th>
                    <th>Directory</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <q:loop type="array" var="test" items="{test_files}">
                    <tr>
                      <td><span class="qa-font-mono">{test.path}</span></td>
                      <td>{test.functions}</td>
                      <td><span class="qa-badge qa-badge-info">{test.directory}</span></td>
                      <td><a href="/admin/source?file=tests/{test.path}" style="color: var(--q-primary-400); text-decoration: none; font-size: 0.8125rem;">View Source</a></td>
                    </tr>
                  </q:loop>
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </main>

    </div>
  </body>
  </html>
</q:component>
