<q:component name="EditPost" require_auth="true" require_role="admin">
  <q:import component="Styles" from="_shared" />
  <q:import component="Header" from="_shared" />
  <q:import component="Footer" from="_shared" />
  <!-- /admin/edit/<id>. The URL (slug) of a post does not change when it is edited. -->

  <q:action name="save" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="excerpt" required="true" minlength="10" maxlength="500" />
    <q:param name="content" required="true" minlength="20" />
    <q:param name="tag_id" type="integer" required="true" />

    <!-- `id` comes from the URL (ROUTE-2), not from the form. -->
    <q:query name="updatePost" datasource="blog-db">
      UPDATE posts
      SET title = :title, excerpt = :excerpt, content = :content, tag_id = :tag,
          reading_time = :minutes, updated_at = datetime('now')
      WHERE id = :id
      <q:param name="title" value="{title}" type="string" />
      <q:param name="excerpt" value="{excerpt}" type="string" />
      <q:param name="content" value="{content}" type="string" />
      <q:param name="tag" value="{tag_id}" type="integer" />
      <q:param name="minutes" value="{max(1, ceil(len(split(content, ' ')) / 200))}" type="integer" />
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:if condition="updatePost_result.affectedRows == 0">
      <q:redirect url="/admin" flash="That post does not exist." flashType="error" />
    </q:if>
    <q:redirect url="/admin" flash="Saved: {title}" />
  </q:action>

  <q:query name="post" datasource="blog-db">
    SELECT id, title, excerpt, content, tag_id FROM posts WHERE id = :id
    <q:param name="id" value="{id}" type="integer" />
  </q:query>
  <q:query name="tags" datasource="blog-db">SELECT id, name FROM tags ORDER BY name</q:query>

  <html>
  <head>
    <title>Edit post - Quantum Blog</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <Styles />
  </head>
  <body>
    <Header />
    <main class="main">
      <div class="panel">
        <q:if condition="post_result.recordCount == 1">
          <h2>Edit post</h2>
          <q:if condition="flash">
            <div class="flash flash-{flashType}">{flash}</div>
          </q:if>
          <form method="POST" action="/admin/edit/{post.id}">
            <input type="hidden" name="action" value="save" />
            <label>Title</label>
            <input type="text" name="title" value="{post.title}" required="required" />
            <label>Excerpt</label>
            <input type="text" name="excerpt" value="{post.excerpt}" required="required" />
            <label>Tag</label>
            <select name="tag_id">
              <q:loop query="tags">
                <q:if condition="tags.id == post.tag_id">
                  <option value="{tags.id}" selected="selected">{tags.name}</option>
                </q:if>
                <q:else>
                  <option value="{tags.id}">{tags.name}</option>
                </q:else>
              </q:loop>
            </select>
            <label>Text</label>
            <textarea name="content" required="required">{post.content}</textarea>
            <button type="submit" class="btn-primary">Save</button>
            <a href="/admin">Cancel</a>
          </form>
        </q:if>
        <q:else>
          <h2>Post not found</h2>
          <a href="/admin">Back to the admin</a>
        </q:else>
      </div>
    </main>
    <Footer />
  </body>
  </html>
</q:component>
