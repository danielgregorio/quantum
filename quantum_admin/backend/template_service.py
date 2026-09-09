"""
Template Service for Quantum Admin
Provides project scaffolding from templates
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import yaml
import json

logger = logging.getLogger(__name__)


@dataclass
class TemplateInfo:
    """Information about a project template"""
    id: str
    name: str
    description: str
    icon: str = "&#128193;"  # folder icon
    category: str = "general"
    features: List[str] = field(default_factory=list)
    options: List[Dict[str, Any]] = field(default_factory=list)
    files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "category": self.category,
            "features": self.features,
            "options": self.options,
            "files": self.files
        }


# Built-in templates
TEMPLATES = {
    "blank": TemplateInfo(
        id="blank",
        name="Blank Project",
        description="Empty project with minimal configuration",
        icon="&#128196;",
        category="starter",
        features=["Minimal setup", "Ready for customization"],
        options=[]
    ),
    "blog": TemplateInfo(
        id="blog",
        name="Blog",
        description="Full-featured blog with posts, comments, and admin",
        icon="&#128221;",
        category="content",
        features=["Posts management", "Comments", "Categories/Tags", "User authentication", "Admin panel"],
        options=[
            {"name": "include_auth", "label": "Include Authentication", "type": "boolean", "default": True},
            {"name": "include_comments", "label": "Enable Comments", "type": "boolean", "default": True},
            {"name": "sample_data", "label": "Include Sample Posts", "type": "boolean", "default": True}
        ]
    ),
    "api": TemplateInfo(
        id="api",
        name="REST API",
        description="RESTful API with CRUD operations and authentication",
        icon="&#128268;",
        category="backend",
        features=["RESTful endpoints", "JWT authentication", "Database integration", "Swagger docs"],
        options=[
            {"name": "include_auth", "label": "Include Authentication", "type": "boolean", "default": True},
            {"name": "include_swagger", "label": "Generate Swagger Docs", "type": "boolean", "default": True},
            {"name": "database", "label": "Database Type", "type": "select", "default": "postgres",
             "choices": ["postgres", "mysql", "sqlite"]}
        ]
    ),
    "dashboard": TemplateInfo(
        id="dashboard",
        name="Dashboard",
        description="Admin dashboard with charts, tables, and data visualization",
        icon="&#128202;",
        category="admin",
        features=["Charts & Graphs", "Data tables", "Real-time updates", "User management"],
        options=[
            {"name": "include_auth", "label": "Include Authentication", "type": "boolean", "default": True},
            {"name": "include_charts", "label": "Include Chart Components", "type": "boolean", "default": True},
            {"name": "sample_data", "label": "Include Sample Data", "type": "boolean", "default": True}
        ]
    ),
    "landing": TemplateInfo(
        id="landing",
        name="Landing Page",
        description="Marketing landing page with sections and contact form",
        icon="&#127968;",
        category="marketing",
        features=["Hero section", "Features grid", "Testimonials", "Contact form", "Responsive design"],
        options=[
            {"name": "include_contact", "label": "Include Contact Form", "type": "boolean", "default": True},
            {"name": "include_newsletter", "label": "Include Newsletter Signup", "type": "boolean", "default": False}
        ]
    )
}


class TemplateService:
    """Service for managing and scaffolding project templates"""

    def __init__(self, templates_dir: Path = None):
        if templates_dir:
            self.templates_dir = templates_dir
        else:
            # Default to quantum_admin/templates
            self.templates_dir = Path(__file__).parent.parent / "templates"

    def list_templates(self) -> List[TemplateInfo]:
        """List all available templates"""
        templates = list(TEMPLATES.values())

        # Also check for custom templates in templates directory
        if self.templates_dir.exists():
            for template_dir in self.templates_dir.iterdir():
                if template_dir.is_dir() and template_dir.name not in TEMPLATES:
                    manifest_path = template_dir / "template.yaml"
                    if manifest_path.exists():
                        try:
                            with open(manifest_path) as f:
                                manifest = yaml.safe_load(f)
                            templates.append(TemplateInfo(
                                id=template_dir.name,
                                name=manifest.get("name", template_dir.name),
                                description=manifest.get("description", ""),
                                icon=manifest.get("icon", "&#128193;"),
                                category=manifest.get("category", "custom"),
                                features=manifest.get("features", []),
                                options=manifest.get("options", [])
                            ))
                        except Exception as e:
                            logger.warning(f"Failed to load template manifest {manifest_path}: {e}")

        return templates

    def get_template(self, template_id: str) -> Optional[TemplateInfo]:
        """Get a specific template by ID"""
        if template_id in TEMPLATES:
            return TEMPLATES[template_id]

        # Check custom templates
        template_dir = self.templates_dir / template_id
        if template_dir.exists():
            manifest_path = template_dir / "template.yaml"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    manifest = yaml.safe_load(f)
                return TemplateInfo(
                    id=template_id,
                    name=manifest.get("name", template_id),
                    description=manifest.get("description", ""),
                    icon=manifest.get("icon", "&#128193;"),
                    category=manifest.get("category", "custom"),
                    features=manifest.get("features", []),
                    options=manifest.get("options", [])
                )

        return None

    def scaffold_project(
        self,
        template_id: str,
        project_name: str,
        target_dir: Path,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create a new project from a template.

        Args:
            template_id: ID of the template to use
            project_name: Name of the new project
            target_dir: Directory where the project will be created
            options: Template-specific options

        Returns:
            Dict with created files and status
        """
        options = options or {}
        template = self.get_template(template_id)

        if not template:
            raise ValueError(f"Template not found: {template_id}")

        project_dir = target_dir / project_name
        if project_dir.exists():
            raise ValueError(f"Project directory already exists: {project_dir}")

        project_dir.mkdir(parents=True)
        created_files = []

        try:
            # Create base structure
            (project_dir / "components").mkdir()
            (project_dir / "migrations").mkdir(exist_ok=True)

            # Create quantum.config.yaml
            config = self._generate_config(template_id, project_name, options)
            config_path = project_dir / "quantum.config.yaml"
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            created_files.append("quantum.config.yaml")

            # Generate template-specific files
            if template_id == "blank":
                created_files.extend(self._scaffold_blank(project_dir, project_name, options))
            elif template_id == "blog":
                created_files.extend(self._scaffold_blog(project_dir, project_name, options))
            elif template_id == "api":
                created_files.extend(self._scaffold_api(project_dir, project_name, options))
            elif template_id == "dashboard":
                created_files.extend(self._scaffold_dashboard(project_dir, project_name, options))
            elif template_id == "landing":
                created_files.extend(self._scaffold_landing(project_dir, project_name, options))
            else:
                # Copy from custom template directory
                template_src = self.templates_dir / template_id
                if template_src.exists():
                    created_files.extend(self._copy_template_files(template_src, project_dir, project_name, options))

            return {
                "success": True,
                "project_dir": str(project_dir),
                "files_created": created_files,
                "message": f"Project '{project_name}' created successfully"
            }

        except Exception as e:
            # Cleanup on failure
            if project_dir.exists():
                shutil.rmtree(project_dir)
            raise

    def _generate_config(self, template_id: str, project_name: str, options: Dict[str, Any]) -> Dict:
        """Generate quantum.config.yaml content"""
        config = {
            "name": project_name,
            "version": "1.0.0",
            "template": template_id,
            "created_at": datetime.utcnow().isoformat(),
            "server": {
                "port": 8080,
                "host": "0.0.0.0"
            }
        }

        # Add database config if needed
        if options.get("database") or template_id in ("blog", "api", "dashboard"):
            db_type = options.get("database", "sqlite")
            config["database"] = {
                "type": db_type,
                "name": project_name if db_type == "sqlite" else f"{project_name}_db"
            }

        # Add auth config if needed
        if options.get("include_auth", True) and template_id != "landing":
            config["auth"] = {
                "enabled": True,
                "type": "session",
                "session_timeout": 3600
            }

        return config

    def _scaffold_blank(self, project_dir: Path, name: str, options: Dict) -> List[str]:
        """Scaffold a blank project"""
        files = []

        # Create index.q
        index_content = f'''<q:component name="index">
    <q:head>
        <title>{name}</title>
    </q:head>

    <q:body>
        <div class="container">
            <h1>Welcome to {name}</h1>
            <p>Your Quantum project is ready!</p>
        </div>
    </q:body>
</q:component>
'''
        with open(project_dir / "components" / "index.q", 'w') as f:
            f.write(index_content)
        files.append("components/index.q")

        return files

    def _scaffold_blog(self, project_dir: Path, name: str, options: Dict) -> List[str]:
        """Scaffold a blog project"""
        files = []
        include_auth = options.get("include_auth", True)
        include_comments = options.get("include_comments", True)

        # Index page
        index_content = f'''<q:component name="index">
    <q:head>
        <title>{name} - Blog</title>
        <link rel="stylesheet" href="/static/blog.css" />
    </q:head>

    <q:query name="posts" datasource="default">
        SELECT id, title, slug, excerpt, created_at, author
        FROM posts
        WHERE published = true
        ORDER BY created_at DESC
        LIMIT 10
    </q:query>

    <q:body>
        <header class="blog-header">
            <h1>{name}</h1>
            <nav>
                <a href="/">Home</a>
                <a href="/about">About</a>
                {"<a href='/admin'>Admin</a>" if include_auth else ""}
            </nav>
        </header>

        <main class="blog-posts">
            <q:loop items="{{posts}}" item="post">
                <article class="post-card">
                    <h2><a href="/post/{{post.slug}}">{{post.title}}</a></h2>
                    <p class="post-meta">By {{post.author}} on {{post.created_at}}</p>
                    <p>{{post.excerpt}}</p>
                    <a href="/post/{{post.slug}}" class="read-more">Read more</a>
                </article>
            </q:loop>
        </main>
    </q:body>
</q:component>
'''
        with open(project_dir / "components" / "index.q", 'w') as f:
            f.write(index_content)
        files.append("components/index.q")

        # Post detail page
        post_content = f'''<q:component name="post">
    <q:set name="slug" value="{{url.params.slug}}" />

    <q:query name="post" datasource="default">
        SELECT id, title, content, created_at, author
        FROM posts
        WHERE slug = :slug AND published = true
    </q:query>

    {"<q:query name='comments' datasource='default'>SELECT * FROM comments WHERE post_id = :post.id ORDER BY created_at</q:query>" if include_comments else ""}

    <q:head>
        <title>{{post.title}} - {name}</title>
    </q:head>

    <q:body>
        <article class="post-full">
            <h1>{{post.title}}</h1>
            <p class="post-meta">By {{post.author}} on {{post.created_at}}</p>
            <div class="post-content">
                {{post.content}}
            </div>
        </article>

        {"<section class='comments'><h3>Comments</h3><q:loop items='{comments}' item='comment'><div class='comment'><p>{comment.content}</p><small>By {comment.author}</small></div></q:loop></section>" if include_comments else ""}

        <a href="/" class="back-link">Back to posts</a>
    </q:body>
</q:component>
'''
        with open(project_dir / "components" / "post.q", 'w') as f:
            f.write(post_content)
        files.append("components/post.q")

        # Migration for posts table
        migration_content = '''-- Migration: Create posts table
-- Version: V001

CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    excerpt TEXT,
    content TEXT,
    author VARCHAR(100),
    published BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_posts_slug ON posts(slug);
CREATE INDEX idx_posts_published ON posts(published);
'''
        with open(project_dir / "migrations" / "V001_create_posts.sql", 'w') as f:
            f.write(migration_content)
        files.append("migrations/V001_create_posts.sql")

        if include_comments:
            comments_migration = '''-- Migration: Create comments table
-- Version: V002

CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    author VARCHAR(100),
    email VARCHAR(255),
    content TEXT NOT NULL,
    approved BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_comments_post ON comments(post_id);
'''
            with open(project_dir / "migrations" / "V002_create_comments.sql", 'w') as f:
                f.write(comments_migration)
            files.append("migrations/V002_create_comments.sql")

        return files

    def _scaffold_api(self, project_dir: Path, name: str, options: Dict) -> List[str]:
        """Scaffold a REST API project"""
        files = []
        include_auth = options.get("include_auth", True)

        # API index with endpoints listing
        index_content = f'''<q:component name="api-index">
    <q:head>
        <title>{name} API</title>
    </q:head>

    <q:body>
        <h1>{name} API</h1>
        <p>Welcome to the {name} REST API</p>

        <h2>Available Endpoints</h2>
        <ul>
            <li>GET /api/items - List all items</li>
            <li>GET /api/items/:id - Get item by ID</li>
            <li>POST /api/items - Create new item</li>
            <li>PUT /api/items/:id - Update item</li>
            <li>DELETE /api/items/:id - Delete item</li>
            {"<li>POST /api/auth/login - Authenticate user</li>" if include_auth else ""}
        </ul>
    </q:body>
</q:component>
'''
        with open(project_dir / "components" / "index.q", 'w') as f:
            f.write(index_content)
        files.append("components/index.q")

        # Items API component
        items_content = '''<q:component name="items-api">
    <!-- List items -->
    <q:function name="list" method="GET" path="/api/items">
        <q:query name="items" datasource="default">
            SELECT * FROM items ORDER BY created_at DESC
        </q:query>
        <q:return format="json">{{items}}</q:return>
    </q:function>

    <!-- Get single item -->
    <q:function name="get" method="GET" path="/api/items/:id">
        <q:query name="item" datasource="default">
            SELECT * FROM items WHERE id = :id
        </q:query>
        <q:if condition="{{!item}}">
            <q:return format="json" status="404">{"error": "Item not found"}</q:return>
        </q:if>
        <q:return format="json">{{item}}</q:return>
    </q:function>

    <!-- Create item -->
    <q:function name="create" method="POST" path="/api/items">
        <q:query name="result" datasource="default">
            INSERT INTO items (name, description)
            VALUES (:body.name, :body.description)
            RETURNING *
        </q:query>
        <q:return format="json" status="201">{{result}}</q:return>
    </q:function>

    <!-- Update item -->
    <q:function name="update" method="PUT" path="/api/items/:id">
        <q:query name="result" datasource="default">
            UPDATE items
            SET name = :body.name, description = :body.description, updated_at = NOW()
            WHERE id = :id
            RETURNING *
        </q:query>
        <q:return format="json">{{result}}</q:return>
    </q:function>

    <!-- Delete item -->
    <q:function name="delete" method="DELETE" path="/api/items/:id">
        <q:query datasource="default">
            DELETE FROM items WHERE id = :id
        </q:query>
        <q:return format="json">{"message": "Item deleted"}</q:return>
    </q:function>
</q:component>
'''
        with open(project_dir / "components" / "items.q", 'w') as f:
            f.write(items_content)
        files.append("components/items.q")

        # Items migration
        migration_content = '''-- Migration: Create items table
-- Version: V001

CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''
        with open(project_dir / "migrations" / "V001_create_items.sql", 'w') as f:
            f.write(migration_content)
        files.append("migrations/V001_create_items.sql")

        return files

    def _scaffold_dashboard(self, project_dir: Path, name: str, options: Dict) -> List[str]:
        """Scaffold a dashboard project"""
        files = []

        # Dashboard index
        index_content = f'''<q:component name="dashboard">
    <q:head>
        <title>{name} - Dashboard</title>
        <link rel="stylesheet" href="/static/dashboard.css" />
    </q:head>

    <q:query name="stats" datasource="default">
        SELECT
            (SELECT COUNT(*) FROM users) as total_users,
            (SELECT COUNT(*) FROM orders) as total_orders,
            (SELECT SUM(amount) FROM orders) as total_revenue
    </q:query>

    <q:body>
        <div class="dashboard-container">
            <header class="dashboard-header">
                <h1>{name}</h1>
                <nav class="dashboard-nav">
                    <a href="/dashboard">Overview</a>
                    <a href="/dashboard/users">Users</a>
                    <a href="/dashboard/orders">Orders</a>
                    <a href="/dashboard/settings">Settings</a>
                </nav>
            </header>

            <main class="dashboard-main">
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Total Users</h3>
                        <p class="stat-value">{{stats.total_users}}</p>
                    </div>
                    <div class="stat-card">
                        <h3>Total Orders</h3>
                        <p class="stat-value">{{stats.total_orders}}</p>
                    </div>
                    <div class="stat-card">
                        <h3>Revenue</h3>
                        <p class="stat-value">${{stats.total_revenue}}</p>
                    </div>
                </div>

                <section class="recent-activity">
                    <h2>Recent Activity</h2>
                    <q:query name="recent" datasource="default">
                        SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 10
                    </q:query>
                    <table class="data-table">
                        <thead>
                            <tr><th>Action</th><th>User</th><th>Time</th></tr>
                        </thead>
                        <tbody>
                            <q:loop items="{{recent}}" item="log">
                                <tr>
                                    <td>{{log.action}}</td>
                                    <td>{{log.user_name}}</td>
                                    <td>{{log.created_at}}</td>
                                </tr>
                            </q:loop>
                        </tbody>
                    </table>
                </section>
            </main>
        </div>
    </q:body>
