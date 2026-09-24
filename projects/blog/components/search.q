<q:component name="Search">
  <q:import component="Styles" from="_shared" />
  <q:import component="Header" from="_shared" />
  <q:import component="Footer" from="_shared" />
  <!-- Search: /search?q=words — title, excerpt and text, most viewed first. -->

  <!-- {trim(query.q)} failed when the URL had no ?q= at all: /search answered 500. -->
  <q:set name="term" value="{query.q}" default="" />
  <q:set name="term" value="{trim(term)}" />

  <q:if condition="term">
    <q:query name="results" datasource="blog-db">
      SELECT p.title, p.slug, p.excerpt, p.published_at, t.name AS tag_name, t.color AS tag_color
      FROM posts p LEFT JOIN tags t ON p.tag_id = t.id
      WHERE p.is_published = 1
        AND (p.title LIKE :pattern OR p.excerpt LIKE :pattern OR p.content LIKE :pattern)
      ORDER BY p.views DESC LIMIT 20
      <q:param name="pattern" value="%{term}%" type="string" />
    </q:query>
  </q:if>

  <html>
  <head>
    <title>Search - Quantum Blog</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <Styles />
  </head>
  <body>
    <Header />
    <main class="main">
      <!-- Search as you type (UI-12): each pause in typing asks for this page
           with ?q= and swaps only #resultados. Without JavaScript, Enter
           searches the same way. -->
      <div class="search-form">
        <ui:input bind="q" search="resultados" placeholder="Search posts" grow="true" />
      </div>

      <div id="resultados">
      <q:if condition="term">
        <h2 class="section-title">{results_result.recordCount} result(s) for "{term}"</h2>
        <div class="posts-grid">
          <q:loop query="results">
            <a href="/post/{results.slug}" class="post-card">
              <div class="post-top">
                <span class="post-tag" style="background: {results.tag_color}20; color: {results.tag_color};">{results.tag_name}</span>
                <span class="post-date">{results.published_at}</span>
              </div>
              <h2>{results.title}</h2>
              <p>{results.excerpt}</p>
            </a>
          </q:loop>
        </div>
      </q:if>
      </div>
    </main>
    <Footer />
  </body>
  </html>
</q:component>
