<q:component name="AdminPage" type="page">

  <q:set name="application.blogName" value="Quantum Blog" scope="application" />
  <q:set name="application.basePath" value="/quantum-blog" scope="application" />

  <!-- Redirect if not logged in -->
  <q:if condition="{!session.authenticated}">
    <q:redirect url="{application.basePath}/login" />
  </q:if>

  <q:set name="successMsg" value="" />
  <q:set name="postCount" value="{application.posts.length}" />

  <html>
  <head>
    <title>Admin - {application.blogName}</title>
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
      .badge { background: #22c55e; color: white; font-size: 0.65rem; font-weight: 700; padding: 2px 8px; border-radius: 10px; margin-left: 8px; text-transform: uppercase; letter-spacing: 0.05em; }
      nav { display: flex; align-items: center; gap: 6px; }
      nav a {
        color: #94a3b8; text-decoration: none; font-size: 0.85rem; font-weight: 500;
        padding: 6px 14px; border-radius: 6px; transition: all 0.2s;
      }
      nav a:hover { color: #e2e8f0; background: rgba(255,255,255,0.08); }
      .nav-user { color: #a5b4fc; font-size: 0.85rem; font-weight: 500; padding: 6px 14px; }

      /* Main */
      .main { max-width: 1000px; margin: 0 auto; padding: 40px 24px; }

      /* Form card */
      .form-card {
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 32px; margin-bottom: 40px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      }
      .form-card h2 { font-size: 1.1rem; font-weight: 700; margin-bottom: 24px; color: #0f172a; }
      .form-group { margin-bottom: 20px; }
      .form-group label { display: block; font-weight: 600; font-size: 0.8rem; color: #475569; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.03em; }
      .form-group input, .form-group textarea {
        width: 100%; padding: 10px 14px; border: 1px solid #e2e8f0; border-radius: 8px;
        font-size: 0.95rem; font-family: inherit; background: #fff; color: #1e293b;
        transition: all 0.2s;
      }
      .form-group input:focus, .form-group textarea:focus { outline: none; border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }
      .form-group textarea { min-height: 140px; resize: vertical; line-height: 1.6; }
      .btn-create {
        padding: 12px 28px; background: #6366f1; color: white; border: none;
        border-radius: 8px; font-size: 0.95rem; font-weight: 600; cursor: pointer;
        transition: all 0.2s;
      }
      .btn-create:hover { background: #4f46e5; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(99,102,241,0.25); }

      /* Table */
      .table-card {
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
        overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      }
      .table-header { padding: 20px 24px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }
      .table-header h2 { font-size: 1.1rem; font-weight: 700; color: #0f172a; }
      .post-count-badge { background: #ede9fe; color: #6d28d9; font-size: 0.8rem; font-weight: 600; padding: 4px 12px; border-radius: 20px; }
      .posts-table { width: 100%; border-collapse: collapse; }
      .posts-table th { padding: 12px 24px; text-align: left; font-size: 0.75rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }
      .posts-table td { padding: 14px 24px; font-size: 0.9rem; border-bottom: 1px solid #f1f5f9; }
      .posts-table tr:last-child td { border-bottom: none; }
      .posts-table tr:hover td { background: #f8fafc; }
      .posts-table td a { color: #6366f1; text-decoration: none; font-weight: 500; }
      .posts-table td a:hover { text-decoration: underline; }

      /* Success message */
      .success { background: #dcfce7; border: 1px solid #86efac; color: #166534; padding: 14px 20px; border-radius: 10px; margin-bottom: 24px; font-size: 0.9rem; font-weight: 500; }

      /* Footer */
      footer { max-width: 1000px; margin: 0 auto; padding: 32px 24px; border-top: 1px solid #e2e8f0; text-align: center; }
      .footer-brand { font-size: 0.85rem; color: #94a3b8; }
      .footer-brand strong { color: #6366f1; }

      @media (max-width: 640px) {
        .form-card { padding: 20px; }
        .posts-table th, .posts-table td { padding: 10px 14px; }
      }
    </style>
  </head>
  <body>

    <header>
      <div class="header-inner">
        <a href="{application.basePath}/" class="logo">
          <span class="logo-icon">Q</span>
          {application.blogName}
          <span class="badge">Admin</span>
        </a>
        <nav>
          <a href="{application.basePath}/">View Blog</a>
          <span class="nav-user">{session.username}</span>
          <a href="{application.basePath}/logout">Logout</a>
        </nav>
      </div>
    </header>

    <main class="main">

      <q:if condition="{successMsg != ''}">
        <div class="success">{successMsg}</div>
      </q:if>

      <div class="form-card">
        <h2>Create New Post</h2>
        <form method="POST" action="{application.basePath}/admin">
          <div class="form-group">
            <label>Title</label>
            <input type="text" name="title" placeholder="Enter post title..." required="required" />
          </div>
          <div class="form-group">
            <label>Excerpt</label>
            <input type="text" name="excerpt" placeholder="A brief summary of the post..." required="required" />
          </div>
          <div class="form-group">
            <label>Content</label>
            <textarea name="content" placeholder="Write your post content here..." required="required"></textarea>
          </div>
          <button type="submit" class="btn-create">Publish Post</button>
        </form>
      </div>

      <div class="table-card">
        <div class="table-header">
          <h2>All Posts</h2>
          <span class="post-count-badge">{postCount} total</span>
        </div>
        <table class="posts-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Title</th>
              <th>Author</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            <q:loop type="array" var="post" items="{application.posts}">
              <tr>
                <td>{post.id}</td>
                <td><a href="{application.basePath}/post?id={post.id}">{post.title}</a></td>
                <td>{post.author}</td>
                <td>{post.date}</td>
              </tr>
            </q:loop>
          </tbody>
        </table>
      </div>

    </main>

    <footer>
      <span class="footer-brand">Built with <strong>Quantum Framework</strong></span>
    </footer>

  </body>
  </html>

</q:component>
