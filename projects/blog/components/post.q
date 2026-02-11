<q:component name="PostView" type="page">
  <!--
    Quantum Blog - Single Post View
    Features:
    - Database-driven content via q:query
    - View counter with IP throttling
    - AI-generated summary (via LLM connector)
    - Related posts based on tag
    - Comments system
    - SEO meta tags
  -->

  <q:set name="application.blogName" value="Quantum Blog" scope="application" />
  <q:set name="application.basePath" value="/quantum-blog" scope="application" />
  <q:set name="isLoggedIn" value="{session.authenticated}" />

  <!-- Get post slug from URL -->
  <q:set name="postSlug" value="{path.slug}" default="{query.slug}" />

  <!-- Query: Get the post by slug (cached 2 min) -->
  <q:query name="post" datasource="blog-db" cache="120">
    SELECT
      p.id,
      p.title,
      p.slug,
      p.excerpt,
      p.content,
      p.views,
      p.likes,
      p.reading_time,
      p.ai_summary,
      p.featured_image,
      p.is_published,
      TO_CHAR(p.published_at, 'YYYY-MM-DD') as published_at,
      TO_CHAR(p.updated_at, 'YYYY-MM-DD') as updated_at,
      t.name as tag_name,
      t.slug as tag_slug,
      t.color as tag_color,
      u.display_name as author_name,
      u.bio as author_bio,
      u.avatar_url as author_avatar,
      UPPER(LEFT(u.display_name, 1)) as author_initial
    FROM posts p
    LEFT JOIN tags t ON p.tag_id = t.id
    LEFT JOIN users u ON p.author_id = u.id
    WHERE p.slug = :slug AND p.is_published = TRUE

    <q:param name="slug" value="{postSlug}" type="string" maxLength="255" />
  </q:query>

  <!-- Track view (only if post exists) -->
  <q:if condition="{post_result.recordCount > 0}">
    <q:query name="trackView" datasource="blog-db" type="execute">
      SELECT increment_post_views(:postId, :ipHash)
      <q:param name="postId" value="{post.id}" type="integer" />
      <q:param name="ipHash" value="{request.clientIpHash}" type="string" />
    </q:query>
  </q:if>

  <!-- Query: Get related posts by same tag (cached 5 min) -->
  <q:query name="relatedPosts" datasource="blog-db" cache="300">
    SELECT
      p.title,
      p.slug,
      p.excerpt,
      TO_CHAR(p.published_at, 'YYYY-MM-DD') as published_at
    FROM posts p
    WHERE p.tag_id = (SELECT tag_id FROM posts WHERE slug = :currentSlug)
      AND p.slug != :currentSlug
      AND p.is_published = TRUE
    ORDER BY p.published_at DESC
    LIMIT 3

    <q:param name="currentSlug" value="{postSlug}" type="string" />
  </q:query>

  <!-- Query: Get approved comments -->
  <q:query name="comments" datasource="blog-db">
    SELECT
      c.id,
      c.author_name,
      c.content,
      c.likes,
      TO_CHAR(c.created_at, 'YYYY-MM-DD HH24:MI') as created_at
    FROM comments c
    WHERE c.post_id = :postId AND c.is_approved = TRUE
    ORDER BY c.created_at DESC

    <q:param name="postId" value="{post.id}" type="integer" />
  </q:query>

  <!-- Generate AI summary if not exists (LLM integration) -->
  <q:if condition="{post.ai_summary == '' and post_result.recordCount > 0}">
    <q:llm name="generateSummary"
           connector="llm"
           response_format="text"
           cache="3600"
           max_tokens="150">
      <q:prompt>
        Summarize this blog post in 2-3 sentences for readers who want a quick overview:

        Title: {post.title}

        Content: {post.content}

        Write a concise, engaging summary that captures the key points.
      </q:prompt>
    </q:llm>

    <!-- Store the generated summary -->
    <q:if condition="{generateSummary.success}">
      <q:query name="updateSummary" datasource="blog-db" type="execute">
        UPDATE posts SET ai_summary = :summary WHERE id = :postId
        <q:param name="summary" value="{generateSummary.data}" type="string" />
        <q:param name="postId" value="{post.id}" type="integer" />
      </q:query>
      <q:set name="post.ai_summary" value="{generateSummary.data}" />
    </q:if>
  </q:if>

  <html>
  <head>
    <!-- Dynamic SEO meta tags -->
    <title>{post.title} - {application.blogName}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="{post.excerpt}" />
    <meta name="author" content="{post.author_name}" />
    <meta name="keywords" content="{post.tag_name}, quantum, blog" />

    <!-- Open Graph -->
    <meta property="og:title" content="{post.title}" />
    <meta property="og:description" content="{post.excerpt}" />
    <meta property="og:type" content="article" />
    <meta property="og:url" content="{application.basePath}/post/{post.slug}" />
    <q:if condition="{post.featured_image != ''}">
      <meta property="og:image" content="{post.featured_image}" />
    </q:if>
    <meta property="article:published_time" content="{post.published_at}" />
    <meta property="article:author" content="{post.author_name}" />
    <meta property="article:tag" content="{post.tag_name}" />

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{post.title}" />
    <meta name="twitter:description" content="{post.excerpt}" />

    <!-- Include shared styles -->
    <q:include component="shared/styles" />
  </head>
  <body>

    <!-- Header -->
    <q:include component="shared/header" />

    <main class="article-container">

      <!-- Post Found -->
      <q:if condition="{post_result.recordCount > 0}">

        <!-- Post Header -->
        <article>
          <div class="post-header">
            <a href="{application.basePath}/?tag={post.tag_slug}"
               class="post-tag"
               style="background: {post.tag_color}20; color: {post.tag_color};">
              {post.tag_name}
            </a>
            <h1 class="post-title">{post.title}</h1>
            <div class="post-meta">
              <div class="meta-author">
                <div class="author-avatar" style="font-size: 1rem; width: 36px; height: 36px;">
                  {post.author_initial}
                </div>
                <div class="author-info">
                  <span class="author-name">{post.author_name}</span>
                  <span class="author-date">{post.published_at} · {post.reading_time} min read · {post.views} views</span>
                </div>
              </div>
            </div>
          </div>

          <!-- AI Summary -->
          <q:if condition="{post.ai_summary != ''}">
            <div class="ai-summary">
              <div class="ai-summary-header">
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                </svg>
                AI Summary
              </div>
              <p>{post.ai_summary}</p>
            </div>
          </q:if>

          <!-- Post Content -->
          <div class="post-content">
            <q:html value="{post.content}" />
          </div>

          <!-- Back Link -->
          <div class="back-bar">
            <a href="{application.basePath}/" class="back-link">&#8592; Back to all posts</a>

            <!-- Social Share -->
            <div style="float: right;">
              <a href="https://twitter.com/intent/tweet?text={encodeURIComponent(post.title)}&amp;url={application.basePath}/post/{post.slug}"
                 target="_blank"
                 style="color: #1da1f2; margin-right: 12px;">
                Share on Twitter
              </a>
              <a href="https://www.linkedin.com/sharing/share-offsite/?url={application.basePath}/post/{post.slug}"
                 target="_blank"
                 style="color: #0077b5;">
                Share on LinkedIn
              </a>
            </div>
          </div>
        </article>

        <!-- Related Posts -->
        <q:if condition="{relatedPosts_result.recordCount > 0}">
          <section class="related-posts">
            <h3>Related Posts</h3>
            <div class="related-grid">
              <q:loop query="relatedPosts">
                <a href="{application.basePath}/post/{relatedPosts.slug}" class="related-card">
                  <h4>{relatedPosts.title}</h4>
                  <p>{relatedPosts.published_at}</p>
                </a>
              </q:loop>
            </div>
          </section>
        </q:if>

        <!-- Comments Section -->
        <section class="comments-section">
          <h3>Comments ({comments_result.recordCount})</h3>

          <!-- Comment Form -->
          <q:action name="addComment" method="POST">
            <q:validate field="author_name" required="true" minLength="2" maxLength="100" />
            <q:validate field="content" required="true" minLength="10" maxLength="2000" />

            <q:query name="insertComment" datasource="blog-db" type="execute">
              INSERT INTO comments (post_id, author_name, author_email, content)
              VALUES (:postId, :authorName, :email, :content)
              <q:param name="postId" value="{post.id}" type="integer" />
              <q:param name="authorName" value="{form.author_name}" type="string" />
              <q:param name="email" value="{form.author_email}" type="string" />
              <q:param name="content" value="{form.content}" type="string" />
            </q:query>

            <q:set name="commentSuccess" value="true" />
          </q:action>

          <q:if condition="{commentSuccess}">
            <div style="background: #dcfce7; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; color: #166534;">
              Thank you! Your comment is pending approval.
            </div>
          </q:if>

          <form class="comment-form" method="POST" action="{application.basePath}/post/{post.slug}">
            <input type="hidden" name="action" value="addComment" />
            <div class="form-group">
              <label>Your Name</label>
              <input type="text" name="author_name" required="required" placeholder="John Doe" />
            </div>
            <div class="form-group">
              <label>Email (optional, not published)</label>
              <input type="email" name="author_email" placeholder="john@example.com" />
            </div>
            <div class="form-group">
              <label>Comment</label>
              <textarea name="content" required="required" placeholder="Share your thoughts..."></textarea>
            </div>
            <button type="submit" class="btn-primary">Post Comment</button>
          </form>

          <!-- Comments List -->
          <div style="margin-top: 32px;">
            <q:loop query="comments">
              <div class="comment">
                <div class="comment-header">
                  <div class="author-avatar" style="width: 32px; height: 32px; font-size: 0.75rem;">
                    {comments.author_name.charAt(0).toUpperCase()}
                  </div>
                  <span class="comment-author">{comments.author_name}</span>
                  <span class="comment-date">{comments.created_at}</span>
                </div>
                <div class="comment-content">{comments.content}</div>
              </div>
            </q:loop>

            <q:if condition="{comments_result.recordCount == 0}">
              <p style="color: #94a3b8; text-align: center; padding: 24px;">
                No comments yet. Be the first to share your thoughts!
              </p>
            </q:if>
          </div>
        </section>

      </q:if>

      <!-- Post Not Found -->
      <q:if condition="{post_result.recordCount == 0}">
        <div class="not-found">
          <div class="nf-code">404</div>
          <h2>Post not found</h2>
          <p>The post you are looking for does not exist or has been removed.</p>
          <a href="{application.basePath}/" class="back-link">&#8592; Back to blog</a>
        </div>
      </q:if>

    </main>

    <!-- Footer -->
    <q:include component="shared/footer" />

  </body>
  </html>

</q:component>
