<q:component name="AdminDashboard">

  <!-- Collect real metrics from the project -->
  <q:python>
import os

base = os.getcwd()

# Count .q components
comp_dir = os.path.join(base, 'components')
comp_files = []
for root, dirs, files in os.walk(comp_dir):
    for f in files:
        if f.endswith('.q'):
            rel = os.path.relpath(os.path.join(root, f), comp_dir).replace('\\', '/')
            comp_files.append(rel)
q.component_count = len(comp_files)
q.component_list = sorted(comp_files)

# Count features
feat_dir = os.path.join(base, 'src', 'core', 'features')
features = []
if os.path.isdir(feat_dir):
    for entry in sorted(os.listdir(feat_dir)):
        full = os.path.join(feat_dir, entry)
        if os.path.isdir(full) and not entry.startswith('_'):
            features.append(entry)
q.feature_count = len(features)
q.feature_list = features

# Count test files
test_dir = os.path.join(base, 'tests')
test_count = 0
for root, dirs, files in os.walk(test_dir):
    for f in files:
        if f.startswith('test_') and f.endswith('.py'):
            test_count += 1
q.test_count = test_count

# Count modular parsers
parser_dir = os.path.join(base, 'src', 'core', 'parsers')
parser_count = 0
if os.path.isdir(parser_dir):
    for root, dirs, files in os.walk(parser_dir):
        for f in files:
            if f.endswith('_parser.py') and f != 'base.py':
                parser_count += 1
q.parser_count = parser_count

# Count modular executors
exec_dir = os.path.join(base, 'src', 'runtime', 'executors')
executor_count = 0
if os.path.isdir(exec_dir):
    for root, dirs, files in os.walk(exec_dir):
        for f in files:
            if f.endswith('_executor.py') and f != 'base.py':
                executor_count += 1
q.executor_count = executor_count

# Count examples
ex_dir = os.path.join(base, 'examples')
example_count = 0
if os.path.isdir(ex_dir):
    for root, dirs, files in os.walk(ex_dir):
        for f in files:
            if f.endswith('.q'):
                example_count += 1
q.example_count = example_count
  </q:python>

  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Dashboard - Quantum Admin</title>
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
            <a href="/admin/dashboard" class="qa-sidebar-link active">
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
          <h1 class="qa-header-title">Dashboard</h1>
          <div class="qa-header-actions">
            <div class="qa-header-status">
              <span class="qa-header-status-dot"></span>
              Server Running
            </div>
          </div>
        </header>

        <!-- Content -->
        <div class="qa-content">

          <!-- Stat Cards -->
          <div class="qa-grid qa-grid-4 qa-mb-6">
            <div class="qa-stat-card">
              <div class="qa-stat-label">Components</div>
              <div class="qa-stat-value">{component_count}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">.q files in components/</span>
              </div>
            </div>

            <div class="qa-stat-card">
              <div class="qa-stat-label">Features</div>
              <div class="qa-stat-value">{feature_count}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">registered in core/features/</span>
              </div>
            </div>

            <div class="qa-stat-card">
              <div class="qa-stat-label">Test Files</div>
              <div class="qa-stat-value">{test_count}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">test_*.py in tests/</span>
              </div>
            </div>

            <div class="qa-stat-card">
              <div class="qa-stat-label">Examples</div>
              <div class="qa-stat-value">{example_count}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">.q files in examples/</span>
              </div>
            </div>
          </div>

          <!-- Architecture Stats -->
          <div class="qa-grid qa-grid-2 qa-mb-6">
            <div class="qa-stat-card">
              <div class="qa-flex qa-items-center qa-justify-between">
                <div>
                  <div class="qa-stat-label">Modular Parsers</div>
                  <div class="qa-stat-value">{parser_count}</div>
                </div>
                <div class="qa-stat-icon" style="background: rgba(168, 85, 247, 0.15); color: #c084fc;">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
                </div>
              </div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">in src/core/parsers/</span>
              </div>
            </div>

            <div class="qa-stat-card">
              <div class="qa-flex qa-items-center qa-justify-between">
                <div>
                  <div class="qa-stat-label">Modular Executors</div>
                  <div class="qa-stat-value">{executor_count}</div>
                </div>
                <div class="qa-stat-icon" style="background: rgba(34, 197, 94, 0.15); color: #4ade80;">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                </div>
              </div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">in src/runtime/executors/</span>
              </div>
            </div>
          </div>

          <!-- Detail Cards -->
          <div class="qa-grid qa-grid-2">

            <!-- Components List -->
            <div class="qa-card">
              <div class="qa-card-header">
                <div>
                  <div class="qa-card-title">Project Components</div>
                  <div class="qa-card-subtitle">{component_count} .q files</div>
                </div>
                <span class="qa-badge qa-badge-primary">.q</span>
              </div>
              <div class="qa-card-body" style="max-height: 360px; overflow-y: auto;">
                <q:loop type="array" var="comp" items="{component_list}">
                  <div class="qa-activity-item">
                    <div class="qa-activity-icon" style="background: rgba(168, 85, 247, 0.15); color: #c084fc;">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>
                    </div>
                    <div>
                      <div class="qa-text-sm qa-font-medium qa-text-primary">{comp}</div>
                    </div>
                  </div>
                </q:loop>
              </div>
            </div>

            <!-- Features List -->
            <div class="qa-card">
              <div class="qa-card-header">
                <div>
                  <div class="qa-card-title">Registered Features</div>
                  <div class="qa-card-subtitle">{feature_count} feature modules</div>
                </div>
                <span class="qa-badge qa-badge-success">Option C</span>
              </div>
              <div class="qa-card-body" style="max-height: 360px; overflow-y: auto;">
                <q:loop type="array" var="feat" items="{feature_list}">
                  <div class="qa-activity-item">
                    <div class="qa-activity-icon" style="background: rgba(34, 197, 94, 0.15); color: #4ade80;">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                    </div>
                    <div>
                      <div class="qa-text-sm qa-font-medium qa-text-primary">{feat}</div>
                    </div>
                  </div>
                </q:loop>
              </div>
            </div>

          </div>

        </div>
      </main>

    </div>
  </body>
  </html>
</q:component>
