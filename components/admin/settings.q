<q:component name="AdminSettings" require_auth="true" require_role="admin" login_url="/admin/login">
  <!--
    quantum.config.yaml da raiz (admin.settings.*) e o ambiente
    (admin.system.info). Salvar muda só as linhas dos valores e mantém os
    comentários; a versão anterior regravava o arquivo inteiro com yaml.dump.
    O formulário vem preenchido com o que está no arquivo — antes vinha com
    debug desligado, log INFO e TTL 300, e salvar trocava esses valores sem
    ninguém ter mexido neles.
  -->
  <q:import component="AdminShell" from="admin" />

  <q:action name="saveSettings" method="POST">
    <q:param name="port" type="integer" required="true" />
    <q:param name="host" type="string" required="true" />
    <q:param name="debug" type="boolean" default="false" />
    <q:param name="reload" type="boolean" default="false" />
    <q:param name="cache_templates" type="boolean" default="false" />
    <q:param name="cache_ttl" type="integer" default="0" />
    <q:param name="log_level" type="string" required="true" />
    <q:param name="xss_protection" type="boolean" default="false" />
    <q:param name="cors_enabled" type="boolean" default="false" />
    <q:invoke name="salvo" service="admin.settings.save_server_config" onerror="continue">
      <q:param name="port" value="{port}" type="integer" />
      <q:param name="host" value="{host}" />
      <q:param name="debug" value="{debug}" type="boolean" />
      <q:param name="reload" value="{reload}" type="boolean" />
      <q:param name="cache_templates" value="{cache_templates}" type="boolean" />
      <q:param name="cache_ttl" value="{cache_ttl}" type="integer" />
      <q:param name="log_level" value="{log_level}" />
      <q:param name="xss_protection" value="{xss_protection}" type="boolean" />
      <q:param name="cors_enabled" value="{cors_enabled}" type="boolean" />
    </q:invoke>
    <q:if condition="salvo_result.success">
      <q:redirect url="/admin/settings" flash="Saved. The server reads quantum.config.yaml when it starts: restart it to apply." />
    </q:if>
    <q:flash type="error" message="{salvo_result.error.message}" />
    <q:redirect url="/admin/settings" />
  </q:action>

  <q:invoke name="cfg" service="admin.settings.server_config" />
  <q:invoke name="sistema" service="admin.system.info" />

  <AdminShell title="Settings" active="settings" flash="{flash}" flashType="{flashType}">

    <q:if condition="not cfg.found">
      <div class="qa-flash qa-flash-error" role="alert">There is no quantum.config.yaml in {sistema.root}.</div>
    </q:if>
    <q:if condition="cfg.error">
      <div class="qa-flash qa-flash-error" role="alert">quantum.config.yaml is not valid YAML: {cfg.error}</div>
    </q:if>

    <q:if condition="cfg.server">
      <div class="qa-grid qa-grid-2 qa-mb-6">
        <div class="qa-card">
          <div class="qa-card-header"><div class="qa-card-title">Paths</div></div>
          <div class="qa-card-body">
            <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Components</span><span class="qa-font-mono">{cfg.paths.components}</span></div>
            <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Static</span><span class="qa-font-mono">{cfg.paths.static}</span></div>
            <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Logs</span><span class="qa-font-mono">{cfg.paths.logs}</span></div>
          </div>
        </div>

        <div class="qa-card">
          <div class="qa-card-header"><div class="qa-card-title">Declared</div></div>
          <div class="qa-card-body">
            <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Datasources</span><span class="qa-font-mono">{join(cfg.datasources, ', ') if cfg.datasources else '-'}</span></div>
            <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Service modules</span><span class="qa-font-mono">{len(cfg.services)}</span></div>
            <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">LLM base URL</span><span class="qa-font-mono">{cfg.llm.base_url if 'base_url' in cfg.llm else '-'}</span></div>
          </div>
        </div>
      </div>

      <div class="qa-card qa-mb-6">
        <div class="qa-card-header">
          <div>
            <div class="qa-card-title">Server Configuration</div>
            <div class="qa-card-subtitle qa-font-mono">{cfg.path}</div>
          </div>
        </div>
        <div class="qa-card-body">
          <form method="POST" action="/admin/settings">
            <input type="hidden" name="action" value="saveSettings" />
            <div class="qa-grid qa-grid-2" style="gap: 24px;">
              <div>
                <div class="qa-form-group qa-mb-4">
                  <label class="qa-label" for="port">Port</label>
                  <input id="port" type="number" name="port" class="qa-input" value="{cfg.server.port}" min="1" max="65535" required="" />
                </div>
                <div class="qa-form-group qa-mb-4">
                  <label class="qa-label" for="host">Host</label>
                  <input id="host" type="text" name="host" class="qa-input" value="{cfg.server.host}" required="" />
                  <div class="qa-text-xs qa-text-muted">127.0.0.1 keeps the server reachable only from this machine.</div>
                </div>
                <div class="qa-flex qa-items-center qa-mb-4" style="gap: 8px;">
                  <q:if condition="cfg.server.debug">
                    <input type="checkbox" name="debug" id="debug" value="true" checked="checked" />
                  <q:else><input type="checkbox" name="debug" id="debug" value="true" /></q:else>
                  </q:if>
                  <label for="debug" class="qa-text-sm">Debug mode (only with a loopback host)</label>
                </div>
                <div class="qa-flex qa-items-center qa-mb-4" style="gap: 8px;">
                  <q:if condition="cfg.server.reload">
                    <input type="checkbox" name="reload" id="reload" value="true" checked="checked" />
                  <q:else><input type="checkbox" name="reload" id="reload" value="true" /></q:else>
                  </q:if>
                  <label for="reload" class="qa-text-sm">Auto-reload</label>
                </div>
              </div>

              <div>
                <div class="qa-form-group qa-mb-4">
                  <label class="qa-label" for="log_level">Log level</label>
                  <select id="log_level" name="log_level" class="qa-input">
                    <q:loop type="array" var="nivel" items="{['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']}">
                      <q:if condition="upper(cfg.logging.level) == nivel">
                        <option value="{nivel}" selected="selected">{nivel}</option>
                      <q:else><option value="{nivel}">{nivel}</option></q:else>
                      </q:if>
                    </q:loop>
                  </select>
                </div>
                <div class="qa-form-group qa-mb-4">
                  <label class="qa-label" for="cache_ttl">Template cache TTL (seconds)</label>
                  <input id="cache_ttl" type="number" name="cache_ttl" class="qa-input" value="{cfg.performance.cache_ttl}" min="0" />
                </div>
                <div class="qa-flex qa-items-center qa-mb-4" style="gap: 8px;">
                  <q:if condition="cfg.performance.cache_templates">
                    <input type="checkbox" name="cache_templates" id="cache_templates" value="true" checked="checked" />
                  <q:else><input type="checkbox" name="cache_templates" id="cache_templates" value="true" /></q:else>
                  </q:if>
                  <label for="cache_templates" class="qa-text-sm">Template cache</label>
                </div>
                <div class="qa-flex qa-items-center qa-mb-4" style="gap: 8px;">
                  <q:if condition="cfg.security.xss_protection">
                    <input type="checkbox" name="xss_protection" id="xss_protection" value="true" checked="checked" />
                  <q:else><input type="checkbox" name="xss_protection" id="xss_protection" value="true" /></q:else>
                  </q:if>
                  <label for="xss_protection" class="qa-text-sm">XSS protection</label>
                </div>
                <div class="qa-flex qa-items-center qa-mb-4" style="gap: 8px;">
                  <q:if condition="cfg.security.cors_enabled">
                    <input type="checkbox" name="cors_enabled" id="cors_enabled" value="true" checked="checked" />
                  <q:else><input type="checkbox" name="cors_enabled" id="cors_enabled" value="true" /></q:else>
                  </q:if>
                  <label for="cors_enabled" class="qa-text-sm">CORS</label>
                </div>
              </div>
            </div>
            <button type="submit" class="qa-btn qa-btn-primary">Save Settings</button>
          </form>
        </div>
      </div>
    </q:if>

    <div class="qa-card">
      <div class="qa-card-header"><div class="qa-card-title">Runtime</div></div>
      <div class="qa-card-body">
        <div class="qa-grid qa-grid-2">
          <div>
            <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Quantum</span><span class="qa-font-mono">{sistema.quantum_version or 'not installed (running from a clone)'}</span></div>
            <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Python</span><span class="qa-font-mono">{sistema.python_version}</span></div>
            <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Platform</span><span class="qa-font-mono">{sistema.platform}</span></div>
          </div>
          <div>
            <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Project root</span><span class="qa-font-mono">{sistema.root}</span></div>
            <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Tags with a parser</span><span class="qa-font-mono">{sistema.parser_tags}</span></div>
            <div class="qa-flex qa-items-center qa-justify-between"><span class="qa-text-sm qa-text-muted">Executors</span><span class="qa-font-mono">{sistema.executors}</span></div>
          </div>
        </div>
      </div>
    </div>

  </AdminShell>
</q:component>
