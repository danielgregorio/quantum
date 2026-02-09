<q:component name="BlogHome" type="page">

  <!-- Blog data with full content for post views -->
  <q:set name="application.blogName" value="Quantum Blog" scope="application" />
  <q:set name="application.basePath" value="/quantum-blog" scope="application" />
  <q:set name="isLoggedIn" value="{session.authenticated}" />

  <q:set name="application.posts" value="[
    {&quot;id&quot;: 1, &quot;title&quot;: &quot;Welcome to Quantum Blog&quot;, &quot;excerpt&quot;: &quot;This blog is built entirely with the Quantum Framework - no JavaScript needed! Discover how declarative XML components power a full-stack web application.&quot;, &quot;content&quot;: &quot;Welcome to the Quantum Blog! This entire application was built using the Quantum Framework, a declarative full-stack web framework that lets you create complete web applications without writing a single line of JavaScript.\n\nWith Quantum, you write XML-based components that handle everything from routing and state management to database queries and authentication. The framework compiles your declarative code into a fully functional web server.\n\nThis blog demonstrates several key features: data binding with curly braces, conditional rendering with q:if, list iteration with q:loop, session management for authentication, and form handling for the admin panel.\n\nWelcome aboard, and happy coding!&quot;, &quot;author&quot;: &quot;Admin&quot;, &quot;date&quot;: &quot;2026-01-28&quot;, &quot;tag&quot;: &quot;Announcement&quot;},
    {&quot;id&quot;: 2, &quot;title&quot;: &quot;How Quantum Works Under the Hood&quot;, &quot;excerpt&quot;: &quot;A deep dive into the Quantum Framework architecture - from XML parsing to HTML rendering, see how it all connects.&quot;, &quot;content&quot;: &quot;The Quantum Framework follows a straightforward pipeline: your .q files (XML-based components) are parsed into an Abstract Syntax Tree (AST), which is then executed by the runtime engine to produce HTML output.\n\nThe parser reads each XML tag and converts it into typed AST nodes. Tags like q:set create variable assignments, q:loop creates iteration nodes, and q:if creates conditional branches.\n\nThe runtime engine walks the AST, evaluating expressions, resolving data bindings, and building the final HTML response. Variables are managed through scoped execution contexts that support page, session, and application-level state.\n\nThe web server (built on Flask) maps URL routes to component files and serves the rendered output. It is a simple yet powerful architecture that proves you do not need complex JavaScript frameworks to build dynamic web applications.&quot;, &quot;author&quot;: &quot;Admin&quot;, &quot;date&quot;: &quot;2026-01-28&quot;, &quot;tag&quot;: &quot;Technical&quot;},
    {&quot;id&quot;: 3, &quot;title&quot;: &quot;Deploy in One Command&quot;, &quot;excerpt&quot;: &quot;From development to production with a single command. Learn how Quantum makes deployment effortless.&quot;, &quot;content&quot;: &quot;Deploying a Quantum application is designed to be as simple as possible. With the quantum deploy command, your application is packaged and ready for production.\n\nThe deploy process bundles your components, configuration, and static assets into a self-contained package. It generates a production-ready WSGI entry point that can be served by any standard Python WSGI server like Gunicorn or uWSGI.\n\nYou can also containerize your app with Docker. The framework generates a Dockerfile and docker-compose configuration automatically. Just run quantum deploy --docker and you are ready to push to any container registry.\n\nWhether you prefer traditional hosting, containers, or cloud platforms, Quantum has you covered.&quot;, &quot;author&quot;: &quot;Admin&quot;, &quot;date&quot;: &quot;2026-01-27&quot;, &quot;tag&quot;: &quot;DevOps&quot;}
  ]" type="json" scope="application" />

  <q:set name="postCount" value="3" />

  <html>
  <head>
    <title>{application.blogName}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&amp;display=swap');

      * { margin: 0; padding: 0; box-sizing: border-box; }
      body { font-family: 'Inter', -apple-system, sans-serif; background: #f8fafc; color: #1e293b; }

      /* Header */
      header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border-bottom: 2px solid #6366f1;
      }
      .header-inner {
        max-width: 1000px; margin: 0 auto; padding: 16px 24px;
        display: flex; justify-content: space-between; align-items: center;
      }
      .logo { color: #fff; font-size: 1.25rem; font-weight: 700; text-decoration: none; display: flex; align-items: center; gap: 10px; }
      .logo-icon { background: #6366f1; color: white; width: 32px; height: 32px; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1rem; }
      nav { display: flex; align-items: center; gap: 6px; }
      nav a {
        color: #94a3b8; text-decoration: none; font-size: 0.85rem; font-weight: 500;
        padding: 6px 14px; border-radius: 6px; transition: all 0.2s;
      }
      nav a:hover { color: #e2e8f0; background: rgba(255,255,255,0.08); }

      /* Hero */
      .hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #312e81 100%);
        padding: 64px 24px 56px; text-align: center; position: relative; overflow: hidden;
      }
      .hero::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(circle at 30% 50%, rgba(99,102,241,0.15) 0%, transparent 50%),
                    radial-gradient(circle at 70% 50%, rgba(139,92,246,0.1) 0%, transparent 50%);
      }
      .hero-content { position: relative; z-index: 1; max-width: 600px; margin: 0 auto; }
      .hero h1 { color: #fff; font-size: 2.5rem; font-weight: 800; margin-bottom: 12px; letter-spacing: -0.02em; }
      .hero h1 span { background: linear-gradient(135deg, #818cf8, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
      .hero p { color: #94a3b8; font-size: 1.1rem; line-height: 1.6; }
      .hero-stats { display: flex; justify-content: center; gap: 32px; margin-top: 28px; }
      .hero-stat { color: #cbd5e1; font-size: 0.85rem; }
      .hero-stat strong { display: block; font-size: 1.5rem; color: #fff; font-weight: 700; }

      /* Main */
      .main { max-width: 1000px; margin: 0 auto; padding: 48px 24px; }
      .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
      .section-title { font-size: 1.3rem; font-weight: 700; color: #0f172a; }
      .post-count-badge { background: #ede9fe; color: #6d28d9; font-size: 0.8rem; font-weight: 600; padding: 4px 12px; border-radius: 20px; }

      /* Post cards */
      .posts-grid { display: flex; flex-direction: column; gap: 20px; }
      .post-card {
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 28px 32px; transition: all 0.25s ease;
        display: block; text-decoration: none; color: inherit;
      }
      .post-card:hover { border-color: #c7d2fe; box-shadow: 0 8px 24px rgba(99,102,241,0.08); transform: translateY(-2px); }
      .post-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
      .post-tag { background: #f1f5f9; color: #6366f1; font-size: 0.75rem; font-weight: 600; padding: 3px 10px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
      .post-date { color: #94a3b8; font-size: 0.8rem; }
      .post-card h2 { font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-bottom: 8px; line-height: 1.4; }
      .post-card p { color: #64748b; font-size: 0.95rem; line-height: 1.7; }
      .post-card .post-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; padding-top: 16px; border-top: 1px solid #f1f5f9; }
      .post-author { display: flex; align-items: center; gap: 8px; }
      .author-avatar { width: 28px; height: 28px; border-radius: 50%; background: linear-gradient(135deg, #6366f1, #8b5cf6); display: flex; align-items: center; justify-content: center; color: white; font-size: 0.7rem; font-weight: 700; }
      .author-name { font-size: 0.85rem; color: #475569; font-weight: 500; }
      .read-more { color: #6366f1; font-size: 0.85rem; font-weight: 600; }

      /* Footer */
      footer { max-width: 1000px; margin: 0 auto; padding: 32px 24px; border-top: 1px solid #e2e8f0; }
      .footer-content { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
      .footer-brand { font-size: 0.85rem; color: #94a3b8; }
      .footer-brand strong { color: #6366f1; }
      .footer-links a { color: #94a3b8; text-decoration: none; font-size: 0.8rem; margin-left: 16px; }
      .footer-links a:hover { color: #6366f1; }

      @media (max-width: 640px) {
        .hero h1 { font-size: 1.8rem; }
        .hero-stats { gap: 20px; }
        .post-card { padding: 20px; }
        .footer-content { flex-direction: column; text-align: center; }
      }
    </style>
  </head>
  <body>

    <header>
      <div class="header-inner">
        <a href="{application.basePath}/" class="logo">
          <span class="logo-icon">Q</span>
          {application.blogName}
        </a>
        <nav>
          <a href="{application.basePath}/">Home</a>
          <q:if condition="{isLoggedIn}">
            <a href="{application.basePath}/admin">Admin</a>
            <a href="{application.basePath}/logout">Logout</a>
          </q:if>
          <q:if condition="{!isLoggedIn}">
            <a href="{application.basePath}/login">Login</a>
          </q:if>
        </nav>
      </div>
    </header>

    <section class="hero">
      <div class="hero-content">
        <h1>The <span>Quantum</span> Blog</h1>
        <p>A fully functional blog built with the Quantum Framework. No JavaScript. Pure declarative XML components.</p>
        <div class="hero-stats">
          <div class="hero-stat">
            <strong>{postCount}</strong> Posts
          </div>
          <div class="hero-stat">
            <strong>0</strong> JavaScript
          </div>
          <div class="hero-stat">
            <strong>5</strong> Components
          </div>
        </div>
      </div>
    </section>

    <main class="main">
      <div class="section-header">
        <h2 class="section-title">Latest Posts</h2>
        <span class="post-count-badge">{postCount} published</span>
      </div>

      <div class="posts-grid">
        <q:loop type="array" var="post" items="{application.posts}">
          <a href="{application.basePath}/post?id={post.id}" class="post-card">
            <div class="post-top">
              <span class="post-tag">{post.tag}</span>
              <span class="post-date">{post.date}</span>
            </div>
            <h2>{post.title}</h2>
            <p>{post.excerpt}</p>
            <div class="post-footer">
              <div class="post-author">
                <div class="author-avatar">A</div>
                <span class="author-name">{post.author}</span>
              </div>
              <span class="read-more">Read more &#8594;</span>
            </div>
          </a>
        </q:loop>
      </div>

      <q:if condition="{postCount == 0}">
        <div style="text-align:center; padding:60px 20px; color:#94a3b8;">
          <p>No posts yet. <a href="{application.basePath}/admin" style="color:#6366f1;">Create one</a>.</p>
        </div>
      </q:if>
    </main>

    <footer>
      <div class="footer-content">
        <span class="footer-brand">Built with <strong>Quantum Framework</strong></span>
        <div class="footer-links">
          <a href="{application.basePath}/">Home</a>
          <a href="{application.basePath}/login">Login</a>
        </div>
      </div>
    </footer>

  </body>
  </html>

</q:component>
