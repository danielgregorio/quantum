<q:component name="AdminSettings">

  <!-- Action: Save settings to quantum.config.yaml -->
  <q:action name="saveSettings" method="POST">
    <q:param name="port" type="string" required="true" />
    <q:param name="host" type="string" required="true" />
    <q:param name="debug" type="string" />
    <q:param name="reload" type="string" />
    <q:param name="cache_enabled" type="string" />
    <q:param name="cache_ttl" type="string" />
    <q:param name="log_level" type="string" />
    <q:param name="xss_protection" type="string" />
    <q:param name="cors_enabled" type="string" />

    <q:python>
import os
import yaml

base = os.getcwd()
config_path = os.path.join(base, 'quantum.config.yaml')

# Read existing config
cfg = {}
if os.path.isfile(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as fh:
            cfg = yaml.safe_load(fh) or {}
    except:
        pass

# Ensure sections exist
if 'server' not in cfg:
    cfg['server'] = {}
if 'performance' not in cfg:
    cfg['performance'] = {}
if 'security' not in cfg:
    cfg['security'] = {}
if 'logging' not in cfg:
    cfg['logging'] = {}

# Update values from form
try:
    port_val = int(q.form.get('port', '8080'))
    if port_val &lt; 1 or port_val &gt; 65535:
        port_val = 8080
except:
    port_val = 8080
cfg['server']['port'] = port_val
cfg['server']['host'] = q.form.get('host', '0.0.0.0')
cfg['server']['debug'] = q.form.get('debug', '') == 'on'
cfg['server']['reload'] = q.form.get('reload', '') == 'on'

cfg['performance']['cache_templates'] = q.form.get('cache_enabled', '') == 'on'
try:
    cfg['performance']['cache_ttl'] = int(q.form.get('cache_ttl', '300'))
except:
    pass

cfg['logging']['level'] = q.form.get('log_level', 'INFO')
cfg['security']['xss_protection'] = q.form.get('xss_protection', '') == 'on'
cfg['security']['cors_enabled'] = q.form.get('cors_enabled', '') == 'on'

# Write config
try:
    with open(config_path, 'w', encoding='utf-8') as fh:
        yaml.dump(cfg, fh, default_flow_style=False, sort_keys=False)
except Exception as e:
    pass
    </q:python>

    <q:redirect url="/admin/settings" flash="Settings saved successfully." flashType="success" />
  </q:action>

  <!-- Collect settings from quantum.config.yaml and runtime info -->
  <q:python>
import os
import sys
import platform
import yaml

base = os.getcwd()
config_path = os.path.join(base, 'quantum.config.yaml')

q.config_found = 'no'

# Defaults
q.server_port = '-'
q.server_host = '-'
q.server_reload = '-'
q.server_debug = '-'
q.server_reload_badge = 'qa-badge-info'
q.server_debug_badge = 'qa-badge-info'

q.paths_components = '-'
q.paths_static = '-'
q.paths_logs = '-'

q.perf_cache = '-'
q.perf_ttl = '-'
q.perf_max_size = '-'
q.perf_cache_badge = 'qa-badge-info'

q.sec_xss = '-'
q.sec_max_upload = '-'
q.sec_cors = '-'
q.sec_xss_badge = 'qa-badge-info'
q.sec_cors_badge = 'qa-badge-info'

q.llm_base_url = '-'
q.llm_model = '-'
q.llm_timeout = '-'

q.log_level = '-'
q.log_console = '-'
q.log_file = '-'
q.log_console_badge = 'qa-badge-info'
q.log_file_badge = 'qa-badge-info'

if os.path.isfile(config_path):
    q.config_found = 'yes'
    try:
        with open(config_path, 'r', encoding='utf-8') as fh:
            cfg = yaml.safe_load(fh) or {}

        # Server
        srv = cfg.get('server', {})
        q.server_port = str(srv.get('port', 8080))
        q.server_host = str(srv.get('host', '0.0.0.0'))
        reload_val = srv.get('reload', False)
        debug_val = srv.get('debug', False)
        q.server_reload = str(reload_val)
        q.server_debug = str(debug_val)
        q.server_reload_badge = 'qa-badge-success' if reload_val else 'qa-badge-danger'
        q.server_debug_badge = 'qa-badge-success' if debug_val else 'qa-badge-danger'

        # Paths
        paths = cfg.get('paths', {})
        q.paths_components = str(paths.get('components', './components'))
        q.paths_static = str(paths.get('static', './static'))
        q.paths_logs = str(paths.get('logs', './logs'))

        # Performance
        perf = cfg.get('performance', {})
        cache_val = perf.get('cache_templates', False)
        q.perf_cache = str(cache_val)
        q.perf_cache_badge = 'qa-badge-success' if cache_val else 'qa-badge-danger'
        q.perf_ttl = str(perf.get('cache_ttl', 0)) + 's'
        q.perf_max_size = str(perf.get('cache_max_size', 0))

        # Security
        sec = cfg.get('security', {})
        xss_val = sec.get('xss_protection', False)
        cors_val = sec.get('cors_enabled', False)
        q.sec_xss = str(xss_val)
        q.sec_xss_badge = 'qa-badge-success' if xss_val else 'qa-badge-danger'
        q.sec_cors = str(cors_val)
        q.sec_cors_badge = 'qa-badge-success' if cors_val else 'qa-badge-danger'
        max_upload = sec.get('max_content_length', 0)
        if max_upload >= 1048576:
            q.sec_max_upload = f"{max_upload // 1048576} MB"
        elif max_upload >= 1024:
            q.sec_max_upload = f"{max_upload // 1024} KB"
        else:
            q.sec_max_upload = str(max_upload) + ' B'

        # LLM
        llm = cfg.get('llm', {})
        q.llm_base_url = str(llm.get('base_url', '-'))
        q.llm_model = str(llm.get('default_model', '-'))
        q.llm_timeout = str(llm.get('timeout', 60)) + 's'

        # Logging
        log = cfg.get('logging', {})
        q.log_level = str(log.get('level', 'INFO'))
        console_val = log.get('console', False)
        file_val = log.get('file', False)
        q.log_console = str(console_val)
        q.log_file = str(file_val)
        q.log_console_badge = 'qa-badge-success' if console_val else 'qa-badge-danger'
        q.log_file_badge = 'qa-badge-success' if file_val else 'qa-badge-danger'

    except Exception as e:
        q.config_found = 'error'

# Runtime info
q.python_version = sys.version.split()[0]
q.platform_info = platform.platform()
q.cwd = os.getcwd().replace('\\', '/')

# Count parsers and executors
parser_dir = os.path.join(base, 'src', 'core', 'parsers')
parser_count = 0
if os.path.isdir(parser_dir):
    for root, dirs, files in os.walk(parser_dir):
        for f in files:
            if f.endswith('_parser.py') and f != 'base.py':
                parser_count += 1
q.parser_count = str(parser_count)

exec_dir = os.path.join(base, 'src', 'runtime', 'executors')
executor_count = 0
if os.path.isdir(exec_dir):
    for root, dirs, files in os.walk(exec_dir):
        for f in files:
            if f.endswith('_executor.py') and f != 'base.py':
                executor_count += 1
q.executor_count = str(executor_count)

# Flash message from query string (after redirect)
q.flash_message = ''
q.flash_type = 'success'
try:
    from flask import request as flask_request
    q.flash_message = flask_request.args.get('flash', '')
    q.flash_type = flask_request.args.get('flashType', 'success')
except:
    pass
  </q:python>

  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Settings - Quantum Admin</title>
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
            <a href="/admin/settings" class="qa-sidebar-link active">
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
          <h1 class="qa-header-title">Settings</h1>
          <div class="qa-header-actions">
            <q:if condition="{config_found} == 'yes'">
              <span class="qa-badge qa-badge-success">quantum.config.yaml found</span>
            </q:if>
            <q:if condition="{config_found} != 'yes'">
              <span class="qa-badge qa-badge-warning">quantum.config.yaml not found</span>
            </q:if>
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

          <!-- Settings Grid -->
          <div class="qa-grid qa-grid-2 qa-mb-6">

            <!-- Server Card -->
            <div class="qa-card">
              <div class="qa-card-header">
                <div class="qa-card-title">Server</div>
              </div>
              <div class="qa-card-body">
                <div style="display: flex; flex-direction: column; gap: 12px;">
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Port</span>
                    <span class="qa-font-mono">{server_port}</span>
                  </div>
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Host</span>
                    <span class="qa-font-mono">{server_host}</span>
                  </div>
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Auto-Reload</span>
                    <span class="qa-badge {server_reload_badge}">{server_reload}</span>
                  </div>
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Debug Mode</span>
                    <span class="qa-badge {server_debug_badge}">{server_debug}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Paths Card -->
            <div class="qa-card">
              <div class="qa-card-header">
                <div class="qa-card-title">Paths</div>
              </div>
              <div class="qa-card-body">
                <div style="display: flex; flex-direction: column; gap: 12px;">
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Components</span>
                    <span class="qa-font-mono">{paths_components}</span>
                  </div>
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Static</span>
                    <span class="qa-font-mono">{paths_static}</span>
                  </div>
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Logs</span>
                    <span class="qa-font-mono">{paths_logs}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Performance Card -->
            <div class="qa-card">
              <div class="qa-card-header">
                <div class="qa-card-title">Performance</div>
              </div>
              <div class="qa-card-body">
                <div style="display: flex; flex-direction: column; gap: 12px;">
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Cache Enabled</span>
                    <span class="qa-badge {perf_cache_badge}">{perf_cache}</span>
                  </div>
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Cache TTL</span>
                    <span class="qa-font-mono">{perf_ttl}</span>
                  </div>
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Max Cache Size</span>
                    <span class="qa-font-mono">{perf_max_size}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Security Card -->
            <div class="qa-card">
              <div class="qa-card-header">
                <div class="qa-card-title">Security</div>
              </div>
              <div class="qa-card-body">
                <div style="display: flex; flex-direction: column; gap: 12px;">
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">XSS Protection</span>
                    <span class="qa-badge {sec_xss_badge}">{sec_xss}</span>
                  </div>
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Max Upload</span>
                    <span class="qa-font-mono">{sec_max_upload}</span>
                  </div>
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">CORS</span>
                    <span class="qa-badge {sec_cors_badge}">{sec_cors}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- LLM Card -->
            <div class="qa-card">
              <div class="qa-card-header">
                <div class="qa-card-title">LLM</div>
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

            <!-- Logging Card -->
            <div class="qa-card">
              <div class="qa-card-header">
                <div class="qa-card-title">Logging</div>
              </div>
              <div class="qa-card-body">
                <div style="display: flex; flex-direction: column; gap: 12px;">
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Level</span>
                    <span class="qa-badge qa-badge-info">{log_level}</span>
                  </div>
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Console Output</span>
                    <span class="qa-badge {log_console_badge}">{log_console}</span>
                  </div>
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">File Output</span>
                    <span class="qa-badge {log_file_badge}">{log_file}</span>
                  </div>
                </div>
              </div>
            </div>

          </div>

          <!-- Runtime Info -->
          <div class="qa-card qa-mb-6">
            <div class="qa-card-header">
              <div>
                <div class="qa-card-title">Runtime Information</div>
                <div class="qa-card-subtitle">Current server environment</div>
              </div>
            </div>
            <div class="qa-card-body">
              <div class="qa-grid qa-grid-2">
                <div style="display: flex; flex-direction: column; gap: 12px;">
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Python Version</span>
                    <span class="qa-font-mono">{python_version}</span>
                  </div>
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Platform</span>
                    <span class="qa-font-mono">{platform_info}</span>
                  </div>
                </div>
                <div style="display: flex; flex-direction: column; gap: 12px;">
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Working Directory</span>
                    <span class="qa-font-mono">{cwd}</span>
                  </div>
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Modular Parsers</span>
                    <span class="qa-font-mono">{parser_count}</span>
                  </div>
                  <div class="qa-flex qa-items-center qa-justify-between">
                    <span class="qa-text-sm qa-text-muted">Modular Executors</span>
                    <span class="qa-font-mono">{executor_count}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Edit Settings Form -->
          <q:if condition="{config_found} == 'yes'">
            <div class="qa-card">
              <div class="qa-card-header">
                <div>
                  <div class="qa-card-title">Edit Settings</div>
                  <div class="qa-card-subtitle">Modify quantum.config.yaml values</div>
                </div>
              </div>
              <div class="qa-card-body">
                <form method="POST" action="/admin/settings">
                  <div class="qa-grid qa-grid-2" style="gap: 24px;">

                    <!-- Server Settings -->
                    <div>
                      <div class="qa-text-sm qa-font-medium qa-text-primary" style="margin-bottom: 12px;">Server</div>
                      <div style="display: flex; flex-direction: column; gap: 12px;">
                        <div>
                          <label class="qa-text-sm qa-text-muted" style="display: block; margin-bottom: 4px;">Port</label>
                          <input type="number" name="port" value="{server_port}" min="1" max="65535" style="width: 100%; padding: 8px 12px; background: var(--q-bg-overlay); border: 1px solid var(--q-border); border-radius: 6px; color: var(--q-text-primary); font-family: 'SF Mono', monospace; font-size: 0.875rem;" />
                        </div>
                        <div>
                          <label class="qa-text-sm qa-text-muted" style="display: block; margin-bottom: 4px;">Host</label>
                          <input type="text" name="host" value="{server_host}" style="width: 100%; padding: 8px 12px; background: var(--q-bg-overlay); border: 1px solid var(--q-border); border-radius: 6px; color: var(--q-text-primary); font-family: 'SF Mono', monospace; font-size: 0.875rem;" />
                        </div>
                        <div class="qa-flex qa-items-center" style="gap: 8px;">
                          <input type="checkbox" name="debug" id="edit_debug" style="accent-color: var(--q-primary-400);" />
                          <label for="edit_debug" class="qa-text-sm qa-text-muted">Debug Mode</label>
                        </div>
                        <div class="qa-flex qa-items-center" style="gap: 8px;">
                          <input type="checkbox" name="reload" id="edit_reload" style="accent-color: var(--q-primary-400);" />
                          <label for="edit_reload" class="qa-text-sm qa-text-muted">Auto-Reload</label>
                        </div>
                      </div>
                    </div>

                    <!-- Performance & Security -->
                    <div>
                      <div class="qa-text-sm qa-font-medium qa-text-primary" style="margin-bottom: 12px;">Performance &amp; Security</div>
                      <div style="display: flex; flex-direction: column; gap: 12px;">
                        <div class="qa-flex qa-items-center" style="gap: 8px;">
                          <input type="checkbox" name="cache_enabled" id="edit_cache" style="accent-color: var(--q-primary-400);" />
                          <label for="edit_cache" class="qa-text-sm qa-text-muted">Template Cache</label>
                        </div>
                        <div>
                          <label class="qa-text-sm qa-text-muted" style="display: block; margin-bottom: 4px;">Cache TTL (seconds)</label>
                          <input type="number" name="cache_ttl" value="300" min="0" style="width: 100%; padding: 8px 12px; background: var(--q-bg-overlay); border: 1px solid var(--q-border); border-radius: 6px; color: var(--q-text-primary); font-family: 'SF Mono', monospace; font-size: 0.875rem;" />
                        </div>
                        <div>
                          <label class="qa-text-sm qa-text-muted" style="display: block; margin-bottom: 4px;">Log Level</label>
                          <select name="log_level" style="width: 100%; padding: 8px 12px; background: var(--q-bg-overlay); border: 1px solid var(--q-border); border-radius: 6px; color: var(--q-text-primary); font-size: 0.875rem;">
                            <option value="DEBUG">DEBUG</option>
                            <option value="INFO" selected="">INFO</option>
                            <option value="WARNING">WARNING</option>
                            <option value="ERROR">ERROR</option>
                          </select>
                        </div>
                        <div class="qa-flex qa-items-center" style="gap: 8px;">
                          <input type="checkbox" name="xss_protection" id="edit_xss" checked="" style="accent-color: var(--q-primary-400);" />
                          <label for="edit_xss" class="qa-text-sm qa-text-muted">XSS Protection</label>
                        </div>
                        <div class="qa-flex qa-items-center" style="gap: 8px;">
                          <input type="checkbox" name="cors_enabled" id="edit_cors" style="accent-color: var(--q-primary-400);" />
                          <label for="edit_cors" class="qa-text-sm qa-text-muted">CORS Enabled</label>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--q-border);">
                    <button type="submit" style="padding: 10px 24px; background: var(--q-primary-400); color: white; border: none; border-radius: 6px; font-size: 0.875rem; font-weight: 600; cursor: pointer;">Save Settings</button>
                  </div>
                </form>
              </div>
            </div>
          </q:if>

        </div>
      </main>

    </div>
  </body>
  </html>
</q:component>
