<q:component name="AdminDatabase">

  <!-- Collect database information -->
  <q:python>
import os
import sqlite3
import datetime
import yaml

base = os.getcwd()
skip_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.claude'}

# Find all .db files
db_files = []
total_tables = 0

for root, dirs, files in os.walk(base):
    dirs[:] = [d for d in dirs if d not in skip_dirs]
    for f in files:
        if f.endswith('.db') and not f.endswith('-journal'):
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, base).replace('\\', '/')

            # File metadata
            file_size = os.path.getsize(full_path)
            if file_size >= 1048576:
                size_str = f"{file_size / 1048576:.1f} MB"
            elif file_size >= 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size} B"

            try:
                mtime = os.path.getmtime(full_path)
                dt = datetime.datetime.fromtimestamp(mtime)
                modified = dt.strftime('%Y-%m-%d %H:%M')
            except:
                modified = '-'

            # Introspect tables
            tables = []
            db_error = ''
            try:
                conn = sqlite3.connect(full_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                for row in cursor.fetchall():
                    table_name = row[0]
                    try:
                        cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                        row_count = cursor.fetchone()[0]
                    except:
                        row_count = 0
                    tables.append({
                        'name': table_name,
                        'rows': str(row_count),
                    })
                conn.close()
            except Exception as e:
                db_error = str(e)[:80]

            total_tables += len(tables)

            db_files.append({
                'path': rel_path,
                'size': size_str,
                'modified': modified,
                'tables': tables,
                'table_count': str(len(tables)),
                'error': db_error,
            })

# Check for configured datasources
config_path = os.path.join(base, 'quantum.config.yaml')
datasources = []
if os.path.isfile(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as fh:
            cfg = yaml.safe_load(fh) or {}
        ds = cfg.get('datasources', {})
        for name, config in ds.items():
            datasources.append({
                'name': name,
                'driver': str(config.get('driver', '-')),
                'database': str(config.get('database', '-')),
            })
    except:
        pass

q.db_files = db_files
q.total_dbs = str(len(db_files))
q.total_tables = str(total_tables)
q.datasources = datasources
q.total_datasources = str(len(datasources))
q.has_dbs = 'yes' if db_files else 'no'
  </q:python>

  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Database - Quantum Admin</title>
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
            <a href="/admin/database" class="qa-sidebar-link active">
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
          <h1 class="qa-header-title">Database</h1>
          <div class="qa-header-actions">
            <span class="qa-badge qa-badge-primary">SQLite</span>
          </div>
        </header>

        <!-- Content -->
        <div class="qa-content">

          <!-- Stat Cards -->
          <div class="qa-grid qa-grid-3 qa-mb-6">
            <div class="qa-stat-card">
              <div class="qa-stat-label">Database Files</div>
              <div class="qa-stat-value">{total_dbs}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">.db files discovered</span>
              </div>
            </div>

            <div class="qa-stat-card">
              <div class="qa-stat-label">Total Tables</div>
              <div class="qa-stat-value">{total_tables}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">across all databases</span>
              </div>
            </div>

            <div class="qa-stat-card">
              <div class="qa-stat-label">Datasources</div>
              <div class="qa-stat-value">{total_datasources}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">configured in YAML</span>
              </div>
            </div>
          </div>

          <!-- Database Cards -->
          <q:if condition="{has_dbs} == 'yes'">
            <q:loop type="array" var="db" items="{db_files}">
              <div class="qa-card qa-mb-4">
                <div class="qa-card-header">
                  <div>
                    <div class="qa-card-title"><span class="qa-font-mono">{db.path}</span></div>
                    <div class="qa-card-subtitle">{db.size} | Modified {db.modified} | {db.table_count} tables</div>
                  </div>
                  <span class="qa-badge qa-badge-success">SQLite</span>
                </div>
                <div class="qa-card-body qa-p-0">
                  <table class="qa-table">
                    <thead>
                      <tr>
                        <th>Table Name</th>
                        <th>Row Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      <q:loop type="array" var="tbl" items="{db.tables}">
                        <tr>
                          <td><span class="qa-font-mono">{tbl.name}</span></td>
                          <td>{tbl.rows}</td>
                        </tr>
                      </q:loop>
                    </tbody>
                  </table>
                </div>
              </div>
            </q:loop>
          </q:if>

          <!-- Datasource Config -->
          <q:if condition="{total_datasources} != '0'">
            <div class="qa-card qa-mb-4">
              <div class="qa-card-header">
                <div>
                  <div class="qa-card-title">Configured Datasources</div>
                  <div class="qa-card-subtitle">From quantum.config.yaml</div>
                </div>
              </div>
              <div class="qa-card-body qa-p-0">
                <table class="qa-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Driver</th>
                      <th>Database</th>
                    </tr>
                  </thead>
                  <tbody>
                    <q:loop type="array" var="ds" items="{datasources}">
                      <tr>
                        <td><span class="qa-font-mono">{ds.name}</span></td>
                        <td><span class="qa-badge qa-badge-info">{ds.driver}</span></td>
                        <td><span class="qa-font-mono">{ds.database}</span></td>
                      </tr>
                    </q:loop>
                  </tbody>
                </table>
              </div>
            </div>
          </q:if>

          <!-- Empty State -->
          <q:if condition="{has_dbs} != 'yes'">
            <q:if condition="{total_datasources} == '0'">
              <div class="qa-card">
                <div class="qa-card-body" style="text-align: center; padding: 48px 24px;">
                  <div style="font-size: 3rem; margin-bottom: 16px; opacity: 0.3;">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="display: inline-block;"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                  </div>
                  <div class="qa-text-lg qa-font-medium qa-text-primary" style="margin-bottom: 8px;">No Databases Found</div>
                  <div class="qa-text-sm qa-text-muted">No .db files were found in the project. Databases will appear here when created via q:query or other data operations.</div>
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
