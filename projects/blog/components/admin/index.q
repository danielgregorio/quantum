<q:component name="Admin" require_auth="true" require_role="admin">
  <q:import component="Styles" from="_shared" />
  <q:import component="Header" from="_shared" />
  <q:import component="Footer" from="_shared" />
  <!-- Every post, published or not. require_auth covers the actions too. -->

  <q:action name="togglePublish" method="POST">
    <q:param name="post_id" type="integer" required="true" />
    <q:query name="toggle" datasource="blog-db">
      UPDATE posts
      SET is_published = 1 - is_published,
          published_at = COALESCE(published_at, date('now')),
          updated_at = datetime('now')
      WHERE id = :id
      <q:param name="id" value="{post_id}" type="integer" />
    </q:query>
    <q:redirect url="/admin" flash="Post updated." />
  </q:action>

  <q:action name="deletePost" method="POST">
    <q:param name="post_id" type="integer" required="true" />
    <q:transaction datasource="blog-db">
      <q:query name="deleteComments">
        DELETE FROM comments WHERE post_id = :id
        <q:param name="id" value="{post_id}" type="integer" />
      </q:query>
      <q:query name="deletePost">
        DELETE FROM posts WHERE id = :id
        <q:param name="id" value="{post_id}" type="integer" />
      </q:query>
    </q:transaction>
    <q:redirect url="/admin" flash="Post deleted." />
  </q:action>

  <q:query name="posts" datasource="blog-db">
    SELECT p.id, p.title, p.slug, p.is_published, p.views, p.published_at,
           t.name AS tag_name,
           (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comment_count
    FROM posts p LEFT JOIN tags t ON p.tag_id = t.id
    ORDER BY p.id DESC
  </q:query>

  <html>
  <head>
    <title>Admin - Quantum Blog</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <Styles />
  </head>
  <body>
    <Header />
    <main class="main">
      <div class="section-header">
        <h2 class="section-title">Posts</h2>
        <a href="/admin/new" class="btn-primary">New post</a>
      </div>
      <p>Signed in as {session.userName}.</p>
      <q:if condition="flash">
        <div class="flash flash-{flashType}">{flash}</div>
      </q:if>

      <table class="admin-table">
        <thead>
          <tr><th>Title</th><th>Tag</th><th>Status</th><th>Views</th><th>Comments</th><th></th></tr>
        </thead>
        <tbody>
          <q:loop query="posts">
            <tr>
              <td><a href="/post/{posts.slug}">{posts.title}</a></td>
              <td>{posts.tag_name}</td>
              <td>
                <span class="badge {'badge-on' if posts.is_published else 'badge-off'}">{'Published' if posts.is_published else 'Draft'}</span>
              </td>
              <td>{posts.views}</td>
              <td>{posts.comment_count}</td>
              <td>
                <a href="/admin/edit/{posts.id}">Edit</a>
                <form method="POST" action="/admin">
                  <input type="hidden" name="action" value="togglePublish" />
                  <input type="hidden" name="post_id" value="{posts.id}" />
                  <button type="submit" class="link-button">{'Unpublish' if posts.is_published else 'Publish'}</button>
                </form>
                <form method="POST" action="/admin">
                  <input type="hidden" name="action" value="deletePost" />
                  <input type="hidden" name="post_id" value="{posts.id}" />
                  <button type="submit" class="link-button danger">Delete</button>
                </form>
              </td>
            </tr>
          </q:loop>
        </tbody>
      </table>
    </main>
    <Footer />
  </body>
  </html>
</q:component>
