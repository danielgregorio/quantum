<q:component name="BlogCRUD">
  <!--
    🎯 BLOG CRUD - Complete Real-World Example

    Features demonstrated:
    - q:query (database queries)
    - q:loop type="array" (iterate query results)
    - q:action (form submission)
    - q:if (conditional rendering)
    - q:function (reusable logic)
    - q:mail (email notifications)
    - Databinding expressions
  -->

  <h1>📝 Quantum Blog</h1>

  <!-- Get query param for action -->
  <q:set name="action" value="{query.action}" />
  <q:set name="postId" value="{query.id}" />

  <!-- QUERY: Get all blog posts -->
  <q:query name="posts" datasource="blog_db" max_rows="10">
    SELECT id, title, author, content, created_at, published
    FROM blog_posts
    WHERE published = 1
    ORDER BY created_at DESC
  </q:query>

  <!-- QUERY: Get post count -->
  <q:query name="stats" datasource="blog_db">
    SELECT
      COUNT(*) as total_posts,
      SUM(CASE WHEN published = 1 THEN 1 ELSE 0 END) as published_posts
    FROM blog_posts
  </q:query>

  <!-- Display stats -->
  <div class="stats">
    <h2>Blog Statistics</h2>
    <p>Total Posts: {stats.data[0].total_posts}</p>
    <p>Published: {stats.data[0].published_posts}</p>
  </div>

  <!-- CREATE: New post form -->
  <div class="create-section">
    <h2>✏️ Create New Post</h2>

    <form method="POST" action="?action=create">
      <div class="form-group">
        <label for="title">Title:</label>
        <input type="text" id="title" name="title" required />
      </div>

      <div class="form-group">
        <label for="author">Author:</label>
        <input type="text" id="author" name="author" required />
      </div>

      <div class="form-group">
        <label for="content">Content:</label>
        <textarea id="content" name="content" rows="10" required></textarea>
      </div>

      <div class="form-group">
        <label>
          <input type="checkbox" name="published" value="1" />
          Publish immediately
        </label>
      </div>

      <button type="submit">Create Post</button>
    </form>
  </div>

  <!-- ACTION: Handle post creation -->
  <q:action name="create" method="POST">
    <q:param name="title" type="string" required="true" />
    <q:param name="author" type="string" required="true" />
    <q:param name="content" type="string" required="true" />
    <q:param name="published" type="boolean" default="false" />

    <!-- Insert new post -->
    <q:query name="insertResult" datasource="blog_db">
      INSERT INTO blog_posts (title, author, content, published, created_at)
      VALUES ('{title}', '{author}', '{content}', {published}, NOW())
    </q:query>

    <!-- Send notification email -->
    <q:mail to="admin@quantum.dev" subject="New Blog Post Created">
      <h2>New Blog Post</h2>
      <p><strong>Title:</strong> {title}</p>
      <p><strong>Author:</strong> {author}</p>
      <p><strong>Published:</strong> {published}</p>
    </q:mail>

    <!-- Redirect to list -->
    <q:redirect url="/blog_crud" flash="Post created successfully!" />
  </q:action>

  <!-- READ: Display all posts -->
  <div class="posts-section">
    <h2>📚 All Posts</h2>

    <div class="posts-grid">
      <q:loop type="array" var="post" items="posts">
        <div class="post-card">
          <h3>{post.title}</h3>
          <p class="author">By {post.author}</p>
          <p class="date">{post.created_at}</p>

          <div class="content-preview">
            {post.content}
          </div>

          <div class="actions">
            <a href="?action=view&id={post.id}" class="btn btn-primary">View</a>
            <a href="?action=edit&id={post.id}" class="btn btn-secondary">Edit</a>
            <a href="?action=delete&id={post.id}" class="btn btn-danger"
               onclick="return confirm('Delete this post?')">Delete</a>
          </div>

          <!-- Published badge -->
          <q:if condition="{post.published}">
            <span class="badge published">Published</span>
          </q:if>

          <q:if condition="{post.published == 0}">
            <span class="badge draft">Draft</span>
          </q:if>
        </div>
      </q:loop>
    </div>
  </div>

  <!-- UPDATE: Edit post form (if action=edit) -->
  <q:if condition="{action == 'edit'}">
    <div class="edit-section">
      <h2>✏️ Edit Post #{postId}</h2>

      <!-- Get post to edit -->
      <q:query name="editPost" datasource="blog_db">
        SELECT * FROM blog_posts WHERE id = {postId}
      </q:query>

      <form method="POST" action="?action=update&id={postId}">
        <div class="form-group">
          <label for="title">Title:</label>
          <input type="text" id="title" name="title"
                 value="{editPost.data[0].title}" required />
        </div>

        <div class="form-group">
          <label for="author">Author:</label>
          <input type="text" id="author" name="author"
                 value="{editPost.data[0].author}" required />
        </div>

        <div class="form-group">
          <label for="content">Content:</label>
          <textarea id="content" name="content" rows="10" required>{editPost.data[0].content}</textarea>
        </div>

        <button type="submit">Update Post</button>
        <a href="/blog_crud" class="btn btn-secondary">Cancel</a>
      </form>
    </div>

    <!-- ACTION: Handle post update -->
    <q:action name="update" method="POST">
      <q:param name="title" type="string" required="true" />
      <q:param name="author" type="string" required="true" />
      <q:param name="content" type="string" required="true" />

      <q:query name="updateResult" datasource="blog_db">
        UPDATE blog_posts
        SET title = '{title}',
            author = '{author}',
            content = '{content}',
            updated_at = NOW()
        WHERE id = {postId}
      </q:query>

      <q:redirect url="/blog_crud" flash="Post updated successfully!" />
    </q:action>
  </q:if>

  <!-- DELETE: Handle post deletion -->
  <q:action name="delete" method="GET">
    <q:query name="deleteResult" datasource="blog_db">
      DELETE FROM blog_posts WHERE id = {postId}
    </q:query>

    <q:redirect url="/blog_crud" flash="Post deleted successfully!" />
  </q:action>

  <!-- Styling -->
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f5f7fa;
      padding: 20px;
    }

    h1 {
      color: #2c3e50;
      margin-bottom: 30px;
    }

    .stats {
      background: white;
      padding: 20px;
      border-radius: 8px;
      margin-bottom: 30px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .create-section, .edit-section {
      background: white;
      padding: 30px;
      border-radius: 8px;
      margin-bottom: 30px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .form-group {
      margin-bottom: 20px;
    }

    .form-group label {
      display: block;
      margin-bottom: 5px;
      font-weight: 500;
      color: #2c3e50;
    }

    .form-group input[type="text"],
    .form-group textarea {
      width: 100%;
      padding: 10px;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 14px;
    }

    .posts-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
      gap: 20px;
    }

    .post-card {
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      position: relative;
    }

    .post-card h3 {
      color: #2c3e50;
      margin-bottom: 10px;
    }

    .author {
      color: #7f8c8d;
      font-size: 14px;
      margin-bottom: 5px;
    }

    .date {
      color: #95a5a6;
      font-size: 12px;
      margin-bottom: 15px;
    }

    .content-preview {
      color: #34495e;
      line-height: 1.6;
      margin-bottom: 15px;
      max-height: 100px;
      overflow: hidden;
    }

    .actions {
      display: flex;
      gap: 10px;
    }

    .btn {
      padding: 8px 16px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      text-decoration: none;
      font-size: 14px;
      display: inline-block;
    }

    .btn-primary {
      background: #3498db;
      color: white;
    }

    .btn-secondary {
      background: #95a5a6;
      color: white;
    }

    .btn-danger {
      background: #e74c3c;
      color: white;
    }

    .badge {
      position: absolute;
      top: 10px;
      right: 10px;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: bold;
    }

    .badge.published {
      background: #2ecc71;
      color: white;
    }

    .badge.draft {
      background: #f39c12;
      color: white;
    }

    button {
      background: #3498db;
      color: white;
      padding: 12px 24px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 16px;
    }

    button:hover {
      background: #2980b9;
    }
  </style>
</q:component>
