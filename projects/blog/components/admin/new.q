<q:component name="NewPost" require_auth="true" require_role="admin">
  <q:import component="Styles" from="_shared" />
  <q:import component="Header" from="_shared" />
  <q:import component="Footer" from="_shared" />

  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="excerpt" required="true" minlength="10" maxlength="500" />
    <q:param name="content" required="true" minlength="20" />
    <q:param name="tag_id" type="integer" required="true" />
    <!-- An unchecked checkbox is not sent at all. -->
    <q:param name="publish" default="off" />

    <!-- The URL comes from the title; a repeated title gets a suffix. -->
    <q:set name="slug" value="{slugify(title)}" />
    <q:query name="taken" datasource="blog-db">
      SELECT COUNT(*) AS n FROM posts WHERE slug = :slug
      <q:param name="slug" value="{slug}" type="string" />
    </q:query>
    <q:if condition="taken.n > 0">
      <q:set name="slug" value="{slug}-{dateFormat(now(), '%Y%m%d%H%M%S')}" />
    </q:if>

    <q:query name="insertPost" datasource="blog-db">
      INSERT INTO posts (title, slug, excerpt, content, tag_id, author_id, reading_time, is_published, published_at)
      VALUES (:title, :slug, :excerpt, :content, :tag, :author, :minutes, :published,
              CASE WHEN :published = 1 THEN date('now') END)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="slug" value="{slug}" type="string" />
      <q:param name="excerpt" value="{excerpt}" type="string" />
      <q:param name="content" value="{content}" type="string" />
      <q:param name="tag" value="{tag_id}" type="integer" />
      <q:param name="author" value="{session.userId}" type="integer" />
      <q:param name="minutes" value="{max(1, ceil(len(split(content, ' ')) / 200))}" type="integer" />
      <q:param name="published" value="{1 if publish == 'on' else 0}" type="integer" />
    </q:query>
    <q:redirect url="/admin" flash="Post created: {title}" />
  </q:action>

  <q:query name="tags" datasource="blog-db">SELECT id, name FROM tags ORDER BY name</q:query>

  <html>
  <head>
    <title>New post - Quantum Blog</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <Styles />
  </head>
  <body>
    <Header />
    <main class="main">
      <div class="panel">
        <h2>New post</h2>
        <q:if condition="flash">
          <div class="flash flash-{flashType}">{flash}</div>
        </q:if>
        <form method="POST" action="/admin/new">
          <input type="hidden" name="action" value="create" />
          <label>Title</label>
          <input type="text" name="title" required="required" />
          <label>Excerpt</label>
          <input type="text" name="excerpt" required="required" />
          <label>Tag</label>
          <select name="tag_id">
            <q:loop query="tags">
              <option value="{tags.id}">{tags.name}</option>
            </q:loop>
          </select>
          <label>Text</label>
          <textarea name="content" required="required"></textarea>
          <label><input type="checkbox" name="publish" style="width: auto;" /> Publish now</label>
          <button type="submit" class="btn-primary">Create</button>
          <a href="/admin">Cancel</a>
        </form>
      </div>
    </main>
    <Footer />
  </body>
  </html>
</q:component>
