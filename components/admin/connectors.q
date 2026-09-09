<q:component name="AdminConnectors">

  <!-- Action: Create a new connector -->
  <q:action name="createConnector" method="POST">
    <q:param name="name" type="string" required="true" />
    <q:param name="conn_type" type="string" required="true" />
    <q:param name="provider" type="string" required="true" />
    <q:param name="host" type="string" />
    <q:param name="port" type="string" />
    <q:param name="database" type="string" />
    <q:param name="username" type="string" />
    <q:param name="password" type="string" />
    <q:param name="scope" type="string" />
    <q:param name="application_id" type="string" />
    <q:param name="is_default" type="string" />

    <q:python>
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, save_yaml, gen_id, now_iso

name = q.form.get('name', '').strip()
conn_type = q.form.get('conn_type', '').strip()
provider = q.form.get('provider', '').strip()

if not name or not conn_type or not provider:
    q.flash_error = 'Name, type and provider are required.'
else:
    connectors = load_yaml('connectors.yaml')

    port_str = q.form.get('port', '0').strip()
    try:
        port_val = int(port_str) if port_str else 0
    except:
        port_val = 0

    docker_images = {
        'postgres': 'postgres:16-alpine', 'mysql': 'mysql:8', 'mariadb': 'mariadb:11',
        'mongodb': 'mongo:7', 'sqlite': '', 'influxdb': 'influxdb:2.7',
        'rabbitmq': 'rabbitmq:3-management-alpine',
        'redis_queue': 'redis:7-alpine', 'kafka': 'confluentinc/cp-kafka:7.5.0',
        'redis': 'redis:7-alpine', 'memcached': 'memcached:1.6-alpine',
        's3': '', 'minio': 'minio/minio:latest', 'local': '',
        'ollama': 'ollama/ollama:latest', 'lmstudio': '', 'anthropic': '', 'openai': '', 'openrouter': '',
    }

    app_id = q.form.get('application_id', '').strip() or None
    scope = q.form.get('scope', 'public').strip()
    set_default = q.form.get('is_default', '') == 'yes'

    new_id = gen_id()
    connector = {
        'id': new_id,
        'name': name,
        'type': conn_type,
        'provider': provider,
        'host': q.form.get('host', '').strip(),
        'port': port_val,
        'database': q.form.get('database', '').strip(),
        'username': q.form.get('username', '').strip(),
        'password': q.form.get('password', '').strip(),
        'options': {},
        'is_default': set_default,
        'docker_auto': False,
        'docker_image': docker_images.get(provider, ''),
        'docker_container_id': '',
        'status': 'unknown',
        'last_tested': None,
        'created_at': now_iso(),
        'updated_at': now_iso(),
        'application_id': app_id,
        'scope': scope,
    }

    if set_default:
        for c in connectors:
            if c.get('type') == conn_type:
                c['is_default'] = False

    connectors.append(connector)
    save_yaml('connectors.yaml', connectors)
    </q:python>

    <q:redirect url="/admin/connectors?flash=Connector+created" />
  </q:action>

  <!-- Action: Delete a connector -->
  <q:action name="deleteConnector" method="POST">
    <q:param name="connector_id" type="string" required="true" />

    <q:python>
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, save_yaml

cid = q.form.get('connector_id', '').strip()
connectors = load_yaml('connectors.yaml')
connectors = [c for c in connectors if c.get('id') != cid]
save_yaml('connectors.yaml', connectors)
    </q:python>

    <q:redirect url="/admin/connectors?flash=Connector+deleted" />
  </q:action>

  <!-- Action: Test a connector -->
  <q:action name="testConnector" method="POST">
    <q:param name="connector_id" type="string" required="true" />

    <q:python>
import sys, os, socket, datetime
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, save_yaml, find_by_id

cid = q.form.get('connector_id', '').strip()
connectors = load_yaml('connectors.yaml')
conn = find_by_id(connectors, cid)

