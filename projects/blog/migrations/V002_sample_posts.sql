-- Quantum Blog - tags and sample posts. No user: the first visit to /login
-- creates the admin account.

INSERT INTO tags (name, slug, color) VALUES
    ('Announcement', 'announcement', '#22c55e'),
    ('Technical', 'technical', '#3b82f6'),
    ('Tutorial', 'tutorial', '#8b5cf6');

INSERT INTO posts (title, slug, excerpt, content, tag_id, is_published, published_at, views, reading_time) VALUES (
    'Welcome to Quantum Blog',
    'welcome-to-quantum-blog',
    'This blog is written in Quantum: pages are .q files, the database is SQLite, and there is no JavaScript.',
    'Welcome! Every page of this blog is a .q file in components/: the home page, this post, the search and the admin.

A page reads the database with q:query, repeats markup with q:loop and decides with q:if. A form posts to a q:action, which validates its fields with q:param and writes with another q:query.

The admin pages are protected with require_auth on the component, which covers their actions too.',
    (SELECT id FROM tags WHERE slug = 'announcement'), 1, '2026-09-01', 42, 1);

INSERT INTO posts (title, slug, excerpt, content, tag_id, is_published, published_at, views, reading_time) VALUES (
    'How a Quantum page runs',
    'how-a-quantum-page-runs',
    'Statements run first, then the markup is rendered. Knowing that order explains most of the language.',
    'A .q file is parsed into a tree. When a request arrives, the statements at the top of the component run in order: q:set, q:query, q:if around them. Then the markup is rendered with the values they produced.

That is why a statement inside an HTML element is a parse error: it would never run. And it is why a q:action does not see the variables the page sets: the action runs instead of the page, and queries what it needs itself.',
    (SELECT id FROM tags WHERE slug = 'technical'), 1, '2026-09-05', 128, 1);

INSERT INTO posts (title, slug, excerpt, content, tag_id, is_published, published_at, views, reading_time) VALUES (
    'Pages are files',
    'pages-are-files',
    'components/about.q is /about, and components/post/[slug].q is every post. That is the whole router.',
    'Quantum serves each file under components/ at the URL of its path. A segment in brackets matches any value and hands it to the page: this post is components/post/[slug].q, and slug is pages-are-files.

Files and folders whose name starts with an underscore are not served. They exist to be imported, like the header and footer of this blog in components/_shared.',
    (SELECT id FROM tags WHERE slug = 'tutorial'), 1, '2026-09-10', 87, 1);
