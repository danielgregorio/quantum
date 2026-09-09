<q:component name="PostCard" type="partial">
  <!--
    Reusable post card component
    Expects: post object with id, slug, title, excerpt, tag_name, tag_color, author_name, published_at, views
  -->

  <a href="{application.basePath}/post/{post.slug}" class="post-card">
    <div class="post-top">
      <span class="post-tag" style="background: {post.tag_color}20; color: {post.tag_color};">{post.tag_name}</span>
      <span class="post-date">{post.published_at}</span>
    </div>
    <h2>{post.title}</h2>
    <p>{post.excerpt}</p>
    <div class="post-footer">
      <div class="post-author">
        <div class="author-avatar">{post.author_initial}</div>
        <span class="author-name">{post.author_name}</span>
      </div>
      <div class="post-meta-right">
        <span class="post-views">{post.views} views</span>
        <span class="read-more">Read more &#8594;</span>
      </div>
    </div>
  </a>

</q:component>
