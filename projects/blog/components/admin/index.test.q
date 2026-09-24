<!-- The author's side of the blog, next to the admin page it tests.
     A *.test.q is never served as a page (ROUTE-4). `test:as` signs in
     without a password; the sign-in form itself is tested in tests/signin.test.q. -->

<q:test name="the admin without a session goes to the login" page="/admin">
  <!-- require_auth covers the actions too: a post without a session changes nothing -->
  <test:submit action="deletePost" post_id="1" />
  <test:expect redirect="/login" />
  <test:expect table="posts" count="3" />
  <test:visit path="/admin" />
  <test:expect redirect="/login" />
</q:test>

<q:test name="an author who is not admin is refused" page="/admin">
  <test:as user="Bob" role="author" id="7" />
  <test:visit />
  <test:expect status="403" />
</q:test>

<q:test name="create, edit, publish and delete a post" page="/admin/new">
  <test:given table="users" id="1" username="ana" display_name="Ana" role="admin" />
  <test:as user="Ana" role="admin" id="1" />
  <test:visit path="/admin" />
  <test:expect text="Signed in as Ana" />

  <test:visit path="/admin/new" />
  <test:submit action="create" title="Héllo, Quântum World" excerpt="A summary long enough"
               tag_id="2" content="a text with more than twenty letters" publish="on" />
  <test:expect redirect="/admin" flash="Post created: Héllo, Quântum World" />
  <test:expect table="posts" count="1"
               where="slug = 'hello-quantum-world' AND is_published = 1 AND author_id = 1 AND reading_time = 1" />
  <test:visit path="/" />
  <test:expect text="Héllo, Quântum World" />

  <test:visit path="/admin/edit/4" />
  <test:submit action="save" title="New title" excerpt="Another summary at all" tag_id="3"
               content="short text but with twenty letters" />
  <test:expect redirect="/admin" flash="Saved: New title" />
  <test:expect table="posts" count="1" where="id = 4 AND title = 'New title' AND tag_id = 3 AND slug = 'hello-quantum-world'" />

  <test:submit action="togglePublish" post_id="4" />
  <test:expect redirect="/admin" flash="Post updated." />
  <test:expect text="Draft" />
  <test:visit path="/" />
  <test:expect no-text="New title" />

  <test:visit path="/admin" />
  <test:submit action="deletePost" post_id="4" />
  <test:expect flash="Post deleted." />
  <test:expect table="posts" count="0" where="id = 4" />
</q:test>

<q:test name="the same title gets another address" page="/admin/new">
  <test:as user="Ana" role="admin" id="1" />
  <test:submit action="create" title="Pages are files" excerpt="A summary long enough" tag_id="1"
               content="a text with more than twenty letters" />
  <test:expect table="posts" count="2" where="title = 'Pages are files'" />
  <test:expect table="posts" count="1" where="title = 'Pages are files' AND slug LIKE 'pages-are-files-%'" />
</q:test>

<q:test name="a post needs a summary of ten letters" page="/admin/new">
  <test:as user="Ana" role="admin" id="1" />
  <test:submit action="create" title="Short" excerpt="tiny" tag_id="1" content="a text with more than twenty letters" />
  <test:expect error="excerpt" />
  <test:expect table="posts" count="3" />
</q:test>
