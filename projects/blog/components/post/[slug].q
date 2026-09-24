<q:component name="Post">
  <q:import component="Styles" from="_shared" />
  <q:import component="Header" from="_shared" />
  <q:import component="Footer" from="_shared" />
  <!-- One post: /post/<slug>. Readers comment; the comment appears at once. -->

  <q:action name="comment" method="POST">
    <q:param name="author_name" required="true" minlength="2" maxlength="100" />
    <q:param name="content" required="true" minlength="3" maxlength="2000" />

    <!-- The action does not run the page: it looks the post up itself. -->
    <q:query name="target" datasource="blog-db">
      SELECT id FROM posts WHERE slug = :slug AND is_published = 1
      <q:param name="slug" value="{slug}" type="string" />
    </q:query>
    <q:if condition="target_result.recordCount == 0">
      <q:redirect url="/" flash="That post does not exist." flashType="error" />
    </q:if>

    <q:query name="insertComment" datasource="blog-db">
      INSERT INTO comments (post_id, author_name, content) VALUES (:post, :author, :content)
      <q:param name="post" value="{target.id}" type="integer" />
      <q:param name="author" value="{author_name}" type="string" />
      <q:param name="content" value="{content}" type="string" />
    </q:query>
    <q:redirect url="/post/{slug}#comments" flash="Thanks, {author_name}! Your comment is published." />
  </q:action>

  <q:query name="post" datasource="blog-db">
    SELECT p.id, p.title, p.excerpt, p.content, p.views, p.reading_time, p.published_at,
           t.name AS tag_name, t.slug AS tag_slug, t.color AS tag_color,
           COALESCE(u.display_name, 'Quantum team') AS author_name
    FROM posts p
    LEFT JOIN tags t ON p.tag_id = t.id
    LEFT JOIN users u ON p.author_id = u.id
    WHERE p.slug = :slug AND p.is_published = 1
    <q:param name="slug" value="{slug}" type="string" />
  </q:query>

  <q:if condition="post_result.recordCount == 1">
    <q:query name="countView" datasource="blog-db">
      UPDATE posts SET views = views + 1 WHERE id = :id
      <q:param name="id" value="{post.id}" type="integer" />
    </q:query>
    <q:query name="comments" datasource="blog-db">
      SELECT author_name, content, created_at FROM comments
      WHERE post_id = :id ORDER BY id DESC
      <q:param name="id" value="{post.id}" type="integer" />
    </q:query>
    <q:query name="related" datasource="blog-db">
      SELECT title, slug, published_at FROM posts
      WHERE tag_id = (SELECT tag_id FROM posts WHERE id = :id) AND id != :id AND is_published = 1
      ORDER BY published_at DESC LIMIT 3
      <q:param name="id" value="{post.id}" type="integer" />
    </q:query>
  </q:if>

  <html>
  <head>
    <title>{post.title if post_result.recordCount else 'Not found'} - Quantum Blog</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <Styles />
  </head>
  <body>
    <Header />
    <main class="article-container">
      <q:if condition="post_result.recordCount == 1">
        <article>
          <div class="post-header">
            <a href="/?tag={post.tag_slug}" class="post-tag"
               style="background: {post.tag_color}20; color: {post.tag_color};">{post.tag_name}</a>
            <h1 class="post-title">{post.title}</h1>
            <div class="post-meta">
              <span class="author-name">{post.author_name}</span>
              <span class="author-date">{post.published_at} · {post.reading_time} min read · {post.views + 1} views</span>
            </div>
          </div>
          <div class="post-content"><p class="text">{post.content}</p></div>
          <div class="back-bar"><a href="/" class="back-link">&#8592; All posts</a></div>
        </article>

        <q:if condition="related_result.recordCount > 0">
          <section class="related-posts">
            <h3>Related posts</h3>
            <div class="related-grid">
              <q:loop query="related">
                <a href="/post/{related.slug}" class="related-card">
                  <h4>{related.title}</h4>
                  <p>{related.published_at}</p>
                </a>
              </q:loop>
            </div>
          </section>
        </q:if>

        <section class="comments-section" id="comments">
          <h3>Comments ({comments_result.recordCount})</h3>
          <q:if condition="flash">
            <div class="flash flash-{flashType}">{flash}</div>
          </q:if>
          <form class="comment-form" method="POST" action="/post/{slug}">
            <input type="hidden" name="action" value="comment" />
            <div class="form-group">
              <label>Your name</label>
              <input type="text" name="author_name" required="required" />
            </div>
            <div class="form-group">
              <label>Comment</label>
              <textarea name="content" required="required"></textarea>
            </div>
            <button type="submit" class="btn-primary">Post comment</button>
          </form>
          <q:loop query="comments">
            <div class="comment">
              <strong>{comments.author_name}</strong> <span class="comment-date">{comments.created_at}</span>
              <p class="text">{comments.content}</p>
            </div>
          </q:loop>
        </section>
      </q:if>
      <q:else>
        <div class="not-found">
          <div class="nf-code">404</div>
          <h2>Post not found</h2>
          <a href="/" class="back-link">&#8592; Back to the blog</a>
        </div>
      </q:else>
    </main>
    <Footer />
  </body>
  </html>
</q:component>
