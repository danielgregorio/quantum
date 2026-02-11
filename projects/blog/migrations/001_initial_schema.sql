-- Quantum Blog - Initial Database Schema
-- Run this migration to set up the blog database

-- =============================================================================
-- USERS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'author' CHECK (role IN ('admin', 'author', 'reader')),
    display_name VARCHAR(100),
    avatar_url VARCHAR(512),
    bio TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- TAGS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    color VARCHAR(7) DEFAULT '#6366f1',
    description TEXT,
    post_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- POSTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    excerpt TEXT,
    content TEXT NOT NULL,
    author_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    tag_id INTEGER REFERENCES tags(id) ON DELETE SET NULL,

    -- Metadata
    featured_image VARCHAR(512),
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    reading_time INTEGER DEFAULT 1,  -- minutes

    -- AI-generated fields
    ai_summary TEXT,
    ai_keywords TEXT[],

    -- Status
    is_published BOOLEAN DEFAULT FALSE,
    is_featured BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- COMMENTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES comments(id) ON DELETE CASCADE,  -- For replies
    author_name VARCHAR(100) NOT NULL,
    author_email VARCHAR(255),
    content TEXT NOT NULL,
    is_approved BOOLEAN DEFAULT FALSE,
    likes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- POST VIEWS TABLE (for analytics)
