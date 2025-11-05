<q:component name="Login">
  <!-- Phase G: Authentication & Security - Login Page -->

  <q:param name="expired" type="string" default="" />
  <q:param name="flash" type="string" default="" />
  <q:param name="flashType" type="string" default="info" />

  <q:action name="login" method="POST">
    <q:param name="email" type="email" required="true" />
    <q:param name="password" type="string" required="true" minlength="6" />
    <q:param name="rememberMe" type="boolean" default="false" />

    <!-- Mock user authentication (in real app, would query database) -->
    <q:set name="validEmail" value="admin@quantum.dev" />
    <q:set name="validPassword" value="quantum123" />

    <q:if condition="{email} == {validEmail} &amp;&amp; {password} == {validPassword}">
      <!-- Login successful -->
      <q:set name="session.authenticated" value="true" />
      <q:set name="session.userId" value="1" />
      <q:set name="session.userName" value="Admin User" />
      <q:set name="session.userRole" value="admin" />
      <q:set name="session.loginTime" value="2025-11-05 18:30:00" />
      <q:set name="session.sessionExpiry" value="2025-11-06 18:30:00" />

      <!-- Get redirect URL if set, otherwise go to dashboard -->
      <q:set name="redirectUrl" value="/dashboard" />

      <q:redirect url="{redirectUrl}" flash="Welcome back, Admin User!" />
    <q:else />
      <!-- Login failed -->
      <q:redirect url="/login" flash="Invalid email or password. Try admin@quantum.dev / quantum123" flashType="error" />
    </q:if>
  </q:action>

  <html>
  <head>
    <title>Login - Quantum Framework</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0;
        padding: 20px;
      }
      .login-container {
        background: white;
        border-radius: 15px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        padding: 40px;
        max-width: 400px;
        width: 100%;
      }
      h1 {
        margin: 0 0 30px 0;
        color: #333;
        text-align: center;
      }
      .alert {
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 20px;
        font-size: 14px;
      }
      .alert-error {
        background: #fee;
        color: #c33;
        border: 1px solid #fcc;
      }
      .alert-info {
        background: #e7f3ff;
        color: #0066cc;
        border: 1px solid #b3d9ff;
      }
      .alert-warning {
        background: #fff3cd;
        color: #856404;
        border: 1px solid #ffc107;
      }
      .form-group {
        margin-bottom: 20px;
      }
      label {
        display: block;
        margin-bottom: 8px;
        color: #555;
        font-weight: 500;
      }
      input[type="email"],
      input[type="password"] {
        width: 100%;
        padding: 12px;
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        font-size: 16px;
        transition: border-color 0.3s;
        box-sizing: border-box;
      }
      input[type="email"]:focus,
      input[type="password"]:focus {
        outline: none;
        border-color: #667eea;
      }
      .checkbox-group {
        display: flex;
        align-items: center;
        margin-bottom: 20px;
      }
      .checkbox-group input[type="checkbox"] {
        margin-right: 8px;
      }
      button {
        width: 100%;
        padding: 14px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        transition: transform 0.2s;
      }
      button:hover {
        transform: translateY(-2px);
      }
      .demo-info {
        margin-top: 30px;
        padding: 15px;
        background: #f8f9fa;
        border-radius: 8px;
        font-size: 14px;
        color: #666;
      }
      .demo-info strong {
        color: #333;
      }
    </style>
  </head>
  <body>
    <div class="login-container">
      <h1>🔐 Quantum Login</h1>

      <q:if condition="{expired} == 'true'">
        <div class="alert alert-warning">
          Your session has expired. Please login again.
        </div>
      </q:if>

      <q:if condition="{flash} != ''">
        <div class="alert alert-{flashType}">
          {flash}
        </div>
      </q:if>

      <form method="POST" action="/login">
        <div class="form-group">
          <label for="email">Email</label>
          <input
            type="email"
            id="email"
            name="email"
            placeholder="admin@quantum.dev"
            required
            autofocus
          />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input
            type="password"
            id="password"
            name="password"
            placeholder="Enter your password"
            required
            minlength="6"
          />
        </div>

        <div class="checkbox-group">
          <input type="checkbox" id="rememberMe" name="rememberMe" value="true" />
          <label for="rememberMe" style="margin: 0;">Remember me</label>
        </div>

        <button type="submit">Login</button>
      </form>

      <div class="demo-info">
        <strong>📝 Demo Credentials:</strong><br>
        Email: <code>admin@quantum.dev</code><br>
        Password: <code>quantum123</code>
      </div>
    </div>
  </body>
  </html>
</q:component>
