<q:component name="AdminAppDetail" require_auth="true" require_role="admin" login_url="/admin/login">
  <!--
    Uma aplicação: /admin/app/<nome>. Cada action acha o projeto pelo `name`
    da URL (ROUTE-2) — a versão anterior confiava em project_id e app_name
    vindos de campos escondidos do formulário. Os serviços estão em
    quantum_admin/services/apps.py, projects.py e connectors.py.

    Saíram desta tela, por nunca terem funcionado: gerar e rodar testes de
    componente do projeto (o gerador importava `core.parser`, que não existe
    desde a troca de src/ para quantum/) e o aviso de "mudanças externas" na
    config. Os testes de componente ficam na tela Components.
  -->
  <q:import component="AdminShell" from="admin/_layout" />

  <!-- ===================================================== projeto -->
  <q:action name="updateProject" method="POST">
    <q:param name="status" type="string" required="true" />
    <q:invoke name="app" service="admin.projects.by_name"><q:param name="name" value="{name}" /></q:invoke>
    <q:invoke name="salvo" service="admin.projects.update" onerror="continue">
      <q:param name="project_id" value="{app.id}" type="integer" />
      <q:param name="name" value="{form.new_name}" />
      <q:param name="description" value="{form.description}" />
      <q:param name="status" value="{status}" />
    </q:invoke>
    <q:if condition="salvo_result.success">
      <q:redirect url="/admin/app/{salvo.name}" flash="Application updated" />
    </q:if>
    <q:flash type="error" message="{salvo_result.error.message}" />
    <q:redirect url="/admin/app/{name}" />
  </q:action>

  <!-- ===================================================== connectors -->
  <q:action name="createProjectConnector" method="POST">
    <q:param name="conn_name" type="string" required="true" />
    <q:param name="conn_type" type="string" required="true" />
    <q:param name="provider" type="string" required="true" />
    <q:param name="port" type="integer" default="0" />
    <q:invoke name="app" service="admin.projects.by_name"><q:param name="name" value="{name}" /></q:invoke>
    <q:invoke name="criado" service="admin.connectors.create" onerror="continue">
      <q:param name="name" value="{conn_name}" />
      <q:param name="type" value="{conn_type}" />
      <q:param name="provider" value="{provider}" />
      <q:param name="host" value="{form.host}" />
      <q:param name="port" value="{port}" type="integer" />
      <q:param name="database" value="{form.database}" />
      <q:param name="username" value="{form.username}" />
      <q:param name="password" value="{form.password}" />
      <q:param name="application_id" value="{app.id}" type="integer" />
    </q:invoke>
    <q:if condition="criado_result.success">
      <q:redirect url="/admin/app/{name}?tab=connectors" flash="Connector {criado.name} created" />
    </q:if>
    <q:flash type="error" message="{criado_result.error.message}" />
    <q:redirect url="/admin/app/{name}?tab=connectors" />
  </q:action>

  <q:action name="testConnector" method="POST">
    <q:param name="connector_id" type="string" required="true" />
    <q:invoke name="teste" service="admin.connectors.test" onerror="continue">
      <q:param name="connector_id" value="{connector_id}" />
    </q:invoke>
    <q:if condition="not teste_result.success">
      <q:flash type="error" message="{teste_result.error.message}" />
      <q:redirect url="/admin/app/{name}?tab=connectors" />
    </q:if>
    <q:if condition="teste.success">
      <q:redirect url="/admin/app/{name}?tab=connectors" flash="Connection OK" />
    </q:if>
    <q:flash type="error" message="Connection failed: {teste.error}" />
    <q:redirect url="/admin/app/{name}?tab=connectors" />
  </q:action>

  <q:action name="detachConnector" method="POST">
    <q:param name="connector_id" type="string" required="true" />
    <q:invoke name="solto" service="admin.connectors.detach" onerror="continue">
      <q:param name="connector_id" value="{connector_id}" />
    </q:invoke>
    <q:if condition="solto_result.success">
      <q:redirect url="/admin/app/{name}?tab=connectors" flash="Connector {solto.name} is now public" />
    </q:if>
    <q:flash type="error" message="{solto_result.error.message}" />
    <q:redirect url="/admin/app/{name}?tab=connectors" />
  </q:action>

  <!-- ===================================================== config -->
  <q:action name="saveProjectConfig" method="POST">
    <q:param name="config_yaml" type="string" />
    <q:invoke name="app" service="admin.projects.by_name"><q:param name="name" value="{name}" /></q:invoke>
    <q:invoke name="gravado" service="admin.projects.save_config" onerror="continue">
      <q:param name="project_id" value="{app.id}" type="integer" />
      <q:param name="config_yaml" value="{form.config_yaml}" />
    </q:invoke>
    <q:if condition="gravado_result.success">
      <q:redirect url="/admin/app/{name}?tab=config" flash="Configuration saved" />
    </q:if>
    <q:flash type="error" message="{gravado_result.error.message}" />
    <q:redirect url="/admin/app/{name}?tab=config" />
  </q:action>

  <!-- ===================================================== ambientes -->
  <q:action name="createEnvironment" method="POST">
    <q:param name="env_name" type="string" required="true" />
    <q:invoke name="app" service="admin.projects.by_name"><q:param name="name" value="{name}" /></q:invoke>
    <q:invoke name="ambiente" service="admin.environments.create" onerror="continue">
      <q:param name="project_id" value="{app.id}" type="integer" />
      <q:param name="name" value="{env_name}" />
    </q:invoke>
    <q:if condition="ambiente_result.success">
      <q:redirect url="/admin/app/{name}?tab=environments" flash="Environment {ambiente.name} created" />
    </q:if>
    <q:flash type="error" message="{ambiente_result.error.message}" />
    <q:redirect url="/admin/app/{name}?tab=environments" />
  </q:action>

  <q:action name="createDefaultEnvironments" method="POST">
    <q:invoke name="app" service="admin.projects.by_name"><q:param name="name" value="{name}" /></q:invoke>
    <q:invoke name="padroes" service="admin.environments.create_defaults">
      <q:param name="project_id" value="{app.id}" type="integer" />
    </q:invoke>
    <q:redirect url="/admin/app/{name}?tab=environments" flash="{len(padroes)} environment(s) created" />
  </q:action>

  <q:action name="updateEnvironment" method="POST">
    <q:param name="environment_id" type="integer" required="true" />
    <q:invoke name="ambiente" service="admin.environments.update" onerror="continue">
      <q:param name="environment_id" value="{environment_id}" type="integer" />
      <q:param name="port" value="{form.port}" />
      <q:param name="branch" value="{form.branch}" />
      <q:param name="variables" value="{form.variables}" />
    </q:invoke>
    <q:if condition="ambiente_result.success">
      <q:redirect url="/admin/app/{name}?tab=environments" flash="Environment {ambiente.name} saved" />
    </q:if>
    <q:flash type="error" message="{ambiente_result.error.message}" />
    <q:redirect url="/admin/app/{name}?tab=environments" />
  </q:action>

  <q:action name="deleteEnvironment" method="POST">
    <q:param name="environment_id" type="integer" required="true" />
    <q:invoke name="removido" service="admin.environments.delete" onerror="continue">
      <q:param name="environment_id" value="{environment_id}" type="integer" />
    </q:invoke>
    <q:if condition="removido_result.success">
      <q:redirect url="/admin/app/{name}?tab=environments" flash="Environment deleted" />
    </q:if>
    <q:flash type="error" message="{removido_result.error.message}" />
    <q:redirect url="/admin/app/{name}?tab=environments" />
  </q:action>

  <!-- ===================================================== servidor -->
  <q:action name="startServer" method="POST">
    <q:invoke name="app" service="admin.projects.by_name"><q:param name="name" value="{name}" /></q:invoke>
    <q:invoke name="subiu" service="admin.servers.start" onerror="continue">
      <q:param name="project_id" value="{app.id}" type="integer" />
    </q:invoke>
    <q:if condition="subiu_result.success">
      <q:redirect url="/admin/app/{name}?tab=runtime" flash="Server started" />
    </q:if>
    <q:flash type="error" message="{subiu_result.error.message}" />
    <q:redirect url="/admin/app/{name}?tab=runtime" />
  </q:action>

  <q:action name="stopServer" method="POST">
    <q:invoke name="app" service="admin.projects.by_name"><q:param name="name" value="{name}" /></q:invoke>
    <q:invoke name="parou" service="admin.servers.stop" onerror="continue">
      <q:param name="project_id" value="{app.id}" type="integer" />
    </q:invoke>
    <q:if condition="parou_result.success">
      <q:redirect url="/admin/app/{name}?tab=runtime" flash="Server stopped" />
    </q:if>
    <q:flash type="error" message="{parou_result.error.message}" />
    <q:redirect url="/admin/app/{name}?tab=runtime" />
  </q:action>

  <!-- ===================================================== dados da página -->
  <q:set name="aba" value="{query.tab}" default="general" />
  <q:set name="abas" type="array" value='[{"id": "general", "label": "General"}, {"id": "connectors", "label": "Connectors"}, {"id": "components", "label": "Components"}, {"id": "config", "label": "Config"}, {"id": "environments", "label": "Environments"}, {"id": "runtime", "label": "Runtime"}]' />
  <q:invoke name="app" service="admin.projects.by_name" onerror="continue">
    <q:param name="name" value="{name}" />
  </q:invoke>
  <q:if condition="app_result.success">
    <q:invoke name="arquivos" service="admin.projects.files">
      <q:param name="project_id" value="{app.id}" type="integer" />
    </q:invoke>
    <q:invoke name="conectores" service="admin.connectors.list">
      <q:param name="application_id" value="{app.id}" type="integer" />
    </q:invoke>
    <q:invoke name="provedores" service="admin.connectors.providers" />
    <q:invoke name="config" service="admin.projects.config">
      <q:param name="project_id" value="{app.id}" type="integer" />
    </q:invoke>
    <q:invoke name="ambientes" service="admin.environments.list">
      <q:param name="project_id" value="{app.id}" type="integer" />
    </q:invoke>
    <!-- sem quantum.config.yaml o status é erro: a aba Runtime diz o motivo -->
    <q:invoke name="servidor" service="admin.servers.status" onerror="continue">
      <q:param name="project_id" value="{app.id}" type="integer" />
    </q:invoke>
    <q:invoke name="log" service="admin.servers.log">
      <q:param name="project_id" value="{app.id}" type="integer" />
    </q:invoke>
  </q:if>

  <AdminShell title="{app.name if app_result.success else 'Application'}" active="applications" flash="{flash}" flashType="{flashType}">

    <q:if condition="not app_result.success">
      <div class="qa-card">
        <div class="qa-empty">
          <div class="qa-empty-title">Application Not Found</div>
          <div class="qa-empty-text">{app_result.error.message}</div>
          <a href="/admin/applications" class="qa-btn qa-btn-primary">Back to Applications</a>
        </div>
      </div>
    </q:if>

    <q:if condition="app_result.success">
      <div class="qa-flex qa-items-center qa-mb-4" style="gap: 12px;">
        <a href="/admin/applications" class="qa-text-sm">Applications</a>
        <span class="{'qa-badge qa-badge-success' if app.status == 'active' else ('qa-badge qa-badge-danger' if app.status == 'error' else 'qa-badge qa-badge-gray')}">{app.status}</span>
        <span class="{'qa-process-running' if servidor_result.success and servidor.running else 'qa-process-stopped'}">{'Running' if servidor_result.success and servidor.running else 'Stopped'}</span>
      </div>

      <q:loop type="array" var="t" items="{abas}">
        <q:if condition="t.id == aba">
          <input type="radio" name="tab" id="tab-{t.id}" class="qa-tab-radio" checked="checked" />
        <q:else><input type="radio" name="tab" id="tab-{t.id}" class="qa-tab-radio" /></q:else>
        </q:if>
      </q:loop>
      <div class="qa-tabs-bar">
        <q:loop type="array" var="t" items="{abas}">
          <label for="tab-{t.id}" class="qa-tab-label">{t.label}</label>
        </q:loop>
      </div>

      <div class="qa-tabs-content">

        <!-- ============================ General -->
        <div class="qa-panel-general">
          <div class="qa-grid qa-grid-4 qa-mb-6">
            <div class="qa-stat-card"><div class="qa-stat-label">Components</div><div class="qa-stat-value">{len(arquivos.components)}</div></div>
            <div class="qa-stat-card"><div class="qa-stat-label">Size on Disk</div><div class="qa-stat-value">{arquivos.disk_size}</div></div>
            <div class="qa-stat-card"><div class="qa-stat-label">Environments</div><div class="qa-stat-value">{len(ambientes)}</div></div>
            <div class="qa-stat-card"><div class="qa-stat-label">Static Files</div><div class="qa-stat-value">{arquivos.static_files}</div></div>
          </div>

          <div class="qa-card qa-mb-6">
            <div class="qa-card-header"><div class="qa-card-title">Application</div></div>
            <div class="qa-card-body">
              <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Source path</span><span class="qa-font-mono qa-text-sm">{app.source_path}</span></div>
              <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Port</span><span class="qa-font-mono qa-text-sm">{app.port or '-'}</span></div>
              <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Created</span><span class="qa-text-sm">{app.created_at}</span></div>
              <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Updated</span><span class="qa-text-sm">{app.updated_at}</span></div>
            </div>
          </div>

          <div class="qa-card">
            <div class="qa-card-header"><div class="qa-card-title">Edit Application</div></div>
            <div class="qa-card-body">
              <form method="POST" action="/admin/app/{app.name}">
                <input type="hidden" name="action" value="updateProject" />
                <div class="qa-form-row qa-mb-4">
                  <div class="qa-form-group">
                    <label class="qa-label" for="new_name">Name</label>
                    <input id="new_name" type="text" name="new_name" class="qa-input" value="{app.name}" minlength="2" required="" />
                  </div>
                  <div class="qa-form-group">
                    <label class="qa-label" for="status">Status</label>
                    <select id="status" name="status" class="qa-input qa-select">
                      <q:loop type="array" var="estado" items="{['active', 'archived', 'error']}">
                        <q:if condition="estado == app.status">
                          <option value="{estado}" selected="selected">{estado}</option>
                        <q:else><option value="{estado}">{estado}</option></q:else>
                        </q:if>
                      </q:loop>
                    </select>
                  </div>
                </div>
                <div class="qa-form-group qa-mb-4">
                  <label class="qa-label" for="description">Description</label>
                  <input id="description" type="text" name="description" class="qa-input" value="{app.description}" />
                </div>
                <button type="submit" class="qa-btn qa-btn-primary">Save Changes</button>
              </form>
            </div>
          </div>
        </div>

        <!-- ============================ Connectors -->
        <div class="qa-panel-connectors">
          <div class="qa-card qa-mb-6">
            <div class="qa-card-header">
              <div>
                <div class="qa-card-title">Connectors</div>
                <div class="qa-card-subtitle">This application's own, and the public ones every application can use</div>
              </div>
            </div>
            <div class="qa-card-body qa-p-0" style="overflow-x: auto;">
              <q:if condition="len(conectores) &gt; 0">
                <table class="qa-table">
                  <thead><tr><th>Name</th><th>Provider</th><th>Host:Port</th><th>Status</th><th>Scope</th><th></th></tr></thead>
                  <tbody>
                    <q:loop type="array" var="conn" items="{conectores}">
                      <tr>
                        <td><span class="qa-font-medium">{conn.name}</span> <span class="qa-badge qa-type-{conn.type}">{conn.type_label}</span></td>
                        <td><span class="qa-text-sm">{conn.provider_name}</span></td>
                        <td><span class="qa-font-mono qa-text-sm">{conn.host}:{conn.port}</span></td>
                        <td><div class="qa-status-badge"><span class="qa-status-dot {conn.status}"></span><span class="qa-status-text">{conn.status}</span></div></td>
                        <td><span class="qa-text-sm qa-text-muted">{'this application' if conn.application_id else 'public'}</span></td>
                        <td>
                          <div class="qa-flex" style="gap: 4px;">
                            <form method="POST" action="/admin/app/{app.name}" style="margin: 0;">
                              <input type="hidden" name="action" value="testConnector" />
                              <input type="hidden" name="connector_id" value="{conn.id}" />
                              <button type="submit" class="qa-btn qa-btn-ghost qa-btn-sm">Test</button>
                            </form>
                            <q:if condition="conn.application_id">
                              <form method="POST" action="/admin/app/{app.name}" style="margin: 0;" onsubmit="return confirm('Make this connector public? Every application will be able to use it.');">
                                <input type="hidden" name="action" value="detachConnector" />
                                <input type="hidden" name="connector_id" value="{conn.id}" />
                                <button type="submit" class="qa-btn qa-btn-ghost qa-btn-sm">Make Public</button>
                              </form>
                            </q:if>
                          </div>
                        </td>
                      </tr>
                    </q:loop>
                  </tbody>
                </table>
              </q:if>
              <q:if condition="len(conectores) == 0">
                <div class="qa-empty"><div class="qa-empty-title">No Connectors</div><div class="qa-empty-text">Create one below, or a public one on the Connectors page.</div></div>
              </q:if>
            </div>
          </div>

          <div class="qa-card">
            <div class="qa-card-header"><div class="qa-card-title">New Connector for {app.name}</div></div>
            <div class="qa-card-body">
              <form method="POST" action="/admin/app/{app.name}">
                <input type="hidden" name="action" value="createProjectConnector" />
                <div class="qa-form-row qa-mb-4">
                  <div class="qa-form-group">
                    <label class="qa-label" for="conn_name">Name</label>
                    <input id="conn_name" type="text" name="conn_name" class="qa-input" placeholder="e.g. App Redis" required="" />
                  </div>
                  <div class="qa-form-group">
                    <label class="qa-label" for="conn_type">Type</label>
                    <select id="conn_type" name="conn_type" class="qa-input qa-select" required="">
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
                    <label class="qa-label" for="provider">Provider</label>
                    <select id="provider" name="provider" class="qa-input qa-select" required="">
                      <option value="">Select provider...</option>
                      <q:loop type="array" var="p" items="{provedores}">
                        <option value="{p.provider}">{p.name}</option>
                      </q:loop>
                    </select>
                  </div>
                  <div class="qa-form-group">
                    <label class="qa-label" for="port">Port</label>
                    <input id="port" type="number" name="port" class="qa-input" min="0" max="65535" placeholder="provider default" />
                  </div>
                </div>
                <div class="qa-form-row qa-mb-4">
                  <div class="qa-form-group">
                    <label class="qa-label" for="host">Host</label>
                    <input id="host" type="text" name="host" class="qa-input" placeholder="localhost" />
                  </div>
                  <div class="qa-form-group">
                    <label class="qa-label" for="database">Database</label>
                    <input id="database" type="text" name="database" class="qa-input" />
                  </div>
                </div>
                <div class="qa-form-row qa-mb-4">
                  <div class="qa-form-group">
                    <label class="qa-label" for="username">Username</label>
                    <input id="username" type="text" name="username" class="qa-input" autocomplete="off" />
                  </div>
                  <div class="qa-form-group">
                    <label class="qa-label" for="password">Password or API key</label>
                    <input id="password" type="password" name="password" class="qa-input" autocomplete="new-password" />
                  </div>
                </div>
                <button type="submit" class="qa-btn qa-btn-primary">Create Connector</button>
              </form>
            </div>
          </div>
        </div>

        <!-- ============================ Components -->
        <div class="qa-panel-components">
          <div class="qa-card">
            <div class="qa-card-header">
              <div>
                <div class="qa-card-title">Components and Routes</div>
                <div class="qa-card-subtitle">{len(arquivos.components)} .q files in {app.source_path}/components</div>
              </div>
            </div>
            <div class="qa-card-body qa-p-0" style="overflow-x: auto;">
              <q:if condition="len(arquivos.components) &gt; 0">
                <table class="qa-table">
                  <thead><tr><th>Route</th><th>Component</th><th>File</th><th>Lines</th><th>Tags</th></tr></thead>
                  <tbody>
                    <q:loop type="array" var="comp" items="{arquivos.components}">
                      <tr>
                        <td><span class="qa-font-mono qa-font-medium">{comp.route}</span> <q:if condition="comp.dynamic"><span class="qa-badge qa-badge-info">dynamic</span></q:if></td>
                        <td>{comp.name}</td>
                        <td><a href="/admin/source?file={comp.source}" class="qa-font-mono qa-text-sm">{comp.path}</a></td>
                        <td style="font-variant-numeric: tabular-nums;">{comp.lines}</td>
                        <td><span class="qa-text-sm qa-text-muted">{join(comp.tags, ', ') if comp.tags else '-'}</span></td>
                      </tr>
                    </q:loop>
                  </tbody>
                </table>
              </q:if>
              <q:if condition="len(arquivos.components) == 0">
                <div class="qa-empty"><div class="qa-empty-title">No Components</div><div class="qa-empty-text">Add .q files to {app.source_path}/components; each one is served at the route shown here.</div></div>
              </q:if>
            </div>
          </div>
        </div>

        <!-- ============================ Config -->
        <div class="qa-panel-config">
          <q:if condition="config.error">
            <div class="qa-flash qa-flash-error" role="alert">The file on disk is not valid YAML: {config.error}</div>
          </q:if>
          <div class="qa-card">
            <div class="qa-card-header">
              <div>
                <div class="qa-card-title">quantum.config.yaml</div>
                <div class="qa-card-subtitle qa-font-mono">{config.path}</div>
              </div>
            </div>
            <div class="qa-card-body">
              <form method="POST" action="/admin/app/{app.name}">
                <input type="hidden" name="action" value="saveProjectConfig" />
                <label class="qa-label" for="config_yaml">YAML</label>
                <textarea id="config_yaml" name="config_yaml" class="qa-config-editor" rows="20" spellcheck="false">{config.text}</textarea>
                <div class="qa-input-hint qa-mb-4">Saved exactly as written, comments included. Invalid YAML, or YAML that is not a mapping, is refused and the file is left as it was.</div>
                <button type="submit" class="qa-btn qa-btn-primary">Save Configuration</button>
              </form>
            </div>
          </div>
        </div>

        <!-- ============================ Environments -->
        <div class="qa-panel-environments">
          <div class="qa-card qa-mb-6">
            <div class="qa-card-header"><div class="qa-card-title">New Environment</div></div>
            <div class="qa-card-body">
              <form method="POST" action="/admin/app/{app.name}" class="qa-flex qa-items-center" style="gap: 8px; flex-wrap: wrap;">
                <input type="hidden" name="action" value="createEnvironment" />
                <label class="qa-label" for="env_name">Name</label>
                <input id="env_name" type="text" name="env_name" class="qa-input" placeholder="staging" required="" style="max-width: 240px;" />
                <button type="submit" class="qa-btn qa-btn-primary">Create</button>
              </form>
              <q:if condition="len(ambientes) == 0">
                <form method="POST" action="/admin/app/{app.name}" style="margin-top: 12px;">
                  <input type="hidden" name="action" value="createDefaultEnvironments" />
                  <button type="submit" class="qa-btn qa-btn-secondary qa-btn-sm">Create development, staging and production</button>
                </form>
              </q:if>
            </div>
          </div>

          <q:loop type="array" var="env" items="{ambientes}">
            <div class="qa-env-card qa-mb-4">
              <div class="qa-flex qa-items-center qa-justify-between qa-mb-4">
                <div>
                  <span class="qa-font-semibold qa-text-lg">{env.display_name or env.name}</span>
                  <span class="qa-text-xs qa-text-muted">{len(env.variables)} variables</span>
                </div>
                <form method="POST" action="/admin/app/{app.name}" style="margin: 0;" onsubmit="return confirm('Delete this environment?');">
                  <input type="hidden" name="action" value="deleteEnvironment" />
                  <input type="hidden" name="environment_id" value="{env.id}" />
                  <button type="submit" class="qa-btn qa-btn-danger qa-btn-sm" aria-label="Delete {env.name}">Delete</button>
                </form>
              </div>
              <form method="POST" action="/admin/app/{app.name}">
                <input type="hidden" name="action" value="updateEnvironment" />
                <input type="hidden" name="environment_id" value="{env.id}" />
                <div class="qa-form-group qa-mb-4">
                  <label class="qa-label" for="variables_{env.id}">Variables (NAME=value, one per line)</label>
                  <textarea id="variables_{env.id}" name="variables" class="qa-input qa-textarea" rows="4">{env.variables_text}</textarea>
                </div>
                <div class="qa-form-row qa-mb-4">
                  <div class="qa-form-group">
                    <label class="qa-label" for="port_{env.id}">Port</label>
                    <input id="port_{env.id}" type="number" name="port" class="qa-input" value="{env.port or ''}" />
                  </div>
                  <div class="qa-form-group">
                    <label class="qa-label" for="branch_{env.id}">Branch</label>
                    <input id="branch_{env.id}" type="text" name="branch" class="qa-input" value="{env.branch or ''}" />
                  </div>
                </div>
                <button type="submit" class="qa-btn qa-btn-secondary qa-btn-sm">Save Environment</button>
              </form>
            </div>
          </q:loop>
        </div>

        <!-- ============================ Runtime -->
        <div class="qa-panel-runtime">
          <div class="qa-card qa-mb-6">
            <div class="qa-card-header">
              <div class="qa-card-title">Server</div>
            </div>
            <div class="qa-card-body">
              <q:if condition="not servidor_result.success">
                <div class="qa-text-sm qa-text-muted">{servidor_result.error.message}</div>
              </q:if>
              <q:if condition="servidor_result.success">
                <div class="qa-flex qa-items-center qa-justify-between qa-mb-4"><span class="qa-text-sm qa-text-muted">Port</span><span class="qa-font-mono qa-text-sm">{app.port or 8080}</span></div>
                <q:if condition="servidor.running">
                  <div class="qa-flex qa-items-center qa-justify-between qa-mb-4"><span class="qa-text-sm qa-text-muted">PID</span><span class="qa-font-mono qa-text-sm">{join(servidor.pids, ', ')}</span></div>
                  <form method="POST" action="/admin/app/{app.name}" onsubmit="return confirm('Stop the running server?');">
                    <input type="hidden" name="action" value="stopServer" />
                    <button type="submit" class="qa-btn qa-btn-danger">Stop Server</button>
                  </form>
                <q:else>
                  <form method="POST" action="/admin/app/{app.name}">
                    <input type="hidden" name="action" value="startServer" />
                    <button type="submit" class="qa-btn qa-btn-success">Start Server</button>
                  </form>
                </q:else>
                </q:if>
              </q:if>
            </div>
          </div>
          <div class="qa-card">
            <div class="qa-card-header"><div class="qa-card-title">Log</div><div class="qa-card-subtitle">last 50 lines</div></div>
            <div class="qa-card-body">
              <q:if condition="log.text">
                <pre class="qa-log-viewer">{log.text}</pre>
              <q:else>
                <div class="qa-text-sm qa-text-muted">Nothing logged yet. Start the server to see its output here.</div>
              </q:else>
              </q:if>
            </div>
          </div>
        </div>

      </div>
    </q:if>

    <script src="/static/quantum-admin-connectors.js"></script>
  </AdminShell>
</q:component>
