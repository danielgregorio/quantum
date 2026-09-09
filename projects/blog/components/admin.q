<q:component name="AdminPage" type="page">
  <!--
    Quantum Blog - Admin Dashboard
    Features:
    - Database-driven post management
    - Create, edit, delete posts
    - Tag management
    - Draft/Publish workflow
    - Image upload support
    - Reading time calculation
  -->

  <q:set name="application.blogName" value="Quantum Blog" scope="application" />
  <q:set name="application.basePath" value="/quantum-blog" scope="application" />

  <!-- Redirect if not logged in -->
  <q:if condition="{!session.authenticated}">
    <q:redirect url="{application.basePath}/login" />
  </q:if>

  <!-- Check admin role -->
  <q:if condition="{session.role != 'admin' and session.role != 'author'}">
    <q:redirect url="{application.basePath}/" />
  </q:if>

  <q:set name="successMsg" value="" />
  <q:set name="errorMsg" value="" />
  <q:set name="editMode" value="false" />
  <q:set name="editPostId" value="{query.edit}" default="" />

  <!-- Get all tags for dropdown (cached) -->
  <q:query name="allTags" datasource="blog-db" cache="300">
    SELECT id, name, slug, color
    FROM tags
    ORDER BY name
  </q:query>

  <!-- If editing, get the post data -->
  <q:if condition="{editPostId != ''}">
    <q:set name="editMode" value="true" />
    <q:query name="editPost" datasource="blog-db">
      SELECT
        id, title, slug, excerpt, content,
        tag_id, is_published, is_featured, featured_image
      FROM posts
      WHERE id = :postId AND author_id = :authorId

      <q:param name="postId" value="{editPostId}" type="integer" />
      <q:param name="authorId" value="{session.userId}" type="integer" />
    </q:query>
  </q:if>

  <!-- Action: Create new post -->
  <q:action name="createPost" method="POST">
    <q:validate field="title" required="true" minLength="3" maxLength="255" />
    <q:validate field="excerpt" required="true" minLength="10" maxLength="500" />
    <q:validate field="content" required="true" minLength="20" />
    <q:validate field="tag_id" required="true" />

    <!-- Generate slug from title -->
    <q:set name="postSlug" value="{slugify(form.title)}" />

    <!-- Calculate reading time (avg 200 words/min) -->
    <q:set name="wordCount" value="{form.content.split(' ').length}" />
    <q:set name="readingTime" value="{Math.max(1, Math.ceil(wordCount / 200))}" />

    <!-- Check if slug already exists -->
    <q:query name="slugCheck" datasource="blog-db">
      SELECT id FROM posts WHERE slug = :slug
      <q:param name="slug" value="{postSlug}" type="string" />
    </q:query>

    <q:if condition="{slugCheck_result.recordCount > 0}">
      <!-- Append timestamp to make unique -->
      <q:set name="postSlug" value="{postSlug}-{Date.now()}" />
    </q:if>

    <!-- Insert new post -->
    <q:query name="insertPost" datasource="blog-db" type="insert">
      INSERT INTO posts (
        title, slug, excerpt, content, tag_id, author_id,
        reading_time, is_published, is_featured, featured_image,
        published_at
      ) VALUES (
        :title, :slug, :excerpt, :content, :tagId, :authorId,
        :readingTime, :isPublished, :isFeatured, :featuredImage,
        CASE WHEN :isPublished THEN NOW() ELSE NULL END
      )
      RETURNING id

      <q:param name="title" value="{form.title}" type="string" />
      <q:param name="slug" value="{postSlug}" type="string" />
      <q:param name="excerpt" value="{form.excerpt}" type="string" />
      <q:param name="content" value="{form.content}" type="string" />
      <q:param name="tagId" value="{form.tag_id}" type="integer" />
      <q:param name="authorId" value="{session.userId}" type="integer" />
      <q:param name="readingTime" value="{readingTime}" type="integer" />
      <q:param name="isPublished" value="{form.is_published == 'on'}" type="boolean" />
      <q:param name="isFeatured" value="{form.is_featured == 'on'}" type="boolean" />
      <q:param name="featuredImage" value="{form.featured_image}" type="string" />
    </q:query>

    <!-- Update tag post count -->
    <q:query name="updateTagCount" datasource="blog-db" type="execute">
      UPDATE tags SET post_count = post_count + 1 WHERE id = :tagId
      <q:param name="tagId" value="{form.tag_id}" type="integer" />
    </q:query>

    <q:set name="successMsg" value="Post created successfully!" />
  </q:action>

  <!-- Action: Update existing post -->
  <q:action name="updatePost" method="POST">
    <q:validate field="post_id" required="true" />
    <q:validate field="title" required="true" minLength="3" maxLength="255" />
    <q:validate field="excerpt" required="true" minLength="10" maxLength="500" />
    <q:validate field="content" required="true" minLength="20" />

    <!-- Calculate reading time -->
    <q:set name="wordCount" value="{form.content.split(' ').length}" />
    <q:set name="readingTime" value="{Math.max(1, Math.ceil(wordCount / 200))}" />

    <q:query name="updatePostQuery" datasource="blog-db" type="execute">
      UPDATE posts SET
        title = :title,
        excerpt = :excerpt,
        content = :content,
        tag_id = :tagId,
        reading_time = :readingTime,
        is_published = :isPublished,
        is_featured = :isFeatured,
        featured_image = :featuredImage,
        published_at = CASE
          WHEN :isPublished AND published_at IS NULL THEN NOW()
          ELSE published_at
        END,
        updated_at = NOW()
      WHERE id = :postId AND author_id = :authorId

      <q:param name="postId" value="{form.post_id}" type="integer" />
      <q:param name="authorId" value="{session.userId}" type="integer" />
      <q:param name="title" value="{form.title}" type="string" />
      <q:param name="excerpt" value="{form.excerpt}" type="string" />
      <q:param name="content" value="{form.content}" type="string" />
      <q:param name="tagId" value="{form.tag_id}" type="integer" />
      <q:param name="readingTime" value="{readingTime}" type="integer" />
      <q:param name="isPublished" value="{form.is_published == 'on'}" type="boolean" />
      <q:param name="isFeatured" value="{form.is_featured == 'on'}" type="boolean" />
      <q:param name="featuredImage" value="{form.featured_image}" type="string" />
    </q:query>

    <q:set name="successMsg" value="Post updated successfully!" />
    <q:set name="editMode" value="false" />
    <q:set name="editPostId" value="" />
  </q:action>

  <!-- Action: Delete post -->
  <q:action name="deletePost" method="POST">
    <q:validate field="post_id" required="true" />

    <!-- Get tag_id before delete for count update -->
    <q:query name="postToDelete" datasource="blog-db">
      SELECT tag_id FROM posts WHERE id = :postId AND author_id = :authorId
      <q:param name="postId" value="{form.post_id}" type="integer" />
      <q:param name="authorId" value="{session.userId}" type="integer" />
    </q:query>

    <q:if condition="{postToDelete_result.recordCount > 0}">
      <!-- Delete comments first -->
      <q:query name="deleteComments" datasource="blog-db" type="execute">
        DELETE FROM comments WHERE post_id = :postId
        <q:param name="postId" value="{form.post_id}" type="integer" />
      </q:query>

      <!-- Delete post views -->
      <q:query name="deleteViews" datasource="blog-db" type="execute">
        DELETE FROM post_views WHERE post_id = :postId
        <q:param name="postId" value="{form.post_id}" type="integer" />
      </q:query>

      <!-- Delete post -->
      <q:query name="deletePostQuery" datasource="blog-db" type="execute">
        DELETE FROM posts WHERE id = :postId AND author_id = :authorId
        <q:param name="postId" value="{form.post_id}" type="integer" />
        <q:param name="authorId" value="{session.userId}" type="integer" />
      </q:query>

      <!-- Update tag count -->
      <q:query name="decrementTagCount" datasource="blog-db" type="execute">
        UPDATE tags SET post_count = GREATEST(0, post_count - 1) WHERE id = :tagId
        <q:param name="tagId" value="{postToDelete.tag_id}" type="integer" />
      </q:query>

      <q:set name="successMsg" value="Post deleted successfully." />
    </q:if>
  </q:action>

  <!-- Action: Toggle publish status -->
  <q:action name="togglePublish" method="POST">
    <q:validate field="post_id" required="true" />

    <q:query name="togglePub" datasource="blog-db" type="execute">
      UPDATE posts SET
        is_published = NOT is_published,
        published_at = CASE
          WHEN NOT is_published THEN NOW()
          ELSE published_at
        END,
        updated_at = NOW()
      WHERE id = :postId AND author_id = :authorId

      <q:param name="postId" value="{form.post_id}" type="integer" />
      <q:param name="authorId" value="{session.userId}" type="integer" />
    </q:query>

    <q:set name="successMsg" value="Post status updated." />
  </q:action>

  <!-- Get posts for current user -->
  <q:query name="myPosts" datasource="blog-db">
    SELECT
      p.id,
      p.title,
      p.slug,
      p.views,
      p.is_published,
      p.is_featured,
      TO_CHAR(p.published_at, 'YYYY-MM-DD') as published_at,
      TO_CHAR(p.created_at, 'YYYY-MM-DD') as created_at,
      t.name as tag_name,
      t.color as tag_color
    FROM posts p
    LEFT JOIN tags t ON p.tag_id = t.id
    WHERE p.author_id = :authorId
    ORDER BY p.created_at DESC

    <q:param name="authorId" value="{session.userId}" type="integer" />
  </q:query>

  <!-- Get stats -->
  <q:query name="stats" datasource="blog-db">
    SELECT
      COUNT(*) as total_posts,
      COUNT(*) FILTER (WHERE is_published = TRUE) as published_posts,
      COUNT(*) FILTER (WHERE is_published = FALSE) as draft_posts,
      COALESCE(SUM(views), 0) as total_views
    FROM posts
    WHERE author_id = :authorId

    <q:param name="authorId" value="{session.userId}" type="integer" />
  </q:query>

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
        max-width: 1200px; margin: 0 auto; padding: 16px 24px;
        display: flex; justify-content: space-between; align-items: center;
      }
      .logo { color: #fff; font-size: 1.25rem; font-weight: 700; text-decoration: none; display: flex; align-items: center; gap: 10px; }
      .logo-icon { background: #6366f1; color: white; width: 32px; height: 32px; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1rem; }
      .badge { background: #22c55e; color: white; font-size: 0.65rem; font-weight: 700; padding: 2px 8px; border-radius: 10px; margin-left: 8px; text-transform: uppercase; }
      nav { display: flex; align-items: center; gap: 6px; }
      nav a { color: #94a3b8; text-decoration: none; font-size: 0.85rem; font-weight: 500; padding: 6px 14px; border-radius: 6px; transition: all 0.2s; }
      nav a:hover { color: #e2e8f0; background: rgba(255,255,255,0.08); }
      .nav-user { color: #a5b4fc; font-size: 0.85rem; font-weight: 500; padding: 6px 14px; }

      /* Main */
      .main { max-width: 1200px; margin: 0 auto; padding: 40px 24px; }

      /* Stats Grid */
      .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 32px; }
      .stat-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; text-align: center; }
      .stat-value { font-size: 2rem; font-weight: 800; color: #6366f1; }
      .stat-label { font-size: 0.8rem; color: #64748b; text-transform: uppercase; margin-top: 4px; }

      /* Form card */
      .form-card {
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 32px; margin-bottom: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      }
      .form-card h2 { font-size: 1.1rem; font-weight: 700; margin-bottom: 24px; color: #0f172a; }
      .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
      .form-group { margin-bottom: 20px; }
      .form-group.full { grid-column: 1 / -1; }
      .form-group label { display: block; font-weight: 600; font-size: 0.8rem; color: #475569; margin-bottom: 6px; text-transform: uppercase; }
      .form-group input, .form-group textarea, .form-group select {
        width: 100%; padding: 10px 14px; border: 1px solid #e2e8f0; border-radius: 8px;
        font-size: 0.95rem; font-family: inherit; background: #fff; color: #1e293b; transition: all 0.2s;
      }
      .form-group input:focus, .form-group textarea:focus, .form-group select:focus {
        outline: none; border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1);
      }
      .form-group textarea { min-height: 200px; resize: vertical; line-height: 1.6; }
      .checkbox-row { display: flex; gap: 24px; margin-bottom: 20px; }
      .checkbox-item { display: flex; align-items: center; gap: 8px; }
      .checkbox-item input[type="checkbox"] { width: 18px; height: 18px; accent-color: #6366f1; }
      .checkbox-item label { font-size: 0.9rem; color: #475569; text-transform: none; }
      .btn-row { display: flex; gap: 12px; }
      .btn-create, .btn-update {
        padding: 12px 28px; background: #6366f1; color: white; border: none;
        border-radius: 8px; font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: all 0.2s;
      }
      .btn-create:hover, .btn-update:hover { background: #4f46e5; transform: translateY(-1px); }
      .btn-cancel { padding: 12px 28px; background: #f1f5f9; color: #475569; border: none; border-radius: 8px; font-size: 0.95rem; font-weight: 600; cursor: pointer; text-decoration: none; }
      .btn-cancel:hover { background: #e2e8f0; }

      /* Table */
      .table-card {
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
        overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      }
      .table-header { padding: 20px 24px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }
      .table-header h2 { font-size: 1.1rem; font-weight: 700; color: #0f172a; }
      .posts-table { width: 100%; border-collapse: collapse; }
      .posts-table th { padding: 12px 20px; text-align: left; font-size: 0.75rem; color: #64748b; font-weight: 600; text-transform: uppercase; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }
      .posts-table td { padding: 14px 20px; font-size: 0.9rem; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
      .posts-table tr:last-child td { border-bottom: none; }
      .posts-table tr:hover td { background: #f8fafc; }
      .post-title-cell a { color: #1e293b; text-decoration: none; font-weight: 500; }
      .post-title-cell a:hover { color: #6366f1; }
      .tag-badge { display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
      .status-badge { display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
      .status-published { background: #dcfce7; color: #166534; }
      .status-draft { background: #fef3c7; color: #92400e; }
      .action-btns { display: flex; gap: 8px; }
      .btn-sm { padding: 6px 12px; font-size: 0.8rem; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; transition: all 0.2s; }
      .btn-edit { background: #e0e7ff; color: #4338ca; }
      .btn-edit:hover { background: #c7d2fe; }
      .btn-toggle { background: #fef3c7; color: #92400e; }
      .btn-toggle:hover { background: #fde68a; }
      .btn-delete { background: #fee2e2; color: #dc2626; }
      .btn-delete:hover { background: #fecaca; }

      /* Messages */
      .success { background: #dcfce7; border: 1px solid #86efac; color: #166534; padding: 14px 20px; border-radius: 10px; margin-bottom: 24px; font-size: 0.9rem; font-weight: 500; }
      .error { background: #fee2e2; border: 1px solid #fecaca; color: #dc2626; padding: 14px 20px; border-radius: 10px; margin-bottom: 24px; font-size: 0.9rem; font-weight: 500; }

      /* Empty state */
      .empty-state { text-align: center; padding: 60px 20px; color: #94a3b8; }

      /* Footer */
      footer { max-width: 1200px; margin: 0 auto; padding: 32px 24px; border-top: 1px solid #e2e8f0; text-align: center; }
      .footer-brand { font-size: 0.85rem; color: #94a3b8; }
      .footer-brand strong { color: #6366f1; }

      @media (max-width: 768px) {
        .form-row { grid-template-columns: 1fr; }
        .stats-grid { grid-template-columns: repeat(2, 1fr); }
        .posts-table th:nth-child(4), .posts-table td:nth-child(4) { display: none; }
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
          <span class="nav-user">{session.displayName}</span>
          <a href="{application.basePath}/logout">Logout</a>
        </nav>
      </div>
    </header>

    <main class="main">

      <!-- Messages -->
      <q:if condition="{successMsg != ''}">
        <div class="success">{successMsg}</div>
      </q:if>
      <q:if condition="{errorMsg != ''}">
        <div class="error">{errorMsg}</div>
      </q:if>

      <!-- Stats -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">{stats.total_posts}</div>
          <div class="stat-label">Total Posts</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{stats.published_posts}</div>
          <div class="stat-label">Published</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{stats.draft_posts}</div>
          <div class="stat-label">Drafts</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{stats.total_views}</div>
          <div class="stat-label">Total Views</div>
        </div>
      </div>

      <!-- Create/Edit Form -->
      <div class="form-card">
        <h2>
          <q:if condition="{editMode}">{editPost.title} - Edit Post</q:if>
          <q:if condition="{!editMode}">Create New Post</q:if>
        </h2>

        <form method="POST" action="{application.basePath}/admin">
          <q:if condition="{editMode}">
            <input type="hidden" name="action" value="updatePost" />
            <input type="hidden" name="post_id" value="{editPost.id}" />
          </q:if>
          <q:if condition="{!editMode}">
            <input type="hidden" name="action" value="createPost" />
          </q:if>

          <div class="form-row">
            <div class="form-group">
              <label>Title</label>
              <input type="text" name="title" placeholder="Enter post title..."
                     value="{editMode ? editPost.title : ''}" required="required" />
            </div>
            <div class="form-group">
              <label>Tag</label>
              <select name="tag_id" required="required">
                <option value="">Select a tag...</option>
                <q:loop query="allTags">
                  <option value="{allTags.id}"
                          selected="{editMode and editPost.tag_id == allTags.id}">
                    {allTags.name}
                  </option>
                </q:loop>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label>Excerpt</label>
            <input type="text" name="excerpt" placeholder="A brief summary of the post..."
                   value="{editMode ? editPost.excerpt : ''}" required="required" />
          </div>

          <div class="form-group">
            <label>Featured Image URL (optional)</label>
            <input type="url" name="featured_image" placeholder="https://example.com/image.jpg"
                   value="{editMode ? editPost.featured_image : ''}" />
          </div>

          <div class="form-group">
            <label>Content</label>
            <textarea name="content" placeholder="Write your post content here (supports HTML)..."
                      required="required">{editMode ? editPost.content : ''}</textarea>
          </div>

          <div class="checkbox-row">
            <div class="checkbox-item">
              <input type="checkbox" name="is_published" id="is_published"
                     checked="{editMode and editPost.is_published}" />
              <label for="is_published">Publish immediately</label>
            </div>
            <div class="checkbox-item">
              <input type="checkbox" name="is_featured" id="is_featured"
                     checked="{editMode and editPost.is_featured}" />
              <label for="is_featured">Feature on homepage</label>
            </div>
          </div>

          <div class="btn-row">
            <q:if condition="{editMode}">
              <button type="submit" class="btn-update">Update Post</button>
              <a href="{application.basePath}/admin" class="btn-cancel">Cancel</a>
            </q:if>
            <q:if condition="{!editMode}">
              <button type="submit" class="btn-create">Create Post</button>
            </q:if>
          </div>
        </form>
      </div>

      <!-- Posts Table -->
      <div class="table-card">
        <div class="table-header">
          <h2>My Posts</h2>
        </div>

        <q:if condition="{myPosts_result.recordCount > 0}">
          <table class="posts-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Tag</th>
                <th>Status</th>
                <th>Views</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <q:loop query="myPosts">
                <tr>
                  <td class="post-title-cell">
                    <a href="{application.basePath}/post/{myPosts.slug}">{myPosts.title}</a>
                  </td>
                  <td>
                    <span class="tag-badge" style="background: {myPosts.tag_color}20; color: {myPosts.tag_color};">
                      {myPosts.tag_name}
                    </span>
                  </td>
                  <td>
                    <q:if condition="{myPosts.is_published}">
                      <span class="status-badge status-published">Published</span>
                    </q:if>
                    <q:if condition="{!myPosts.is_published}">
                      <span class="status-badge status-draft">Draft</span>
                    </q:if>
                  </td>
                  <td>{myPosts.views}</td>
                  <td>{myPosts.published_at || myPosts.created_at}</td>
                  <td>
                    <div class="action-btns">
                      <a href="{application.basePath}/admin?edit={myPosts.id}" class="btn-sm btn-edit">Edit</a>
                      <form method="POST" action="{application.basePath}/admin" style="display:inline;">
                        <input type="hidden" name="action" value="togglePublish" />
                        <input type="hidden" name="post_id" value="{myPosts.id}" />
                        <button type="submit" class="btn-sm btn-toggle">
                          {myPosts.is_published ? 'Unpublish' : 'Publish'}
                        </button>
                      </form>
                      <form method="POST" action="{application.basePath}/admin" style="display:inline;"
                            onsubmit="return confirm('Are you sure you want to delete this post?');">
                        <input type="hidden" name="action" value="deletePost" />
                        <input type="hidden" name="post_id" value="{myPosts.id}" />
                        <button type="submit" class="btn-sm btn-delete">Delete</button>
                      </form>
                    </div>
                  </td>
                </tr>
              </q:loop>
            </tbody>
          </table>
        </q:if>

        <q:if condition="{myPosts_result.recordCount == 0}">
          <div class="empty-state">
            <p>No posts yet. Create your first post above!</p>
          </div>
        </q:if>
      </div>

    </main>

    <footer>
      <span class="footer-brand">Built with <strong>Quantum Framework</strong></span>
    </footer>

  </body>
  </html>

</q:component>