if conn:
    host = conn.get('host', '')
    port = conn.get('port', 0)
    provider = conn.get('provider', '')
    conn_type = conn.get('type', '')
    status = 'unknown'
    error_msg = ''

    if conn_type == 'storage' and provider == 'local':
        db = conn.get('database', '')
        if db and os.path.isdir(db):
            status = 'connected'
        elif not db:
            status = 'unknown'
            error_msg = 'No path configured'
        else:
            status = 'error'
            error_msg = 'Directory not found'
    elif provider in ('anthropic', 'openai', 'openrouter'):
        status = 'unknown'
        error_msg = 'API key validation not supported yet'
    elif provider in ('ollama', 'lmstudio'):
        urls = {
            'ollama': '/api/tags',
            'lmstudio': '/v1/models',
        }
        path = urls.get(provider, '/')
        try:
            import http.client
            c = http.client.HTTPConnection(host, int(port), timeout=5)
            c.request('GET', path)
            resp = c.getresponse()
            if resp.status &lt; 400:
                status = 'connected'
            else:
                status = 'error'
                error_msg = f'HTTP {resp.status}'
            c.close()
        except Exception as e:
            status = 'error'
            error_msg = str(e)[:100]
    elif provider == 'sqlite':
        db = conn.get('database', '')
        if db and os.path.isfile(db):
            status = 'connected'
        elif not db:
            status = 'connected'
        else:
            status = 'error'
            error_msg = 'Database file not found'
    elif host and port:
        try:
            sock = socket.create_connection((host, int(port)), timeout=3)
            sock.close()
            status = 'connected'
        except Exception as e:
            status = 'error'
            error_msg = str(e)[:100]
    else:
        status = 'unknown'
        error_msg = 'No host/port configured'

    conn['status'] = status
    conn['last_tested'] = datetime.datetime.now().isoformat()
    save_yaml('connectors.yaml', connectors)
    </q:python>

    <q:redirect url="/admin/connectors?flash=Connection+tested" />
  </q:action>

  <!-- Action: Update a connector -->
  <q:action name="updateConnector" method="POST">
    <q:param name="connector_id" type="string" required="true" />
    <q:param name="name" type="string" />
    <q:param name="conn_type" type="string" />
    <q:param name="provider" type="string" />
    <q:param name="host" type="string" />
    <q:param name="port" type="string" />
    <q:param name="database" type="string" />
    <q:param name="username" type="string" />
    <q:param name="password" type="string" />
    <q:param name="scope" type="string" />
    <q:param name="is_default" type="string" />

    <q:python>
import sys, os, datetime
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, save_yaml, find_by_id

cid = q.form.get('connector_id', '').strip()
connectors = load_yaml('connectors.yaml')
conn = find_by_id(connectors, cid)

if conn:
    name = q.form.get('name', '').strip()
    if name:
        conn['name'] = name
    ct = q.form.get('conn_type', '').strip()
    if ct:
        conn['type'] = ct
    prov = q.form.get('provider', '').strip()
    if prov:
        conn['provider'] = prov
    conn['host'] = q.form.get('host', conn.get('host', '')).strip()
    port_str = q.form.get('port', '').strip()
    if port_str:
        try:
            conn['port'] = int(port_str)
        except:
            pass
    conn['database'] = q.form.get('database', conn.get('database', '')).strip()
    conn['username'] = q.form.get('username', conn.get('username', '')).strip()
    pw = q.form.get('password', '').strip()
    if pw:
        conn['password'] = pw
    scope = q.form.get('scope', '').strip()
    if scope:
        conn['scope'] = scope

    set_default = q.form.get('is_default', '') == 'yes'
    conn_type = conn.get('type', '')
    if set_default:
        for c in connectors:
            if c.get('type') == conn_type:
                c['is_default'] = (c.get('id') == cid)
    else:
        conn['is_default'] = False

    conn['updated_at'] = datetime.datetime.now().isoformat()
    save_yaml('connectors.yaml', connectors)
    </q:python>

    <q:redirect url="/admin/connectors?flash=Connector+updated" />
  </q:action>

  <!-- Action: Test all connectors -->
  <q:action name="testAll" method="POST">
    <q:python>
import sys, os, socket, datetime
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml, save_yaml

connectors = load_yaml('connectors.yaml')
tested = 0

