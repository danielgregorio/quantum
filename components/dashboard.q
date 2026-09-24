<q:component name="Dashboard" require_auth="true">
  <!-- Phase G: Protected Dashboard - Requires Authentication -->

  <q:param name="flash" type="string" default="" />
  <q:param name="flashType" type="string" default="success" />

  <html>
  <head>
    <title>Dashboard - Quantum Framework</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: #f5f7fa;
        margin: 0;
        padding: 0;
      }
      .header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px 40px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      }
      .header h1 {
        margin: 0;
        font-size: 24px;
      }
      .header p {
        margin: 5px 0 0 0;
        opacity: 0.9;
      }
      .container {
        max-width: 1200px;
        margin: 40px auto;
        padding: 0 20px;
      }
      .alert {
        padding: 15px 20px;
        border-radius: 8px;
        margin-bottom: 30px;
        font-size: 14px;
      }
      .alert-success {
        background: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
      }
      .card {
        background: white;
        border-radius: 12px;
        padding: 30px;
        margin-bottom: 30px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      }
      .card h2 {
        margin: 0 0 20px 0;
        color: #333;
      }
      .info-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
      }
      .info-item {
        padding: 15px;
        background: #f8f9fa;
        border-radius: 8px;
        border-left: 4px solid #667eea;
      }
      .info-label {
        font-size: 12px;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 5px;
      }
      .info-value {
        font-size: 18px;
        font-weight: 600;
        color: #333;
      }
      .logout-btn {
        display: inline-block;
        padding: 12px 24px;
        background: #dc3545;
        color: white;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
        transition: background 0.3s;
      }
      .logout-btn:hover {
        background: #c82333;
      }
      .feature-list {
        list-style: none;
        padding: 0;
      }
      .feature-list li {
        padding: 10px 0;
        border-bottom: 1px solid #e0e0e0;
      }
      .feature-list li:last-child {
        border-bottom: none;
      }
      .feature-list li:before {
        content: "✅ ";
        margin-right: 8px;
      }
    </style>
  </head>
  <body>
    <div class="header">
      <h1>🎛️ Dashboard</h1>
      <p>Welcome, {session.userName}!</p>
    </div>

    <div class="container">
      <q:if condition="{flash} != ''">
        <div class="alert alert-{flashType}">
          {flash}
        </div>
      </q:if>

      <div class="card">
        <h2>👤 Session Information</h2>
        <div class="info-grid">
          <div class="info-item">
            <div class="info-label">User ID</div>
            <div class="info-value">{session.userId}</div>
          </div>
          <div class="info-item">
            <div class="info-label">User Name</div>
            <div class="info-value">{session.userName}</div>
          </div>
          <div class="info-item">
            <div class="info-label">Role</div>
            <div class="info-value">{session.userRole}</div>
          </div>
          <div class="info-item">
            <div class="info-label">Login Time</div>
            <div class="info-value">{session.loginTime}</div>
          </div>
        </div>
      </div>

      <div class="card">
        <h2>🔐 Phase G Features Demonstrated</h2>
        <ul class="feature-list">
          <li><code>require_auth="true"</code> - This component requires authentication</li>
          <li>Session-based authentication using <code>session.authenticated</code></li>
          <li>User info stored in session scope (<code>session.userId</code>, <code>session.userName</code>)</li>
          <li>Role-based access control (RBAC) ready (<code>session.userRole</code>)</li>
          <li>Automatic redirect to /login for unauthenticated users</li>
          <li>Session expiry checking (24h default, 30d with remember me)</li>
          <li>Flash messages for user feedback</li>
        </ul>
      </div>

      <div class="card">
        <h2>🧪 Try These Features:</h2>
        <ul class="feature-list">
          <li><a href="/admin_panel">Admin Panel</a> - Requires "admin" role (you have it!)</li>
          <li><a href="/editor_panel">Editor Panel</a> - Requires "editor" role (you don't have it - will get 403)</li>
          <li><a href="/logout">Logout</a> - Clear session and return to login</li>
        </ul>
      </div>

      <div class="card">
        <a href="/logout" class="logout-btn">🚪 Logout</a>
      </div>
    </div>
  </body>
  </html>
</q:component>
