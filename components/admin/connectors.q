<q:component name="AdminConnectors" require_auth="true" require_role="admin" login_url="/admin/login">
  <!--
    Connectors de infraestrutura (admin.connectors.*), guardados em
    settings/connectors.yaml por connector_service. A versão anterior
    reimplementava o arquivo em q:python e gravava a senha em texto puro;
    connector_service cifra, e nenhuma resposta traz a senha de volta.
    Aqui se criam connectors públicos; os de uma aplicação ficam na tela dela.
  -->
  <q:import component="AdminShell" from="admin/_layout" />

  <q:action name="createConnector" method="POST">
    <q:param name="name" type="string" required="true" />
    <q:param name="conn_type" type="string" required="true" />
    <q:param name="provider" type="string" required="true" />
    <q:param name="port" type="integer" default="0" />
    <q:param name="is_default" type="boolean" default="false" />
    <q:invoke name="criado" service="admin.connectors.create" onerror="continue">
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
    <q:if condition="criado_result.success">
      <q:redirect url="/admin/connectors" flash="Connector {criado.name} created" />
    </q:if>
    <q:flash type="error" message="{criado_result.error.message}" />
    <q:redirect url="/admin/connectors" />
  </q:action>

  <q:action name="updateConnector" method="POST">
    <q:param name="connector_id" type="string" required="true" />
    <q:param name="port" type="integer" default="0" />
    <q:param name="is_default" type="boolean" default="false" />
    <q:invoke name="alterado" service="admin.connectors.update" onerror="continue">
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
    <q:if condition="alterado_result.success">
      <q:redirect url="/admin/connectors" flash="Connector {alterado.name} updated" />
    </q:if>
    <q:flash type="error" message="{alterado_result.error.message}" />
    <q:redirect url="/admin/connectors?edit={connector_id}#edit-form" />
  </q:action>

  <q:action name="deleteConnector" method="POST">
    <q:param name="connector_id" type="string" required="true" />
    <q:invoke name="removido" service="admin.connectors.delete" onerror="continue">
      <q:param name="connector_id" value="{connector_id}" />
    </q:invoke>
    <q:if condition="removido_result.success">
      <q:redirect url="/admin/connectors" flash="Connector deleted" />
    </q:if>
    <q:flash type="error" message="{removido_result.error.message}" />
    <q:redirect url="/admin/connectors" />
  </q:action>

  <q:action name="testConnector" method="POST">
    <q:param name="connector_id" type="string" required="true" />
    <q:invoke name="teste" service="admin.connectors.test" onerror="continue">
      <q:param name="connector_id" value="{connector_id}" />
    </q:invoke>
    <q:if condition="not teste_result.success">
      <q:flash type="error" message="{teste_result.error.message}" />
      <q:redirect url="/admin/connectors" />
    </q:if>
    <q:if condition="teste.success">
      <q:redirect url="/admin/connectors" flash="Connection OK" />
    </q:if>
    <q:flash type="error" message="Connection failed: {teste.error}" />
    <q:redirect url="/admin/connectors" />
  </q:action>

  <q:action name="testAll" method="POST">
    <q:invoke name="testes" service="admin.connectors.test_all" />
    <q:redirect url="/admin/connectors" flash="Tested {len(testes)} connector(s)" />
  </q:action>

  <q:invoke name="painel" service="admin.connectors.overview" />
  <q:set name="editar" value="{query.edit}" />
  <q:if condition="editar">
    <q:invoke name="edicao" service="admin.connectors.get" onerror="continue">
      <q:param name="connector_id" value="{editar}" />
    </q:invoke>
  </q:if>

  <!-- Um formulário só: com ?edit=<id> vem preenchido e altera; sem, cria. -->
  <q:set name="emEdicao" value="{editar and edicao_result.success}" type="boolean" />

  <AdminShell title="Connectors" active="connectors" flash="{flash}" flashType="{flashType}">

    <div class="qa-flex qa-items-center qa-mb-6" style="gap: 8px; flex-wrap: wrap;">
      <span class="qa-badge qa-badge-primary">{painel.total} registered</span>
      <span class="qa-badge qa-badge-success">{painel.connected} connected</span>
      <q:if condition="painel.errors &gt; 0">
        <span class="qa-badge qa-badge-danger">{painel.errors} with errors</span>
      </q:if>
      <q:if condition="painel.total &gt; 0">
        <form method="POST" action="/admin/connectors" style="margin: 0 0 0 auto;">
          <input type="hidden" name="action" value="testAll" />
          <button type="submit" class="qa-btn qa-btn-primary qa-btn-sm">Test All</button>
        </form>
      </q:if>
    </div>

    <div class="qa-grid qa-grid-5 qa-mb-6">
      <q:loop type="array" var="grupo" items="{painel.types}">
        <div class="qa-stat-card">
          <div class="qa-flex qa-items-center qa-justify-between">
            <div class="qa-stat-label">{grupo.label}</div>
            <span class="qa-badge qa-type-{grupo.type}">{len(grupo.connectors)}</span>
          </div>
          <q:loop type="array" var="c" items="{grupo.connectors}">
            <div class="qa-stat-connector-item">
              <span class="qa-status-dot {c.status}"></span>
              <span>{c.name}</span>
              <q:if condition="c.is_default"><span title="default for this type">&#9733;</span></q:if>
            </div>
          </q:loop>
          <q:if condition="len(grupo.connectors) == 0">
            <div class="qa-text-sm qa-text-muted">None configured</div>
          </q:if>
        </div>
      </q:loop>
    </div>

    <q:if condition="painel.total &gt; 0">
      <div class="qa-card qa-mb-6">
        <div class="qa-card-body qa-p-0" style="overflow-x: auto;">
          <table class="qa-table">
            <thead><tr><th>Name</th><th>Type</th><th>Provider</th><th>Host:Port</th><th>Status</th><th>Scope</th><th></th></tr></thead>
            <tbody>
              <q:loop type="array" var="grupo" items="{painel.types}">
                <q:loop type="array" var="conn" items="{grupo.connectors}">
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

    <q:if condition="editar and not edicao_result.success">
      <div class="qa-flash qa-flash-error" role="alert">{edicao_result.error.message}</div>
    </q:if>

    <div class="qa-card" id="edit-form">
      <div class="qa-card-header">
        <div>
          <div class="qa-card-title">{'Edit ' + edicao.name if emEdicao else 'New Connector'}</div>
          <div class="qa-card-subtitle">{'Blank password keeps the current one' if emEdicao else 'Public: available to every application'}</div>
        </div>
        <q:if condition="emEdicao">
          <a href="/admin/connectors" class="qa-btn qa-btn-ghost qa-btn-sm">Cancel</a>
        </q:if>
      </div>
      <div class="qa-card-body">
        <form method="POST" action="/admin/connectors">
          <q:if condition="emEdicao">
            <input type="hidden" name="action" value="updateConnector" />
            <input type="hidden" name="connector_id" value="{edicao.id}" />
          <q:else>
            <input type="hidden" name="action" value="createConnector" />
          </q:else>
          </q:if>
          <div class="qa-form-row qa-mb-4">
            <div class="qa-form-group">
              <label class="qa-label" for="name">Name</label>
              <input id="name" type="text" name="name" class="qa-input" placeholder="e.g. Production Redis" required="" value="{edicao.name if emEdicao else ''}" />
            </div>
            <div class="qa-form-group">
              <label class="qa-label" for="conn_type">Type</label>
              <select id="conn_type" name="conn_type" class="qa-input qa-select" required="">
                <option value="">Select type...</option>
                <q:loop type="array" var="grupo" items="{painel.types}">
                  <q:if condition="emEdicao and edicao.type == grupo.type">
                    <option value="{grupo.type}" selected="selected">{grupo.label}</option>
                  <q:else><option value="{grupo.type}">{grupo.label}</option></q:else>
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
                <q:loop type="array" var="grupo" items="{painel.types}">
                  <optgroup label="{grupo.label}">
                    <q:loop type="array" var="p" items="{grupo.providers}">
                      <q:if condition="emEdicao and edicao.provider == p.provider">
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
              <input id="port" type="number" name="port" class="qa-input" min="0" max="65535" placeholder="provider default" value="{edicao.port if emEdicao else ''}" />
            </div>
          </div>
          <div class="qa-form-row qa-mb-4">
            <div class="qa-form-group">
              <label class="qa-label" for="host">Host</label>
              <input id="host" type="text" name="host" class="qa-input" placeholder="localhost" value="{edicao.host if emEdicao else ''}" />
            </div>
            <div class="qa-form-group">
              <label class="qa-label" for="database">Database</label>
              <input id="database" type="text" name="database" class="qa-input" placeholder="Database, bucket or path" value="{edicao.database if emEdicao else ''}" />
            </div>
          </div>
          <div class="qa-form-row qa-mb-4">
            <div class="qa-form-group">
              <label class="qa-label" for="username">Username</label>
              <input id="username" type="text" name="username" class="qa-input" autocomplete="off" value="{edicao.username if emEdicao else ''}" />
            </div>
            <div class="qa-form-group">
              <label class="qa-label" for="password">Password or API key</label>
              <input id="password" type="password" name="password" class="qa-input" autocomplete="new-password"
                     placeholder="{'saved — leave blank to keep' if emEdicao and edicao.has_password else ''}" />
            </div>
          </div>
          <div class="qa-mb-4">
            <label class="qa-flex qa-items-center" style="gap: 8px;">
              <q:if condition="emEdicao and edicao.is_default">
                <input type="checkbox" name="is_default" value="true" checked="checked" />
              <q:else><input type="checkbox" name="is_default" value="true" /></q:else>
              </q:if>
              <span class="qa-text-sm">Default for this type</span>
            </label>
          </div>
          <button type="submit" class="qa-btn qa-btn-primary">{'Save Changes' if emEdicao else 'Create Connector'}</button>
        </form>
      </div>
    </div>

    <script src="/static/quantum-admin-connectors.js"></script>
  </AdminShell>
</q:component>