for conn in connectors:
    host = conn.get('host', '')
    port = conn.get('port', 0)
    provider = conn.get('provider', '')
    conn_type = conn.get('type', '')
    status = 'unknown'

    if conn_type == 'storage' and provider == 'local':
        db = conn.get('database', '')
        if db and os.path.isdir(db):
            status = 'connected'
        elif not db:
            status = 'unknown'
        else:
            status = 'error'
    elif provider in ('anthropic', 'openai', 'openrouter'):
        status = 'unknown'
    elif provider in ('ollama', 'lmstudio'):
        urls = {'ollama': '/api/tags', 'lmstudio': '/v1/models'}
        path = urls.get(provider, '/')
        try:
            import http.client
            c = http.client.HTTPConnection(host, int(port), timeout=5)
            c.request('GET', path)
            resp = c.getresponse()
            if resp.status &lt; 400:
                status = 'connected'
            else:
                status = 'error'
            c.close()
        except:
            status = 'error'
    elif provider == 'sqlite':
        db = conn.get('database', '')
        if db and os.path.isfile(db):
            status = 'connected'
        elif not db:
            status = 'connected'
        else:
            status = 'error'
    elif host and port:
        try:
            sock = socket.create_connection((host, int(port)), timeout=3)
            sock.close()
            status = 'connected'
        except:
            status = 'error'

    conn['status'] = status
    conn['last_tested'] = datetime.datetime.now().isoformat()
    tested += 1

save_yaml('connectors.yaml', connectors)
    </q:python>

    <q:redirect url="/admin/connectors?flash=Tested+all+connectors" />
  </q:action>

  <!-- Collect data -->
  <q:python>
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'components', 'admin'))
from _lib import load_yaml

connectors = load_yaml('connectors.yaml')

# Provider display info
provider_names = {
    'postgres': 'PostgreSQL', 'mysql': 'MySQL', 'mariadb': 'MariaDB',
    'mongodb': 'MongoDB', 'sqlite': 'SQLite', 'influxdb': 'InfluxDB',
    'rabbitmq': 'RabbitMQ', 'redis_queue': 'Redis Queue', 'kafka': 'Kafka',
    'redis': 'Redis', 'memcached': 'Memcached', 's3': 'Amazon S3',
    'minio': 'MinIO', 'local': 'Local FS', 'ollama': 'Ollama',
    'lmstudio': 'LM Studio', 'anthropic': 'Anthropic', 'openai': 'OpenAI',
    'openrouter': 'OpenRouter',
}

type_labels = {
    'database': 'Database', 'mq': 'Message Queue', 'message_queue': 'Message Queue',
    'cache': 'Cache', 'storage': 'Storage', 'ai': 'AI',
}

type_badge_class = {
    'database': 'qa-type-database', 'mq': 'qa-type-message_queue',
    'message_queue': 'qa-type-message_queue', 'cache': 'qa-type-cache',
    'storage': 'qa-type-storage', 'ai': 'qa-type-ai',
}

# Count by type
counts = {'database': 0, 'mq': 0, 'cache': 0, 'storage': 0, 'ai': 0}
for c in connectors:
    t = c.get('type', '')
    if t in counts:
        counts[t] += 1
    elif t == 'message_queue':
        counts['mq'] += 1

q.count_database = str(counts['database'])
q.count_mq = str(counts['mq'])
q.count_cache = str(counts['cache'])
q.count_storage = str(counts['storage'])
q.count_ai = str(counts['ai'])
q.total_connectors = str(len(connectors))

# Enrich connectors for display
display_connectors = []
for c in connectors:
    dc = dict(c)
    dc['provider_name'] = provider_names.get(c.get('provider', ''), c.get('provider', ''))
    dc['type_label'] = type_labels.get(c.get('type', ''), c.get('type', ''))
    dc['type_badge'] = type_badge_class.get(c.get('type', ''), 'qa-badge-gray')
    dc['provider_class'] = 'qa-provider-' + c.get('provider', '')
    dc['provider_initial'] = dc['provider_name'][:2].upper() if dc['provider_name'] else '??'
    dc['status_class'] = c.get('status', 'unknown')
    host = c.get('host', '')
    port = c.get('port', 0)
    dc['host_port'] = f"{host}:{port}" if host and port else host or '-'
    dc['scope_label'] = c.get('scope', 'public').capitalize()
    dc['is_default_star'] = 'yes' if c.get('is_default') else 'no'
    dc['port'] = str(port)
    display_connectors.append(dc)

