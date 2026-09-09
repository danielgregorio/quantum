<q:component name="BlogHome" type="page">
  <!--
    Quantum Blog - Home Page
    Features:
    - Database-driven posts via q:query
    - Query caching for performance
    - Pagination support
    - Tag filtering
    - View counts from database
    - AI-generated stats (optional)
  -->

  <!-- Application-level settings -->
  <q:set name="application.blogName" value="Quantum Blog" scope="application" />
  <q:set name="application.basePath" value="/quantum-blog" scope="application" />
  <q:set name="isLoggedIn" value="{session.authenticated}" />

  <!-- Pagination settings -->
  <q:set name="page" value="{query.page}" default="1" type="integer" />
  <q:set name="perPage" value="10" type="integer" />
  <q:set name="offset" value="{(page - 1) * perPage}" type="integer" />

  <!-- Tag filter -->
  <q:set name="tagFilter" value="{query.tag}" default="" />

  <!-- Query: Get total post count (cached 5 min) -->
  <q:query name="postStats" datasource="blog-db" cache="300">
    SELECT
      COUNT(*) FILTER (WHERE is_published = TRUE) as total_posts,
      COUNT(DISTINCT author_id) as total_authors,
      SUM(views) as total_views
    FROM posts
  </q:query>

  <!-- Query: Get all tags for filter (cached 10 min) -->
  <q:query name="allTags" datasource="blog-db" cache="600">
    SELECT id, name, slug, color, post_count
    FROM tags
    WHERE post_count > 0
    ORDER BY post_count DESC
  </q:query>

  <!-- Query: Get published posts with pagination -->
  <q:query name="posts" datasource="blog-db" cache="60">
    SELECT
      p.id,
      p.title,
      p.slug,
      p.excerpt,
      p.views,
      p.reading_time,
      p.is_featured,
      TO_CHAR(p.published_at, 'YYYY-MM-DD') as published_at,
      t.name as tag_name,
      t.slug as tag_slug,
      t.color as tag_color,
      u.display_name as author_name,
      UPPER(LEFT(u.display_name, 1)) as author_initial
    FROM posts p
    LEFT JOIN tags t ON p.tag_id = t.id
    LEFT JOIN users u ON p.author_id = u.id
    WHERE p.is_published = TRUE
    <q:if condition="{tagFilter != ''}">
      AND t.slug = :tagFilter
      <q:param name="tagFilter" value="{tagFilter}" type="string" />
    </q:if>
    ORDER BY p.is_featured DESC, p.published_at DESC
    LIMIT :limit OFFSET :offset
    <q:param name="limit" value="{perPage}" type="integer" />
    <q:param name="offset" value="{offset}" type="integer" />
  </q:query>

  <!-- Query: Get featured posts for hero (cached 5 min) -->
  <q:query name="featuredPosts" datasource="blog-db" cache="300">
    SELECT p.title, p.slug, p.excerpt
    FROM posts p
    WHERE p.is_published = TRUE AND p.is_featured = TRUE
    ORDER BY p.published_at DESC
    LIMIT 3
  </q:query>

  <!-- Calculate pagination -->
  <q:set name="totalPages" value="{Math.ceil(postStats.total_posts / perPage)}" type="integer" />
  <q:set name="hasPrev" value="{page > 1}" />
  <q:set name="hasNext" value="{page < totalPages}" />

  <html>
  <head>
    <title>{application.blogName} - Modern Blog Built with Quantum</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="A modern blog built entirely with the Quantum Framework. No JavaScript needed." />

    <!-- Open Graph -->
    <meta property="og:title" content="{application.blogName}" />
    <meta property="og:description" content="A modern blog built with the Quantum Framework" />
    <meta property="og:type" content="website" />
    <meta property="og:url" content="{application.basePath}/" />

    <!-- Include shared styles -->
    <q:include component="shared/styles" />
  </head>
  <body>

    <!-- Header -->
    <q:include component="shared/header" />

    <!-- Hero Section -->
    <section class="hero">
      <div class="hero-content">
        <h1>The <span>Quantum</span> Blog</h1>
        <p>A fully functional blog powered by PostgreSQL, with caching, pagination, and AI features. Zero JavaScript.</p>
        <div class="hero-stats">
          <div class="hero-stat">
            <strong>{postStats.total_posts}</strong> Posts
          </div>
          <div class="hero-stat">
            <strong>{postStats.total_views}</strong> Views
          </div>
          <div class="hero-stat">
            <strong>0</strong> JavaScript
          </div>
        </div>
      </div>
    </section>

    <main class="main">
      <!-- Tags Filter -->
      <div class="tags-filter">
        <a href="{application.basePath}/" class="tag-pill {tagFilter == '' ? 'active' : ''}">All</a>
        <q:loop query="allTags">
          <a href="{application.basePath}/?tag={allTags.slug}"
             class="tag-pill {tagFilter == allTags.slug ? 'active' : ''}"
             style="--tag-color: {allTags.color};">
            {allTags.name} ({allTags.post_count})
          </a>
        </q:loop>
      </div>

      <!-- Section Header -->
      <div class="section-header">
        <h2 class="section-title">
          <q:if condition="{tagFilter != ''}">
            Posts tagged "{tagFilter}"
          </q:if>
          <q:if condition="{tagFilter == ''}">
            Latest Posts
          </q:if>
        </h2>
        <span class="post-count-badge">{postStats.total_posts} published</span>
      </div>

      <!-- Posts Grid -->
      <div class="posts-grid">
        <q:loop query="posts">
          <a href="{application.basePath}/post/{posts.slug}" class="post-card">
            <div class="post-top">
              <span class="post-tag" style="background: {posts.tag_color}20; color: {posts.tag_color};">
                {posts.tag_name}
              </span>
              <span class="post-date">{posts.published_at}</span>
            </div>
            <h2>{posts.title}</h2>
            <p>{posts.excerpt}</p>
            <div class="post-footer">
              <div class="post-author">
                <div class="author-avatar">{posts.author_initial}</div>
                <span class="author-name">{posts.author_name}</span>
              </div>
              <div class="post-meta-right">
                <span class="post-views">{posts.views} views</span>
                <span class="read-more">Read more &#8594;</span>
              </div>
            </div>
          </a>
        </q:loop>
      </div>

      <!-- Empty State -->
      <q:if condition="{posts_result.recordCount == 0}">
        <div style="text-align:center; padding:60px 20px; color:#94a3b8;">
          <q:if condition="{tagFilter != ''}">
            <p>No posts found with tag "{tagFilter}".</p>
            <a href="{application.basePath}/" style="color:#6366f1;">View all posts</a>
          </q:if>
          <q:if condition="{tagFilter == ''}">
            <p>No posts yet. <a href="{application.basePath}/admin" style="color:#6366f1;">Create one</a>.</p>
          </q:if>
        </div>
      </q:if>

      <!-- Pagination -->
      <q:if condition="{totalPages > 1}">
        <div class="pagination">
          <q:if condition="{hasPrev}">
            <a href="{application.basePath}/?page={page - 1}{tagFilter != '' ? '&amp;tag=' + tagFilter : ''}">
              &#8592; Previous
            </a>
          </q:if>
          <q:if condition="{!hasPrev}">
            <span class="disabled">&#8592; Previous</span>
          </q:if>

          <span class="current">Page {page} of {totalPages}</span>

          <q:if condition="{hasNext}">
            <a href="{application.basePath}/?page={page + 1}{tagFilter != '' ? '&amp;tag=' + tagFilter : ''}">
              Next &#8594;
            </a>
          </q:if>
          <q:if condition="{!hasNext}">
            <span class="disabled">Next &#8594;</span>
          </q:if>
        </div>
      </q:if>
    </main>

    <!-- Footer -->
    <q:include component="shared/footer" />

  </body>
  </html>

</q:component>
