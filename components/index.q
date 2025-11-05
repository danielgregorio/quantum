<!-- Quantum Home Page - Simple HTML rendering example -->
<q:component name="HomePage">
  <q:set name="title" value="Welcome to Quantum!" />
  <q:set name="subtitle" value="HTML Rendering Phase 1 Complete" />
  <q:set name="version" value="1.0.0" />

  <!DOCTYPE html>
  <html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        max-width: 1000px;
        margin: 0 auto;
        padding: 40px 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
      }
      .container {
        background: white;
        border-radius: 15px;
        padding: 40px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
      }
      h1 {
        color: #667eea;
        font-size: 3em;
        margin: 0 0 10px 0;
      }
      .subtitle {
        color: #666;
        font-size: 1.3em;
        margin-bottom: 30px;
      }
      .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin: 30px 0;
      }
      .feature-card {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #667eea;
      }
      .feature-card h3 {
        margin-top: 0;
        color: #667eea;
      }
      .demo-box {
        background: #e8f5e9;
        border: 2px dashed #4caf50;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
      }
      .badge {
        background: #4caf50;
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.9em;
        font-weight: bold;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>🚀 {title}</h1>
      <p class="subtitle">{subtitle}</p>
      <p><span class="badge">v{version}</span></p>

      <div class="demo-box">
        <h2>✨ This page was rendered by Quantum!</h2>
        <p>This HTML was generated from a <code>.q</code> component with full databinding support.</p>
      </div>

      <h2>🎯 Features Implemented</h2>
      <div class="feature-grid">
        <div class="feature-card">
          <h3>✅ HTML Rendering</h3>
          <p>Write HTML directly in .q components</p>
        </div>

        <div class="feature-card">
          <h3>✅ Databinding</h3>
          <p>Use {variable} syntax for dynamic content</p>
        </div>

        <div class="feature-card">
          <h3>✅ Server-Side</h3>
          <p>All rendering happens on the server</p>
        </div>

        <div class="feature-card">
          <h3>✅ Flask Integration</h3>
          <p>Built-in web server with auto-reload</p>
        </div>

        <div class="feature-card">
          <h3>✅ Configuration</h3>
          <p>quantum.config.yaml for easy setup</p>
        </div>

        <div class="feature-card">
          <h3>✅ Static Files</h3>
          <p>CSS, JS, images served automatically</p>
        </div>
      </div>

      <h2>📚 Example Components</h2>
      <ul>
        <li><a href="/products">Products List</a> - Loop + databinding example</li>
        <li><a href="/hello">Hello World</a> - Simple component</li>
      </ul>

      <h2>🛠️ How It Works</h2>
      <ol>
        <li><strong>Write:</strong> Create .q component with HTML + Quantum tags</li>
        <li><strong>Start:</strong> Run <code>quantum start</code></li>
        <li><strong>Visit:</strong> Open http://localhost:8080</li>
        <li><strong>Magic!</strong> HTML is rendered with databinding applied</li>
      </ol>

      <div class="demo-box">
        <h3>🎨 Try It Yourself!</h3>
        <p>Edit <code>components/index.q</code> and refresh this page.</p>
        <p>Changes are reflected immediately (auto-reload is ON).</p>
      </div>

      <footer style="margin-top: 40px; padding-top: 20px; border-top: 2px solid #eee; text-align: center; color: #666;">
        <p>⚡ Powered by Quantum Language | 🪄 ColdFusion-style magic | ❤️ Built with love</p>
      </footer>
    </div>
  </body>
  </html>
</q:component>