q.connectors = display_connectors

# Group by type for stat cards
type_groups = {'database': [], 'mq': [], 'cache': [], 'storage': [], 'ai': []}
for dc in display_connectors:
    t = dc.get('type', '')
    key = 'mq' if t == 'message_queue' else t
    if key in type_groups:
        type_groups[key].append(dc)

q.db_connectors = type_groups['database']
q.mq_connectors = type_groups['mq']
q.cache_connectors = type_groups['cache']
q.storage_connectors = type_groups['storage']
q.ai_connectors = type_groups['ai']

# Flash message
q.flash_message = ''
q.edit_id = ''
q.edit_mode = 'no'
try:
    from flask import request as flask_request
    q.flash_message = flask_request.args.get('flash', '')
    q.edit_id = flask_request.args.get('edit', '')
except:
    pass

# If editing, pre-fill form with connector data
q.edit_name = ''
q.edit_type = ''
q.edit_provider = ''
q.edit_host = ''
q.edit_port = ''
q.edit_database = ''
q.edit_username = ''
q.edit_scope = 'public'
q.edit_is_default = 'no'
q.form_title = 'New Connector'
q.form_subtitle = 'Add a new infrastructure connector'
q.form_action = 'createConnector'
q.form_button = 'Create Connector'

if q.edit_id:
    from _lib import find_by_id
    edit_conn = find_by_id(connectors, q.edit_id)
    if edit_conn:
        q.edit_mode = 'yes'
        q.edit_name = edit_conn.get('name', '')
        q.edit_type = edit_conn.get('type', '')
        q.edit_provider = edit_conn.get('provider', '')
        q.edit_host = edit_conn.get('host', '')
        q.edit_port = str(edit_conn.get('port', ''))
        q.edit_database = edit_conn.get('database', '')
        q.edit_username = edit_conn.get('username', '')
        q.edit_scope = edit_conn.get('scope', 'public')
        q.edit_is_default = 'yes' if edit_conn.get('is_default') else 'no'
        q.form_title = 'Edit Connector'
        q.form_subtitle = f'Editing: {q.edit_name}'
        q.form_action = 'updateConnector'
        q.form_button = 'Update Connector'

