<q:component name="HomePage" xmlns:q="https://quantum.lang/ns">
  <q:set name="title" value="Welcome to Quantum!" />
  <q:set name="subtitle" value="HTML Rendering Phase 1 Complete" />
  <q:set name="version" value="1.0.0" />

  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    <link rel="stylesheet" href="/static/css/style.css" />
  </head>
  <body>
    <div>
      <h1>{title}</h1>
      <p>{subtitle}</p>
      <p>Version: {version}</p>

      <h2>Features Implemented</h2>
      <ul>
        <li>HTML Rendering - Write HTML directly in .q components</li>
        <li>Databinding - Use {variable} syntax for dynamic content</li>
        <li>Server-Side Rendering - All rendering happens on the server</li>
        <li>Flask Integration - Built-in web server with auto-reload</li>
      </ul>

      <h2>Example Components</h2>
      <ul>
        <li><a href="/hello">Hello World</a> - Simple component</li>
        <li><a href="/test">Test Component</a> - Basic test</li>
      </ul>

      <h2>How It Works</h2>
      <ol>
        <li>Write: Create .q component with HTML + Quantum tags</li>
        <li>Start: Run <code>quantum start</code></li>
        <li>Visit: Open http://localhost:8080</li>
        <li>Magic! HTML is rendered with databinding applied</li>
      </ol>

      <p>Powered by Quantum Language</p>
    </div>
  </body>
  </html>
</q:component>
