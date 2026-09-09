<q:component name="AdminJobs">

  <!-- Collect job data from quantum_jobs.db -->
  <q:python>
import os
import sqlite3

base = os.getcwd()

# Try multiple possible DB locations
db_paths = [
    os.path.join(base, 'quantum_jobs.db'),
    os.path.join(base, 'src', 'quantum_jobs.db'),
]

db_path = None
for p in db_paths:
    if os.path.isfile(p):
        db_path = p
        break

q.db_found = 'yes' if db_path else 'no'
q.pending_count = '0'
q.running_count = '0'
q.completed_count = '0'
q.failed_count = '0'
q.total_jobs = '0'
q.jobs = []

if db_path:
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Count by status
        cursor.execute("SELECT status, COUNT(*) as cnt FROM quantum_jobs GROUP BY status")
        for row in cursor.fetchall():
            s = row['status']
            c = str(row['cnt'])
            if s == 'pending':
                q.pending_count = c
            elif s == 'running':
                q.running_count = c
            elif s == 'completed':
                q.completed_count = c
            elif s == 'failed':
                q.failed_count = c

        # Total
        cursor.execute("SELECT COUNT(*) as cnt FROM quantum_jobs")
        q.total_jobs = str(cursor.fetchone()['cnt'])

        # Recent 50 jobs
        cursor.execute("""
            SELECT id, name, queue, status, attempts, max_attempts,
                   created_at, error
            FROM quantum_jobs
            ORDER BY id DESC
            LIMIT 50
        """)
        jobs = []
        for row in cursor.fetchall():
            status = row['status'] or 'unknown'
            if status == 'completed':
                badge_class = 'qa-badge-success'
            elif status == 'running':
                badge_class = 'qa-badge-info'
            elif status == 'pending':
                badge_class = 'qa-badge-warning'
            elif status == 'failed':
                badge_class = 'qa-badge-danger'
            else:
                badge_class = 'qa-badge-info'

            error_text = row['error'] or '-'
            if len(error_text) > 60:
                error_text = error_text[:60] + '...'

            jobs.append({
                'id': str(row['id']),
                'name': row['name'] or '-',
                'queue': row['queue'] or 'default',
                'status': status,
                'badge_class': badge_class,
                'attempts': f"{row['attempts']}/{row['max_attempts']}",
                'created_at': row['created_at'] or '-',
                'error': error_text,
            })
        q.jobs = jobs
        conn.close()
    except Exception as e:
        q.db_found = 'error'
        q.jobs = []
  </q:python>

  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Jobs - Quantum Admin</title>
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
            <a href="/admin/jobs" class="qa-sidebar-link active">
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
          <h1 class="qa-header-title">Jobs</h1>
          <div class="qa-header-actions">
            <q:if condition="{db_found} == 'yes'">
              <span class="qa-badge qa-badge-success">DB Connected</span>
            </q:if>
            <q:if condition="{db_found} != 'yes'">
              <span class="qa-badge qa-badge-warning">DB Not Found</span>
            </q:if>
          </div>
        </header>

        <!-- Content -->
        <div class="qa-content">

          <!-- Stat Cards -->
          <div class="qa-grid qa-grid-4 qa-mb-6">
            <div class="qa-stat-card">
              <div class="qa-stat-label">Pending</div>
              <div class="qa-stat-value" style="color: var(--q-warning);">{pending_count}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">waiting in queue</span>
              </div>
            </div>

            <div class="qa-stat-card">
              <div class="qa-stat-label">Running</div>
              <div class="qa-stat-value" style="color: var(--q-info);">{running_count}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">currently executing</span>
              </div>
            </div>

            <div class="qa-stat-card">
              <div class="qa-stat-label">Completed</div>
              <div class="qa-stat-value" style="color: var(--q-success);">{completed_count}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">finished successfully</span>
              </div>
            </div>

            <div class="qa-stat-card">
              <div class="qa-stat-label">Failed</div>
              <div class="qa-stat-value" style="color: var(--q-danger);">{failed_count}</div>
              <div class="qa-stat-change">
                <span class="qa-text-muted">errored out</span>
              </div>
            </div>
          </div>

          <!-- Jobs Table or Empty State -->
          <q:if condition="{db_found} == 'yes'">
            <div class="qa-card">
              <div class="qa-card-header">
                <div>
                  <div class="qa-card-title">Recent Jobs</div>
                  <div class="qa-card-subtitle">{total_jobs} total jobs (showing last 50)</div>
                </div>
              </div>
              <div class="qa-card-body qa-p-0">
                <table class="qa-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Name</th>
                      <th>Queue</th>
                      <th>Status</th>
                      <th>Attempts</th>
                      <th>Created</th>
                      <th>Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    <q:loop type="array" var="job" items="{jobs}">
                      <tr>
                        <td><span class="qa-font-mono">{job.id}</span></td>
                        <td>{job.name}</td>
                        <td><span class="qa-badge qa-badge-info">{job.queue}</span></td>
                        <td><span class="qa-badge {job.badge_class}">{job.status}</span></td>
                        <td>{job.attempts}</td>
                        <td><span class="qa-text-sm qa-text-muted">{job.created_at}</span></td>
                        <td><span class="qa-text-sm qa-text-muted">{job.error}</span></td>
                      </tr>
                    </q:loop>
                  </tbody>
                </table>
              </div>
            </div>
          </q:if>

          <q:if condition="{db_found} != 'yes'">
            <div class="qa-card">
              <div class="qa-card-body" style="text-align: center; padding: 48px 24px;">
                <div style="font-size: 3rem; margin-bottom: 16px; opacity: 0.3;">
                  <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="display: inline-block;"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                </div>
                <div class="qa-text-lg qa-font-medium qa-text-primary" style="margin-bottom: 8px;">No Job Database Found</div>
                <div class="qa-text-sm qa-text-muted">The quantum_jobs.db file was not found. Jobs will appear here when the scheduler creates them.</div>
              </div>
            </div>
          </q:if>

        </div>
      </main>

    </div>
  </body>
  </html>
</q:component>
