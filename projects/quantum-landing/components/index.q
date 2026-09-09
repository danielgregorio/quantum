<q:component name="LandingPage" type="page">

  <!-- Page Data -->
  <q:set name="frameworkName" value="Quantum Framework" />
  <q:set name="tagline" value="Build web apps without writing JavaScript" />
  <q:set name="version" value="1.0.0" />

  <q:set name="features" value="[
    {&quot;icon&quot;: &quot;&#9889;&quot;, &quot;title&quot;: &quot;Declarative XML&quot;, &quot;desc&quot;: &quot;Write apps in clean, readable XML tags. No boilerplate.&quot;},
    {&quot;icon&quot;: &quot;&#128640;&quot;, &quot;title&quot;: &quot;Zero JavaScript&quot;, &quot;desc&quot;: &quot;Full-stack web apps without a single line of JS.&quot;},
    {&quot;icon&quot;: &quot;&#128218;&quot;, &quot;title&quot;: &quot;Built-in Database&quot;, &quot;desc&quot;: &quot;SQL queries with q:query. MySQL, PostgreSQL, SQLite.&quot;},
    {&quot;icon&quot;: &quot;&#128274;&quot;, &quot;title&quot;: &quot;Auth &amp; RBAC&quot;, &quot;desc&quot;: &quot;Session auth and role-based access in one tag.&quot;},
    {&quot;icon&quot;: &quot;&#127918;&quot;, &quot;title&quot;: &quot;2D Game Engine&quot;, &quot;desc&quot;: &quot;Build games with sprites, physics, and state machines.&quot;},
    {&quot;icon&quot;: &quot;&#128230;&quot;, &quot;title&quot;: &quot;One-Command Deploy&quot;, &quot;desc&quot;: &quot;quantum deploy and your app is live. That simple.&quot;}
  ]" type="json" />

  <q:set name="stats" value="[
    {&quot;number&quot;: &quot;30+&quot;, &quot;label&quot;: &quot;Built-in Tags&quot;},
    {&quot;number&quot;: &quot;0&quot;, &quot;label&quot;: &quot;Lines of JS Needed&quot;},
    {&quot;number&quot;: &quot;1&quot;, &quot;label&quot;: &quot;Command to Deploy&quot;},
    {&quot;number&quot;: &quot;5min&quot;, &quot;label&quot;: &quot;To First App&quot;}
  ]" type="json" />

  <q:set name="codeExample" value="&lt;q:component name=&quot;Hello&quot;&gt;
  &lt;q:set name=&quot;greeting&quot; value=&quot;World&quot; /&gt;
  &lt;h1&gt;Hello, {greeting}!&lt;/h1&gt;
&lt;/q:component&gt;" />

  <q:set name="demos" value="[
    {&quot;name&quot;: &quot;Quantum Blog&quot;, &quot;desc&quot;: &quot;Mini blog with auth, posts, and admin panel&quot;, &quot;url&quot;: &quot;/quantum-blog/&quot;, &quot;icon&quot;: &quot;&#128221;&quot;},
    {&quot;name&quot;: &quot;Snake Game&quot;, &quot;desc&quot;: &quot;Classic snake built with the 2D game engine&quot;, &quot;url&quot;: &quot;/quantum-snake/&quot;, &quot;icon&quot;: &quot;&#128013;&quot;},
    {&quot;name&quot;: &quot;Tic Tac Toe&quot;, &quot;desc&quot;: &quot;Two-player game with win detection&quot;, &quot;url&quot;: &quot;/quantum-tictactoe/&quot;, &quot;icon&quot;: &quot;&#10060;&quot;},
    {&quot;name&quot;: &quot;Tower Defense&quot;, &quot;desc&quot;: &quot;Strategic tower defense game&quot;, &quot;url&quot;: &quot;/quantum-tower/&quot;, &quot;icon&quot;: &quot;&#127984;&quot;}
  ]" type="json" />

  <html>
  <head>
    <title>{frameworkName}</title>
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #e2e8f0; background: #0f172a; }
      a { color: #818cf8; text-decoration: none; }
      a:hover { color: #a5b4fc; }

      /* Hero */
      .hero { text-align: center; padding: 100px 20px 80px; background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%); }
      .hero h1 { font-size: 3.5rem; font-weight: 800; background: linear-gradient(135deg, #818cf8, #c084fc, #f472b6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 16px; }
      .hero p { font-size: 1.3rem; color: #94a3b8; max-width: 600px; margin: 0 auto 40px; }
      .hero-buttons { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }
      .btn { padding: 14px 32px; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; border: none; transition: all 0.2s; }
      .btn-primary { background: #6366f1; color: white; }
      .btn-primary:hover { background: #4f46e5; transform: translateY(-2px); }
      .btn-outline { background: transparent; color: #818cf8; border: 2px solid #818cf8; }
      .btn-outline:hover { background: #818cf81a; }

      /* Stats */
      .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; max-width: 900px; margin: -40px auto 0; padding: 0 20px; position: relative; z-index: 1; }
      .stat-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 24px; text-align: center; }
      .stat-card .number { font-size: 2.5rem; font-weight: 800; color: #818cf8; }
      .stat-card .label { font-size: 0.9rem; color: #94a3b8; margin-top: 4px; }

      /* Features */
      .features { padding: 100px 20px; max-width: 1100px; margin: 0 auto; }
      .features h2 { text-align: center; font-size: 2.2rem; margin-bottom: 60px; color: #f1f5f9; }
      .features-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px; }
      .feature-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 32px; transition: all 0.3s; }
      .feature-card:hover { border-color: #6366f1; transform: translateY(-4px); box-shadow: 0 8px 30px rgba(99,102,241,0.15); }
      .feature-icon { font-size: 2rem; margin-bottom: 16px; }
      .feature-card h3 { font-size: 1.2rem; color: #f1f5f9; margin-bottom: 8px; }
      .feature-card p { color: #94a3b8; line-height: 1.6; }

      /* Demos */
      .demos { padding: 80px 20px; background: #0f172a; }
      .demos h2 { text-align: center; font-size: 2.2rem; color: #f1f5f9; margin-bottom: 16px; }
      .demos-subtitle { text-align: center; color: #94a3b8; margin-bottom: 48px; }
      .demos-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; max-width: 1100px; margin: 0 auto; }
      .demo-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 24px; text-align: center; transition: all 0.3s; text-decoration: none; display: block; }
      .demo-card:hover { border-color: #6366f1; transform: translateY(-4px); box-shadow: 0 8px 30px rgba(99,102,241,0.15); }
      .demo-icon { font-size: 2.5rem; margin-bottom: 12px; }
      .demo-card h3 { font-size: 1.1rem; color: #f1f5f9; margin-bottom: 8px; }
      .demo-card p { color: #94a3b8; font-size: 0.9rem; line-height: 1.5; }

      /* Code */
      .code-section { padding: 80px 20px; background: #1e293b; }
      .code-section h2 { text-align: center; font-size: 2.2rem; color: #f1f5f9; margin-bottom: 40px; }
      .code-block { max-width: 600px; margin: 0 auto; background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 24px; }
      .code-block pre { color: #a5b4fc; font-family: 'Fira Code', monospace; font-size: 0.95rem; line-height: 1.8; white-space: pre; overflow-x: auto; }

      /* Footer */
      .footer { text-align: center; padding: 40px 20px; color: #64748b; border-top: 1px solid #1e293b; }

      @media (max-width: 768px) {
        .hero h1 { font-size: 2.2rem; }
        .stats { grid-template-columns: repeat(2, 1fr); }
        .features-grid { grid-template-columns: 1fr; }
        .demos-grid { grid-template-columns: repeat(2, 1fr); }
      }
    </style>
  </head>
  <body>

    <!-- Hero Section -->
    <section class="hero">
      <h1>{frameworkName}</h1>
      <p>{tagline}</p>
      <div class="hero-buttons">
        <a href="https://github.com/danielgregorio/quantum" class="btn btn-primary">Get Started</a>
        <a href="#features" class="btn btn-outline">See Features</a>
      </div>
    </section>

    <!-- Stats -->
    <section class="stats">
      <q:loop type="array" var="stat" items="{stats}">
        <div class="stat-card">
          <div class="number">{stat.number}</div>
          <div class="label">{stat.label}</div>
        </div>
      </q:loop>
    </section>

    <!-- Features -->
    <section class="features" id="features">
      <h2>Everything You Need</h2>
      <div class="features-grid">
        <q:loop type="array" var="feature" items="{features}">
          <div class="feature-card">
            <div class="feature-icon">{feature.icon}</div>
            <h3>{feature.title}</h3>
            <p>{feature.desc}</p>
          </div>
        </q:loop>
      </div>
    </section>

    <!-- Live Demos -->
    <section class="demos" id="demos">
      <h2>Live Examples</h2>
      <p class="demos-subtitle">Try these apps built with Quantum - running on Forge</p>
      <div class="demos-grid">
        <q:loop type="array" var="demo" items="{demos}">
          <a href="{demo.url}" class="demo-card">
            <div class="demo-icon">{demo.icon}</div>
            <h3>{demo.name}</h3>
            <p>{demo.desc}</p>
          </a>
        </q:loop>
      </div>
    </section>

    <!-- Code Example -->
    <section class="code-section">
      <h2>Simple by Design</h2>
      <div class="code-block">
        <pre>{codeExample}</pre>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <p>{frameworkName} v{version} - Built with Quantum</p>
    </footer>

  </body>
  </html>

</q:component>
