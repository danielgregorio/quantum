<q:component name="AdminConnectors" require_auth="true" require_role="admin" login_url="/admin/login">
  <!--
    Infrastructure connectors (admin.connectors.*), kept in
    settings/connectors.yaml by connector_service. The previous version
    reimplemented the file in q:python and stored the password in plain text;
    connector_service encrypts it, and no response brings the password back.
    Public connectors are created here; an application's own are on its screen.
  -->
  <q:import component="AdminShell" from="admin/_layout" />

  <q:action name="createConnector" method="POST">
    <q:param name="name" type="string" required="true" />
    <q:param name="conn_type" type="string" required="true" />
    <q:param name="provider" type="string" required="true" />
    <q:param name="port" type="integer" default="0" />
    <q:param name="is_default" type="boolean" default="false" />
    <q:invoke name="created" service="admin.connectors.create" onerror="continue">
      <q:param name="name" value="{name}" />
      <q:param name="type" value="{conn_type}" />
      <q:param name="provider" value="{provider}" />
      <q:param name="host" value="{form.host}" />
      <q:param name="port" value="{port}" type="integer" />
      <q:param name="database" value="{form.database}" />
      <q:param name="username" value="{form.username}" />
      <q:param name="password" value="{form.password}" />
      <q:param name="is_default" value="{is_default}" type="boolean" />
    </q:invoke>
    <q:if condition="created_result.success">
      <q:redirect url="/admin/connectors" flash="Connector {created.name} created" />
    </q:if>
    <q:flash type="error" message="{created_result.error.message}" />
    <q:redirect url="/admin/connectors" />
  </q:action>

  <q:action name="updateConnector" method="POST">
    <q:param name="connector_id" type="string" required="true" />
    <q:param name="port" type="integer" default="0" />
    <q:param name="is_default" type="boolean" default="false" />
    <q:invoke name="updated" service="admin.connectors.update" onerror="continue">
      <q:param name="connector_id" value="{connector_id}" />
      <q:param name="name" value="{form.name}" />
      <q:param name="type" value="{form.conn_type}" />
      <q:param name="provider" value="{form.provider}" />
      <q:param name="host" value="{form.host}" />
      <q:param name="port" value="{port}" type="integer" />
      <q:param name="database" value="{form.database}" />
      <q:param name="username" value="{form.username}" />
      <q:param name="password" value="{form.password}" />
      <q:param name="is_default" value="{is_default}" type="boolean" />
    </q:invoke>
    <q:if condition="updated_result.success">
      <q:redirect url="/admin/connectors" flash="Connector {updated.name} updated" />
    </q:if>
    <q:flash type="error" message="{updated_result.error.message}" />
    <q:redirect url="/admin/connectors?edit={connector_id}#edit-form" />
  </q:action>

  <q:action name="deleteConnector" method="POST">
    <q:param name="connector_id" type="string" required="true" />
    <q:invoke name="removed" service="admin.connectors.delete" onerror="continue">
      <q:param name="connector_id" value="{connector_id}" />
    </q:invoke>
    <q:if condition="removed_result.success">
      <q:redirect url="/admin/connectors" flash="Connector deleted" />
    </q:if>
    <q:flash type="error" message="{removed_result.error.message}" />
    <q:redirect url="/admin/connectors" />
  </q:action>

  <q:action name="testConnector" method="POST">
    <q:param name="connector_id" type="string" required="true" />
    <q:invoke name="test" service="admin.connectors.test" onerror="continue">
      <q:param name="connector_id" value="{connector_id}" />
    </q:invoke>
    <q:if condition="not test_result.success">
      <q:flash type="error" message="{test_result.error.message}" />
      <q:redirect url="/admin/connectors" />
    </q:if>
    <q:if condition="test.success">
      <q:redirect url="/admin/connectors" flash="Connection OK" />
    </q:if>
    <q:flash type="error" message="Connection failed: {test.error}" />
    <q:redirect url="/admin/connectors" />
  </q:action>

  <q:action name="testAll" method="POST">
    <q:invoke name="tests" service="admin.connectors.test_all" />
    <q:redirect url="/admin/connectors" flash="Tested {len(tests)} connector(s)" />
  </q:action>

  <q:invoke name="overview" service="admin.connectors.overview" />
  <q:set name="edit_id" value="{query.edit}" />
  <q:if condition="edit_id">
    <q:invoke name="editing" service="admin.connectors.get" onerror="continue">
      <q:param name="connector_id" value="{edit_id}" />
    </q:invoke>
  </q:if>

  <!-- A single form: with ?edit=<id> it comes filled in and updates; without, it creates. -->
  <q:set name="isEditing" value="{edit_id and editing_result.success}" type="boolean" />

  <AdminShell title="Connectors" active="connectors" flash="{flash}" flashType="{flashType}">

    <div class="qa-flex qa-items-center qa-mb-6" style="gap: 8px; flex-wrap: wrap;">
      <span class="qa-badge qa-badge-primary">{overview.total} registered</span>
      <span class="qa-badge qa-badge-success">{overview.connected} connected</span>
      <q:if condition="overview.errors &gt; 0">
        <span class="qa-badge qa-badge-danger">{overview.errors} with errors</span>
      </q:if>
      <q:if condition="overview.total &gt; 0">
        <form method="POST" action="/admin/connectors" style="margin: 0 0 0 auto;">
          <input type="hidden" name="action" value="testAll" />
          <button type="submit" class="qa-btn qa-btn-primary qa-btn-sm">Test All</button>
        </form>
      </q:if>
    </div>

    <div class="qa-grid qa-grid-5 qa-mb-6">
      <q:loop type="array" var="group" items="{overview.types}">
        <div class="qa-stat-card">
          <div class="qa-flex qa-items-center qa-justify-between">
            <div class="qa-stat-label">{group.label}</div>
            <span class="qa-badge qa-type-{group.type}">{len(group.connectors)}</span>
          </div>
          <q:loop type="array" var="c" items="{group.connectors}">
            <div class="qa-stat-connector-item">
              <span class="qa-status-dot {c.status}"></span>
              <span>{c.name}</span>
              <q:if condition="c.is_default"><span title="default for this type">&#9733;</span></q:if>
            </div>
          </q:loop>
          <q:if condition="len(group.connectors) == 0">
            <div class="qa-text-sm qa-text-muted">None configured</div>
          </q:if>
        </div>
      </q:loop>
    </div>

    <q:if condition="overview.total &gt; 0">
      <div class="qa-card qa-mb-6">
        <div class="qa-card-body qa-p-0" style="overflow-x: auto;">
          <table class="qa-table">
            <thead><tr><th>Name</th><th>Type</th><th>Provider</th><th>Host:Port</th><th>Status</th><th>Scope</th><th></th></tr></thead>
            <tbody>
              <q:loop type="array" var="group" items="{overview.types}">
                <q:loop type="array" var="conn" items="{group.connectors}">
                  <tr>
                    <td><span class="qa-font-medium">{conn.name}</span></td>
                    <td><span class="qa-badge qa-type-{conn.type}">{conn.type_label}</span></td>
                    <td><span class="qa-text-sm">{conn.provider_name}</span></td>
                    <td><span class="qa-font-mono qa-text-sm">{conn.host}:{conn.port}</span></td>
                    <td>
                      <div class="qa-status-badge" title="{'last tested ' + conn.last_tested if conn.last_tested else 'never tested'}">
                        <span class="qa-status-dot {conn.status}"></span>
                        <span class="qa-status-text">{conn.status}</span>
                      </div>
                    </td>
                    <td><span class="qa-text-sm qa-text-muted">{'application #' + str(conn.application_id) if conn.application_id else 'public'}</span></td>
                    <td>
                      <div class="qa-flex" style="gap: 4px;">
                        <form method="POST" action="/admin/connectors" style="margin: 0;">
                          <input type="hidden" name="action" value="testConnector" />
                          <input type="hidden" name="connector_id" value="{conn.id}" />
                          <button type="submit" class="qa-btn qa-btn-ghost qa-btn-sm">Test</button>
                        </form>
                        <a href="/admin/connectors?edit={conn.id}#edit-form" class="qa-btn qa-btn-ghost qa-btn-sm">Edit</a>
                        <form method="POST" action="/admin/connectors" style="margin: 0;" onsubmit="return confirm('Delete this connector?');">
                          <input type="hidden" name="action" value="deleteConnector" />
                          <input type="hidden" name="connector_id" value="{conn.id}" />
                          <button type="submit" class="qa-btn qa-btn-danger qa-btn-sm" aria-label="Delete {conn.name}">Delete</button>
                        </form>
                      </div>
                    </td>
                  </tr>
                </q:loop>
              </q:loop>
            </tbody>
          </table>
        </div>
      </div>
    </q:if>

    <q:if condition="edit_id and not editing_result.success">
      <div class="qa-flash qa-flash-error" role="alert">{editing_result.error.message}</div>
    </q:if>

    <div class="qa-card" id="edit-form">
      <div class="qa-card-header">
        <div>
          <div class="qa-card-title">{'Edit ' + editing.name if isEditing else 'New Connector'}</div>
          <div class="qa-card-subtitle">{'Blank password keeps the current one' if isEditing else 'Public: available to every application'}</div>
        </div>
        <q:if condition="isEditing">
          <a href="/admin/connectors" class="qa-btn qa-btn-ghost qa-btn-sm">Cancel</a>
        </q:if>
      </div>
      <div class="qa-card-body">
        <form method="POST" action="/admin/connectors">
          <q:if condition="isEditing">
            <input type="hidden" name="action" value="updateConnector" />
            <input type="hidden" name="connector_id" value="{editing.id}" />
          <q:else>
            <input type="hidden" name="action" value="createConnector" />
          </q:else>
          </q:if>
          <div class="qa-form-row qa-mb-4">
            <div class="qa-form-group">
              <label class="qa-label" for="name">Name</label>
              <input id="name" type="text" name="name" class="qa-input" placeholder="e.g. Production Redis" required="" value="{editing.name if isEditing else ''}" />
            </div>
            <div class="qa-form-group">
              <label class="qa-label" for="conn_type">Type</label>
              <select id="conn_type" name="conn_type" class="qa-input qa-select" required="">
                <option value="">Select type...</option>
                <q:loop type="array" var="group" items="{overview.types}">
                  <q:if condition="isEditing and editing.type == group.type">
                    <option value="{group.type}" selected="selected">{group.label}</option>
                  <q:else><option value="{group.type}">{group.label}</option></q:else>
                  </q:if>
                </q:loop>
              </select>
            </div>
          </div>
          <div class="qa-form-row qa-mb-4">
            <div class="qa-form-group">
              <label class="qa-label" for="provider">Provider</label>
              <select id="provider" name="provider" class="qa-input qa-select" required="">
                <option value="">Select provider...</option>
                <q:loop type="array" var="group" items="{overview.types}">
                  <optgroup label="{group.label}">
                    <q:loop type="array" var="p" items="{group.providers}">
                      <q:if condition="isEditing and editing.provider == p.provider">
                        <option value="{p.provider}" selected="selected">{p.name}</option>
                      <q:else><option value="{p.provider}">{p.name}</option></q:else>
                      </q:if>
                    </q:loop>
                  </optgroup>
                </q:loop>
              </select>
            </div>
            <div class="qa-form-group">
              <label class="qa-label" for="port">Port</label>
              <input id="port" type="number" name="port" class="qa-input" min="0" max="65535" placeholder="provider default" value="{editing.port if isEditing else ''}" />
            </div>
          </div>
          <div class="qa-form-row qa-mb-4">
            <div class="qa-form-group">
              <label class="qa-label" for="host">Host</label>
              <input id="host" type="text" name="host" class="qa-input" placeholder="localhost" value="{editing.host if isEditing else ''}" />
            </div>
            <div class="qa-form-group">
              <label class="qa-label" for="database">Database</label>
              <input id="database" type="text" name="database" class="qa-input" placeholder="Database, bucket or path" value="{editing.database if isEditing else ''}" />
            </div>
          </div>
          <div class="qa-form-row qa-mb-4">
            <div class="qa-form-group">
              <label class="qa-label" for="username">Username</label>
              <input id="username" type="text" name="username" class="qa-input" autocomplete="off" value="{editing.username if isEditing else ''}" />
            </div>
            <div class="qa-form-group">
              <label class="qa-label" for="password">Password or API key</label>
              <input id="password" type="password" name="password" class="qa-input" autocomplete="new-password"
                     placeholder="{'saved — leave blank to keep' if isEditing and editing.has_password else ''}" />
            </div>
          </div>
          <div class="qa-mb-4">
            <label class="qa-flex qa-items-center" style="gap: 8px;">
              <q:if condition="isEditing and editing.is_default">
                <input type="checkbox" name="is_default" value="true" checked="checked" />
              <q:else><input type="checkbox" name="is_default" value="true" /></q:else>
              </q:if>
              <span class="qa-text-sm">Default for this type</span>
            </label>
          </div>
          <button type="submit" class="qa-btn qa-btn-primary">{'Save Changes' if isEditing else 'Create Connector'}</button>
        </form>
      </div>
    </div>

    <script src="/static/quantum-admin-connectors.js"></script>
  </AdminShell>
</q:component>