# Count connected / error
connected_count = sum(1 for c in connectors if c.get('status') == 'connected')
error_count = sum(1 for c in connectors if c.get('status') == 'error')
q.connected_count = str(connected_count)
q.error_count = str(error_count)
  </q:python>

  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Connectors - Quantum Admin</title>
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
            <a href="/admin/connectors" class="qa-sidebar-link active">
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
          <h1 class="qa-header-title">Connectors</h1>
          <div class="qa-header-actions">
            <span class="qa-badge qa-badge-primary">{total_connectors} registered</span>
            <span class="qa-badge qa-badge-success">{connected_count} connected</span>
            <q:if condition="{error_count} != '0'">
              <span class="qa-badge qa-badge-danger">{error_count} error</span>
            </q:if>
            <form method="POST" action="/admin/connectors" style="display: inline; margin-left: 8px;">
              <input type="hidden" name="action" value="testAll" />
              <button type="submit" class="qa-btn qa-btn-primary qa-btn-sm">Test All</button>
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

          <!-- Stat Cards by Type -->
          <div class="qa-grid qa-grid-5 qa-mb-6" style="grid-template-columns: repeat(5, 1fr);">

            <!-- Database -->
            <div class="qa-stat-card">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <div class="qa-stat-label" style="margin-bottom: 0;">Database</div>
                <span class="qa-badge qa-type-database">{count_database}</span>
              </div>
              <q:if condition="{count_database} != '0'">
                <q:loop type="array" var="c" items="{db_connectors}">
                  <div class="qa-stat-connector-item">
                    <span class="qa-status-dot {c.status_class}"></span>
                    <span>{c.name}</span>
                    <q:if condition="{c.is_default_star} == 'yes'">
                      <span style="color: var(--q-warning); margin-left: auto;">&#9733;</span>
                    </q:if>
                  </div>
                </q:loop>
              </q:if>
              <q:if condition="{count_database} == '0'">
                <div class="qa-text-sm qa-text-muted" style="padding: 4px 0;">None configured</div>
              </q:if>
            </div>

            <!-- Message Queue -->
            <div class="qa-stat-card">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <div class="qa-stat-label" style="margin-bottom: 0;">Message Queue</div>
                <span class="qa-badge qa-type-message_queue">{count_mq}</span>
              </div>
              <q:if condition="{count_mq} != '0'">
                <q:loop type="array" var="c" items="{mq_connectors}">
                  <div class="qa-stat-connector-item">
                    <span class="qa-status-dot {c.status_class}"></span>
                    <span>{c.name}</span>
                    <q:if condition="{c.is_default_star} == 'yes'">
                      <span style="color: var(--q-warning); margin-left: auto;">&#9733;</span>
                    </q:if>
                  </div>
                </q:loop>
              </q:if>
              <q:if condition="{count_mq} == '0'">
                <div class="qa-text-sm qa-text-muted" style="padding: 4px 0;">None configured</div>
              </q:if>
            </div>

            <!-- Cache -->
            <div class="qa-stat-card">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <div class="qa-stat-label" style="margin-bottom: 0;">Cache</div>
                <span class="qa-badge qa-type-cache">{count_cache}</span>
              </div>
              <q:if condition="{count_cache} != '0'">
                <q:loop type="array" var="c" items="{cache_connectors}">
                  <div class="qa-stat-connector-item">
                    <span class="qa-status-dot {c.status_class}"></span>
                    <span>{c.name}</span>
                    <q:if condition="{c.is_default_star} == 'yes'">
                      <span style="color: var(--q-warning); margin-left: auto;">&#9733;</span>
                    </q:if>
                  </div>
                </q:loop>
              </q:if>
              <q:if condition="{count_cache} == '0'">
                <div class="qa-text-sm qa-text-muted" style="padding: 4px 0;">None configured</div>
              </q:if>
            </div>

            <!-- Storage -->
            <div class="qa-stat-card">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <div class="qa-stat-label" style="margin-bottom: 0;">Storage</div>
                <span class="qa-badge qa-type-storage">{count_storage}</span>
              </div>
              <q:if condition="{count_storage} != '0'">
                <q:loop type="array" var="c" items="{storage_connectors}">
                  <div class="qa-stat-connector-item">
                    <span class="qa-status-dot {c.status_class}"></span>
                    <span>{c.name}</span>
                    <q:if condition="{c.is_default_star} == 'yes'">
                      <span style="color: var(--q-warning); margin-left: auto;">&#9733;</span>
                    </q:if>
                  </div>
                </q:loop>
              </q:if>
              <q:if condition="{count_storage} == '0'">
                <div class="qa-text-sm qa-text-muted" style="padding: 4px 0;">None configured</div>
              </q:if>
            </div>

            <!-- AI -->
            <div class="qa-stat-card">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <div class="qa-stat-label" style="margin-bottom: 0;">AI</div>
                <span class="qa-badge qa-type-ai">{count_ai}</span>
              </div>
              <q:if condition="{count_ai} != '0'">
                <q:loop type="array" var="c" items="{ai_connectors}">
                  <div class="qa-stat-connector-item">
                    <span class="qa-status-dot {c.status_class}"></span>
                    <span>{c.name}</span>
                    <q:if condition="{c.is_default_star} == 'yes'">
                      <span style="color: var(--q-warning); margin-left: auto;">&#9733;</span>
                    </q:if>
                  </div>
                </q:loop>
              </q:if>
              <q:if condition="{count_ai} == '0'">
                <div class="qa-text-sm qa-text-muted" style="padding: 4px 0;">None configured</div>
              </q:if>
            </div>

          </div>

          <!-- Connectors Table -->
          <q:if condition="{total_connectors} != '0'">
            <div class="qa-card qa-mb-6">
              <div class="qa-card-header">
                <div>
                  <div class="qa-card-title">All Connectors</div>
                  <div class="qa-card-subtitle">{total_connectors} infrastructure connectors</div>
                </div>
              </div>
              <div class="qa-card-body" style="padding: 0;">
                <table class="qa-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Type</th>
                      <th>Provider</th>
                      <th>Host:Port</th>
                      <th>Status</th>
                      <th>Scope</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    <q:loop type="array" var="conn" items="{connectors}">
                      <tr>
                        <td>
                          <div class="qa-flex qa-items-center qa-gap-2">
                            <div class="qa-connector-icon {conn.provider_class}" style="width: 28px; height: 28px; border-radius: 6px; font-size: 0.625rem; font-weight: 700;">
                              {conn.provider_initial}
                            </div>
                            <span class="qa-font-medium">{conn.name}</span>
                          </div>
                        </td>
                        <td><span class="qa-badge {conn.type_badge}">{conn.type_label}</span></td>
                        <td><span class="qa-text-sm">{conn.provider_name}</span></td>
                        <td><span class="qa-font-mono qa-text-sm">{conn.host_port}</span></td>
                        <td>
                          <div class="qa-status-badge">
                            <span class="qa-status-dot {conn.status_class}"></span>
                            <span class="qa-status-text">{conn.status}</span>
                          </div>
                        </td>
                        <td><span class="qa-text-sm qa-text-muted">{conn.scope_label}</span></td>
                        <td>
                          <div class="qa-flex qa-gap-1">
                            <form method="POST" action="/admin/connectors" style="display: inline;">
                              <input type="hidden" name="action" value="testConnector" />
                              <input type="hidden" name="connector_id" value="{conn.id}" />
                              <button type="submit" class="qa-btn qa-btn-ghost qa-btn-sm">Test</button>
                            </form>
                            <a href="/admin/connectors?edit={conn.id}#edit-form" class="qa-btn qa-btn-ghost qa-btn-sm">Edit</a>
                            <form method="POST" action="/admin/connectors" style="display: inline;" onsubmit="return confirm('Delete this connector?');">
                              <input type="hidden" name="action" value="deleteConnector" />
                              <input type="hidden" name="connector_id" value="{conn.id}" />
                              <button type="submit" class="qa-btn qa-btn-danger qa-btn-sm">Delete</button>
                            </form>
                          </div>
                        </td>
                      </tr>
                    </q:loop>
                  </tbody>
                </table>
              </div>
            </div>
          </q:if>

          <!-- Empty State -->
          <q:if condition="{total_connectors} == '0'">
            <div class="qa-card qa-mb-6">
              <div class="qa-card-body" style="text-align: center; padding: 48px 24px;">
                <div style="font-size: 3rem; margin-bottom: 16px; opacity: 0.3;">
                  <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="display: inline-block;"><path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M6 8H5a4 4 0 0 0 0 8h1"/><line x1="6" y1="12" x2="18" y2="12"/></svg>
                </div>
                <div class="qa-text-lg qa-font-medium qa-text-primary" style="margin-bottom: 8px;">No Connectors</div>
                <div class="qa-text-sm qa-text-muted">Create your first infrastructure connector using the form below.</div>
              </div>
            </div>
          </q:if>

          <!-- Connector Form (Create / Edit) -->
          <div class="qa-card" id="edit-form">
            <div class="qa-card-header">
              <div>
                <div class="qa-card-title">{form_title}</div>
                <div class="qa-card-subtitle">{form_subtitle}</div>
              </div>
              <q:if condition="{edit_mode} == 'yes'">
                <a href="/admin/connectors" class="qa-btn qa-btn-ghost qa-btn-sm">Cancel Edit</a>
              </q:if>
            </div>
            <div class="qa-card-body">
              <form method="POST" action="/admin/connectors">
                <input type="hidden" name="action" value="{form_action}" />
                <q:if condition="{edit_mode} == 'yes'">
                  <input type="hidden" name="connector_id" value="{edit_id}" />
                </q:if>

                <div class="qa-form-row qa-mb-4">
                  <div class="qa-form-group">
                    <label class="qa-label">Name</label>
                    <input type="text" name="name" class="qa-input" placeholder="e.g. Production Redis" required="" value="{edit_name}" />
                  </div>
                  <div class="qa-form-group">
                    <label class="qa-label">Type</label>
                    <select name="conn_type" class="qa-input qa-select" required="">
                      <option value="">Select type...</option>
                      <option value="database">Database</option>
                      <option value="mq">Message Queue</option>
                      <option value="cache">Cache</option>
                      <option value="storage">Storage</option>
                      <option value="ai">AI</option>
                    </select>
                  </div>
                </div>

                <div class="qa-form-row qa-mb-4">
                  <div class="qa-form-group">
                    <label class="qa-label">Provider</label>
                    <select name="provider" class="qa-input qa-select" required="">
                      <option value="">Select provider...</option>
                      <optgroup label="Database">
                        <option value="postgres">PostgreSQL</option>
                        <option value="mysql">MySQL</option>
                        <option value="mariadb">MariaDB</option>
                        <option value="mongodb">MongoDB</option>
                        <option value="sqlite">SQLite</option>
                        <option value="influxdb">InfluxDB</option>
                      </optgroup>
                      <optgroup label="Message Queue">
                        <option value="rabbitmq">RabbitMQ</option>
                        <option value="redis_queue">Redis Queue</option>
                        <option value="kafka">Kafka</option>
                      </optgroup>
                      <optgroup label="Cache">
                        <option value="redis">Redis</option>
                        <option value="memcached">Memcached</option>
                      </optgroup>
                      <optgroup label="Storage">
                        <option value="s3">Amazon S3</option>
                        <option value="minio">MinIO</option>
                        <option value="local">Local Filesystem</option>
                      </optgroup>
                      <optgroup label="AI">
                        <option value="ollama">Ollama</option>
                        <option value="lmstudio">LM Studio</option>
                        <option value="anthropic">Anthropic</option>
                        <option value="openai">OpenAI</option>
                        <option value="openrouter">OpenRouter</option>
                      </optgroup>
                    </select>
                  </div>
                  <div class="qa-form-group">
                    <label class="qa-label">Scope</label>
                    <select name="scope" class="qa-input qa-select">
                      <option value="public">Public (all projects)</option>
                      <option value="application">Application-scoped</option>
                    </select>
                  </div>
                </div>

                <div class="qa-form-row qa-mb-4">
                  <div class="qa-form-group">
                    <label class="qa-label">Host</label>
                    <input type="text" name="host" class="qa-input" placeholder="e.g. localhost or localhost" value="{edit_host}" />
                  </div>
                  <div class="qa-form-group">
                    <label class="qa-label">Port</label>
                    <input type="number" name="port" class="qa-input" placeholder="e.g. 6379" value="{edit_port}" />
                  </div>
                </div>

                <div class="qa-form-row qa-mb-4">
                  <div class="qa-form-group">
                    <label class="qa-label">Database</label>
                    <input type="text" name="database" class="qa-input" placeholder="Database name or path" value="{edit_database}" />
                  </div>
                  <div class="qa-form-group">
                    <label class="qa-label">Username</label>
                    <input type="text" name="username" class="qa-input" placeholder="Username" value="{edit_username}" />
                  </div>
                </div>

                <div class="qa-form-row qa-mb-4">
                  <div class="qa-form-group">
                    <label class="qa-label">Password</label>
                    <input type="password" name="password" class="qa-input" placeholder="Leave blank to keep current" />
                  </div>
                  <div class="qa-form-group">
                    <q:if condition="{edit_mode} == 'yes'">
                      <div class="qa-text-sm qa-text-muted" style="padding-top: 28px;">Editing: <span class="qa-font-mono">{edit_provider}</span> / <span class="qa-font-mono">{edit_type}</span></div>
                    </q:if>
                  </div>
                </div>

                <div class="qa-mb-4">
                  <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                    <q:if condition="{edit_is_default} == 'yes'">
                      <input type="checkbox" name="is_default" value="yes" checked="" />
                    </q:if>
                    <q:if condition="{edit_is_default} != 'yes'">
                      <input type="checkbox" name="is_default" value="yes" />
                    </q:if>
                    <span class="qa-text-sm">Set as default for this type</span>
                  </label>
                </div>

                <div style="padding-top: 16px; border-top: 1px solid var(--q-border);">
                  <button type="submit" class="qa-btn qa-btn-primary">{form_button}</button>
                  <q:if condition="{edit_mode} == 'yes'">
                    <a href="/admin/connectors" class="qa-btn qa-btn-ghost" style="margin-left: 8px;">Cancel</a>
                  </q:if>
                </div>
              </form>
            </div>
          </div>

        </div>
      </main>

    </div>
    <script src="/static/quantum-admin-connectors.js"></script>
  </body>
  </html>
</q:component>
