-- Quantum Blog - SQLite Schema (Development)
-- Run this migration for local development with SQLite

-- =============================================================================
-- USERS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'author' CHECK (role IN ('admin', 'author', 'reader')),
    display_name TEXT,
    avatar_url TEXT,
    bio TEXT,
    is_active INTEGER DEFAULT 1,
    last_login TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- =============================================================================
-- TAGS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    color TEXT DEFAULT '#6366f1',
    description TEXT,
    post_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- =============================================================================
-- POSTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    excerpt TEXT,
    content TEXT NOT NULL,
    author_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    tag_id INTEGER REFERENCES tags(id) ON DELETE SET NULL,
    featured_image TEXT,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    reading_time INTEGER DEFAULT 1,
    ai_summary TEXT,
    is_published INTEGER DEFAULT 0,
    is_featured INTEGER DEFAULT 0,
    published_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- =============================================================================
-- COMMENTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES comments(id) ON DELETE CASCADE,
    author_name TEXT NOT NULL,
    author_email TEXT,
    content TEXT NOT NULL,
    is_approved INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- =============================================================================
-- POST VIEWS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS post_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    ip_hash TEXT,
    user_agent TEXT,
    referrer TEXT,
    viewed_at TEXT DEFAULT (datetime('now'))
);

-- =============================================================================
-- LOGIN ATTEMPTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    ip_address TEXT,
    user_agent TEXT,
    success INTEGER DEFAULT 0,
    attempted_at TEXT DEFAULT (datetime('now'))
);

-- =============================================================================
-- INDEXES
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(is_published, published_at);
CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author_id);
CREATE INDEX IF NOT EXISTS idx_posts_tag ON posts(tag_id);
CREATE INDEX IF NOT EXISTS idx_posts_slug ON posts(slug);
CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id, is_approved);
CREATE INDEX IF NOT EXISTS idx_post_views_post ON post_views(post_id, viewed_at);
CREATE INDEX IF NOT EXISTS idx_login_attempts ON login_attempts(user_id, attempted_at);

-- =============================================================================
-- SEED DATA
-- =============================================================================

-- Default admin user (password: quantum123 - bcrypt hash)
INSERT OR IGNORE INTO users (username, email, password_hash, role, display_name, bio)
VALUES (
    'admin',
    'admin@quantumblog.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyBAjH.1P7F/Gm',
    'admin',
    'Admin',
    'Blog administrator'
);

-- Default tags
INSERT OR IGNORE INTO tags (name, slug, color, description) VALUES
    ('Announcement', 'announcement', '#22c55e', 'Official announcements and news');
INSERT OR IGNORE INTO tags (name, slug, color, description) VALUES
    ('Technical', 'technical', '#3b82f6', 'Technical deep-dives and tutorials');
INSERT OR IGNORE INTO tags (name, slug, color, description) VALUES
    ('DevOps', 'devops', '#f59e0b', 'Deployment, infrastructure, and operations');
INSERT OR IGNORE INTO tags (name, slug, color, description) VALUES
    ('Tutorial', 'tutorial', '#8b5cf6', 'Step-by-step guides');
INSERT OR IGNORE INTO tags (name, slug, color, description) VALUES
    ('News', 'news', '#ec4899', 'Industry news and updates');

-- Sample posts
INSERT OR IGNORE INTO posts (title, slug, excerpt, content, author_id, tag_id, is_published, published_at, views)
SELECT
    'Welcome to Quantum Blog',
    'welcome-to-quantum-blog',
    'This blog is built entirely with the Quantum Framework - no JavaScript needed! Discover how declarative XML components power a full-stack web application.',
    'Welcome to the Quantum Blog! This entire application was built using the Quantum Framework, a declarative full-stack web framework that lets you create complete web applications without writing a single line of JavaScript.

With Quantum, you write XML-based components that handle everything from routing and state management to database queries and authentication. The framework compiles your declarative code into a fully functional web server.

This blog demonstrates several key features: data binding with curly braces, conditional rendering with q:if, list iteration with q:loop, session management for authentication, and form handling for the admin panel.

Welcome aboard, and happy coding!',
    (SELECT id FROM users WHERE username = 'admin'),
    (SELECT id FROM tags WHERE slug = 'announcement'),
    1,
    '2026-01-28',
    42
WHERE NOT EXISTS (SELECT 1 FROM posts WHERE slug = 'welcome-to-quantum-blog');

INSERT OR IGNORE INTO posts (title, slug, excerpt, content, author_id, tag_id, is_published, published_at, views)
SELECT
    'How Quantum Works Under the Hood',
    'how-quantum-works-under-the-hood',
    'A deep dive into the Quantum Framework architecture - from XML parsing to HTML rendering, see how it all connects.',
    'The Quantum Framework follows a straightforward pipeline: your .q files (XML-based components) are parsed into an Abstract Syntax Tree (AST), which is then executed by the runtime engine to produce HTML output.

The parser reads each XML tag and converts it into typed AST nodes. Tags like q:set create variable assignments, q:loop creates iteration nodes, and q:if creates conditional branches.

The runtime engine walks the AST, evaluating expressions, resolving data bindings, and building the final HTML response. Variables are managed through scoped execution contexts that support page, session, and application-level state.

The web server (built on Flask) maps URL routes to component files and serves the rendered output. It is a simple yet powerful architecture that proves you do not need complex JavaScript frameworks to build dynamic web applications.',
    (SELECT id FROM users WHERE username = 'admin'),
    (SELECT id FROM tags WHERE slug = 'technical'),
    1,
    '2026-01-28',
    128
WHERE NOT EXISTS (SELECT 1 FROM posts WHERE slug = 'how-quantum-works-under-the-hood');

INSERT OR IGNORE INTO posts (title, slug, excerpt, content, author_id, tag_id, is_published, published_at, views)
SELECT
    'Deploy in One Command',
    'deploy-in-one-command',
    'From development to production with a single command. Learn how Quantum makes deployment effortless.',
    'Deploying a Quantum application is designed to be as simple as possible. With the quantum deploy command, your application is packaged and ready for production.

The deploy process bundles your components, configuration, and static assets into a self-contained package. It generates a production-ready WSGI entry point that can be served by any standard Python WSGI server like Gunicorn or uWSGI.

You can also containerize your app with Docker. The framework generates a Dockerfile and docker-compose configuration automatically. Just run quantum deploy --docker and you are ready to push to any container registry.

Whether you prefer traditional hosting, containers, or cloud platforms, Quantum has you covered.',
    (SELECT id FROM users WHERE username = 'admin'),
    (SELECT id FROM tags WHERE slug = 'devops'),
    1,
    '2026-01-27',
    87
WHERE NOT EXISTS (SELECT 1 FROM posts WHERE slug = 'deploy-in-one-command');

-- Update tag post counts
UPDATE tags SET post_count = (
    SELECT COUNT(*) FROM posts WHERE posts.tag_id = tags.id AND posts.is_published = 1
);