</q:component>
'''
        with open(project_dir / "components" / "index.q", 'w') as f:
            f.write(index_content)
        files.append("components/index.q")

        return files

    def _scaffold_landing(self, project_dir: Path, name: str, options: Dict) -> List[str]:
        """Scaffold a landing page project"""
        files = []
        include_contact = options.get("include_contact", True)

        # Landing page
        landing_content = f'''<q:component name="landing">
    <q:head>
        <title>{name}</title>
        <link rel="stylesheet" href="/static/landing.css" />
    </q:head>

    <q:body>
        <!-- Hero Section -->
        <section class="hero">
            <div class="hero-content">
                <h1>{name}</h1>
                <p class="hero-subtitle">Your amazing product description goes here</p>
                <a href="#features" class="cta-button">Get Started</a>
            </div>
        </section>

        <!-- Features Section -->
        <section id="features" class="features">
            <h2>Features</h2>
            <div class="features-grid">
                <div class="feature-card">
                    <h3>Feature One</h3>
                    <p>Description of your first amazing feature</p>
                </div>
                <div class="feature-card">
                    <h3>Feature Two</h3>
                    <p>Description of your second amazing feature</p>
                </div>
                <div class="feature-card">
                    <h3>Feature Three</h3>
                    <p>Description of your third amazing feature</p>
                </div>
            </div>
        </section>

        <!-- Testimonials -->
        <section class="testimonials">
            <h2>What People Say</h2>
            <div class="testimonials-grid">
                <blockquote>
                    <p>"This product changed my life!"</p>
                    <cite>- Happy Customer</cite>
                </blockquote>
            </div>
        </section>

        {"<!-- Contact Form --><section id='contact' class='contact'><h2>Contact Us</h2><form class='contact-form' action='/api/contact' method='POST'><input type='text' name='name' placeholder='Your Name' required /><input type='email' name='email' placeholder='Your Email' required /><textarea name='message' placeholder='Your Message' required></textarea><button type='submit'>Send Message</button></form></section>" if include_contact else ""}

        <!-- Footer -->
        <footer class="footer">
            <p>&copy; 2024 {name}. All rights reserved.</p>
        </footer>
    </q:body>
</q:component>
'''
        with open(project_dir / "components" / "index.q", 'w') as f:
            f.write(landing_content)
        files.append("components/index.q")

        return files

    def _copy_template_files(
        self,
        template_src: Path,
        project_dir: Path,
        name: str,
        options: Dict
    ) -> List[str]:
        """Copy files from a custom template directory"""
        files = []

        for src_file in template_src.rglob("*"):
            if src_file.is_file() and src_file.name != "template.yaml":
                rel_path = src_file.relative_to(template_src)
                dest_file = project_dir / rel_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                # Read and process content (replace placeholders)
                try:
                    content = src_file.read_text()
                    content = content.replace("{{PROJECT_NAME}}", name)
                    for key, value in options.items():
                        content = content.replace(f"{{{{OPTIONS.{key}}}}}", str(value))
                    dest_file.write_text(content)
                except Exception:
                    # Binary file, just copy
                    shutil.copy2(src_file, dest_file)

                files.append(str(rel_path))

        return files


def get_template_service() -> TemplateService:
    """Get template service instance"""
    return TemplateService()
