<q:component name="AdminLogin">
  <!--
    Login do admin. Usa as mesmas credenciais do FastAPI (admin.auth.login:
    ADMIN_PASSWORD, ou a senha gerada e impressa na subida), com bloqueio
    depois de tentativas erradas seguidas. Grava na sessão o que AUTH-1 exige.
  -->
  <q:action name="signIn" method="POST">
    <q:param name="username" type="string" required="true" />
    <q:param name="password" type="string" required="true" />

    <q:invoke name="auth" service="admin.auth.login">
      <q:param name="username" value="{username}" />
      <q:param name="password" value="{password}" />
    </q:invoke>

    <q:if condition="auth.ok">
      <q:set name="session.authenticated" value="true" type="boolean" />
      <q:set name="session.userName" value="{auth.username}" />
      <q:set name="session.userRole" value="{auth.role}" />
      <q:set name="session.sessionExpiry" value="{dateAdd('h', auth.expires_in_hours)}" />
      <q:redirect url="/admin/applications" />
    </q:if>

    <q:flash type="error" message="{auth.error}" />
    <q:redirect url="/admin/login" />
  </q:action>

  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Sign in - Quantum Admin</title>
    <link rel="stylesheet" href="/static/quantum-admin.css" />
  </head>
  <body>
    <main class="qa-login">
      <div class="qa-card qa-login-card">
        <div class="qa-card-header">
          <div class="qa-sidebar-logo-icon">Q</div>
          <div class="qa-card-title">Quantum Admin</div>
        </div>
        <div class="qa-card-body">
          <q:if condition="flash">
            <div class="{'qa-flash qa-flash-error' if flashType == 'error' else 'qa-flash qa-flash-success'}" role="alert">{flash}</div>
          </q:if>
          <q:if condition="query.expired">
            <div class="qa-flash qa-flash-error" role="alert">Your session expired. Sign in again.</div>
          </q:if>
          <form method="POST" action="/admin/login">
            <div class="qa-form-group qa-mb-4">
              <label class="qa-label" for="username">User</label>
              <input id="username" type="text" name="username" class="qa-input" autocomplete="username" required="" autofocus="" />
            </div>
            <div class="qa-form-group qa-mb-4">
              <label class="qa-label" for="password">Password</label>
              <input id="password" type="password" name="password" class="qa-input" autocomplete="current-password" required="" />
            </div>
            <button type="submit" class="qa-btn qa-btn-primary">Sign in</button>
          </form>
        </div>
      </div>
    </main>
  </body>
  </html>
</q:component>
