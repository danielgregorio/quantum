<q:component name="SessionDemo">
  <!-- Phase F: Session Management Demo -->

  <!-- Initialize session variables if not set -->
  <q:if condition="{session.visitCount} == ''">
    <q:set name="session.visitCount" value="0" />
  </q:if>

  <q:if condition="{application.totalVisits} == ''">
    <q:set name="application.totalVisits" value="0" />
  </q:if>

  <!-- Increment counters -->
  <q:set name="session.visitCount" value="{session.visitCount + 1}" />
  <q:set name="application.totalVisits" value="{application.totalVisits + 1}" />

  <!-- Store user info in session -->
  <q:set name="session.userName" value="Daniel" />
  <q:set name="session.lastVisit" value="2025-11-05" />

  <html>
  <head>
    <title>Phase F: Session Management Demo</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        max-width: 900px;
        margin: 50px auto;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
      }
      .container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 40px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
      }
      .scope-box {
        background: rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
        border-left: 4px solid #4caf50;
      }
      .scope-box h3 {
        margin-top: 0;
        color: #4caf50;
      }
      .value {
        background: rgba(0, 0, 0, 0.3);
        padding: 5px 10px;
        border-radius: 5px;
        font-family: 'Courier New', monospace;
        display: inline-block;
        margin: 5px 0;
      }
      code {
        background: rgba(0, 0, 0, 0.3);
        padding: 2px 8px;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
      }
      .info {
        background: rgba(33, 150, 243, 0.2);
        border-left: 4px solid #2196f3;
        padding: 15px;
        border-radius: 5px;
        margin: 20px 0;
      }
      button {
        background: #4caf50;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        cursor: pointer;
        font-size: 16px;
        margin: 10px 5px;
      }
      button:hover {
        background: #45a049;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>🔄 Phase F: Session Management</h1>
      <p>ColdFusion-inspired session, application, and request scopes in action!</p>

      <div class="info">
        <strong>💡 How it works:</strong> Refresh this page to see the counters increment.
        Session scope is user-specific (persists across requests),
        Application scope is global (shared by all users),
        Request scope is request-specific (cleared after response).
      </div>

      <!-- Session Scope Demo -->
      <div class="scope-box">
        <h3>📦 Session Scope (User-Specific)</h3>
        <p><strong>Your visit count:</strong> <span class="value">{session.visitCount}</span></p>
        <p><strong>User name:</strong> <span class="value">{session.userName}</span></p>
        <p><strong>Last visit:</strong> <span class="value">{session.lastVisit}</span></p>
        <p><em>These values persist across YOUR requests only (stored in Flask session)</em></p>
        <p><code>&lt;q:set name="session.visitCount" value="{session.visitCount + 1}" /&gt;</code></p>
      </div>

      <!-- Application Scope Demo -->
      <div class="scope-box">
        <h3>🌍 Application Scope (Global)</h3>
        <p><strong>Total visits (all users):</strong> <span class="value">{application.totalVisits}</span></p>
        <p><em>This value is shared across ALL users (global state)</em></p>
        <p><code>&lt;q:set name="application.totalVisits" value="{application.totalVisits + 1}" /&gt;</code></p>
      </div>

      <!-- Request Scope Demo -->
      <div class="scope-box">
        <h3>📨 Request Scope (Request-Specific)</h3>
        <p><strong>HTTP Method:</strong> <span class="value">{request.method}</span></p>
        <p><strong>Current Path:</strong> <span class="value">{request.path}</span></p>
        <p><strong>Full URL:</strong> <span class="value">{request.url}</span></p>
        <p><em>These values are specific to this request only</em></p>
      </div>

      <div class="info">
        <h3>🧪 Try It Out:</h3>
        <ul>
          <li><strong>Refresh this page</strong> - session.visitCount increments (your counter)</li>
          <li><strong>Open in new tab/browser</strong> - session.visitCount starts at 1 (new session)</li>
          <li><strong>Compare tabs</strong> - application.totalVisits is the same (global)</li>
        </ul>
      </div>

      <div style="margin-top: 30px;">
        <button onclick="location.reload()">🔄 Refresh Page</button>
        <button onclick="window.open('/session_demo', '_blank')">🪟 Open in New Tab</button>
        <a href="/" style="color: white; margin-left: 20px;">← Back to Home</a>
      </div>

      <div class="info" style="margin-top: 30px;">
        <h3>✅ Phase F Features Demonstrated:</h3>
        <ul>
          <li>✅ <code>session.variable</code> syntax - user-specific persistent storage</li>
          <li>✅ <code>application.variable</code> syntax - global shared state</li>
          <li>✅ <code>request.variable</code> syntax - request metadata</li>
          <li>✅ Automatic session synchronization with Flask</li>
          <li>✅ ColdFusion-style simplicity and magic</li>
        </ul>
      </div>
    </div>
  </body>
  </html>
</q:component>
