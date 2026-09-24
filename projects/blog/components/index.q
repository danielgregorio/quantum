<q:component name="Home">
  <q:import component="Styles" from="_shared" />
  <q:import component="Header" from="_shared" />
  <q:import component="Footer" from="_shared" />
  <!-- Home: published posts, newest first, filtered by tag, ten per page.
       The page is the URL's ?page= (DB-9); <ui:pager> draws the links and
       keeps ?tag= in them (UI-11). -->

  <q:set name="tagFilter" value="{query.tag}" default="" />

  <q:query name="stats" datasource="blog-db">
    SELECT COUNT(*) AS total_posts, COALESCE(SUM(views), 0) AS total_views
    FROM posts WHERE is_published = 1
  </q:query>

  <q:query name="tags" datasource="blog-db">
    SELECT t.name, t.slug, t.color, COUNT(p.id) AS post_count
    FROM tags t JOIN posts p ON p.tag_id = t.id AND p.is_published = 1
    GROUP BY t.id ORDER BY post_count DESC, t.name
  </q:query>

  <q:query name="posts" datasource="blog-db" paginate="true" page_size="10">
    SELECT p.title, p.slug, p.excerpt, p.views, p.reading_time, p.published_at,
           t.name AS tag_name, t.color AS tag_color,
           COALESCE(u.display_name, 'Quantum team') AS author_name
    FROM posts p
    LEFT JOIN tags t ON p.tag_id = t.id
    LEFT JOIN users u ON p.author_id = u.id
    WHERE p.is_published = 1 AND (:tag = '' OR t.slug = :tag)
    ORDER BY p.published_at DESC, p.id DESC
    <q:param name="tag" value="{tagFilter}" type="string" />
  </q:query>

  <html>
  <head>
    <title>Quantum Blog</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <Styles />
  </head>
  <body>
    <Header />

    <section class="hero">
      <div class="hero-content">
        <h1>The <span>Quantum</span> Blog</h1>
        <p>A blog written in Quantum: .q pages over SQLite, no JavaScript.</p>
        <div class="hero-stats">
          <div class="hero-stat"><strong>{stats.total_posts}</strong> Posts</div>
          <div class="hero-stat"><strong>{stats.total_views}</strong> Views</div>
        </div>
      </div>
    </section>

    <main class="main">
      <q:if condition="flash">
        <div class="flash flash-{flashType}">{flash}</div>
      </q:if>
      <div class="tags-filter">
        <a href="/" class="tag-pill {'active' if tagFilter == '' else ''}">All</a>
        <q:loop query="tags">
          <a href="/?tag={tags.slug}" class="tag-pill {'active' if tagFilter == tags.slug else ''}"
             style="--tag-color: {tags.color};">{tags.name} ({tags.post_count})</a>
        </q:loop>
      </div>

      <div class="section-header">
        <h2 class="section-title">
          <q:if condition="tagFilter">Posts tagged "{tagFilter}"</q:if>
          <q:else>Latest posts</q:else>
        </h2>
        <span class="post-count-badge">{posts_result.pagination.totalRecords} published</span>
      </div>

      <div class="posts-grid">
        <q:loop query="posts">
          <a href="/post/{posts.slug}" class="post-card">
            <div class="post-top">
              <span class="post-tag" style="background: {posts.tag_color}20; color: {posts.tag_color};">{posts.tag_name}</span>
              <span class="post-date">{posts.published_at}</span>
            </div>
            <h2>{posts.title}</h2>
            <p>{posts.excerpt}</p>
            <div class="post-footer">
              <span class="author-name">{posts.author_name}</span>
              <span class="post-views">{posts.views} views · {posts.reading_time} min</span>
            </div>
          </a>
        </q:loop>
      </div>

      <q:if condition="posts_result.recordCount == 0">
        <p class="empty">No posts here yet.</p>
      </q:if>

      <ui:pager for="posts" />
    </main>

    <Footer />
  </body>
  </html>
</q:component>
