<q:component name="EditorPanel" require_auth="true" require_role="editor">
  <!-- Phase G: RBAC Demo - Editor Panel (requires editor role) -->

  <html>
  <head>
    <title>Editor Panel - Quantum Framework</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: #f5f7fa;
        margin: 0;
        padding: 0;
      }
      .header {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
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
    </style>
  </head>
  <body>
    <div class="header">
      <h1>✏️ Editor Panel</h1>
    </div>

    <div class="container">
      <div class="card">
        <h2>Editor Dashboard</h2>
        <p>This page requires the <strong>editor</strong> role.</p>
        <p>Since you're an admin (not an editor), you shouldn't see this page - you should have gotten a 403 Forbidden error!</p>
      </div>
    </div>
  </body>
  </html>
</q:component>
