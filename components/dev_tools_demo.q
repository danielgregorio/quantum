<q:component name="DevToolsDemo">
  <!-- Phase C: Developer Experience Demo -->

  <h1>🛠️ Developer Experience Demo</h1>

  <div class="section">
    <h2>✨ CLI Commands</h2>

    <p>Quantum provides a powerful CLI for enhanced developer experience:</p>

    <div class="command-list">
      <div class="command">
        <code>./quantum create component MyComponent</code>
        <span>Create a new component</span>
      </div>

      <div class="command">
        <code>./quantum create component MyForm --template=form</code>
        <span>Create component with form template</span>
      </div>

      <div class="command">
        <code>./quantum dev --port=8080</code>
        <span>Start dev server with HMR</span>
      </div>

      <div class="command">
        <code>./quantum build --production</code>
        <span>Build for production</span>
      </div>

      <div class="command">
        <code>./quantum inspect DevToolsDemo</code>
        <span>Inspect this component</span>
      </div>

      <div class="command">
        <code>./quantum init</code>
        <span>Initialize new project</span>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>🔥 Hot Module Replacement</h2>

    <p>With HMR enabled (default in dev mode):</p>

    <ul>
      <li>✅ File changes automatically reload</li>
      <li>✅ No manual refresh needed</li>
      <li>✅ Fast development feedback</li>
      <li>✅ Edit .q files and see instant updates!</li>
    </ul>

    <p class="info">Try it: Edit this file and watch it reload automatically!</p>
  </div>

  <div class="section">
    <h2>💡 Better Error Messages</h2>

    <p>Enhanced error messages with:</p>

    <ul>
      <li>📍 File path and line numbers</li>
      <li>📝 Code context around the error</li>
      <li>💡 Suggestions to fix the issue</li>
      <li>🔍 Helpful hints</li>
    </ul>

    <div class="error-example">
      <h4>Example Error:</h4>
      <pre><code>❌ QUANTUM ERROR
=====================================
📂 File: components/Card.q:15:8

💥 Component 'Button' not found

📝 Code:
    13 | &lt;div class="card"&gt;
    14 |   &lt;h2&gt;{{title}}&lt;/h2&gt;
  → 15 |   &lt;Button label="Click Me" /&gt;
              ^
    16 | &lt;/div&gt;

💡 Suggestion: Did you mean 'button'?
🔍 Hint: Add: &lt;q:import component="Button" /&gt;</code></pre>
    </div>
  </div>

  <div class="section">
    <h2>🔍 Component Inspector</h2>

    <p>Use <code>quantum inspect</code> to analyze components:</p>

    <div class="info-box">
      <p><strong>This Component:</strong></p>
      <ul>
        <li>Name: DevToolsDemo</li>
        <li>Type: pure</li>
        <li>URL: http://localhost:8080/dev_tools_demo</li>
        <li>Has Actions: No</li>
        <li>Has Queries: No</li>
      </ul>
    </div>
  </div>

  <div class="section">
    <h2>📊 Development Features</h2>

    <table>
      <thead>
        <tr>
          <th>Feature</th>
          <th>Status</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>CLI Commands</td>
          <td class="status-enabled">✅ Enabled</td>
          <td>Create, build, inspect, init</td>
        </tr>
        <tr>
          <td>Hot Reload</td>
          <td class="status-enabled">✅ Enabled</td>
          <td>Auto-reload on file changes</td>
        </tr>
        <tr>
          <td>Better Errors</td>
          <td class="status-enabled">✅ Enabled</td>
          <td>Context, suggestions, hints</td>
        </tr>
        <tr>
          <td>Debug Mode</td>
          <td class="status-enabled">✅ Enabled</td>
          <td>Detailed error messages</td>
        </tr>
        <tr>
          <td>Production Build</td>
          <td class="status-enabled">✅ Available</td>
          <td>Minification & optimization</td>
        </tr>
      </tbody>
    </table>
  </div>

  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      max-width: 1000px;
      margin: 0 auto;
      padding: 20px;
      background: #f8f9fa;
    }

    h1 {
      color: #007bff;
      border-bottom: 3px solid #007bff;
      padding-bottom: 10px;
    }

    .section {
      background: white;
      padding: 25px;
      margin-bottom: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .section h2 {
      color: #333;
      margin-top: 0;
      font-size: 1.5rem;
    }

    .command-list {
      margin-top: 15px;
    }

    .command {
      background: #f8f9fa;
      padding: 15px;
      margin-bottom: 10px;
      border-left: 4px solid #007bff;
      border-radius: 4px;
    }

    .command code {
      background: #2d2d2d;
      color: #50fa7b;
      padding: 8px 12px;
      border-radius: 4px;
      display: block;
      margin-bottom: 8px;
      font-family: 'Courier New', monospace;
      font-size: 14px;
    }

    .command span {
      color: #666;
      font-size: 14px;
    }

    .error-example {
      background: #2d2d2d;
      padding: 20px;
      border-radius: 8px;
      margin-top: 15px;
    }

    .error-example h4 {
      color: #f8f9fa;
      margin-top: 0;
    }

    .error-example pre {
      margin: 0;
      color: #f8f9fa;
      font-family: 'Courier New', monospace;
      font-size: 13px;
      line-height: 1.5;
    }

    .error-example code {
      color: #f8f9fa;
    }

    .info {
      background: #e7f3ff;
      border-left: 4px solid #007bff;
      padding: 12px;
      border-radius: 4px;
      color: #004085;
      margin: 15px 0;
    }

    .info-box {
      background: #f8f9fa;
      padding: 15px;
      border-radius: 8px;
      border: 2px solid #dee2e6;
    }

    .info-box strong {
      color: #007bff;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 15px;
    }

    th, td {
      padding: 12px;
      text-align: left;
      border-bottom: 1px solid #dee2e6;
    }

    th {
      background: #f8f9fa;
      font-weight: bold;
      color: #333;
    }

    .status-enabled {
      color: #28a745;
      font-weight: bold;
    }

    ul {
      line-height: 1.8;
    }

    li {
      margin-bottom: 8px;
    }

    code {
      background: #f8f9fa;
      padding: 2px 6px;
      border-radius: 3px;
      font-family: 'Courier New', monospace;
      color: #e83e8c;
    }
  </style>
</q:component>