-- =============================================================================
CREATE TABLE IF NOT EXISTS post_views (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    ip_hash VARCHAR(64),  -- Hashed IP for privacy
    user_agent VARCHAR(255),
    referrer VARCHAR(512),
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- RELATED POSTS TABLE (AI-generated relationships)
-- =============================================================================
CREATE TABLE IF NOT EXISTS related_posts (
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    related_post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    similarity_score FLOAT,
    PRIMARY KEY (post_id, related_post_id)
);

-- =============================================================================
-- LOGIN ATTEMPTS TABLE (security tracking)
-- =============================================================================
CREATE TABLE IF NOT EXISTS login_attempts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    ip_address VARCHAR(45),  -- IPv4 or IPv6
    user_agent VARCHAR(255),
    success BOOLEAN DEFAULT FALSE,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INDEXES
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(is_published, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author_id);
CREATE INDEX IF NOT EXISTS idx_posts_tag ON posts(tag_id);
CREATE INDEX IF NOT EXISTS idx_posts_slug ON posts(slug);
CREATE INDEX IF NOT EXISTS idx_posts_featured ON posts(is_featured, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id, is_approved);
CREATE INDEX IF NOT EXISTS idx_post_views_post ON post_views(post_id, viewed_at);
CREATE INDEX IF NOT EXISTS idx_login_attempts ON login_attempts(user_id, attempted_at DESC);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_posts_search ON posts USING gin(to_tsvector('english', title || ' ' || COALESCE(excerpt, '') || ' ' || content));

-- =============================================================================
-- SEED DATA
-- =============================================================================

-- Default admin user (password: quantum123)
INSERT INTO users (username, email, password_hash, role, display_name, bio)
VALUES (
    'admin',
    'admin@quantumblog.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyBAjH.1P7F/Gm',
    'admin',
    'Admin',
    'Blog administrator'
) ON CONFLICT (username) DO NOTHING;

-- Default tags
INSERT INTO tags (name, slug, color, description) VALUES
    ('Announcement', 'announcement', '#22c55e', 'Official announcements and news'),
    ('Technical', 'technical', '#3b82f6', 'Technical deep-dives and tutorials'),
    ('DevOps', 'devops', '#f59e0b', 'Deployment, infrastructure, and operations'),
    ('Tutorial', 'tutorial', '#8b5cf6', 'Step-by-step guides'),
    ('News', 'news', '#ec4899', 'Industry news and updates')
ON CONFLICT (slug) DO NOTHING;

-- Migrate existing posts
INSERT INTO posts (title, slug, excerpt, content, author_id, tag_id, is_published, published_at, views)
SELECT
    'Welcome to Quantum Blog',
    'welcome-to-quantum-blog',
    'This blog is built entirely with the Quantum Framework - no JavaScript needed! Discover how declarative XML components power a full-stack web application.',
    E'Welcome to the Quantum Blog! This entire application was built using the Quantum Framework, a declarative full-stack web framework that lets you create complete web applications without writing a single line of JavaScript.\n\nWith Quantum, you write XML-based components that handle everything from routing and state management to database queries and authentication. The framework compiles your declarative code into a fully functional web server.\n\nThis blog demonstrates several key features: data binding with curly braces, conditional rendering with q:if, list iteration with q:loop, session management for authentication, and form handling for the admin panel.\n\nWelcome aboard, and happy coding!',
    (SELECT id FROM users WHERE username = 'admin'),
    (SELECT id FROM tags WHERE slug = 'announcement'),
    TRUE,
    '2026-01-28',
    42
WHERE NOT EXISTS (SELECT 1 FROM posts WHERE slug = 'welcome-to-quantum-blog');

INSERT INTO posts (title, slug, excerpt, content, author_id, tag_id, is_published, published_at, views)
SELECT
    'How Quantum Works Under the Hood',
    'how-quantum-works-under-the-hood',
    'A deep dive into the Quantum Framework architecture - from XML parsing to HTML rendering, see how it all connects.',
    E'The Quantum Framework follows a straightforward pipeline: your .q files (XML-based components) are parsed into an Abstract Syntax Tree (AST), which is then executed by the runtime engine to produce HTML output.\n\nThe parser reads each XML tag and converts it into typed AST nodes. Tags like q:set create variable assignments, q:loop creates iteration nodes, and q:if creates conditional branches.\n\nThe runtime engine walks the AST, evaluating expressions, resolving data bindings, and building the final HTML response. Variables are managed through scoped execution contexts that support page, session, and application-level state.\n\nThe web server (built on Flask) maps URL routes to component files and serves the rendered output. It is a simple yet powerful architecture that proves you do not need complex JavaScript frameworks to build dynamic web applications.',
    (SELECT id FROM users WHERE username = 'admin'),
    (SELECT id FROM tags WHERE slug = 'technical'),
    TRUE,
    '2026-01-28',
    128
WHERE NOT EXISTS (SELECT 1 FROM posts WHERE slug = 'how-quantum-works-under-the-hood');

INSERT INTO posts (title, slug, excerpt, content, author_id, tag_id, is_published, published_at, views)
SELECT
    'Deploy in One Command',
    'deploy-in-one-command',
    'From development to production with a single command. Learn how Quantum makes deployment effortless.',
    E'Deploying a Quantum application is designed to be as simple as possible. With the quantum deploy command, your application is packaged and ready for production.\n\nThe deploy process bundles your components, configuration, and static assets into a self-contained package. It generates a production-ready WSGI entry point that can be served by any standard Python WSGI server like Gunicorn or uWSGI.\n\nYou can also containerize your app with Docker. The framework generates a Dockerfile and docker-compose configuration automatically. Just run quantum deploy --docker and you are ready to push to any container registry.\n\nWhether you prefer traditional hosting, containers, or cloud platforms, Quantum has you covered.',
    (SELECT id FROM users WHERE username = 'admin'),
    (SELECT id FROM tags WHERE slug = 'devops'),
    TRUE,
    '2026-01-27',
    87
WHERE NOT EXISTS (SELECT 1 FROM posts WHERE slug = 'deploy-in-one-command');

-- Update post counts for tags
UPDATE tags SET post_count = (
    SELECT COUNT(*) FROM posts WHERE posts.tag_id = tags.id AND posts.is_published = TRUE
);

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_posts_updated_at ON posts;
CREATE TRIGGER update_posts_updated_at
    BEFORE UPDATE ON posts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to increment post view count
CREATE OR REPLACE FUNCTION increment_post_views(p_post_id INTEGER, p_ip_hash VARCHAR)
RETURNS VOID AS $$
BEGIN
    -- Check if already viewed recently (within 1 hour)
    IF NOT EXISTS (
        SELECT 1 FROM post_views
        WHERE post_id = p_post_id
        AND ip_hash = p_ip_hash
        AND viewed_at > CURRENT_TIMESTAMP - INTERVAL '1 hour'
    ) THEN
        -- Insert view record
        INSERT INTO post_views (post_id, ip_hash) VALUES (p_post_id, p_ip_hash);
        -- Increment counter
        UPDATE posts SET views = views + 1 WHERE id = p_post_id;
    END IF;
END;
$$ LANGUAGE plpgsql;
