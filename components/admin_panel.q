<q:component name="AdminPanel" require_auth="true" require_role="admin">
  <!-- Phase G: RBAC Demo - Admin Panel (requires admin role) -->

  <html>
  <head>
    <title>Admin Panel - Quantum Framework</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: #f5f7fa;
        margin: 0;
        padding: 0;
      }
      .header {
        background: linear-gradient(135deg, #fc5c7d 0%, #6a82fb 100%);
        color: white;
        padding: 20px 40px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      }
      .header h1 {
        margin: 0;
        font-size: 24px;
      }
      .container {
        max-width: 1200px;
        margin: 40px auto;
        padding: 0 20px;
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
      .success-badge {
        display: inline-block;
        padding: 8px 16px;
        background: #d4edda;
        color: #155724;
        border-radius: 20px;
        font-weight: 600;
        margin-bottom: 20px;
      }
      .back-link {
        display: inline-block;
        padding: 10px 20px;
        background: #667eea;
        color: white;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
      }
      .back-link:hover {
        background: #5568d3;
      }
    </style>
  </head>
  <body>
    <div class="header">
      <h1>👑 Admin Panel</h1>
    </div>

    <div class="container">
      <div class="card">
        <span class="success-badge">✅ Access Granted</span>
        <h2>Welcome, Administrator!</h2>
        <p>You have successfully accessed the Admin Panel because you have the <strong>admin</strong> role.</p>
        <p><strong>Your role:</strong> {session.userRole}</p>

        <h3>🔐 How RBAC Works:</h3>
        <ul>
          <li>This component has <code>require_role="admin"</code> attribute</li>
          <li>Your session has <code>session.userRole = "admin"</code></li>
          <li>The web server checked your role before rendering this page</li>
          <li>If you didn't have the admin role, you'd see a 403 Forbidden page</li>
        </ul>

        <a href="/dashboard" class="back-link">← Back to Dashboard</a>
      </div>
    </div>
  </body>
  </html>
</q:component>
