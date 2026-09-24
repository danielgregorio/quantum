<!-- What a visitor does on the blog: `quantum test` in projects/blog.
     Each q:test starts from a fresh database built by migrations/ (three
     published posts, three tags, no users). -->

<q:test name="the home lists the published posts" page="/">
  <test:visit />
  <test:expect text="Welcome to Quantum Blog" />
  <test:expect text="Pages are files" />
  <test:expect text="3 Posts" />
  <test:expect text="257 Views" />
</q:test>

<q:test name="filter by tag" page="/">
  <test:visit tag="tutorial" />
  <test:expect text="Posts tagged &quot;tutorial&quot;" />
  <test:expect text="Pages are files" />
  <test:expect no-text="Welcome to Quantum Blog" />
</q:test>

<q:test name="a post and a comment" page="/post/pages-are-files">
  <test:visit />
  <test:expect text="Comments (0)" />
  <test:expect text="88 views" />
  <test:submit action="comment" author_name="Bia" content="Very good!" />
  <test:expect redirect="/post/pages-are-files#comments" flash="Thanks, Bia! Your comment is published." />
  <test:expect table="comments" count="1" where="author_name = 'Bia' AND content = 'Very good!'" />
  <test:expect text="Comments (1)" />
  <test:expect text="Very good!" />
</q:test>

<q:test name="an invalid comment is not saved" page="/post/pages-are-files">
  <test:submit action="comment" author_name="B" content="x" />
  <test:expect error="author_name" />
  <test:expect error="content" />
  <test:expect text="at least 2 characters" />
  <test:expect table="comments" count="0" />
</q:test>

<q:test name="a comment on a post that does not exist" page="/post/no-such-post">
  <test:submit action="comment" author_name="Bia" content="Hi hi" />
  <test:expect redirect="/" flash="That post does not exist." />
  <test:expect table="comments" count="0" />
  <test:visit path="/post/no-such-post" />
  <test:expect text="Post not found" />
</q:test>

<q:test name="search" page="/search">
  <test:visit q="router" />
  <test:expect text="1 result(s) for &quot;router&quot;" />
  <test:expect text="Pages are files" />
  <test:visit />
  <test:expect no-text="result(s)" />
</q:test>

<q:test name="more than ten posts become two pages" page="/">
  <!-- 13 published; test:given fills slug, excerpt and content (NOT NULL) -->
  <test:given table="posts" title="Extra 1" tag_id="3" is_published="1" published_at="2026-08-01" />
  <test:given table="posts" title="Extra 2" tag_id="3" is_published="1" published_at="2026-08-02" />
  <test:given table="posts" title="Extra 3" tag_id="3" is_published="1" published_at="2026-08-03" />
  <test:given table="posts" title="Extra 4" tag_id="3" is_published="1" published_at="2026-08-04" />
  <test:given table="posts" title="Extra 5" tag_id="3" is_published="1" published_at="2026-08-05" />
  <test:given table="posts" title="Extra 6" tag_id="3" is_published="1" published_at="2026-08-06" />
  <test:given table="posts" title="Extra 7" tag_id="3" is_published="1" published_at="2026-08-07" />
  <test:given table="posts" title="Extra 8" tag_id="3" is_published="1" published_at="2026-08-08" />
  <test:given table="posts" title="Extra 9" tag_id="3" is_published="1" published_at="2026-08-09" />
  <test:given table="posts" title="Extra 10" tag_id="3" is_published="1" published_at="2026-08-10" />
  <!-- newest first: the three sample posts (September) and Extra 10..4 on page 1 -->
  <test:visit />
  <test:expect text="13 published" />
  <test:expect text="Extra 4" />
  <test:expect no-text="Extra 3" />
  <test:visit page="2" />
  <test:expect text="Extra 3" />
  <test:expect no-text="Pages are files" />
</q:test>
