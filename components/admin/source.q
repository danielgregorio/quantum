<q:component name="AdminSource">

  <!-- Read and display source code for a given file -->
  <q:python>
import os
import datetime

base = os.getcwd()

# Get file path from query string
file_param = ''
try:
    from flask import request as flask_request
    file_param = flask_request.args.get('file', '')
except:
    pass

q.file_path = file_param
q.file_content = ''
q.file_found = 'no'
q.line_count = '0'
q.file_size = '-'
q.file_modified = '-'
q.file_type = '-'
q.file_type_badge = 'qa-badge-info'
q.error_message = ''

if file_param:
    # Security: prevent directory traversal
    normalized = os.path.normpath(file_param)
    if '..' in normalized or normalized.startswith('/') or normalized.startswith('\\'):
        q.error_message = 'Invalid file path: directory traversal not allowed'
    else:
        full_path = os.path.join(base, normalized)
        # Ensure the resolved path is within project root
        real_base = os.path.realpath(base)
        real_path = os.path.realpath(full_path)
        if not real_path.startswith(real_base):
            q.error_message = 'Invalid file path: outside project root'
        elif not os.path.isfile(full_path):
            q.error_message = f'File not found: {file_param}'
        else:
            q.file_found = 'yes'

            # Detect file type
            ext = os.path.splitext(file_param)[1].lower()
            type_map = {
                '.q': ('Quantum', 'qa-badge-primary'),
                '.py': ('Python', 'qa-badge-success'),
                '.yaml': ('YAML', 'qa-badge-warning'),
                '.yml': ('YAML', 'qa-badge-warning'),
                '.json': ('JSON', 'qa-badge-info'),
                '.html': ('HTML', 'qa-badge-danger'),
                '.css': ('CSS', 'qa-badge-info'),
                '.js': ('JavaScript', 'qa-badge-warning'),
                '.md': ('Markdown', 'qa-badge-info'),
                '.txt': ('Text', 'qa-badge-info'),
            }
            ft, fb = type_map.get(ext, ('Unknown', 'qa-badge-info'))
            q.file_type = ft
            q.file_type_badge = fb

            # File metadata
            file_size = os.path.getsize(full_path)
            if file_size >= 1048576:
                q.file_size = f"{file_size / 1048576:.1f} MB"
            elif file_size >= 1024:
                q.file_size = f"{file_size / 1024:.1f} KB"
            else:
                q.file_size = f"{file_size} B"

            try:
                mtime = os.path.getmtime(full_path)
                dt = datetime.datetime.fromtimestamp(mtime)
                q.file_modified = dt.strftime('%Y-%m-%d %H:%M')
            except:
                pass

            # Read raw content — renderer will HTML-escape it
            try:
                with open(full_path, 'r', encoding='utf-8', errors='replace') as fh:
                    raw = fh.read()
                lines = raw.split('\n')
                q.line_count = str(len(lines))
                q.file_content = raw
            except Exception as e:
                q.error_message = f'Error reading file: {str(e)[:100]}'
                q.file_found = 'no'
else:
    q.error_message = 'No file specified. Use ?file=path/to/file in the URL.'
  </q:python>

  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Source: {file_path} - Quantum Admin</title>
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
          <h1 class="qa-header-title" style="font-size: 1.1rem;"><span class="qa-font-mono">{file_path}</span></h1>
          <div class="qa-header-actions">
            <span class="qa-badge {file_type_badge}">{file_type}</span>
            <a href="javascript:history.back()" style="color: var(--q-primary-400); text-decoration: none; font-size: 0.875rem; margin-left: 12px;">Back</a>
          </div>
        </header>

        <!-- Content -->
        <div class="qa-content">

          <!-- File metadata bar -->
          <q:if condition="{file_found} == 'yes'">
            <div class="qa-flex qa-items-center qa-mb-4" style="gap: 24px;">
              <span class="qa-text-sm qa-text-muted">{line_count} lines</span>
              <span class="qa-text-sm qa-text-muted">{file_size}</span>
              <span class="qa-text-sm qa-text-muted">Modified {file_modified}</span>
            </div>

            <!-- Source code display -->
            <div class="qa-card">
              <div class="qa-card-body qa-p-0">
                <div class="qa-source-viewer">
                  <div class="qa-source-gutter" id="sourceGutter"></div>
                  <pre class="qa-source-code" id="sourceCode">{file_content}</pre>
                </div>
              </div>
            </div>
            <script src="/static/quantum-source-highlight.js"></script>
          </q:if>

          <!-- Error state -->
          <q:if condition="{file_found} != 'yes'">
            <div class="qa-card">
              <div class="qa-card-body" style="text-align: center; padding: 48px 24px;">
                <div style="font-size: 3rem; margin-bottom: 16px; opacity: 0.3;">
                  <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="display: inline-block;"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>
                </div>
                <div class="qa-text-lg qa-font-medium qa-text-primary" style="margin-bottom: 8px;">Cannot Display Source</div>
                <div class="qa-text-sm qa-text-muted">{error_message}</div>
                <div style="margin-top: 24px;">
                  <a href="javascript:history.back()" style="color: var(--q-primary-400); text-decoration: none;">Go Back</a>
                </div>
              </div>
            </div>
          </q:if>

        </div>
      </main>

    </div>
  </body>
  </html>
</q:component>
