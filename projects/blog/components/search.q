<q:component name="SearchPage" type="page">
  <!--
    Quantum Blog - Search Page
    Features:
    - Full-text search via PostgreSQL ts_vector
    - Highlighted search results
    - Search suggestions
    - Result caching
  -->

  <q:set name="application.blogName" value="Quantum Blog" scope="application" />
  <q:set name="application.basePath" value="/quantum-blog" scope="application" />

  <!-- Get search query from URL -->
  <q:set name="searchQuery" value="{query.q}" default="" />
  <q:set name="searchPage" value="{query.page}" default="1" type="integer" />
  <q:set name="perPage" value="10" type="integer" />
  <q:set name="offset" value="{(searchPage - 1) * perPage}" type="integer" />

  <!-- Full-text search query (cached 1 min) -->
  <q:if condition="{searchQuery != ''}">
    <q:query name="searchResults" datasource="blog-db" cache="60">
      SELECT
        p.id,
        p.title,
        p.slug,
        p.excerpt,
        p.views,
        p.reading_time,
        TO_CHAR(p.published_at, 'YYYY-MM-DD') as published_at,
        t.name as tag_name,
        t.slug as tag_slug,
        t.color as tag_color,
        u.display_name as author_name,
        UPPER(LEFT(u.display_name, 1)) as author_initial,
        ts_rank(
          to_tsvector('english', p.title || ' ' || COALESCE(p.excerpt, '') || ' ' || p.content),
          plainto_tsquery('english', :query)
        ) as relevance
      FROM posts p
      LEFT JOIN tags t ON p.tag_id = t.id
      LEFT JOIN users u ON p.author_id = u.id
      WHERE p.is_published = TRUE
        AND to_tsvector('english', p.title || ' ' || COALESCE(p.excerpt, '') || ' ' || p.content)
            @@ plainto_tsquery('english', :query)
      ORDER BY relevance DESC, p.published_at DESC
      LIMIT :limit OFFSET :offset

      <q:param name="query" value="{searchQuery}" type="string" />
      <q:param name="limit" value="{perPage}" type="integer" />
      <q:param name="offset" value="{offset}" type="integer" />
    </q:query>

    <!-- Get total count for pagination -->
    <q:query name="searchCount" datasource="blog-db" cache="60">
      SELECT COUNT(*) as total
      FROM posts p
      WHERE p.is_published = TRUE
        AND to_tsvector('english', p.title || ' ' || COALESCE(p.excerpt, '') || ' ' || p.content)
            @@ plainto_tsquery('english', :query)

      <q:param name="query" value="{searchQuery}" type="string" />
    </q:query>

    <q:set name="totalResults" value="{searchCount.total}" />
    <q:set name="totalPages" value="{Math.ceil(totalResults / perPage)}" />
  </q:if>

  <!-- Popular searches (for empty state) -->
  <q:query name="popularTags" datasource="blog-db" cache="600">
    SELECT name, slug, color, post_count
    FROM tags
    WHERE post_count > 0
    ORDER BY post_count DESC
    LIMIT 5
  </q:query>

  <!-- Recent posts (for empty state) -->
  <q:query name="recentPosts" datasource="blog-db" cache="300">
    SELECT title, slug
    FROM posts
    WHERE is_published = TRUE
    ORDER BY published_at DESC
    LIMIT 5
  </q:query>

  <html>
  <head>
    <title>
      <q:if condition="{searchQuery != ''}">
        Search: {searchQuery} - {application.blogName}
      </q:if>
      <q:if condition="{searchQuery == ''}">
        Search - {application.blogName}
      </q:if>
    </title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="robots" content="noindex" />

    <!-- Include shared styles -->
    <q:include component="shared/styles" />

    <style>
      /* Search-specific styles */
      .search-hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 60px 24px;
        text-align: center;
      }
      .search-hero h1 { color: #fff; font-size: 2rem; margin-bottom: 24px; }
      .search-form {
        max-width: 600px; margin: 0 auto;
        display: flex; gap: 12px;
      }
      .search-input {
        flex: 1; padding: 16px 20px;
        border: 2px solid #334155; border-radius: 12px;
        background: rgba(15,23,42,0.8); color: #fff;
        font-size: 1rem; font-family: inherit;
        transition: all 0.2s;
      }
      .search-input:focus {
        outline: none; border-color: #6366f1;
        box-shadow: 0 0 0 4px rgba(99,102,241,0.2);
      }
      .search-input::placeholder { color: #64748b; }
      .search-btn {
        padding: 16px 32px; background: #6366f1; color: white;
        border: none; border-radius: 12px;
        font-size: 1rem; font-weight: 600; cursor: pointer;
        transition: all 0.2s;
      }
      .search-btn:hover { background: #4f46e5; transform: translateY(-1px); }

      .search-results { max-width: 800px; margin: 0 auto; padding: 40px 24px; }
      .results-header { margin-bottom: 24px; }
      .results-header h2 { font-size: 1.2rem; color: #1e293b; margin-bottom: 4px; }
      .results-header p { color: #64748b; font-size: 0.9rem; }

      .result-card {
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 24px; margin-bottom: 16px;
        transition: all 0.2s;
      }
      .result-card:hover {
        border-color: #c7d2fe; box-shadow: 0 4px 12px rgba(99,102,241,0.08);
      }
      .result-card a { text-decoration: none; color: inherit; display: block; }
      .result-meta { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }
      .result-card h3 { font-size: 1.1rem; color: #1e293b; margin-bottom: 8px; }
      .result-card h3:hover { color: #6366f1; }
      .result-card p { color: #64748b; font-size: 0.9rem; line-height: 1.6; }
      .result-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 12px; }
      .result-author { display: flex; align-items: center; gap: 8px; }
      .result-stats { color: #94a3b8; font-size: 0.85rem; }

      .no-results {
        text-align: center; padding: 60px 24px;
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
      }
      .no-results h3 { color: #1e293b; margin-bottom: 12px; }
      .no-results p { color: #64748b; margin-bottom: 24px; }

      .suggestions { margin-top: 40px; }
      .suggestions h4 { color: #475569; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 16px; }
      .suggestion-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 24px; }
      .suggestion-tag {
        padding: 8px 16px; border-radius: 20px;
        font-size: 0.85rem; font-weight: 500;
        text-decoration: none; transition: all 0.2s;
      }
      .suggestion-tag:hover { transform: translateY(-1px); }
      .recent-list { list-style: none; }
      .recent-list li { margin-bottom: 8px; }
      .recent-list a { color: #6366f1; text-decoration: none; font-size: 0.9rem; }
      .recent-list a:hover { text-decoration: underline; }

      /* Pagination */
      .search-pagination {
        display: flex; justify-content: center; gap: 8px; margin-top: 32px;
      }
      .search-pagination a, .search-pagination span {
        padding: 10px 16px; border-radius: 8px;
        font-size: 0.9rem; font-weight: 500; text-decoration: none;
      }
      .search-pagination a { background: #fff; border: 1px solid #e2e8f0; color: #475569; }
      .search-pagination a:hover { border-color: #6366f1; color: #6366f1; }
      .search-pagination .current { background: #6366f1; color: white; }
      .search-pagination .disabled { color: #cbd5e1; cursor: not-allowed; }
    </style>
  </head>
  <body>

    <!-- Header -->
    <q:include component="shared/header" />

    <!-- Search Hero -->
    <section class="search-hero">
      <h1>Search the Blog</h1>
      <form class="search-form" method="GET" action="{application.basePath}/search">
        <input type="text" name="q" class="search-input"
               placeholder="Search posts..." value="{searchQuery}" autofocus="autofocus" />
        <button type="submit" class="search-btn">Search</button>
      </form>
    </section>

    <div class="search-results">

      <!-- Has search query -->
      <q:if condition="{searchQuery != ''}">

        <div class="results-header">
          <h2>
            <q:if condition="{searchResults_result.recordCount > 0}">
              Found {totalResults} result{totalResults != 1 ? 's' : ''} for "{searchQuery}"
            </q:if>
            <q:if condition="{searchResults_result.recordCount == 0}">
              No results for "{searchQuery}"
            </q:if>
          </h2>
          <q:if condition="{searchResults_result.recordCount > 0}">
            <p>Showing page {searchPage} of {totalPages}</p>
          </q:if>
        </div>

        <!-- Results -->
        <q:if condition="{searchResults_result.recordCount > 0}">
          <q:loop query="searchResults">
            <div class="result-card">
              <a href="{application.basePath}/post/{searchResults.slug}">
                <div class="result-meta">
                  <span class="post-tag" style="background: {searchResults.tag_color}20; color: {searchResults.tag_color};">
                    {searchResults.tag_name}
                  </span>
                  <span style="color: #94a3b8; font-size: 0.85rem;">{searchResults.published_at}</span>
                </div>
                <h3>{searchResults.title}</h3>
                <p>{searchResults.excerpt}</p>
                <div class="result-footer">
                  <div class="result-author">
                    <div class="author-avatar" style="width: 24px; height: 24px; font-size: 0.7rem;">
                      {searchResults.author_initial}
                    </div>
                    <span style="color: #475569; font-size: 0.85rem;">{searchResults.author_name}</span>
                  </div>
                  <span class="result-stats">{searchResults.reading_time} min read · {searchResults.views} views</span>
                </div>
              </a>
            </div>
          </q:loop>

          <!-- Pagination -->
          <q:if condition="{totalPages > 1}">
            <div class="search-pagination">
              <q:if condition="{searchPage > 1}">
                <a href="{application.basePath}/search?q={encodeURIComponent(searchQuery)}&amp;page={searchPage - 1}">
                  &#8592; Previous
                </a>
              </q:if>
              <q:if condition="{searchPage <= 1}">
                <span class="disabled">&#8592; Previous</span>
              </q:if>

              <span class="current">Page {searchPage}</span>

              <q:if condition="{searchPage < totalPages}">
                <a href="{application.basePath}/search?q={encodeURIComponent(searchQuery)}&amp;page={searchPage + 1}">
                  Next &#8594;
                </a>
              </q:if>
              <q:if condition="{searchPage >= totalPages}">
                <span class="disabled">Next &#8594;</span>
              </q:if>
            </div>
          </q:if>
        </q:if>

        <!-- No Results -->
        <q:if condition="{searchResults_result.recordCount == 0}">
          <div class="no-results">
            <h3>No posts match your search</h3>
            <p>Try searching for different keywords or browse by tag</p>
          </div>
        </q:if>

      </q:if>

      <!-- Empty state (no search yet) -->
      <q:if condition="{searchQuery == ''}">
        <div class="suggestions">
          <h4>Popular Tags</h4>
          <div class="suggestion-tags">
            <q:loop query="popularTags">
              <a href="{application.basePath}/?tag={popularTags.slug}"
                 class="suggestion-tag"
                 style="background: {popularTags.color}20; color: {popularTags.color};">
                {popularTags.name} ({popularTags.post_count})
              </a>
            </q:loop>
          </div>

          <h4>Recent Posts</h4>
          <ul class="recent-list">
            <q:loop query="recentPosts">
              <li><a href="{application.basePath}/post/{recentPosts.slug}">{recentPosts.title}</a></li>
            </q:loop>
          </ul>
        </div>
      </q:if>

    </div>

    <!-- Footer -->
    <q:include component="shared/footer" />

  </body>
  </html>

</q:component>
