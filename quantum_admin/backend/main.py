"""
Quantum Admin - FastAPI Backend
Main application entry point
"""
from fastapi import FastAPI, Depends, HTTPException, status, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import os
import logging

logger = logging.getLogger(__name__)

try:
    # Try relative imports (when running as module)
    from . import crud, schemas, models
    from .database import get_db, init_db, seed_db
    from .docker_service import DockerService
    from .db_setup_service import DatabaseSetupService
    from .settings_service import get_settings_service, SettingsService
    from .auth_service import get_auth_service, AuthService, User
    from .audit_service import audit_log, get_audit_service, AuditAction, AuditService
    from .resource_manager import get_resource_manager, ResourceManager
    from .log_service import get_log_service, LogService, LogSource, LogLevel
    from .health_service import get_health_service, HealthService, HealthStatus
    from .template_service import get_template_service, TemplateService
except ImportError:
    # Fall back to absolute imports (when running directly)
    import crud
    import schemas
    import models
    from database import get_db, init_db, seed_db
    from docker_service import DockerService
    from db_setup_service import DatabaseSetupService
    from settings_service import get_settings_service, SettingsService
    from auth_service import get_auth_service, AuthService, User
    from audit_service import audit_log, get_audit_service, AuditAction, AuditService
    from resource_manager import get_resource_manager, ResourceManager
    from log_service import get_log_service, LogService, LogSource, LogLevel
    from health_service import get_health_service, HealthService, HealthStatus
    from template_service import get_template_service, TemplateService

# Security scheme for JWT
security = HTTPBearer(auto_error=False)

# Create FastAPI app
# Get root path from environment (for reverse proxy deployment)
ROOT_PATH = os.environ.get("ROOT_PATH", "")
# URL prefix for all routes in HTML templates
URL_PREFIX = ROOT_PATH

app = FastAPI(
    title="Quantum Admin API",
    description="Administration interface for Quantum Language projects",
    version="1.0.0",
    root_path=ROOT_PATH
)

# Initialize Docker service (singleton)
docker_service = None

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (frontend)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/frontend", StaticFiles(directory=frontend_path), name="frontend")

# Mount static files (CSS, JS, etc.)
# Try multiple possible locations
static_paths = [
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"),  # quantum_admin/static
    os.path.join(os.path.dirname(__file__), "..", "static"),  # relative path
    "/var/www/quantum-admin/static",  # production path
]

static_mounted = False
for static_path in static_paths:
    if os.path.exists(static_path) and os.path.isdir(static_path):
        try:
            app.mount("/static", StaticFiles(directory=static_path), name="static")
            print(f"[OK] Static files mounted from: {static_path}")
            static_mounted = True
            break
        except Exception as e:
            print(f"[WARN] Failed to mount static from {static_path}: {e}")

if not static_mounted:
    print(f"[WARN] Static files directory not found. Tried: {static_paths}")


# ============================================================================
# LIFECYCLE EVENTS
# ============================================================================

@app.on_event("startup")
def startup_event():
    """Initialize database and Docker service on application startup"""
    global docker_service

    # Initialize database
    init_db()
    seed_db()

    # Initialize Docker service - try Forge first
    forge_host = os.environ.get("DOCKER_HOST", "ssh://abathur@10.10.1.40")
    try:
        docker_service = DockerService(docker_host=forge_host)
        print(f"[OK] Docker service initialized: {forge_host}")
    except RuntimeError as e:
        print(f"[WARN] Docker service unavailable: {e}")
        print("[INFO] Datasource container management will be disabled")
        # Try local Docker as fallback
        try:
            docker_service = DockerService()
            print("[OK] Local Docker service initialized")
        except RuntimeError:
            pass

    print("[OK] Quantum Admin API started successfully")


@app.on_event("shutdown")
def shutdown_event():
    """Cleanup on application shutdown"""
    print("[INFO] Quantum Admin API shutting down")


# ============================================================================
# ROOT & HEALTH CHECK
# ============================================================================

# Admin UI routes - supports both direct access and behind reverse proxy
@app.get("/", tags=["Admin UI"], response_class=HTMLResponse)
@app.get("/admin/", tags=["Admin UI"], response_class=HTMLResponse)
@app.get("/admin", tags=["Admin UI"], response_class=HTMLResponse)
def serve_admin_ui_root(request: Request = None, db: Session = Depends(get_db)):
    """Serve admin UI dashboard"""
    return HTMLResponse(content=get_admin_shell("Dashboard", "dashboard", ""))


# Admin UI pages - defined as explicit routes to avoid conflicts with API routes
ADMIN_UI_PAGE_CONFIG = {
    "": ("Dashboard", "dashboard"),
    "projects": ("Applications", "projects"),
    "docker": ("Docker", "docker"),
    "deploy": ("Deploy", "deploy"),
    "jobs": ("Jobs", "jobs"),
    "cicd": ("CI/CD", "cicd"),
    "tests": ("Tests", "tests"),
    "settings": ("Settings", "settings"),
    "resources": ("Resources", "resources"),
    "users": ("Users", "users"),
    "components": ("Components", "components"),
}


def _serve_admin_page(page: str, db: Session):
    """Common handler for admin UI pages"""
    if page == "login":
        return HTMLResponse(content=get_login_page())
    if page == "logout":
        response = RedirectResponse(url=f"{URL_PREFIX}/login")
        response.delete_cookie("token")
        return response
    title, active = ADMIN_UI_PAGE_CONFIG.get(page, ("Quantum Admin", "dashboard"))
    return HTMLResponse(content=get_admin_shell(title, active, page))


@app.get("/projects/{project_id:int}", tags=["Admin UI"], response_class=HTMLResponse)
@app.get("/admin/projects/{project_id:int}", tags=["Admin UI"], response_class=HTMLResponse)
def serve_project_detail(project_id: int, db: Session = Depends(get_db)):
    """Serve project detail page"""
    project = crud.get_project(db, project_id)
    if project:
        return HTMLResponse(content=get_admin_shell(
            f"Application: {project.name}",
            "projects",
            "project_detail",
            project_id=project_id
        ))
    return HTMLResponse(content=get_admin_shell("Application Not Found", "projects", "projects"))


@app.get("/login", tags=["Admin UI"], response_class=HTMLResponse)
@app.get("/admin/login", tags=["Admin UI"], response_class=HTMLResponse)
def serve_login_page():
    return HTMLResponse(content=get_login_page())


@app.get("/logout", tags=["Admin UI"], response_class=HTMLResponse)
@app.get("/admin/logout", tags=["Admin UI"], response_class=HTMLResponse)
def serve_logout_page():
    response = RedirectResponse(url=f"{URL_PREFIX}/login")
    response.delete_cookie("token")
    return response


# Explicit routes for each admin UI page
@app.get("/projects", tags=["Admin UI"], response_class=HTMLResponse)
@app.get("/admin/projects", tags=["Admin UI"], response_class=HTMLResponse)
def serve_projects_page(db: Session = Depends(get_db)):
    return _serve_admin_page("projects", db)


@app.get("/docker", tags=["Admin UI"], response_class=HTMLResponse)
@app.get("/admin/docker", tags=["Admin UI"], response_class=HTMLResponse)
def serve_docker_page(db: Session = Depends(get_db)):
    return _serve_admin_page("docker", db)


@app.get("/deploy", tags=["Admin UI"], response_class=HTMLResponse)
@app.get("/admin/deploy", tags=["Admin UI"], response_class=HTMLResponse)
def serve_deploy_page(db: Session = Depends(get_db)):
    return _serve_admin_page("deploy", db)


@app.get("/jobs", tags=["Admin UI"], response_class=HTMLResponse)
@app.get("/admin/jobs", tags=["Admin UI"], response_class=HTMLResponse)
def serve_jobs_page(db: Session = Depends(get_db)):
    return _serve_admin_page("jobs", db)


@app.get("/cicd", tags=["Admin UI"], response_class=HTMLResponse)
@app.get("/admin/cicd", tags=["Admin UI"], response_class=HTMLResponse)
def serve_cicd_page(db: Session = Depends(get_db)):
    return _serve_admin_page("cicd", db)


@app.get("/tests", tags=["Admin UI"], response_class=HTMLResponse)
@app.get("/admin/tests", tags=["Admin UI"], response_class=HTMLResponse)
def serve_tests_page(db: Session = Depends(get_db)):
    return _serve_admin_page("tests", db)


@app.get("/settings", tags=["Admin UI"], response_class=HTMLResponse)
@app.get("/admin/settings", tags=["Admin UI"], response_class=HTMLResponse)
def serve_settings_page(db: Session = Depends(get_db)):
    return _serve_admin_page("settings", db)


@app.get("/resources", tags=["Admin UI"], response_class=HTMLResponse)
@app.get("/admin/resources", tags=["Admin UI"], response_class=HTMLResponse)
def serve_resources_page(db: Session = Depends(get_db)):
    return _serve_admin_page("resources", db)


@app.get("/users", tags=["Admin UI"], response_class=HTMLResponse)
@app.get("/admin/users", tags=["Admin UI"], response_class=HTMLResponse)
def serve_users_page(db: Session = Depends(get_db)):
    return _serve_admin_page("users", db)


@app.get("/components", tags=["Admin UI"], response_class=HTMLResponse)
@app.get("/admin/components", tags=["Admin UI"], response_class=HTMLResponse)
def serve_components_page(db: Session = Depends(get_db)):
    return _serve_admin_page("components", db)


# This is now just a simple handler for the old serve_admin_ui function reference
def serve_admin_ui(path: str = "", request: Request = None, db: Session = Depends(get_db)):
    """Legacy function - not used as a route anymore"""
    pass  # No longer used


def get_login_page():
    """Return login page HTML - Dark theme"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Login - Quantum Admin</title>
  <link rel="stylesheet" href="{URL_PREFIX}/static/quantum-admin.css">
</head>
<body class="qa-login-page">
  <div class="qa-login-card">
    <div class="qa-login-logo">
      <div class="qa-login-logo-icon">Q</div>
      <h1 class="qa-login-title">Quantum Admin</h1>
      <p class="qa-login-subtitle">Sign in to your account</p>
    </div>
    <div id="error-msg" class="qa-hidden qa-mb-4" style="padding: 12px; background: var(--q-danger-dim); border-radius: 8px;">
      <p class="qa-text-sm qa-text-danger">Invalid credentials</p>
    </div>
    <form id="login-form" onsubmit="doLogin(event)">
      <div class="qa-form-group">
        <label class="qa-label">Username</label>
        <input type="text" name="username" id="username" required class="qa-input" placeholder="Enter your username" value="admin" />
      </div>
      <div class="qa-form-group">
        <label class="qa-label">Password</label>
        <input type="password" name="password" id="password" required class="qa-input" placeholder="Enter your password" value="admin" />
      </div>
      <button type="submit" class="qa-btn qa-btn-primary qa-btn-block qa-btn-lg">Sign In</button>
    </form>
    <div class="qa-mt-6 qa-text-center" style="padding-top: 16px; border-top: 1px solid var(--q-border);">
      <p class="qa-text-xs qa-text-muted">
        Default: <code class="qa-font-mono" style="background: var(--q-bg-overlay); padding: 2px 6px; border-radius: 4px;">admin</code> /
        <code class="qa-font-mono" style="background: var(--q-bg-overlay); padding: 2px 6px; border-radius: 4px;">admin</code>
      </p>
    </div>
  </div>
  <script>
    async function doLogin(e) {
      e.preventDefault();
      const username = document.getElementById('username').value;
      const password = document.getElementById('password').value;
      try {
        const res = await fetch('{URL_PREFIX}/auth/login?username=' + encodeURIComponent(username) + '&password=' + encodeURIComponent(password), {method: 'POST'});
        const data = await res.json();
        if (data.access_token) {
          localStorage.setItem('token', data.access_token);
          window.location.href = '{URL_PREFIX}/';
        } else {
          document.getElementById('error-msg').classList.remove('qa-hidden');
        }
      } catch(err) {
        document.getElementById('error-msg').classList.remove('qa-hidden');
      }
    }
  </script>
</body>
</html>'''


def get_admin_shell(title: str, active: str, page: str, project_id: int = None):
    """Return admin shell HTML with dynamic content"""

    # Content for each page
    page_contents = {
        "dashboard": get_dashboard_content(),
        "projects": get_projects_content(),
        "docker": get_docker_content(),
        "deploy": get_deploy_content(),
        "jobs": get_jobs_content(),
        "cicd": get_cicd_content(),
        "tests": get_tests_content(),
        "settings": get_settings_content(),
        "resources": get_resources_content(),
        "users": get_users_content(),
        "components": get_components_content(),
    }

    # Handle project detail page
    if page == "project_detail" and project_id:
        content = get_project_detail_content(project_id)
    else:
        content = page_contents.get(page, page_contents["dashboard"])

    # Replace {URL_PREFIX} placeholder in content
    content = content.replace("{URL_PREFIX}", URL_PREFIX)

    def nav_class(name):
        return "qa-sidebar-link active" if name == active else "qa-sidebar-link"

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - Quantum Admin</title>
  <script src="https://unpkg.com/htmx.org@2.0.0"></script>
  <link rel="stylesheet" href="{URL_PREFIX}/static/quantum-admin.css">
</head>
<body>
  <div class="qa-layout">
    <!-- Sidebar -->
    <aside class="qa-sidebar">
      <div class="qa-sidebar-header">
        <a href="{URL_PREFIX}/" class="qa-sidebar-logo">
          <div class="qa-sidebar-logo-icon">Q</div>
          <div>
            <span class="qa-sidebar-logo-text">Quantum Admin</span>
            <span class="qa-sidebar-version">v2.0</span>
          </div>
        </a>
      </div>
      <nav class="qa-sidebar-nav">
        <div class="qa-sidebar-section">
          <a href="{URL_PREFIX}/" class="{nav_class("dashboard")}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
            Dashboard
          </a>
          <a href="{URL_PREFIX}/projects" class="{nav_class("projects")}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
            Applications
          </a>
          <a href="{URL_PREFIX}/docker" class="{nav_class("docker")}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2"/></svg>
            Docker
          </a>
          <a href="{URL_PREFIX}/deploy" class="{nav_class("deploy")}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>
            Deploy
          </a>
        </div>
        <div class="qa-sidebar-section">
          <div class="qa-sidebar-section-title">DevOps</div>
          <a href="{URL_PREFIX}/jobs" class="{nav_class("jobs")}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            Jobs
          </a>
          <a href="{URL_PREFIX}/cicd" class="{nav_class("cicd")}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
            CI/CD
          </a>
          <a href="{URL_PREFIX}/tests" class="{nav_class("tests")}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            Tests
          </a>
          <a href="{URL_PREFIX}/components" class="{nav_class("components")}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/></svg>
            Components
          </a>
        </div>
        <div class="qa-sidebar-section">
          <div class="qa-sidebar-section-title">System</div>
          <a href="{URL_PREFIX}/resources" class="{nav_class("resources")}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/></svg>
            Resources
          </a>
          <a href="{URL_PREFIX}/settings" class="{nav_class("settings")}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
            Settings
          </a>
          <a href="{URL_PREFIX}/users" class="{nav_class("users")}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
            Users
          </a>
          <a href="https://quantum.sargas.cloud" target="_blank" rel="noopener noreferrer" class="qa-sidebar-link">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>
            Docs
            <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="margin-left: auto; opacity: 0.5;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
          </a>
        </div>
      </nav>
      <div class="qa-sidebar-footer">
        <div class="qa-sidebar-user">
          <div class="qa-sidebar-user-avatar">A</div>
          <div class="qa-sidebar-user-info">
            <div class="qa-sidebar-user-name">admin</div>
            <div class="qa-sidebar-user-role">Administrator</div>
          </div>
          <a href="{URL_PREFIX}/logout" class="qa-btn qa-btn-ghost qa-btn-icon">
            <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
          </a>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="qa-main">
      <header class="qa-header">
        <h2 class="qa-header-title">{title}</h2>
        <div id="header-status" hx-get="{URL_PREFIX}/docker/status" hx-trigger="load, every 30s" hx-swap="innerHTML" class="qa-header-status">
          <span class="qa-header-status-dot" style="background: var(--q-text-dim);"></span>
          <span class="qa-text-muted">Checking...</span>
        </div>
      </header>
      <div class="qa-content">
        {content}
      </div>
    </main>
  </div>
  <div id="toast-container" style="position: fixed; bottom: 16px; right: 16px; z-index: 100; display: flex; flex-direction: column; gap: 8px;"></div>
  <script>
    function showToast(msg, type) {{
      const c = document.getElementById('toast-container');
      const t = document.createElement('div');
      const colors = {{success:'var(--q-success)',error:'var(--q-danger)',warning:'var(--q-warning)',info:'var(--q-info)'}};
      t.style.cssText = 'padding: 12px 16px; border-radius: 8px; color: white; font-weight: 500; box-shadow: 0 4px 12px rgba(0,0,0,0.3); background:' + (colors[type]||colors.info);
      t.textContent = msg;
      c.appendChild(t);
      setTimeout(() => t.remove(), 3000);
    }}
  </script>
</body>
</html>'''
    # Replace any remaining {URL_PREFIX} in the HTML
    return html.replace("{URL_PREFIX}", URL_PREFIX)


def get_dashboard_content():
    return '''
    <!-- Row 1: Core Stats (4 cards) -->
    <div class="qa-grid qa-grid-4 qa-mb-4" hx-get="{URL_PREFIX}/dashboard/stats" hx-trigger="load" hx-swap="innerHTML">
      <div class="qa-stat-card qa-pulse"><div class="qa-stat-label">Loading...</div><div class="qa-stat-value">-</div></div>
      <div class="qa-stat-card qa-pulse"><div class="qa-stat-label">Loading...</div><div class="qa-stat-value">-</div></div>
      <div class="qa-stat-card qa-pulse"><div class="qa-stat-label">Loading...</div><div class="qa-stat-value">-</div></div>
      <div class="qa-stat-card qa-pulse"><div class="qa-stat-label">Loading...</div><div class="qa-stat-value">-</div></div>
      <div class="qa-stat-card qa-pulse"><div class="qa-stat-label">Loading...</div><div class="qa-stat-value">-</div></div>
      <div class="qa-stat-card qa-pulse"><div class="qa-stat-label">Loading...</div><div class="qa-stat-value">-</div></div>
      <div class="qa-stat-card qa-pulse"><div class="qa-stat-label">Loading...</div><div class="qa-stat-value">-</div></div>
      <div class="qa-stat-card qa-pulse"><div class="qa-stat-label">Loading...</div><div class="qa-stat-value">-</div></div>
    </div>

    <!-- Row 2: Activity + Quick Actions -->
    <div class="qa-grid qa-grid-3 qa-gap-6">
      <div class="qa-card" style="grid-column: span 2;">
        <div class="qa-card-header"><h3 class="qa-card-title">Recent Activity</h3></div>
        <div class="qa-card-body" id="activity-feed" hx-get="{URL_PREFIX}/dashboard/activity" hx-trigger="load, every 30s" hx-swap="innerHTML"><div class="qa-text-center qa-text-muted qa-p-6">Loading...</div></div>
      </div>
      <div class="qa-card">
        <div class="qa-card-header"><h3 class="qa-card-title">Quick Actions</h3></div>
        <div class="qa-card-body" style="padding: 8px;">
          <a href="{URL_PREFIX}/projects" class="qa-sidebar-link"><svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>New Application</a>
          <a href="{URL_PREFIX}/deploy" class="qa-sidebar-link"><svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>Deploy App</a>
          <a href="{URL_PREFIX}/docker" class="qa-sidebar-link"><svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2"/></svg>Manage Containers</a>
          <a href="{URL_PREFIX}/settings" class="qa-sidebar-link"><svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>Settings</a>
        </div>
      </div>
    </div>
    <div class="qa-grid qa-grid-2 qa-mt-6">
      <div class="qa-card">
        <div class="qa-card-header">
          <h3 class="qa-card-title">Docker Status</h3>
          <button class="qa-btn qa-btn-ghost qa-btn-sm" hx-post="{URL_PREFIX}/docker/connect?host=ssh://abathur@10.10.1.40" hx-target="#docker-info" hx-swap="innerHTML">Reconnect</button>
        </div>
        <div class="qa-card-body" id="docker-info" hx-get="{URL_PREFIX}/docker/info" hx-trigger="load" hx-swap="innerHTML"><div class="qa-text-center qa-text-muted">Connecting...</div></div>
      </div>
      <div class="qa-card">
        <div class="qa-card-header"><h3 class="qa-card-title">System Health</h3></div>
        <div class="qa-card-body">
          <div class="qa-flex qa-justify-between qa-items-center qa-mb-4"><span class="qa-text-secondary">API Server</span><span class="qa-flex qa-items-center qa-gap-2"><span class="qa-connector-status-dot connected"></span><span class="qa-text-success">Online</span></span></div>
          <div class="qa-flex qa-justify-between qa-items-center qa-mb-4"><span class="qa-text-secondary">Database</span><span hx-get="{URL_PREFIX}/health/database" hx-trigger="load" hx-swap="innerHTML"></span></div>
          <div class="qa-flex qa-justify-between qa-items-center"><span class="qa-text-secondary">Docker</span><span hx-get="{URL_PREFIX}/docker/status" hx-trigger="load" hx-swap="innerHTML"></span></div>
        </div>
      </div>
    </div>
    '''


def get_docker_content():
    return '''
    <div class="qa-card qa-mb-6">
      <div class="qa-card-body qa-flex qa-justify-between qa-items-center">
        <div hx-get="{URL_PREFIX}/docker/status" hx-trigger="load, every 30s" hx-swap="innerHTML" class="qa-flex qa-items-center qa-gap-2"></div>
        <button class="qa-btn qa-btn-secondary" hx-post="{URL_PREFIX}/docker/connect?host=ssh://abathur@10.10.1.40" hx-swap="none" onclick="setTimeout(()=>location.reload(),1000)">Reconnect</button>
      </div>
    </div>
    <div class="qa-tabs">
      <button class="qa-tab active" onclick="showTab('containers')">Containers</button>
      <button class="qa-tab" onclick="showTab('images')">Images</button>
      <button class="qa-tab" onclick="showTab('volumes')">Volumes</button>
      <button class="qa-tab" onclick="showTab('networks')">Networks</button>
    </div>
    <div id="tab-containers" class="qa-tab-panel active">
      <div class="qa-flex qa-justify-between qa-items-center qa-mb-4">
        <select class="qa-input qa-select" style="width: 160px;"><option value="all">All</option><option value="running">Running</option><option value="stopped">Stopped</option></select>
        <button class="qa-btn qa-btn-secondary" hx-get="{URL_PREFIX}/docker/containers" hx-target="#containers-tbody" hx-swap="innerHTML">Refresh</button>
      </div>
      <div class="qa-card" style="overflow: hidden;">
        <table class="qa-table">
          <thead>
            <tr>
              <th>Container</th>
              <th>Image</th>
              <th>Status</th>
              <th>Ports</th>
              <th>Created</th>
              <th class="qa-text-right">Actions</th>
            </tr>
          </thead>
          <tbody id="containers-tbody" hx-get="{URL_PREFIX}/docker/containers" hx-trigger="load" hx-swap="innerHTML">
            <tr><td colspan="6" class="qa-text-center qa-text-muted qa-p-6">Loading...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
    <div id="tab-images" class="qa-tab-panel">
      <div class="qa-card" style="overflow: hidden;">
        <table class="qa-table">
          <thead>
            <tr>
              <th>Repository</th>
              <th>Tag</th>
              <th>Size</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody id="images-tbody" hx-get="{URL_PREFIX}/docker/images" hx-trigger="load" hx-swap="innerHTML">
            <tr><td colspan="4" class="qa-text-center qa-text-muted qa-p-6">Loading...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
    <div id="tab-volumes" class="qa-tab-panel">
      <div class="qa-card" style="overflow: hidden;">
        <table class="qa-table">
          <thead>
            <tr><th>Name</th><th>Driver</th><th>Mountpoint</th></tr>
          </thead>
          <tbody id="volumes-tbody" hx-get="{URL_PREFIX}/docker/volumes" hx-trigger="load" hx-swap="innerHTML">
            <tr><td colspan="3" class="qa-text-center qa-text-muted qa-p-6">Loading...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
    <div id="tab-networks" class="qa-tab-panel">
      <div class="qa-card" style="overflow: hidden;">
        <table class="qa-table">
          <thead>
            <tr><th>Name</th><th>Driver</th><th>Scope</th></tr>
          </thead>
          <tbody id="networks-tbody" hx-get="{URL_PREFIX}/docker/networks" hx-trigger="load" hx-swap="innerHTML">
            <tr><td colspan="3" class="qa-text-center qa-text-muted qa-p-6">Loading...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
    <script>
      function showTab(name) {
        document.querySelectorAll('.qa-tab-panel').forEach(t => t.classList.remove('active'));
        document.getElementById('tab-' + name).classList.add('active');
        document.querySelectorAll('.qa-tab').forEach(b => b.classList.remove('active'));
        event.target.classList.add('active');
      }
      function startContainer(id) { fetch('{URL_PREFIX}/docker/containers/' + id + '/start', {method:'POST'}).then(() => htmx.trigger('#containers-tbody', 'load')); }
      function stopContainer(id) { fetch('{URL_PREFIX}/docker/containers/' + id + '/stop', {method:'POST'}).then(() => htmx.trigger('#containers-tbody', 'load')); }
      function showLogs(id) { window.open('{URL_PREFIX}/docker/containers/' + id + '/logs', '_blank'); }
    </script>
    '''


def get_projects_content():
    return '''
    <div class="qa-section-header">
      <input type="text" id="project-search" placeholder="Search applications..." class="qa-input" style="width: 260px;" oninput="filterProjects(this.value)" />
      <div class="qa-flex qa-gap-2">
        <button class="qa-btn qa-btn-secondary" onclick="openCreateWizard()">
          <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/></svg>
          From Template
        </button>
        <button class="qa-btn qa-btn-primary" onclick="openProjectModal()">
          <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
          New Application
        </button>
      </div>
    </div>

    <div id="projects-grid" hx-get="{URL_PREFIX}/api/projects-grid" hx-trigger="load" hx-swap="innerHTML" class="qa-grid qa-grid-3">
      <div class="qa-card qa-pulse"><div class="qa-card-body"><div class="qa-text-muted">Loading projects...</div></div></div>
    </div>

    <!-- Create/Edit Project Modal -->
    <div id="project-modal" class="qa-modal qa-hidden">
      <div class="qa-modal-backdrop" onclick="closeProjectModal()"></div>
      <div class="qa-modal-content">
        <div class="qa-modal-header">
          <h3 id="project-modal-title">New Application</h3>
          <button class="qa-btn qa-btn-ghost qa-btn-sm" onclick="closeProjectModal()">
            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="qa-modal-body">
          <form id="project-form" onsubmit="saveProject(event)">
            <input type="hidden" id="project-id" value="" />
            <div class="qa-form-group">
              <label class="qa-label">Application Name</label>
              <input type="text" id="project-name" class="qa-input" placeholder="My Quantum App" required />
            </div>
            <div class="qa-form-group">
              <label class="qa-label">Description</label>
              <textarea id="project-description" class="qa-input" rows="3" placeholder="A brief description of your project..."></textarea>
            </div>
          </form>
        </div>
        <div class="qa-modal-footer">
          <button class="qa-btn qa-btn-secondary" onclick="closeProjectModal()">Cancel</button>
          <button class="qa-btn qa-btn-primary" onclick="saveProject(event)">
            <span id="project-save-text">Create Application</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div id="delete-modal" class="qa-modal qa-hidden">
      <div class="qa-modal-backdrop" onclick="closeDeleteModal()"></div>
      <div class="qa-modal-content" style="max-width: 400px;">
        <div class="qa-modal-header">
          <h3>Delete Application</h3>
          <button class="qa-btn qa-btn-ghost qa-btn-sm" onclick="closeDeleteModal()">
            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="qa-modal-body">
          <p class="qa-text-muted">Are you sure you want to delete <strong id="delete-project-name"></strong>? This action cannot be undone.</p>
          <input type="hidden" id="delete-project-id" />
        </div>
        <div class="qa-modal-footer">
          <button class="qa-btn qa-btn-secondary" onclick="closeDeleteModal()">Cancel</button>
          <button class="qa-btn qa-btn-danger" onclick="confirmDeleteProject()">Delete Application</button>
        </div>
      </div>
    </div>

    <script>
    function openProjectModal(projectId = null) {
      document.getElementById('project-modal').classList.remove('qa-hidden');
      document.getElementById('project-id').value = projectId || '';
      document.getElementById('project-name').value = '';
      document.getElementById('project-description').value = '';

      if (projectId) {
        document.getElementById('project-modal-title').textContent = 'Edit Application';
        document.getElementById('project-save-text').textContent = 'Save Changes';
        // Load project data
        fetch('{URL_PREFIX}/projects/' + projectId, {
          headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
        })
        .then(r => r.json())
        .then(p => {
          document.getElementById('project-name').value = p.name;
          document.getElementById('project-description').value = p.description || '';
        });
      } else {
        document.getElementById('project-modal-title').textContent = 'New Application';
        document.getElementById('project-save-text').textContent = 'Create Application';
      }
    }

    function closeProjectModal() {
      document.getElementById('project-modal').classList.add('qa-hidden');
    }

    function saveProject(e) {
      e.preventDefault();
      const id = document.getElementById('project-id').value;
      const name = document.getElementById('project-name').value;
      const description = document.getElementById('project-description').value;

      const method = id ? 'PUT' : 'POST';
      const url = id ? '/projects/' + id : '/projects';

      fetch(url, {
        method: method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + localStorage.getItem('token')
        },
        body: JSON.stringify({ name, description })
      })
      .then(r => {
        if (r.ok) {
          closeProjectModal();
          htmx.trigger('#projects-grid', 'load');
        } else {
          r.json().then(d => alert(d.detail || 'Error saving project'));
        }
      });
    }

    function editProject(id) {
      openProjectModal(id);
    }

    function deleteProject(id, name) {
      document.getElementById('delete-project-id').value = id;
      document.getElementById('delete-project-name').textContent = name;
      document.getElementById('delete-modal').classList.remove('qa-hidden');
    }

    function closeDeleteModal() {
      document.getElementById('delete-modal').classList.add('qa-hidden');
    }

    function confirmDeleteProject() {
      const id = document.getElementById('delete-project-id').value;
      fetch('{URL_PREFIX}/projects/' + id, {
        method: 'DELETE',
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
      })
      .then(r => {
        if (r.ok) {
          closeDeleteModal();
          htmx.trigger('#projects-grid', 'load');
        } else {
          alert('Error deleting project');
        }
      });
    }

    function filterProjects(query) {
      const cards = document.querySelectorAll('#projects-grid .qa-card');
      const lowerQuery = query.toLowerCase();
      cards.forEach(card => {
        const title = card.querySelector('.qa-card-title');
        const desc = card.querySelector('.qa-text-muted');
        const text = (title?.textContent || '') + ' ' + (desc?.textContent || '');
        card.style.display = text.toLowerCase().includes(lowerQuery) ? '' : 'none';
      });
    }

    function openCreateWizard() {
      document.getElementById('create-wizard-modal').classList.add('active');
    }

    function closeCreateWizard() {
      document.getElementById('create-wizard-modal').classList.remove('active');
      // Reset wizard state
      currentStep = 1;
      selectedTemplate = null;
      document.querySelectorAll('.wizard-step').forEach(s => s.classList.remove('active'));
      document.getElementById('wizard-step-1').classList.add('active');
    }
    </script>

    <!-- Create from Template Wizard Modal -->
    <div id="create-wizard-modal" class="qa-modal-overlay">
      <div class="qa-modal qa-modal-lg">
        <div class="qa-modal-header">
          <h3 class="qa-modal-title">Create from Template</h3>
          <button class="qa-modal-close" onclick="closeCreateWizard()">
            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="qa-modal-body" hx-get="{URL_PREFIX}/create-project-wizard" hx-trigger="load" hx-swap="innerHTML">
          <div class="qa-text-center qa-p-6">Loading templates...</div>
        </div>
      </div>
    </div>
    '''


def get_project_detail_content(project_id: int):
    """Return project detail/edit page content"""
    return f'''
    <!-- Back button and header -->
    <div class="qa-flex qa-items-center qa-gap-4 qa-mb-6">
      <a href="{URL_PREFIX}/projects" class="qa-btn qa-btn-ghost">
        <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/></svg>
        Back to Applications
      </a>
    </div>

    <!-- Project header with status -->
    <div class="qa-card qa-mb-6">
      <div class="qa-card-body qa-flex qa-justify-between qa-items-center" id="project-header" hx-get="{URL_PREFIX}/api/projects/{project_id}/header" hx-trigger="load" hx-swap="innerHTML">
        <div class="qa-flex qa-items-center qa-gap-4">
          <div class="qa-project-icon" style="width: 56px; height: 56px;">
            <svg width="28" height="28" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
          </div>
          <div>
            <h2 class="qa-text-xl qa-font-bold">Loading...</h2>
            <p class="qa-text-muted">Loading project details...</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Tabs Navigation -->
    <div class="qa-tabs qa-mb-6">
      <button class="qa-tab active" data-tab="general" onclick="showTab('general')">
        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
        General
      </button>
      <button class="qa-tab" data-tab="source" onclick="showTab('source')">
        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>
        Source Code
      </button>
      <button class="qa-tab" data-tab="datasources" onclick="showTab('datasources')">
        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"/></svg>
        Datasources
      </button>
      <button class="qa-tab" data-tab="connectors" onclick="showTab('connectors')">
        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/></svg>
        Connectors
      </button>
      <button class="qa-tab" data-tab="environments" onclick="showTab('environments')">
        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2"/></svg>
        Environments
      </button>
      <button class="qa-tab" data-tab="paths" onclick="showTab('paths')">
        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
        Paths
      </button>
      <button class="qa-tab" data-tab="envvars" onclick="showTab('envvars')">
        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
        Env Vars
      </button>
      <button class="qa-tab" data-tab="logs" onclick="showTab('logs')">
        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
        Logs
      </button>
      <button class="qa-tab" data-tab="activity" onclick="showTab('activity')">
        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        Activity
      </button>
    </div>

    <!-- Tab Content -->
    <div id="tab-content">
      <!-- General Tab -->
      <div id="tab-general" class="qa-tab-content active">
        <div class="qa-card">
          <div class="qa-card-header">
            <h3 class="qa-card-title">Application Settings</h3>
          </div>
          <div class="qa-card-body" hx-get="{URL_PREFIX}/api/projects/{project_id}/general" hx-trigger="load" hx-swap="innerHTML">
            <div class="qa-text-center qa-text-muted qa-p-6">Loading...</div>
          </div>
        </div>
      </div>

      <!-- Source Code Tab -->
      <div id="tab-source" class="qa-tab-content qa-hidden">
        <div class="qa-card">
          <div class="qa-card-header">
            <h3 class="qa-card-title">Source Code Configuration</h3>
          </div>
          <div class="qa-card-body" hx-get="{URL_PREFIX}/api/projects/{project_id}/source-html" hx-trigger="load" hx-swap="innerHTML">
            <div class="qa-text-center qa-text-muted qa-p-6">Loading...</div>
          </div>
        </div>
      </div>

      <!-- Datasources Tab -->
      <div id="tab-datasources" class="qa-tab-content qa-hidden">
        <div class="qa-card">
          <div class="qa-card-header qa-flex qa-justify-between qa-items-center">
            <h3 class="qa-card-title">Datasources</h3>
            <button class="qa-btn qa-btn-primary qa-btn-sm" onclick="openDatasourceModal()">
              <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
              Add Datasource
            </button>
          </div>
          <div class="qa-card-body" id="datasources-list" hx-get="{URL_PREFIX}/api/projects/{project_id}/datasources-html" hx-trigger="load" hx-swap="innerHTML">
            <div class="qa-text-center qa-text-muted qa-p-6">Loading datasources...</div>
          </div>
        </div>
      </div>

      <!-- Connectors Tab -->
      <div id="tab-connectors" class="qa-tab-content qa-hidden">
        <div class="qa-card">
          <div class="qa-card-header">
            <h3 class="qa-card-title">Connector Access</h3>
            <p class="qa-text-sm qa-text-muted">Configure which connectors this project can access</p>
          </div>
          <div class="qa-card-body" id="connectors-list" hx-get="{URL_PREFIX}/api/projects/{project_id}/connectors-html" hx-trigger="load" hx-swap="innerHTML">
            <div class="qa-text-center qa-text-muted qa-p-6">Loading connectors...</div>
          </div>
        </div>
      </div>

      <!-- Environments Tab -->
      <div id="tab-environments" class="qa-tab-content qa-hidden">
        <div class="qa-card">
          <div class="qa-card-header qa-flex qa-justify-between qa-items-center">
            <h3 class="qa-card-title">Deploy Environments</h3>
            <div class="qa-flex qa-gap-2">
              <button class="qa-btn qa-btn-secondary qa-btn-sm" onclick="createDefaultEnvs()">Create Defaults</button>
              <button class="qa-btn qa-btn-primary qa-btn-sm" onclick="openEnvironmentModal()">
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
                Add Environment
              </button>
            </div>
          </div>
          <div class="qa-card-body" id="environments-list" hx-get="{URL_PREFIX}/api/projects/{project_id}/environments-html" hx-trigger="load" hx-swap="innerHTML">
            <div class="qa-text-center qa-text-muted qa-p-6">Loading environments...</div>
          </div>
        </div>
      </div>

      <!-- Paths Tab -->
      <div id="tab-paths" class="qa-tab-content qa-hidden">
        <div class="qa-card">
          <div class="qa-card-header">
            <h3 class="qa-card-title">Application Paths</h3>
          </div>
          <div class="qa-card-body" hx-get="{URL_PREFIX}/api/projects/{project_id}/paths-html" hx-trigger="load" hx-swap="innerHTML">
            <div class="qa-text-center qa-text-muted qa-p-6">Loading paths...</div>
          </div>
        </div>
      </div>

      <!-- Env Vars Tab -->
      <div id="tab-envvars" class="qa-tab-content qa-hidden">
        <div class="qa-card">
          <div class="qa-card-header qa-flex qa-justify-between qa-items-center">
            <h3 class="qa-card-title">Environment Variables</h3>
            <button class="qa-btn qa-btn-primary qa-btn-sm" onclick="openEnvVarModal()">
              <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
              Add Variable
            </button>
          </div>
          <div class="qa-card-body" id="envvars-list" hx-get="{URL_PREFIX}/projects/{project_id}/environment-variables" hx-trigger="load" hx-swap="innerHTML">
            <div class="qa-text-center qa-text-muted qa-p-6">Loading environment variables...</div>
          </div>
        </div>
      </div>

      <!-- Logs Tab -->
      <div id="tab-logs" class="qa-tab-content qa-hidden">
        <div class="qa-card">
          <div class="qa-card-header">
            <div class="qa-flex qa-justify-between qa-items-center qa-mb-3">
              <h3 class="qa-card-title">Application Logs</h3>
              <div class="qa-flex qa-gap-2">
                <button class="qa-btn qa-btn-ghost qa-btn-sm" id="logs-auto-refresh" onclick="toggleAutoRefresh()">
                  <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                  Auto
                </button>
                <button class="qa-btn qa-btn-secondary qa-btn-sm" hx-get="{URL_PREFIX}/api/projects/{project_id}/logs-html" hx-target="#logs-list" hx-swap="innerHTML">
                  <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                  Refresh
                </button>
              </div>
            </div>
            <!-- Filters -->
            <div class="qa-flex qa-gap-2 qa-flex-wrap">
              <input type="text" id="log-search" class="qa-input qa-input-sm" placeholder="Search logs..." style="width: 200px;" onkeyup="filterLogs()">
              <select id="log-source" class="qa-input qa-input-sm qa-select" style="width: 120px;" onchange="filterLogs()">
                <option value="">All Sources</option>
                <option value="app">App</option>
                <option value="db">Database</option>
                <option value="access">Access</option>
                <option value="deploy">Deploy</option>
                <option value="system">System</option>
              </select>
              <select id="log-level" class="qa-input qa-input-sm qa-select" style="width: 120px;" onchange="filterLogs()">
                <option value="">All Levels</option>
                <option value="DEBUG">Debug</option>
                <option value="INFO">Info</option>
                <option value="WARNING">Warning</option>
                <option value="ERROR">Error</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>
          </div>
          <div class="qa-card-body qa-p-0" id="logs-list" hx-get="{URL_PREFIX}/api/projects/{project_id}/logs-html" hx-trigger="load" hx-swap="innerHTML" style="max-height: 500px; overflow-y: auto;">
            <div class="qa-text-center qa-text-muted qa-p-6">Loading logs...</div>
          </div>
        </div>
        <script>
          let logsAutoRefresh = false;
          let logsInterval = null;

          function toggleAutoRefresh() {{
            logsAutoRefresh = !logsAutoRefresh;
            const btn = document.getElementById('logs-auto-refresh');
            if (logsAutoRefresh) {{
              btn.classList.add('qa-btn-primary');
              btn.classList.remove('qa-btn-ghost');
              logsInterval = setInterval(() => htmx.trigger('#logs-list', 'load'), 5000);
            }} else {{
              btn.classList.remove('qa-btn-primary');
              btn.classList.add('qa-btn-ghost');
              if (logsInterval) clearInterval(logsInterval);
            }}
          }}

          function filterLogs() {{
            const search = document.getElementById('log-search').value;
            const source = document.getElementById('log-source').value;
            const level = document.getElementById('log-level').value;

            let url = '/api/projects/{project_id}/logs-html?limit=100';
            if (search) url += '&search=' + encodeURIComponent(search);
            if (source) url += '&source=' + source;
            if (level) url += '&level=' + level;

            htmx.ajax('GET', url, {{ target: '#logs-list', swap: 'innerHTML' }});
          }}
        </script>
      </div>

      <!-- Activity/Audit Log Tab -->
      <div id="tab-activity" class="qa-tab-content qa-hidden">
        <div class="qa-card">
          <div class="qa-card-header qa-flex qa-justify-between qa-items-center">
            <h3 class="qa-card-title">Activity Log</h3>
            <button class="qa-btn qa-btn-secondary qa-btn-sm" hx-get="{URL_PREFIX}/api/projects/{project_id}/audit-log-html" hx-target="#activity-list" hx-swap="innerHTML">
              <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
              Refresh
            </button>
          </div>
          <div class="qa-card-body" id="activity-list" hx-get="{URL_PREFIX}/api/projects/{project_id}/audit-log-html" hx-trigger="load" hx-swap="innerHTML">
            <div class="qa-text-center qa-text-muted qa-p-6">Loading activity log...</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Datasource Modal -->
    <div id="datasource-modal" class="qa-modal qa-hidden">
      <div class="qa-modal-backdrop" onclick="closeDatasourceModal()"></div>
      <div class="qa-modal-content" style="max-width: 600px;">
        <div class="qa-modal-header">
          <h3 id="datasource-modal-title">Add Datasource</h3>
          <button class="qa-btn qa-btn-ghost qa-btn-sm" onclick="closeDatasourceModal()">
            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="qa-modal-body">
          <form id="datasource-form" onsubmit="saveDatasource(event)">
            <input type="hidden" id="ds-id" value="" />
            <div class="qa-form-row">
              <div class="qa-form-group">
                <label class="qa-label">Name</label>
                <input type="text" id="ds-name" class="qa-input" placeholder="main-db" required />
              </div>
              <div class="qa-form-group">
                <label class="qa-label">Type</label>
                <select id="ds-type" class="qa-input qa-select" required>
                  <option value="postgres">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                  <option value="mongodb">MongoDB</option>
                </select>
              </div>
            </div>
            <div class="qa-form-group">
              <label class="qa-label">Connection Type</label>
              <select id="ds-connection-type" class="qa-input qa-select" onchange="toggleDsFields()" required>
                <option value="direct">Direct Connection</option>
                <option value="docker">Docker Container</option>
              </select>
            </div>
            <div id="ds-direct-fields">
              <div class="qa-form-row">
                <div class="qa-form-group" style="flex: 2;">
                  <label class="qa-label">Host</label>
                  <input type="text" id="ds-host" class="qa-input" placeholder="localhost" />
                </div>
                <div class="qa-form-group" style="flex: 1;">
                  <label class="qa-label">Port</label>
                  <input type="number" id="ds-port" class="qa-input" placeholder="5432" />
                </div>
              </div>
            </div>
            <div id="ds-docker-fields" class="qa-hidden">
              <div class="qa-form-group">
                <label class="qa-label">Docker Image</label>
                <input type="text" id="ds-image" class="qa-input" placeholder="postgres:15-alpine" />
              </div>
            </div>
            <div class="qa-form-row">
              <div class="qa-form-group">
                <label class="qa-label">Database Name</label>
                <input type="text" id="ds-database" class="qa-input" placeholder="myapp" />
              </div>
              <div class="qa-form-group">
                <label class="qa-label">Username</label>
                <input type="text" id="ds-username" class="qa-input" placeholder="postgres" />
              </div>
            </div>
            <div class="qa-form-group">
              <label class="qa-label">Password</label>
              <input type="password" id="ds-password" class="qa-input" placeholder="Enter password" />
            </div>
          </form>
        </div>
        <div class="qa-modal-footer">
          <button class="qa-btn qa-btn-secondary" onclick="closeDatasourceModal()">Cancel</button>
          <button class="qa-btn qa-btn-primary" onclick="saveDatasource(event)">Save Datasource</button>
        </div>
      </div>
    </div>

    <!-- Environment Modal -->
    <div id="environment-modal" class="qa-modal qa-hidden">
      <div class="qa-modal-backdrop" onclick="closeEnvironmentModal()"></div>
      <div class="qa-modal-content" style="max-width: 700px;">
        <div class="qa-modal-header">
          <h3 id="environment-modal-title">Add Environment</h3>
          <button class="qa-btn qa-btn-ghost qa-btn-sm" onclick="closeEnvironmentModal()">
            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="qa-modal-body">
          <form id="environment-form" onsubmit="saveEnvironment(event)">
            <input type="hidden" id="env-id" value="" />

            <!-- Basic Info -->
            <div class="qa-form-row">
              <div class="qa-form-group">
                <label class="qa-label">Name (ID)</label>
                <input type="text" id="env-name" class="qa-input" placeholder="production" required />
                <p class="qa-text-xs qa-text-muted qa-mt-1">Unique identifier (lowercase, no spaces)</p>
              </div>
              <div class="qa-form-group">
                <label class="qa-label">Display Name</label>
                <input type="text" id="env-display-name" class="qa-input" placeholder="Production" />
              </div>
            </div>

            <div class="qa-form-row">
              <div class="qa-form-group" style="flex: 1;">
                <label class="qa-label">Order</label>
                <input type="number" id="env-order" class="qa-input" value="1" min="1" />
                <p class="qa-text-xs qa-text-muted qa-mt-1">Promotion chain order</p>
              </div>
              <div class="qa-form-group" style="flex: 2;">
                <label class="qa-label">Git Branch</label>
                <input type="text" id="env-branch" class="qa-input" value="main" />
              </div>
            </div>

            <hr class="qa-my-4" style="border-color: var(--q-border);" />

            <!-- Docker Configuration -->
            <h4 class="qa-font-bold qa-mb-3">Docker Configuration</h4>
            <div class="qa-form-group">
              <label class="qa-label">Docker Host</label>
              <input type="text" id="env-docker-host" class="qa-input" placeholder="ssh://user@hostname or unix://" />
              <p class="qa-text-xs qa-text-muted qa-mt-1">Leave empty for local Docker</p>
            </div>

            <div class="qa-form-row">
              <div class="qa-form-group">
                <label class="qa-label">Docker Registry</label>
                <input type="text" id="env-docker-registry" class="qa-input" placeholder="docker.io/myorg" />
              </div>
              <div class="qa-form-group">
                <label class="qa-label">Container Name</label>
                <input type="text" id="env-container-name" class="qa-input" placeholder="myapp-prod" />
              </div>
            </div>

            <div class="qa-form-row">
              <div class="qa-form-group">
                <label class="qa-label">Port</label>
                <input type="number" id="env-port" class="qa-input" placeholder="8080" />
              </div>
              <div class="qa-form-group">
                <label class="qa-label">Deploy Path</label>
                <input type="text" id="env-deploy-path" class="qa-input" placeholder="/var/www/app" />
              </div>
            </div>

            <hr class="qa-my-4" style="border-color: var(--q-border);" />

            <!-- Health & Deploy Settings -->
            <h4 class="qa-font-bold qa-mb-3">Health & Deploy Settings</h4>
            <div class="qa-form-group">
              <label class="qa-label">Health Check URL</label>
              <input type="text" id="env-health-url" class="qa-input" placeholder="http://localhost:8080/health" />
            </div>

            <div class="qa-flex qa-gap-6 qa-mt-4">
              <label class="qa-flex qa-items-center qa-gap-2 qa-cursor-pointer">
                <input type="checkbox" id="env-auto-deploy" class="qa-checkbox" />
                <span>Auto-deploy on push</span>
              </label>
              <label class="qa-flex qa-items-center qa-gap-2 qa-cursor-pointer">
                <input type="checkbox" id="env-requires-approval" class="qa-checkbox" />
                <span>Requires approval</span>
              </label>
            </div>
          </form>
        </div>
        <div class="qa-modal-footer">
          <button class="qa-btn qa-btn-secondary" onclick="closeEnvironmentModal()">Cancel</button>
          <button class="qa-btn qa-btn-primary" onclick="saveEnvironment(event)">Save Environment</button>
        </div>
      </div>
    </div>

    <script>
    const PROJECT_ID = {project_id};

    // Tab switching
    function showTab(tabName) {{
      // Update tab buttons
      document.querySelectorAll('.qa-tab').forEach(t => t.classList.remove('active'));
      document.querySelector(`.qa-tab[data-tab="${{tabName}}"]`).classList.add('active');

      // Update tab content
      document.querySelectorAll('.qa-tab-content').forEach(c => c.classList.add('qa-hidden'));
      document.getElementById(`tab-${{tabName}}`).classList.remove('qa-hidden');
    }}

    // Datasource modal
    function openDatasourceModal(dsId = null) {{
      document.getElementById('datasource-modal').classList.remove('qa-hidden');
      document.getElementById('ds-id').value = dsId || '';

      if (dsId) {{
        document.getElementById('datasource-modal-title').textContent = 'Edit Datasource';
        // Load datasource data
        fetch(`/projects/${{PROJECT_ID}}/datasources`, {{
          headers: {{ 'Authorization': 'Bearer ' + localStorage.getItem('token') }}
        }})
        .then(r => r.json())
        .then(list => {{
          const ds = list.find(d => d.id === dsId);
          if (ds) {{
            document.getElementById('ds-name').value = ds.name;
            document.getElementById('ds-type').value = ds.type;
            document.getElementById('ds-connection-type').value = ds.connection_type;
            document.getElementById('ds-host').value = ds.host || '';
            document.getElementById('ds-port').value = ds.port || '';
            document.getElementById('ds-database').value = ds.database_name || '';
            document.getElementById('ds-username').value = ds.username || '';
            document.getElementById('ds-image').value = ds.image || '';
            toggleDsFields();
          }}
        }});
      }} else {{
        document.getElementById('datasource-modal-title').textContent = 'Add Datasource';
        document.getElementById('datasource-form').reset();
      }}
    }}

    function closeDatasourceModal() {{
      document.getElementById('datasource-modal').classList.add('qa-hidden');
    }}

    function toggleDsFields() {{
      const type = document.getElementById('ds-connection-type').value;
      document.getElementById('ds-direct-fields').classList.toggle('qa-hidden', type === 'docker');
      document.getElementById('ds-docker-fields').classList.toggle('qa-hidden', type === 'direct');
    }}

    function saveDatasource(e) {{
      e.preventDefault();
      const dsId = document.getElementById('ds-id').value;
      const data = {{
        name: document.getElementById('ds-name').value,
        type: document.getElementById('ds-type').value,
        connection_type: document.getElementById('ds-connection-type').value,
        host: document.getElementById('ds-host').value,
        port: parseInt(document.getElementById('ds-port').value) || null,
        database_name: document.getElementById('ds-database').value,
        username: document.getElementById('ds-username').value,
        password: document.getElementById('ds-password').value,
        image: document.getElementById('ds-image').value
      }};

      const method = dsId ? 'PUT' : 'POST';
      const url = dsId ? `/datasources/${{dsId}}` : `/projects/${{PROJECT_ID}}/datasources`;

      fetch(url, {{
        method: method,
        headers: {{
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + localStorage.getItem('token')
        }},
        body: JSON.stringify(data)
      }})
      .then(r => {{
        if (r.ok) {{
          closeDatasourceModal();
          htmx.trigger('#datasources-list', 'load');
        }} else {{
          r.json().then(d => alert(d.detail || 'Error saving datasource'));
        }}
      }});
    }}

    function deleteDatasource(dsId, dsName) {{
      if (!confirm(`Delete datasource "${{dsName}}"? This cannot be undone.`)) return;

      fetch(`/datasources/${{dsId}}`, {{
        method: 'DELETE',
        headers: {{ 'Authorization': 'Bearer ' + localStorage.getItem('token') }}
      }})
      .then(r => {{
        if (r.ok) {{
          htmx.trigger('#datasources-list', 'load');
        }} else {{
          alert('Error deleting datasource');
        }}
      }});
    }}

    function startDatasource(dsId) {{
      fetch(`/datasources/${{dsId}}/start`, {{
        method: 'POST',
        headers: {{ 'Authorization': 'Bearer ' + localStorage.getItem('token') }}
      }})
      .then(r => r.json())
      .then(d => {{
        if (d.status === 'running') {{
          htmx.trigger('#datasources-list', 'load');
        }} else {{
          alert(d.message || 'Error starting datasource');
        }}
      }});
    }}

    function stopDatasource(dsId) {{
      fetch(`/datasources/${{dsId}}/stop`, {{
        method: 'POST',
        headers: {{ 'Authorization': 'Bearer ' + localStorage.getItem('token') }}
      }})
      .then(r => r.json())
      .then(d => {{
        htmx.trigger('#datasources-list', 'load');
      }});
    }}

    function viewDatasourceLogs(dsId, dsName) {{
      // Open a modal with logs
      const modal = document.createElement('div');
      modal.className = 'qa-modal';
      modal.id = 'logs-modal';
      modal.innerHTML = `
        <div class="qa-modal-backdrop" onclick="document.getElementById('logs-modal').remove()"></div>
        <div class="qa-modal-content" style="max-width: 900px; max-height: 80vh;">
          <div class="qa-modal-header">
            <h3 class="qa-modal-title">Logs: ${{dsName}}</h3>
            <button class="qa-modal-close" onclick="document.getElementById('logs-modal').remove()">&times;</button>
          </div>
          <div class="qa-modal-body" style="max-height: 60vh; overflow-y: auto;">
            <pre id="logs-content" class="qa-logs-container" style="background: #0d1117; color: #c9d1d9; padding: 16px; border-radius: 8px; font-family: monospace; font-size: 12px; white-space: pre-wrap; word-break: break-all;">Loading logs...</pre>
          </div>
          <div class="qa-modal-footer">
            <button class="qa-btn qa-btn-secondary" onclick="refreshLogs(${{dsId}})">Refresh</button>
            <button class="qa-btn qa-btn-primary" onclick="document.getElementById('logs-modal').remove()">Close</button>
          </div>
        </div>
      `;
      document.body.appendChild(modal);

      // Fetch logs
      refreshLogs(dsId);
    }}

    function refreshLogs(dsId) {{
      fetch(`/datasources/${{dsId}}/logs?tail=200`, {{
        headers: {{ 'Authorization': 'Bearer ' + localStorage.getItem('token') }}
      }})
      .then(r => r.json())
      .then(d => {{
        const logsEl = document.getElementById('logs-content');
        if (d.logs) {{
          logsEl.textContent = d.logs;
          logsEl.scrollTop = logsEl.scrollHeight;
        }} else if (d.error) {{
          logsEl.textContent = 'Error: ' + d.error;
        }}
      }})
      .catch(err => {{
        document.getElementById('logs-content').textContent = 'Error fetching logs: ' + err.message;
      }});
    }}

    function testDatasourceConnection(dsId) {{
      const btn = event.target.closest('button');
      const originalHTML = btn.innerHTML;
      btn.innerHTML = '<span class="qa-spinner qa-spinner-sm"></span>';
      btn.disabled = true;

      fetch(`/datasources/${{dsId}}/test`, {{
        method: 'POST',
        headers: {{ 'Authorization': 'Bearer ' + localStorage.getItem('token') }}
      }})
      .then(r => r.json())
      .then(d => {{
        btn.innerHTML = originalHTML;
        btn.disabled = false;
        if (d.success) {{
          showToast(`Connection successful! ${{d.version || ''}}`, 'success');
        }} else {{
          showToast(`Connection failed: ${{d.error}}`, 'error');
        }}
      }})
      .catch(err => {{
        btn.innerHTML = originalHTML;
        btn.disabled = false;
        showToast('Error testing connection', 'error');
      }});
    }}

    // =========================================================================
    // Environment Functions
    // =========================================================================

    function createDefaultEnvs(projectId) {{
      const pid = projectId || PROJECT_ID;
      fetch(`/projects/${{pid}}/environments/defaults`, {{
        method: 'POST',
        headers: {{ 'Authorization': 'Bearer ' + localStorage.getItem('token') }}
      }})
      .then(r => {{
        if (r.ok) {{
          htmx.trigger('#environments-list', 'load');
        }} else {{
          r.json().then(d => alert(d.detail || 'Error creating environments'));
        }}
      }});
    }}

    function openEnvironmentModal(envId = null) {{
      document.getElementById('environment-modal').classList.remove('qa-hidden');
      document.getElementById('env-id').value = envId || '';

      if (envId) {{
        document.getElementById('environment-modal-title').textContent = 'Edit Environment';
        // Load environment data
        fetch(`/projects/${{PROJECT_ID}}/environments/${{envId}}`, {{
          headers: {{ 'Authorization': 'Bearer ' + localStorage.getItem('token') }}
        }})
        .then(r => r.json())
        .then(env => {{
          document.getElementById('env-name').value = env.name || '';
          document.getElementById('env-display-name').value = env.display_name || '';
          document.getElementById('env-order').value = env.order || 1;
          document.getElementById('env-branch').value = env.branch || 'main';
          document.getElementById('env-docker-host').value = env.docker_host || '';
          document.getElementById('env-docker-registry').value = env.docker_registry || '';
          document.getElementById('env-container-name').value = env.container_name || '';
          document.getElementById('env-port').value = env.port || '';
          document.getElementById('env-deploy-path').value = env.deploy_path || '';
          document.getElementById('env-health-url').value = env.health_url || '';
          document.getElementById('env-auto-deploy').checked = env.auto_deploy || false;
          document.getElementById('env-requires-approval').checked = env.requires_approval || false;
        }});
      }} else {{
        document.getElementById('environment-modal-title').textContent = 'Add Environment';
        document.getElementById('environment-form').reset();
        document.getElementById('env-order').value = '1';
        document.getElementById('env-branch').value = 'main';
      }}
    }}

    function closeEnvironmentModal() {{
      document.getElementById('environment-modal').classList.add('qa-hidden');
    }}

    function editEnvironment(envId) {{
      openEnvironmentModal(envId);
    }}

    function saveEnvironment(e) {{
      e.preventDefault();
      const envId = document.getElementById('env-id').value;
      const data = {{
        name: document.getElementById('env-name').value,
        display_name: document.getElementById('env-display-name').value,
        order: parseInt(document.getElementById('env-order').value) || 1,
        branch: document.getElementById('env-branch').value,
        docker_host: document.getElementById('env-docker-host').value,
        docker_registry: document.getElementById('env-docker-registry').value,
        container_name: document.getElementById('env-container-name').value,
        port: parseInt(document.getElementById('env-port').value) || null,
        deploy_path: document.getElementById('env-deploy-path').value,
        health_url: document.getElementById('env-health-url').value,
        auto_deploy: document.getElementById('env-auto-deploy').checked,
        requires_approval: document.getElementById('env-requires-approval').checked
      }};

      const method = envId ? 'PUT' : 'POST';
      const url = envId
        ? `/projects/${{PROJECT_ID}}/environments/${{envId}}`
        : `/projects/${{PROJECT_ID}}/environments`;

      fetch(url, {{
        method: method,
        headers: {{
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + localStorage.getItem('token')
        }},
        body: JSON.stringify(data)
      }})
      .then(r => {{
        if (r.ok) {{
          closeEnvironmentModal();
          htmx.trigger('#environments-list', 'load');
        }} else {{
          r.json().then(d => alert(d.detail || 'Error saving environment'));
        }}
      }});
    }}

    function deleteEnvironment(envId, envName) {{
      if (!confirm(`Delete environment "${{envName}}"? This cannot be undone.`)) return;

      fetch(`/projects/${{PROJECT_ID}}/environments/${{envId}}`, {{
        method: 'DELETE',
        headers: {{ 'Authorization': 'Bearer ' + localStorage.getItem('token') }}
      }})
      .then(r => {{
        if (r.ok) {{
          htmx.trigger('#environments-list', 'load');
        }} else {{
          alert('Error deleting environment');
        }}
      }});
    }}

    function testEnvironment(envId) {{
      const btn = event.target.closest('button');
      const originalText = btn.innerHTML;
      btn.innerHTML = '<span class="qa-spinner"></span> Testing...';
      btn.disabled = true;

      fetch(`/projects/${{PROJECT_ID}}/environments/${{envId}}/test`, {{
        method: 'POST',
        headers: {{ 'Authorization': 'Bearer ' + localStorage.getItem('token') }}
      }})
      .then(r => r.json())
      .then(result => {{
        btn.innerHTML = originalText;
        btn.disabled = false;
        if (result.success) {{
          alert(`Connection successful!\\n\\nDocker: ${{result.docker_version}}\\nContainers: ${{result.containers}}\\nOS: ${{result.os}}`);
        }} else {{
          alert(`Connection failed: ${{result.error}}`);
        }}
      }})
      .catch(err => {{
        btn.innerHTML = originalText;
        btn.disabled = false;
        alert('Error testing connection');
      }});
    }}

    function deployToEnvironment(envId) {{
      if (!confirm('Start deployment to this environment?')) return;

      // Redirect to deploy page with pre-selected environment
      window.location.href = `/admin/deploy?project=${{PROJECT_ID}}&env=${{envId}}`;
    }}

    function launchApp(projectId, envId, envName) {{
      const btn = event.target.closest('button');
      const originalText = btn.innerHTML;
      btn.innerHTML = '<span class="qa-spinner"></span> Launching...';
      btn.disabled = true;

      fetch(`/projects/${{projectId}}/environments/${{envId}}/launch`, {{
        method: 'POST',
        headers: {{
          'Authorization': 'Bearer ' + localStorage.getItem('token'),
          'Content-Type': 'application/json'
        }}
      }})
      .then(r => r.json())
      .then(result => {{
        btn.innerHTML = originalText;
        btn.disabled = false;
        if (result.success) {{
          // Open the app in a new tab
          const appUrl = result.url;
          window.open(appUrl, '_blank');
          showToast(`Application launched on ${{envName}}`, 'success');
        }} else {{
          showToast(`Failed to launch: ${{result.error}}`, 'error');
        }}
      }})
      .catch(err => {{
        btn.innerHTML = originalText;
        btn.disabled = false;
        showToast('Error launching application', 'error');
      }});
    }}
    </script>
    '''


def get_deploy_content():
    return '''
    <!-- Project Selection -->
    <div class="qa-card qa-mb-6">
      <div class="qa-card-header">
        <h3 class="qa-card-title">Select Application</h3>
      </div>
      <div class="qa-card-body">
        <select id="project-select" class="qa-input qa-select" onchange="loadEnvironments(this.value)" style="max-width: 400px;">
          <option value="">Select an application...</option>
        </select>
      </div>
    </div>

    <!-- Environments Grid -->
    <div id="environments-section" class="qa-hidden">
      <div class="qa-section-header qa-mb-4">
        <h3 class="qa-section-title">Environments</h3>
        <button class="qa-btn qa-btn-secondary" onclick="openEnvModal()">
          <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
          Add Environment
        </button>
      </div>
      <div id="environments-grid" class="qa-grid qa-grid-3 qa-gap-4 qa-mb-6">
        <!-- Environments loaded dynamically -->
      </div>
    </div>

    <!-- Active Deployment -->
    <div id="active-deploy-section" class="qa-hidden qa-mb-6">
      <div class="qa-card">
        <div class="qa-card-header">
          <h3 class="qa-card-title">
            <span id="deploy-title">Deployment</span>
            <span id="deploy-id" class="qa-badge qa-ml-2"></span>
          </h3>
          <button id="cancel-deploy-btn" class="qa-btn qa-btn-danger qa-btn-sm" onclick="cancelDeploy()">Cancel</button>
        </div>
        <div class="qa-card-body">
          <!-- Pipeline Steps -->
          <div class="qa-pipeline-steps qa-mb-4">
            <div class="qa-pipeline-step" data-step="git_pull">
              <div class="qa-pipeline-step-icon">
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/></svg>
              </div>
              <span class="qa-pipeline-step-label">Git Pull</span>
            </div>
            <div class="qa-pipeline-connector"></div>
            <div class="qa-pipeline-step" data-step="build">
              <div class="qa-pipeline-step-icon">
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
              </div>
              <span class="qa-pipeline-step-label">Build</span>
            </div>
            <div class="qa-pipeline-connector"></div>
            <div class="qa-pipeline-step" data-step="test">
              <div class="qa-pipeline-step-icon">
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              </div>
              <span class="qa-pipeline-step-label">Test</span>
            </div>
            <div class="qa-pipeline-connector"></div>
            <div class="qa-pipeline-step" data-step="push">
              <div class="qa-pipeline-step-icon">
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>
              </div>
              <span class="qa-pipeline-step-label">Push</span>
            </div>
            <div class="qa-pipeline-connector"></div>
            <div class="qa-pipeline-step" data-step="deploy">
              <div class="qa-pipeline-step-icon">
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2"/></svg>
              </div>
              <span class="qa-pipeline-step-label">Deploy</span>
            </div>
            <div class="qa-pipeline-connector"></div>
            <div class="qa-pipeline-step" data-step="health">
              <div class="qa-pipeline-step-icon">
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/></svg>
              </div>
              <span class="qa-pipeline-step-label">Health</span>
            </div>
          </div>

          <!-- Live Logs -->
          <div class="qa-card" style="background: var(--q-bg-tertiary);">
            <div class="qa-card-header">
              <span class="qa-text-sm qa-text-muted">Live Logs</span>
              <button class="qa-btn qa-btn-ghost qa-btn-sm" onclick="clearLogs()">Clear</button>
            </div>
            <div id="deploy-logs" class="qa-code-block" style="height: 300px; overflow-y: auto; font-family: monospace; font-size: 12px; padding: 12px;">
              <div class="qa-text-muted">Waiting for deployment to start...</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Version History -->
    <div id="versions-section" class="qa-hidden">
      <div class="qa-card">
        <div class="qa-card-header">
          <h3 class="qa-card-title">Version History</h3>
          <select id="env-filter" class="qa-input qa-select" style="width: 160px;" onchange="loadVersions()">
            <option value="">All Environments</option>
          </select>
        </div>
        <div id="versions-list" class="qa-card-body">
          <div class="qa-text-center qa-text-muted qa-p-4">Select a project to view versions</div>
        </div>
      </div>
    </div>

    <!-- Add/Edit Environment Modal -->
    <div id="env-modal" class="qa-modal-overlay">
      <div class="qa-modal">
        <div class="qa-modal-header">
          <h3 id="env-modal-title" class="qa-modal-title">Add Environment</h3>
          <button class="qa-modal-close" onclick="closeEnvModal()">
            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="qa-modal-body">
          <form id="env-form" onsubmit="saveEnvironment(event)">
            <input type="hidden" name="env_id" id="env-id" />
            <div class="qa-form-row">
              <div class="qa-form-group">
                <label class="qa-label">Name</label>
                <input type="text" name="name" class="qa-input" placeholder="production, staging, dev" required />
              </div>
              <div class="qa-form-group">
                <label class="qa-label">Display Name</label>
                <input type="text" name="display_name" class="qa-input" placeholder="Production Server" />
              </div>
            </div>
            <div class="qa-form-row">
              <div class="qa-form-group">
                <label class="qa-label">Git Branch</label>
                <input type="text" name="branch" class="qa-input" value="main" />
              </div>
              <div class="qa-form-group">
                <label class="qa-label">Port</label>
                <input type="number" name="port" class="qa-input" value="8000" />
              </div>
            </div>
            <div class="qa-form-group">
              <label class="qa-label">Docker Host</label>
              <input type="text" name="docker_host" class="qa-input" placeholder="ssh://user@host or unix://" />
            </div>
            <div class="qa-form-group">
              <label class="qa-label">Health Check URL</label>
              <input type="text" name="health_url" class="qa-input" placeholder="http://localhost:8000/health" />
            </div>
            <div class="qa-form-row">
              <label class="qa-checkbox-group">
                <input type="checkbox" name="auto_deploy" class="qa-checkbox" />
                <span>Auto-deploy on push</span>
              </label>
              <label class="qa-checkbox-group">
                <input type="checkbox" name="requires_approval" class="qa-checkbox" />
                <span>Requires approval</span>
              </label>
            </div>
          </form>
        </div>
        <div class="qa-modal-footer">
          <button type="button" class="qa-btn qa-btn-ghost" onclick="closeEnvModal()">Cancel</button>
          <button type="button" class="qa-btn qa-btn-secondary" onclick="testEnvConnection()">Test Connection</button>
          <button type="button" class="qa-btn qa-btn-primary" onclick="document.getElementById('env-form').requestSubmit()">Save</button>
        </div>
      </div>
    </div>

    <style>
      .qa-pipeline-steps {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 20px 0;
      }
      .qa-pipeline-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
      }
      .qa-pipeline-step-icon {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: var(--q-bg-overlay);
        border: 2px solid var(--q-border);
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--q-text-dim);
        transition: all 0.3s;
      }
      .qa-pipeline-step.running .qa-pipeline-step-icon {
        border-color: var(--q-info);
        color: var(--q-info);
        animation: pulse 1.5s infinite;
      }
      .qa-pipeline-step.completed .qa-pipeline-step-icon {
        border-color: var(--q-success);
        background: var(--q-success);
        color: white;
      }
      .qa-pipeline-step.failed .qa-pipeline-step-icon {
        border-color: var(--q-danger);
        background: var(--q-danger);
        color: white;
      }
      .qa-pipeline-step-label {
        font-size: 12px;
        color: var(--q-text-secondary);
      }
      .qa-pipeline-connector {
        flex: 1;
        height: 2px;
        background: var(--q-border);
        margin: 0 8px;
        margin-bottom: 24px;
      }
      .qa-pipeline-connector.active {
        background: var(--q-success);
      }
      .qa-env-card {
        background: var(--q-bg-secondary);
        border: 1px solid var(--q-border);
        border-radius: 12px;
        padding: 20px;
        position: relative;
      }
      .qa-env-card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 16px;
      }
      .qa-env-card-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--q-text-primary);
      }
      .qa-env-card-branch {
        font-size: 13px;
        color: var(--q-text-secondary);
        font-family: monospace;
      }
      .qa-env-card-badges {
        display: flex;
        gap: 4px;
      }
      .qa-env-card-version {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        background: var(--q-bg-overlay);
        border-radius: 8px;
        margin-bottom: 16px;
      }
      .qa-env-card-actions {
        display: flex;
        gap: 8px;
      }
      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
      }
      .qa-log-line {
        padding: 2px 0;
        border-bottom: 1px solid var(--q-border);
      }
      .qa-log-line.info { color: var(--q-text-secondary); }
      .qa-log-line.success { color: var(--q-success); }
      .qa-log-line.warning { color: var(--q-warning); }
      .qa-log-line.error { color: var(--q-danger); }
      .qa-log-timestamp {
        color: var(--q-text-dim);
        margin-right: 8px;
      }
    </style>

    <script>
      let currentProjectId = null;
      let currentDeployId = null;
      let deployWs = null;
      let environments = [];

      // Load projects on page load
      document.addEventListener('DOMContentLoaded', function() {
        loadProjects();
      });

      async function loadProjects() {
        try {
          const res = await fetch('{URL_PREFIX}/projects');
          const projects = await res.json();
          const select = document.getElementById('project-select');
          select.innerHTML = '<option value="">Select an application...</option>';
          projects.forEach(p => {
            select.innerHTML += `<option value="${p.id}">${p.name}</option>`;
          });
        } catch (e) {
          console.error('Failed to load projects:', e);
        }
      }

      async function loadEnvironments(projectId) {
        if (!projectId) {
          document.getElementById('environments-section').classList.add('qa-hidden');
          document.getElementById('versions-section').classList.add('qa-hidden');
          return;
        }

        currentProjectId = projectId;
        document.getElementById('environments-section').classList.remove('qa-hidden');
        document.getElementById('versions-section').classList.remove('qa-hidden');

        try {
          const res = await fetch(`/projects/${projectId}/environments`);
          environments = await res.json();
          renderEnvironments();
          updateEnvFilter();
          loadVersions();
        } catch (e) {
          console.error('Failed to load environments:', e);
        }
      }

      function renderEnvironments() {
        const grid = document.getElementById('environments-grid');

        if (environments.length === 0) {
          grid.innerHTML = `
            <div class="qa-text-center qa-text-muted qa-p-6" style="grid-column: span 3;">
              <p class="qa-mb-4">No environments configured</p>
              <button class="qa-btn qa-btn-primary" onclick="createDefaultEnvs()">Create Default Environments</button>
            </div>
          `;
          return;
        }

        grid.innerHTML = environments.map(env => `
          <div class="qa-env-card">
            <div class="qa-env-card-header">
              <div>
                <div class="qa-env-card-title">${env.display_name || env.name}</div>
                <div class="qa-env-card-branch">Branch: ${env.branch}</div>
              </div>
              <div class="qa-env-card-badges">
                ${env.auto_deploy ? '<span class="qa-badge qa-badge-info">Auto</span>' : ''}
                ${env.requires_approval ? '<span class="qa-badge qa-badge-warning">Approval</span>' : ''}
              </div>
            </div>
            <div class="qa-env-card-version">
              <span class="qa-connector-status-dot connected"></span>
              <span class="qa-font-mono qa-text-sm">v${env.current_version || 'Not deployed'}</span>
            </div>
            <div class="qa-env-card-actions">
              <button class="qa-btn qa-btn-primary qa-btn-sm qa-flex-1" onclick="startDeploy(${env.id}, '${env.display_name || env.name}')">
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>
                Deploy
              </button>
              <button class="qa-btn qa-btn-ghost qa-btn-sm" onclick="editEnvironment(${env.id})">
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/></svg>
              </button>
            </div>
          </div>
        `).join('');
      }

      async function startDeploy(envId, envName) {
        if (!currentProjectId) return;

        try {
          const res = await fetch('{URL_PREFIX}/deploy/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `project_id=${currentProjectId}&environment_id=${envId}`
          });
          const data = await res.json();

          if (data.success) {
            currentDeployId = data.deployment_id;
            showDeployPanel(envName, currentDeployId);
            connectWebSocket(currentDeployId);
          } else {
            showToast('Failed to start deployment', 'error');
          }
        } catch (e) {
          showToast('Error: ' + e.message, 'error');
        }
      }

      function showDeployPanel(envName, deployId) {
        document.getElementById('active-deploy-section').classList.remove('qa-hidden');
        document.getElementById('deploy-title').textContent = `Deploying to ${envName}`;
        document.getElementById('deploy-id').textContent = `#${deployId}`;
        document.getElementById('deploy-logs').innerHTML = '';

        // Reset pipeline steps
        document.querySelectorAll('.qa-pipeline-step').forEach(step => {
          step.classList.remove('running', 'completed', 'failed');
        });
        document.querySelectorAll('.qa-pipeline-connector').forEach(conn => {
          conn.classList.remove('active');
        });
      }

      function connectWebSocket(deployId) {
        if (deployWs) {
          deployWs.close();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        deployWs = new WebSocket(`${protocol}//${window.location.host}/ws/deploy/${deployId}/logs`);

        deployWs.onmessage = function(event) {
          const msg = JSON.parse(event.data);
          handleDeployMessage(msg);
        };

        deployWs.onclose = function() {
          console.log('WebSocket closed');
        };
      }

      function handleDeployMessage(msg) {
        if (msg.type === 'log') {
          addLogLine(msg.data);
        } else if (msg.type === 'status') {
          updatePipelineStep(msg.data.step, 'running');
        } else if (msg.type === 'step_complete') {
          updatePipelineStep(msg.data.step, msg.data.success ? 'completed' : 'failed');
        } else if (msg.type === 'complete') {
          if (msg.data.success) {
            showToast('Deployment completed successfully!', 'success');
          } else {
            showToast('Deployment failed: ' + msg.data.message, 'error');
          }
          document.getElementById('cancel-deploy-btn').classList.add('qa-hidden');
          loadVersions();
        }
      }

      function addLogLine(log) {
        const logsDiv = document.getElementById('deploy-logs');
        const line = document.createElement('div');
        line.className = 'qa-log-line ' + log.level;

        const time = new Date(log.timestamp).toLocaleTimeString();
        line.innerHTML = `<span class="qa-log-timestamp">[${time}]</span>${log.message}`;

        logsDiv.appendChild(line);
        logsDiv.scrollTop = logsDiv.scrollHeight;
      }

      function updatePipelineStep(step, status) {
        const stepEl = document.querySelector(`.qa-pipeline-step[data-step="${step}"]`);
        if (stepEl) {
          stepEl.classList.remove('running', 'completed', 'failed');
          stepEl.classList.add(status);
        }
      }

      function clearLogs() {
        document.getElementById('deploy-logs').innerHTML = '';
      }

      async function cancelDeploy() {
        if (!currentDeployId) return;

        try {
          await fetch(`/deploy/pipeline/${currentDeployId}/cancel`, { method: 'POST' });
          showToast('Deployment cancelled', 'warning');
        } catch (e) {
          showToast('Failed to cancel', 'error');
        }
      }

      function updateEnvFilter() {
        const select = document.getElementById('env-filter');
        select.innerHTML = '<option value="">All Environments</option>';
        environments.forEach(env => {
          select.innerHTML += `<option value="${env.id}">${env.display_name || env.name}</option>`;
        });
      }

      async function loadVersions() {
        if (!currentProjectId) return;

        const envId = document.getElementById('env-filter').value;
        let url = `/projects/${currentProjectId}/versions?limit=10`;
        if (envId) url += `&environment_id=${envId}`;

        try {
          const res = await fetch(url);
          const versions = await res.json();
          renderVersions(versions);
        } catch (e) {
          console.error('Failed to load versions:', e);
        }
      }

      function renderVersions(versions) {
        const list = document.getElementById('versions-list');

        if (versions.length === 0) {
          list.innerHTML = '<div class="qa-text-center qa-text-muted qa-p-4">No deployments yet</div>';
          return;
        }

        list.innerHTML = versions.map((v, i) => `
          <div class="qa-flex qa-justify-between qa-items-center qa-p-3 ${i > 0 ? 'qa-border-top' : ''}">
            <div class="qa-flex qa-items-center qa-gap-3">
              <span class="qa-connector-status-dot ${v.is_current ? 'connected' : ''}"></span>
              <div>
                <span class="qa-font-mono qa-text-sm">${v.git_commit ? v.git_commit.substring(0, 7) : v.docker_tag || 'unknown'}</span>
                ${v.is_current ? '<span class="qa-badge qa-badge-success qa-ml-2">Current</span>' : ''}
              </div>
            </div>
            <div class="qa-flex qa-items-center qa-gap-4">
              <span class="qa-text-sm qa-text-muted">${v.git_message ? v.git_message.substring(0, 40) : ''}</span>
              <span class="qa-text-xs qa-text-dim">${new Date(v.created_at).toLocaleString()}</span>
              ${!v.is_current ? `<button class="qa-btn qa-btn-ghost qa-btn-sm" onclick="rollbackToVersion(${v.id})">Rollback</button>` : ''}
            </div>
          </div>
        `).join('');
      }

      async function rollbackToVersion(versionId) {
        // Need to get the current deployment ID first
        showToast('Rollback feature coming soon', 'info');
      }

      async function createDefaultEnvs() {
        if (!currentProjectId) return;

        try {
          const res = await fetch(`/projects/${currentProjectId}/environments/defaults`, { method: 'POST' });
          if (res.ok) {
            showToast('Default environments created', 'success');
            loadEnvironments(currentProjectId);
          }
        } catch (e) {
          showToast('Failed to create environments', 'error');
        }
      }

      function openEnvModal(envId = null) {
        document.getElementById('env-modal').classList.add('active');
        document.getElementById('env-modal-title').textContent = envId ? 'Edit Environment' : 'Add Environment';
        document.getElementById('env-id').value = envId || '';

        if (envId) {
          const env = environments.find(e => e.id === envId);
          if (env) {
            const form = document.getElementById('env-form');
            form.querySelector('[name="name"]').value = env.name;
            form.querySelector('[name="display_name"]').value = env.display_name || '';
            form.querySelector('[name="branch"]').value = env.branch || 'main';
            form.querySelector('[name="port"]').value = env.port || 8000;
            form.querySelector('[name="docker_host"]').value = env.docker_host || '';
            form.querySelector('[name="health_url"]').value = env.health_url || '';
            form.querySelector('[name="auto_deploy"]').checked = env.auto_deploy;
            form.querySelector('[name="requires_approval"]').checked = env.requires_approval;
          }
        } else {
          document.getElementById('env-form').reset();
          document.getElementById('env-form').querySelector('[name="branch"]').value = 'main';
          document.getElementById('env-form').querySelector('[name="port"]').value = 8000;
        }
      }

      function closeEnvModal() {
        document.getElementById('env-modal').classList.remove('active');
      }

      function editEnvironment(envId) {
        openEnvModal(envId);
      }

      async function saveEnvironment(e) {
        e.preventDefault();
        const form = e.target;
        const envId = document.getElementById('env-id').value;
        const data = Object.fromEntries(new FormData(form));
        data.auto_deploy = form.querySelector('[name="auto_deploy"]').checked;
        data.requires_approval = form.querySelector('[name="requires_approval"]').checked;
        data.port = parseInt(data.port) || 8000;

        const url = envId
          ? `/projects/${currentProjectId}/environments/${envId}`
          : `/projects/${currentProjectId}/environments`;
        const method = envId ? 'PUT' : 'POST';

        try {
          const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
          });

          if (res.ok) {
            closeEnvModal();
            loadEnvironments(currentProjectId);
            showToast(envId ? 'Environment updated' : 'Environment created', 'success');
          } else {
            const err = await res.json();
            showToast('Error: ' + (err.detail || 'Failed to save'), 'error');
          }
        } catch (e) {
          showToast('Error: ' + e.message, 'error');
        }
      }

      async function testEnvConnection() {
        const host = document.getElementById('env-form').querySelector('[name="docker_host"]').value;
        if (!host) {
          showToast('Enter a Docker host first', 'warning');
          return;
        }

        showToast('Testing connection...', 'info');

        const envId = document.getElementById('env-id').value;
        if (envId) {
          try {
            const res = await fetch(`/projects/${currentProjectId}/environments/${envId}/test`, { method: 'POST' });
            const result = await res.json();
            if (result.success) {
              showToast(`Connected! Docker ${result.docker_version}`, 'success');
            } else {
              showToast('Connection failed: ' + result.error, 'error');
            }
          } catch (e) {
            showToast('Test failed: ' + e.message, 'error');
          }
        } else {
          showToast('Save the environment first to test', 'warning');
        }
      }
    </script>
    '''


def get_settings_content():
    return '''
    <div class="qa-tabs">
      <button class="qa-tab active" onclick="showSettingsTab('server')">Server</button>
      <button class="qa-tab" onclick="showSettingsTab('docker')">Docker</button>
      <button class="qa-tab" onclick="showSettingsTab('connectors')">Connectors</button>
      <button class="qa-tab" onclick="showSettingsTab('cloud')">Cloud</button>
      <button class="qa-tab" onclick="showSettingsTab('email')">Email</button>
      <button class="qa-tab" onclick="showSettingsTab('security')">Security</button>
    </div>

    <!-- Server Tab -->
    <div id="settings-server" class="qa-tab-panel active">
      <div class="qa-card">
        <div class="qa-card-header"><h3 class="qa-card-title">Server Configuration</h3></div>
        <div class="qa-card-body">
          <div class="qa-form-row">
            <div class="qa-form-group"><label class="qa-label">Port</label><input type="number" class="qa-input" value="8001" /><p class="qa-input-hint">Server port</p></div>
            <div class="qa-form-group"><label class="qa-label">Host</label><input type="text" class="qa-input" value="0.0.0.0" /><p class="qa-input-hint">Bind address</p></div>
          </div>
          <div class="qa-form-row">
            <div class="qa-form-group"><label class="qa-label">Debug Mode</label><select class="qa-input qa-select"><option value="false">Disabled</option><option value="true">Enabled</option></select></div>
            <div class="qa-form-group"><label class="qa-label">Auto Reload</label><select class="qa-input qa-select"><option value="true">Enabled</option><option value="false">Disabled</option></select></div>
          </div>
        </div>
        <div class="qa-card-footer qa-flex qa-justify-end"><button class="qa-btn qa-btn-primary">Save Server Settings</button></div>
      </div>
    </div>

    <!-- Docker Tab -->
    <div id="settings-docker" class="qa-tab-panel">
      <div class="qa-card">
        <div class="qa-card-header"><h3 class="qa-card-title">Docker Configuration</h3></div>
        <div class="qa-card-body">
          <div class="qa-form-group"><label class="qa-label">Docker Host</label><input type="text" class="qa-input" value="ssh://abathur@10.10.1.40" /><p class="qa-input-hint">SSH or TCP connection</p></div>
          <div class="qa-form-row">
            <div class="qa-form-group"><label class="qa-label">Registry</label><input type="text" class="qa-input" placeholder="registry.example.com:5000" /></div>
            <div class="qa-form-group"><label class="qa-label">Timeout (seconds)</label><input type="number" class="qa-input" value="30" /></div>
          </div>
        </div>
        <div class="qa-card-footer qa-flex qa-justify-end qa-gap-2">
          <button class="qa-btn qa-btn-secondary" hx-post="{URL_PREFIX}/docker/connect?host=ssh://abathur@10.10.1.40" hx-swap="none">Test Connection</button>
          <button class="qa-btn qa-btn-primary">Save Docker Settings</button>
        </div>
      </div>
    </div>

    <!-- Connectors Tab -->
    <div id="settings-connectors" class="qa-tab-panel">
      <div class="qa-section-header">
        <div>
          <h3 class="qa-section-title">Infrastructure Connectors</h3>
          <p class="qa-section-subtitle">Manage connections to databases, caches, message queues, storage, and AI providers</p>
        </div>
        <button class="qa-btn qa-btn-primary" onclick="openConnectorModal()">
          <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
          Add Connector
        </button>
      </div>

      <!-- Connector Type Filters -->
      <div class="qa-subtabs">
        <button class="qa-subtab active" onclick="showConnectorType('all')" data-type="all">All</button>
        <button class="qa-subtab" onclick="showConnectorType('database')" data-type="database">
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"/></svg>
          Databases
        </button>
        <button class="qa-subtab" onclick="showConnectorType('mq')" data-type="mq">
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>
          Queues
        </button>
        <button class="qa-subtab" onclick="showConnectorType('cache')" data-type="cache">
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
          Cache
        </button>
        <button class="qa-subtab" onclick="showConnectorType('storage')" data-type="storage">
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/></svg>
          Storage
        </button>
        <button class="qa-subtab" onclick="showConnectorType('ai')" data-type="ai">
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
          AI
        </button>
      </div>

      <!-- Connectors Grid -->
      <div id="connectors-grid" class="qa-grid qa-grid-3" hx-get="{URL_PREFIX}/settings/connectors" hx-trigger="load" hx-swap="innerHTML">
        <div class="qa-text-center qa-text-muted qa-p-6" style="grid-column: span 3;">Loading connectors...</div>
      </div>
    </div>

    <!-- Add/Edit Connector Modal -->
    <div id="connector-modal" class="qa-modal-overlay">
      <div class="qa-modal qa-modal-lg">
        <div class="qa-modal-header">
          <h3 id="connector-modal-title" class="qa-modal-title">Add Connector</h3>
          <button class="qa-modal-close" onclick="closeConnectorModal()"><svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg></button>
        </div>
        <div class="qa-modal-body">
          <form id="connector-form" onsubmit="saveConnector(event)">
            <div class="qa-form-group">
              <label class="qa-label">Name</label>
              <input type="text" name="name" class="qa-input" placeholder="e.g., Production Database, Dev Redis" required />
            </div>

            <div class="qa-form-row">
              <div class="qa-form-group">
                <label class="qa-label">Type</label>
                <select name="type" class="qa-input qa-select" onchange="updateProviderOptions(this.value)" required>
                  <option value="">Select type...</option>
                  <option value="database">Database</option>
                  <option value="mq">Message Queue</option>
                  <option value="cache">Cache</option>
                  <option value="storage">Storage</option>
                  <option value="ai">AI Provider</option>
                </select>
              </div>
              <div class="qa-form-group">
                <label class="qa-label">Provider</label>
                <select name="provider" class="qa-input qa-select" onchange="updateProviderDefaults(this.value)" required>
                  <option value="">Select provider...</option>
                </select>
              </div>
            </div>

            <div class="qa-form-row">
              <div class="qa-form-group">
                <label class="qa-label">Host</label>
                <input type="text" name="host" class="qa-input" value="localhost" />
              </div>
              <div class="qa-form-group">
                <label class="qa-label">Port</label>
                <input type="number" name="port" class="qa-input" />
              </div>
            </div>

            <div class="qa-form-row" id="auth-fields">
              <div class="qa-form-group">
                <label class="qa-label">Username</label>
                <input type="text" name="username" class="qa-input" />
              </div>
              <div class="qa-form-group">
                <label class="qa-label">Password / API Key</label>
                <input type="password" name="password" class="qa-input" />
              </div>
            </div>

            <div class="qa-form-group" id="database-field">
              <label class="qa-label">Database / Bucket</label>
              <input type="text" name="database" class="qa-input" placeholder="e.g., mydb, my-bucket" />
            </div>

            <div class="qa-card qa-mb-4" style="background: var(--q-bg-overlay);">
              <div class="qa-card-body">
                <label class="qa-checkbox-group" style="cursor: pointer;">
                  <input type="checkbox" name="docker_auto" class="qa-checkbox" onchange="toggleDockerOptions(this.checked)" />
                  <span class="qa-font-medium">Enable Docker Auto-Provision</span>
                </label>
                <p class="qa-text-xs qa-text-muted qa-mt-2">Automatically start a Docker container for this connection</p>
                <div id="docker-options" class="qa-hidden qa-mt-4">
                  <label class="qa-label">Docker Image</label>
                  <input type="text" name="docker_image" class="qa-input" placeholder="e.g., postgres:16-alpine" />
                </div>
              </div>
            </div>

            <!-- Scope Selection -->
            <div class="qa-card qa-mb-4" style="background: var(--q-bg-overlay);">
              <div class="qa-card-body">
                <label class="qa-label">Scope</label>
                <div class="qa-radio-group qa-mt-2">
                  <label class="qa-radio-option">
                    <input type="radio" name="scope" value="public" checked onchange="toggleApplicationSelect(false)" />
                    <span>Public (all apps)</span>
                  </label>
                  <label class="qa-radio-option">
                    <input type="radio" name="scope" value="application" onchange="toggleApplicationSelect(true)" />
                    <span>Application-specific</span>
                  </label>
                </div>
                <div id="application-select" class="qa-hidden qa-mt-4">
                  <label class="qa-label">Application</label>
                  <select name="application_id" class="qa-input qa-select" id="application-id-select">
                    <option value="">Select application...</option>
                  </select>
                </div>
              </div>
            </div>

            <label class="qa-checkbox-group" style="cursor: pointer;">
              <input type="checkbox" name="is_default" class="qa-checkbox" />
              <span>Set as default for this type</span>
            </label>
          </form>
        </div>
        <div class="qa-modal-footer">
          <button type="button" class="qa-btn qa-btn-ghost" onclick="closeConnectorModal()">Cancel</button>
          <button type="button" class="qa-btn qa-btn-secondary" onclick="testConnectorForm()">Test Connection</button>
          <button type="button" class="qa-btn qa-btn-primary" onclick="document.getElementById('connector-form').requestSubmit()">Save Connector</button>
        </div>
      </div>
    </div>

    <style>
      /* Legacy compatibility - will be removed */
      .connector-type-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 500;
        color: #64748b;
        background: white;
        border: 1px solid #e2e8f0;
        cursor: pointer;
        transition: all 0.15s;
      }
      .connector-type-btn:hover {
        background: #f1f5f9;
        color: #1e293b;
      }
      .connector-type-btn.active {
        background: #6366f1;
        color: white;
        border-color: #6366f1;
      }
    </style>

    <script>
      // Provider configurations
      const connectorProviders = {
        database: [
          { value: 'postgres', label: 'PostgreSQL', port: 5432, image: 'postgres:16-alpine' },
          { value: 'mysql', label: 'MySQL', port: 3306, image: 'mysql:8.0' },
          { value: 'mariadb', label: 'MariaDB', port: 3306, image: 'mariadb:11.2' },
          { value: 'mongodb', label: 'MongoDB', port: 27017, image: 'mongo:7.0' },
          { value: 'sqlite', label: 'SQLite', port: 0, image: null }
        ],
        mq: [
          { value: 'rabbitmq', label: 'RabbitMQ', port: 5672, image: 'rabbitmq:3-management' },
          { value: 'redis-queue', label: 'Redis Queue', port: 6379, image: 'redis:7-alpine' },
          { value: 'kafka', label: 'Apache Kafka', port: 9092, image: 'confluentinc/cp-kafka:7.5.0' }
        ],
        cache: [
          { value: 'redis', label: 'Redis', port: 6379, image: 'redis:7-alpine' },
          { value: 'memcached', label: 'Memcached', port: 11211, image: 'memcached:1.6-alpine' }
        ],
        storage: [
          { value: 's3', label: 'Amazon S3', port: 443, image: null },
          { value: 'minio', label: 'MinIO', port: 9000, image: 'minio/minio' },
          { value: 'local', label: 'Local Storage', port: 0, image: null }
        ],
        ai: [
          { value: 'ollama', label: 'Ollama', port: 11434, image: 'ollama/ollama' },
          { value: 'lmstudio', label: 'LM Studio', port: 1234, image: null },
          { value: 'anthropic', label: 'Anthropic (Claude)', port: 443, image: null },
          { value: 'openai', label: 'OpenAI', port: 443, image: null },
          { value: 'openrouter', label: 'OpenRouter', port: 443, image: null }
        ]
      };

      let editingConnectorId = null;
      let currentConnectorType = 'all';
      let applicationsCache = null;

      // Load applications list
      async function loadApplications() {
        if (applicationsCache) return applicationsCache;
        try {
          const res = await fetch('{URL_PREFIX}/projects');
          applicationsCache = await res.json();
          return applicationsCache;
        } catch (e) {
          console.error('Failed to load applications:', e);
          return [];
        }
      }

      function toggleApplicationSelect(show) {
        const el = document.getElementById('application-select');
        el.classList.toggle('qa-hidden', !show);
        if (show) {
          loadApplications().then(apps => {
            const select = document.getElementById('application-id-select');
            select.innerHTML = '<option value="">Select application...</option>';
            apps.forEach(app => {
              select.innerHTML += `<option value="${app.id}">${app.name}</option>`;
            });
          });
        }
      }

      function openConnectorModal(id = null) {
        editingConnectorId = id;
        const form = document.getElementById('connector-form');
        const title = document.getElementById('connector-modal-title');

        // Reset scope to public
        form.querySelector('[name="scope"][value="public"]').checked = true;
        toggleApplicationSelect(false);

        if (id) {
          title.textContent = 'Edit Connector';
          // Load connector data
          fetch('{URL_PREFIX}/settings/connectors/id/' + id)
            .then(r => r.json())
            .then(conn => {
              form.querySelector('[name="name"]').value = conn.name || '';
              form.querySelector('[name="type"]').value = conn.type || '';
              updateProviderOptions(conn.type);
              form.querySelector('[name="provider"]').value = conn.provider || '';
              form.querySelector('[name="host"]').value = conn.host || 'localhost';
              form.querySelector('[name="port"]').value = conn.port || '';
              form.querySelector('[name="username"]').value = conn.username || '';
              form.querySelector('[name="password"]').value = '';
              form.querySelector('[name="password"]').placeholder = conn.password_masked || 'Enter password';
              form.querySelector('[name="database"]').value = conn.database || '';
              form.querySelector('[name="docker_auto"]').checked = conn.docker_auto || false;
              form.querySelector('[name="docker_image"]').value = conn.docker_image || '';
              form.querySelector('[name="is_default"]').checked = conn.is_default || false;
              toggleDockerOptions(conn.docker_auto);

              // Set scope
              if (conn.scope === 'application' && conn.application_id) {
                form.querySelector('[name="scope"][value="application"]').checked = true;
                toggleApplicationSelect(true);
                setTimeout(() => {
                  document.getElementById('application-id-select').value = conn.application_id;
                }, 100);
              }
            });
        } else {
          title.textContent = 'Add Connector';
          form.reset();
          form.querySelector('[name="host"]').value = 'localhost';
          form.querySelector('[name="scope"][value="public"]').checked = true;
        }

        document.getElementById('connector-modal').classList.add('active');
      }

      function closeConnectorModal() {
        document.getElementById('connector-modal').classList.remove('active');
        editingConnectorId = null;
      }

      function updateProviderOptions(type) {
        const select = document.querySelector('[name="provider"]');
        select.innerHTML = '<option value="">Select provider...</option>';

        const providers = connectorProviders[type] || [];
        providers.forEach(p => {
          const option = document.createElement('option');
          option.value = p.value;
          option.textContent = p.label;
          select.appendChild(option);
        });
      }

      function updateProviderDefaults(provider) {
        const type = document.querySelector('[name="type"]').value;
        const providers = connectorProviders[type] || [];
        const config = providers.find(p => p.value === provider);

        if (config) {
          document.querySelector('[name="port"]').value = config.port || '';
          document.querySelector('[name="docker_image"]').value = config.image || '';
        }
      }

      function toggleDockerOptions(show) {
        document.getElementById('docker-options').classList.toggle('qa-hidden', !show);
      }

      async function saveConnector(e) {
        e.preventDefault();
        const form = e.target;
        const data = Object.fromEntries(new FormData(form));
        data.docker_auto = form.querySelector('[name="docker_auto"]').checked;
        data.is_default = form.querySelector('[name="is_default"]').checked;
        data.port = parseInt(data.port) || 0;

        // Handle scope and application_id
        if (data.scope === 'application' && data.application_id) {
          data.application_id = parseInt(data.application_id);
        } else {
          data.scope = 'public';
          data.application_id = null;
        }

        const url = editingConnectorId ? '/settings/connectors/' + editingConnectorId : '/settings/connectors';
        const method = editingConnectorId ? 'PUT' : 'POST';

        const res = await fetch(url, {
          method: method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });

        if (res.ok) {
          closeConnectorModal();
          refreshConnectors();
          showToast(editingConnectorId ? 'Connector updated!' : 'Connector created!', 'success');
        } else {
          const err = await res.json();
          showToast('Error: ' + (err.detail || 'Failed to save'), 'error');
        }
      }

      async function testConnectorForm() {
        const form = document.getElementById('connector-form');
        const data = Object.fromEntries(new FormData(form));
        data.port = parseInt(data.port) || 0;

        showToast('Testing connection...', 'info');

        const res = await fetch('{URL_PREFIX}/settings/connectors/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });

        const result = await res.json();
        if (result.success) {
          showToast('Connection successful!', 'success');
        } else {
          showToast('Connection failed: ' + result.error, 'error');
        }
      }

      async function testConnector(id) {
        showToast('Testing connection...', 'info');
        const res = await fetch('{URL_PREFIX}/settings/connectors/' + id + '/test', { method: 'POST' });
        const result = await res.json();
        if (result.success) {
          showToast('Connection successful!', 'success');
          refreshConnectors();
        } else {
          showToast('Connection failed: ' + result.error, 'error');
        }
      }

      function editConnector(id) {
        openConnectorModal(id);
      }

      async function deleteConnector(id) {
        if (!confirm('Delete this connector?')) return;
        await fetch('{URL_PREFIX}/settings/connectors/' + id, { method: 'DELETE' });
        refreshConnectors();
        showToast('Connector deleted', 'success');
      }

      async function setDefaultConnector(id) {
        await fetch('{URL_PREFIX}/settings/connectors/' + id + '/default', { method: 'POST' });
        refreshConnectors();
        showToast('Default connector updated', 'success');
      }

      function showConnectorType(type) {
        currentConnectorType = type;
        document.querySelectorAll('.qa-subtab').forEach(btn => {
          btn.classList.toggle('active', btn.dataset.type === type);
        });
        refreshConnectors();
      }

      function refreshConnectors() {
        const url = currentConnectorType === 'all'
          ? '/settings/connectors'
          : '/settings/connectors?connector_type=' + currentConnectorType;
        htmx.ajax('GET', url, { target: '#connectors-grid', swap: 'innerHTML' });
      }
    </script>

    <!-- Cloud Integrations Tab -->
    <div id="settings-cloud" class="qa-tab-panel">
      <div class="qa-section-header">
        <div>
          <h3 class="qa-section-title">Cloud Integrations</h3>
          <p class="qa-section-subtitle">Configure cloud providers for deployment (AWS, Kubernetes, Azure, GCP)</p>
        </div>
        <button class="qa-btn qa-btn-primary" onclick="openCloudModal()">
          <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
          Add Integration
        </button>
      </div>

      <!-- Provider Cards Grid -->
      <div id="cloud-integrations-grid" class="qa-grid qa-grid-2 qa-gap-4" hx-get="{URL_PREFIX}/settings/cloud" hx-trigger="load" hx-swap="innerHTML">
        <div class="qa-text-center qa-text-muted qa-p-6" style="grid-column: span 2;">Loading cloud integrations...</div>
      </div>

      <!-- Available Providers (if none configured) -->
      <div id="available-providers" class="qa-mt-6">
        <h4 class="qa-text-sm qa-font-medium qa-text-muted qa-mb-4">Available Providers</h4>
        <div class="qa-grid qa-grid-4 qa-gap-4">
          <div class="qa-card qa-card-interactive" onclick="openCloudModal('aws')" style="cursor:pointer;">
            <div class="qa-card-body qa-text-center qa-p-4">
              <div class="qa-text-3xl qa-mb-2">&#9729;</div>
              <p class="qa-font-medium">AWS</p>
              <p class="qa-text-xs qa-text-muted">ECS, EKS, Lambda</p>
            </div>
          </div>
          <div class="qa-card qa-card-interactive" onclick="openCloudModal('kubernetes')" style="cursor:pointer;">
            <div class="qa-card-body qa-text-center qa-p-4">
              <div class="qa-text-3xl qa-mb-2">&#9096;</div>
              <p class="qa-font-medium">Kubernetes</p>
              <p class="qa-text-xs qa-text-muted">Any K8s cluster</p>
            </div>
          </div>
          <div class="qa-card qa-card-interactive" onclick="openCloudModal('azure')" style="cursor:pointer;">
            <div class="qa-card-body qa-text-center qa-p-4">
              <div class="qa-text-3xl qa-mb-2">&#9729;</div>
              <p class="qa-font-medium">Azure</p>
              <p class="qa-text-xs qa-text-muted">ACI, AKS</p>
            </div>
          </div>
          <div class="qa-card qa-card-interactive" onclick="openCloudModal('gcp')" style="cursor:pointer;">
            <div class="qa-card-body qa-text-center qa-p-4">
              <div class="qa-text-3xl qa-mb-2">&#9729;</div>
              <p class="qa-font-medium">GCP</p>
              <p class="qa-text-xs qa-text-muted">Cloud Run, GKE</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Cloud Integration Modal -->
    <div id="cloud-modal" class="qa-modal-overlay">
      <div class="qa-modal qa-modal-lg">
        <div class="qa-modal-header">
          <h3 id="cloud-modal-title" class="qa-modal-title">Add Cloud Integration</h3>
          <button class="qa-modal-close" onclick="closeCloudModal()"><svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg></button>
        </div>
        <div class="qa-modal-body">
          <form id="cloud-form" onsubmit="saveCloudIntegration(event)">
            <div class="qa-form-row">
              <div class="qa-form-group">
                <label class="qa-label">Name</label>
                <input type="text" name="name" class="qa-input" placeholder="e.g., Production AWS" required />
              </div>
              <div class="qa-form-group">
                <label class="qa-label">Provider</label>
                <select name="provider" class="qa-input qa-select" onchange="updateCloudCredentialFields(this.value)" required>
                  <option value="">Select provider...</option>
                  <option value="aws">AWS (ECS/EKS)</option>
                  <option value="kubernetes">Kubernetes</option>
                  <option value="azure">Azure (ACI/AKS)</option>
                  <option value="gcp">GCP (Cloud Run)</option>
                </select>
              </div>
            </div>

            <!-- AWS Credentials -->
            <div id="cloud-creds-aws" class="cloud-creds-section qa-hidden">
              <div class="qa-form-row">
                <div class="qa-form-group">
                  <label class="qa-label">Access Key ID</label>
                  <input type="text" name="access_key_id" class="qa-input" />
                </div>
                <div class="qa-form-group">
                  <label class="qa-label">Secret Access Key</label>
                  <input type="password" name="secret_access_key" class="qa-input" />
                </div>
              </div>
              <div class="qa-form-group">
                <label class="qa-label">Region</label>
                <select name="aws_region" class="qa-input qa-select">
                  <option value="us-east-1">US East (N. Virginia)</option>
                  <option value="us-west-2">US West (Oregon)</option>
                  <option value="eu-west-1">Europe (Ireland)</option>
                  <option value="ap-southeast-1">Asia Pacific (Singapore)</option>
                  <option value="sa-east-1">South America (Sao Paulo)</option>
                </select>
              </div>
            </div>

            <!-- Kubernetes Credentials -->
            <div id="cloud-creds-kubernetes" class="cloud-creds-section qa-hidden">
              <div class="qa-form-group">
                <label class="qa-label">Kubeconfig (paste content or base64)</label>
                <textarea name="kubeconfig" class="qa-input" rows="6" placeholder="Paste your kubeconfig YAML here..."></textarea>
              </div>
              <p class="qa-text-xs qa-text-muted">Or provide API server and token:</p>
              <div class="qa-form-row qa-mt-2">
                <div class="qa-form-group">
                  <label class="qa-label">API Server URL</label>
                  <input type="text" name="api_server" class="qa-input" placeholder="https://k8s-api.example.com:6443" />
                </div>
                <div class="qa-form-group">
                  <label class="qa-label">Bearer Token</label>
                  <input type="password" name="k8s_token" class="qa-input" />
                </div>
              </div>
            </div>

            <!-- Azure Credentials -->
            <div id="cloud-creds-azure" class="cloud-creds-section qa-hidden">
              <div class="qa-form-row">
                <div class="qa-form-group">
                  <label class="qa-label">Subscription ID</label>
                  <input type="text" name="subscription_id" class="qa-input" />
                </div>
                <div class="qa-form-group">
                  <label class="qa-label">Tenant ID</label>
                  <input type="text" name="tenant_id" class="qa-input" />
                </div>
              </div>
              <div class="qa-form-row">
                <div class="qa-form-group">
                  <label class="qa-label">Client ID</label>
                  <input type="text" name="client_id" class="qa-input" />
                </div>
                <div class="qa-form-group">
                  <label class="qa-label">Client Secret</label>
                  <input type="password" name="client_secret" class="qa-input" />
                </div>
              </div>
            </div>

            <!-- GCP Credentials -->
            <div id="cloud-creds-gcp" class="cloud-creds-section qa-hidden">
              <div class="qa-form-group">
                <label class="qa-label">Project ID</label>
                <input type="text" name="project_id" class="qa-input" />
              </div>
              <div class="qa-form-group">
                <label class="qa-label">Service Account JSON</label>
                <textarea name="service_account_json" class="qa-input" rows="6" placeholder="Paste your service account JSON here..."></textarea>
              </div>
              <div class="qa-form-group">
                <label class="qa-label">Region</label>
                <select name="gcp_region" class="qa-input qa-select">
                  <option value="us-central1">Iowa (us-central1)</option>
                  <option value="us-east1">South Carolina (us-east1)</option>
                  <option value="europe-west1">Belgium (europe-west1)</option>
                  <option value="asia-northeast1">Tokyo (asia-northeast1)</option>
                  <option value="southamerica-east1">Sao Paulo (southamerica-east1)</option>
                </select>
              </div>
            </div>

            <div class="qa-mt-4">
              <label class="qa-checkbox-group" style="cursor: pointer;">
                <input type="checkbox" name="is_default" class="qa-checkbox" />
                <span>Set as default for deployments</span>
              </label>
            </div>
          </form>
        </div>
        <div class="qa-modal-footer">
          <button type="button" class="qa-btn qa-btn-ghost" onclick="closeCloudModal()">Cancel</button>
          <button type="button" class="qa-btn qa-btn-secondary" onclick="testCloudConnection()">Test Connection</button>
          <button type="button" class="qa-btn qa-btn-primary" onclick="document.getElementById('cloud-form').requestSubmit()">Save Integration</button>
        </div>
      </div>
    </div>

    <script>
      let editingCloudId = null;

      function updateCloudCredentialFields(provider) {
        document.querySelectorAll('.cloud-creds-section').forEach(s => s.classList.add('qa-hidden'));
        if (provider) {
          const section = document.getElementById('cloud-creds-' + provider);
          if (section) section.classList.remove('qa-hidden');
        }
      }

      function openCloudModal(provider = null, id = null) {
        editingCloudId = id;
        const form = document.getElementById('cloud-form');
        const title = document.getElementById('cloud-modal-title');

        form.reset();
        document.querySelectorAll('.cloud-creds-section').forEach(s => s.classList.add('qa-hidden'));

        if (id) {
          title.textContent = 'Edit Cloud Integration';
          fetch('{URL_PREFIX}/settings/cloud/' + id)
            .then(r => r.json())
            .then(data => {
              form.querySelector('[name="name"]').value = data.name || '';
              form.querySelector('[name="provider"]').value = data.provider || '';
              updateCloudCredentialFields(data.provider);
              if (data.is_default) {
                form.querySelector('[name="is_default"]').checked = true;
              }
              // Note: credentials are not returned for security
            });
        } else {
          title.textContent = 'Add Cloud Integration';
          if (provider) {
            form.querySelector('[name="provider"]').value = provider;
            updateCloudCredentialFields(provider);
          }
        }

        document.getElementById('cloud-modal').classList.add('active');
      }

      function closeCloudModal() {
        document.getElementById('cloud-modal').classList.remove('active');
        editingCloudId = null;
      }

      async function saveCloudIntegration(e) {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);
        const provider = formData.get('provider');

        const data = {
          name: formData.get('name'),
          provider: provider,
          is_default: form.querySelector('[name="is_default"]').checked,
          credentials: {}
        };

        // Build credentials based on provider
        if (provider === 'aws') {
          data.credentials = {
            access_key_id: formData.get('access_key_id'),
            secret_access_key: formData.get('secret_access_key'),
            region: formData.get('aws_region')
          };
          data.region = formData.get('aws_region');
        } else if (provider === 'kubernetes') {
          data.credentials = {
            kubeconfig: formData.get('kubeconfig'),
            api_server: formData.get('api_server'),
            token: formData.get('k8s_token')
          };
        } else if (provider === 'azure') {
          data.credentials = {
            subscription_id: formData.get('subscription_id'),
            tenant_id: formData.get('tenant_id'),
            client_id: formData.get('client_id'),
            client_secret: formData.get('client_secret')
          };
        } else if (provider === 'gcp') {
          data.credentials = {
            project_id: formData.get('project_id'),
            service_account_json: formData.get('service_account_json')
          };
          data.region = formData.get('gcp_region');
        }

        const url = editingCloudId ? '/settings/cloud/' + editingCloudId : '/settings/cloud';
        const method = editingCloudId ? 'PUT' : 'POST';

        const res = await fetch(url, {
          method: method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });

        if (res.ok) {
          closeCloudModal();
          htmx.ajax('GET', '/settings/cloud', { target: '#cloud-integrations-grid', swap: 'innerHTML' });
          showToast(editingCloudId ? 'Integration updated!' : 'Integration created!', 'success');
        } else {
          const err = await res.json();
          showToast('Error: ' + (err.detail || 'Failed to save'), 'error');
        }
      }

      async function testCloudConnection() {
        const form = document.getElementById('cloud-form');
        const formData = new FormData(form);
        const provider = formData.get('provider');

        if (!provider) {
          showToast('Please select a provider', 'warning');
          return;
        }

        const credentials = {};
        if (provider === 'aws') {
          credentials.access_key_id = formData.get('access_key_id');
          credentials.secret_access_key = formData.get('secret_access_key');
          credentials.region = formData.get('aws_region');
        } else if (provider === 'kubernetes') {
          credentials.kubeconfig = formData.get('kubeconfig');
          credentials.api_server = formData.get('api_server');
          credentials.token = formData.get('k8s_token');
        } else if (provider === 'azure') {
          credentials.subscription_id = formData.get('subscription_id');
          credentials.tenant_id = formData.get('tenant_id');
          credentials.client_id = formData.get('client_id');
          credentials.client_secret = formData.get('client_secret');
        } else if (provider === 'gcp') {
          credentials.project_id = formData.get('project_id');
          credentials.service_account_json = formData.get('service_account_json');
        }

        showToast('Testing connection...', 'info');

        const res = await fetch('{URL_PREFIX}/settings/cloud/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider, credentials })
        });

        const result = await res.json();
        if (result.success) {
          showToast('Connection successful!', 'success');
        } else {
          showToast('Connection failed: ' + (result.error || 'Unknown error'), 'error');
        }
      }

      async function deleteCloudIntegration(id) {
        if (!confirm('Delete this cloud integration?')) return;
        await fetch('{URL_PREFIX}/settings/cloud/' + id, { method: 'DELETE' });
        htmx.ajax('GET', '/settings/cloud', { target: '#cloud-integrations-grid', swap: 'innerHTML' });
        showToast('Integration deleted', 'success');
      }

      async function testExistingCloudIntegration(id) {
        showToast('Testing connection...', 'info');
        const res = await fetch('{URL_PREFIX}/settings/cloud/' + id + '/test', { method: 'POST' });
        const result = await res.json();
        if (result.success) {
          showToast('Connection successful!', 'success');
          htmx.ajax('GET', '/settings/cloud', { target: '#cloud-integrations-grid', swap: 'innerHTML' });
        } else {
          showToast('Connection failed: ' + (result.error || 'Unknown error'), 'error');
        }
      }
    </script>

    <!-- Email Tab -->
    <div id="settings-email" class="qa-tab-panel">
      <div class="qa-card">
        <div class="qa-card-header"><h3 class="qa-card-title">Email Configuration</h3></div>
        <div class="qa-card-body">
          <div class="qa-form-row">
            <div class="qa-form-group"><label class="qa-label">SMTP Host</label><input type="text" class="qa-input" placeholder="smtp.gmail.com" /></div>
            <div class="qa-form-group"><label class="qa-label">SMTP Port</label><input type="number" class="qa-input" value="587" /></div>
          </div>
          <div class="qa-form-row">
            <div class="qa-form-group"><label class="qa-label">Username</label><input type="text" class="qa-input" /></div>
            <div class="qa-form-group"><label class="qa-label">Password</label><input type="password" class="qa-input" /></div>
          </div>
        </div>
        <div class="qa-card-footer qa-flex qa-justify-end"><button class="qa-btn qa-btn-primary">Save Email Settings</button></div>
      </div>
    </div>

    <!-- Security Tab -->
    <div id="settings-security" class="qa-tab-panel">
      <div class="qa-card">
        <div class="qa-card-header"><h3 class="qa-card-title">Security Configuration</h3></div>
        <div class="qa-card-body">
          <div class="qa-form-group">
            <label class="qa-label">JWT Secret Key</label>
            <div class="qa-flex qa-gap-2">
              <input type="password" class="qa-input qa-flex-1" value="quantum-admin-secret" />
              <button class="qa-btn qa-btn-secondary">Generate</button>
            </div>
            <p class="qa-text-xs qa-text-danger qa-mt-2">Change in production!</p>
          </div>
          <div class="qa-form-row">
            <div class="qa-form-group"><label class="qa-label">JWT Expiry (hours)</label><input type="number" class="qa-input" value="24" /></div>
            <div class="qa-form-group"><label class="qa-label">JWT Algorithm</label><select class="qa-input qa-select"><option>HS256</option><option>HS384</option><option>HS512</option></select></div>
          </div>
        </div>
        <div class="qa-card-footer qa-flex qa-justify-end"><button class="qa-btn qa-btn-primary">Save Security Settings</button></div>
      </div>
    </div>

    <script>
      function showSettingsTab(name) {
        document.querySelectorAll('.qa-tab-panel').forEach(t => t.classList.remove('active'));
        document.getElementById('settings-' + name).classList.add('active');
        document.querySelectorAll('.qa-tab').forEach(b => b.classList.remove('active'));
        event.target.classList.add('active');
      }
    </script>
    '''


def get_users_content():
    return '''
    <div class="qa-section-header">
      <p class="qa-text-secondary">Manage admin users and permissions</p>
      <button class="qa-btn qa-btn-primary" onclick="document.getElementById('add-user-modal').classList.add('active')"><svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>Add User</button>
    </div>
    <div class="qa-card" style="overflow: hidden;">
      <table class="qa-table">
        <thead>
          <tr>
            <th>User</th>
            <th>Role</th>
            <th>Status</th>
            <th class="qa-text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <div class="qa-flex qa-items-center qa-gap-3">
                <div class="qa-sidebar-user-avatar">A</div>
                <div><p class="qa-font-medium">admin</p><p class="qa-text-xs qa-text-muted">ID: 1</p></div>
              </div>
            </td>
            <td><span class="qa-badge qa-badge-primary">Admin</span></td>
            <td><span class="qa-flex qa-items-center qa-gap-2"><span class="qa-connector-status-dot connected"></span><span class="qa-text-success">Active</span></span></td>
            <td class="qa-text-right"><button class="qa-btn qa-btn-ghost qa-btn-sm">Change Password</button></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div id="add-user-modal" class="qa-modal-overlay">
      <div class="qa-modal">
        <div class="qa-modal-header">
          <h3 class="qa-modal-title">Add New User</h3>
          <button class="qa-modal-close" onclick="document.getElementById('add-user-modal').classList.remove('active')">
            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="qa-modal-body">
          <div class="qa-form-group"><label class="qa-label">Username</label><input type="text" class="qa-input" placeholder="Enter username" /></div>
          <div class="qa-form-group"><label class="qa-label">Password</label><input type="password" class="qa-input" placeholder="Enter password" /></div>
          <div class="qa-form-group"><label class="qa-label">Role</label><select class="qa-input qa-select"><option value="user">User</option><option value="admin">Admin</option></select></div>
        </div>
        <div class="qa-modal-footer">
          <button class="qa-btn qa-btn-secondary" onclick="document.getElementById('add-user-modal').classList.remove('active')">Cancel</button>
          <button class="qa-btn qa-btn-primary">Create User</button>
        </div>
      </div>
    </div>
    '''


def get_jobs_content():
    """Content for the Jobs Management page"""
    return '''
    <div class="qa-section-header">
      <p class="qa-text-secondary">Manage background jobs, schedules, and queues</p>
    </div>

    <!-- Stats Cards -->
    <div class="qa-grid qa-grid-4 qa-gap-4 qa-mb-6" hx-get="{URL_PREFIX}/jobs/overview" hx-trigger="load, every 10s" hx-swap="innerHTML">
      <div class="qa-stat-card qa-pulse"><div class="qa-stat-label">Loading...</div><div class="qa-stat-value">-</div></div>
      <div class="qa-stat-card qa-pulse"><div class="qa-stat-label">Loading...</div><div class="qa-stat-value">-</div></div>
      <div class="qa-stat-card qa-pulse"><div class="qa-stat-label">Loading...</div><div class="qa-stat-value">-</div></div>
      <div class="qa-stat-card qa-pulse"><div class="qa-stat-label">Loading...</div><div class="qa-stat-value">-</div></div>
    </div>

    <!-- Tabs -->
    <div class="qa-tabs qa-mb-4">
      <button class="qa-tab qa-tab-active" onclick="showJobTab('jobs', this)">Jobs</button>
      <button class="qa-tab" onclick="showJobTab('schedules', this)">Schedules</button>
      <button class="qa-tab" onclick="showJobTab('threads', this)">Threads</button>
      <button class="qa-tab" onclick="showJobTab('queues', this)">Queues</button>
    </div>

    <!-- Jobs Tab -->
    <div id="tab-jobs" class="qa-tab-content">
      <div class="qa-card">
        <div class="qa-card-header qa-flex qa-justify-between qa-items-center">
          <h3 class="qa-card-title">Queued Jobs</h3>
          <button class="qa-btn qa-btn-secondary qa-btn-sm" hx-get="{URL_PREFIX}/jobs" hx-target="#jobs-list" hx-swap="innerHTML">Refresh</button>
        </div>
        <div class="qa-card-body qa-p-0" id="jobs-list" hx-get="{URL_PREFIX}/jobs" hx-trigger="load" hx-swap="innerHTML">
          <div class="qa-text-center qa-text-muted qa-p-6">Loading jobs...</div>
        </div>
      </div>
    </div>

    <!-- Schedules Tab -->
    <div id="tab-schedules" class="qa-tab-content qa-hidden">
      <div class="qa-card">
        <div class="qa-card-header"><h3 class="qa-card-title">Scheduled Tasks</h3></div>
        <div class="qa-card-body" id="schedules-list" hx-get="{URL_PREFIX}/schedules" hx-trigger="load" hx-swap="innerHTML">
          <div class="qa-text-center qa-text-muted qa-p-6">Loading schedules...</div>
        </div>
      </div>
    </div>

    <!-- Threads Tab -->
    <div id="tab-threads" class="qa-tab-content qa-hidden">
      <div class="qa-card">
        <div class="qa-card-header"><h3 class="qa-card-title">Running Threads</h3></div>
        <div class="qa-card-body" id="threads-list" hx-get="{URL_PREFIX}/threads" hx-trigger="load" hx-swap="innerHTML">
          <div class="qa-text-center qa-text-muted qa-p-6">Loading threads...</div>
        </div>
      </div>
    </div>

    <!-- Queues Tab -->
    <div id="tab-queues" class="qa-tab-content qa-hidden">
      <div class="qa-card">
        <div class="qa-card-header"><h3 class="qa-card-title">Queue Statistics</h3></div>
        <div class="qa-card-body" id="queues-list" hx-get="{URL_PREFIX}/queues" hx-trigger="load" hx-swap="innerHTML">
          <div class="qa-text-center qa-text-muted qa-p-6">Loading queues...</div>
        </div>
      </div>
    </div>

    <script>
    function showJobTab(tab, btn) {
      document.querySelectorAll('.qa-tab-content').forEach(t => t.classList.add('qa-hidden'));
      document.getElementById('tab-' + tab).classList.remove('qa-hidden');
      document.querySelectorAll('.qa-tab').forEach(b => b.classList.remove('qa-tab-active'));
      btn.classList.add('qa-tab-active');
    }
    </script>
    '''


def get_cicd_content():
    """Content for the CI/CD page"""
    return '''
    <div class="qa-section-header">
      <p class="qa-text-secondary">Continuous Integration and Deployment pipelines</p>
    </div>

    <!-- Project Selector -->
    <div class="qa-card qa-mb-6">
      <div class="qa-card-body">
        <label class="qa-label">Select Application</label>
        <select id="cicd-project" class="qa-input qa-select" style="max-width: 400px;" onchange="loadCicdDashboard(this.value)">
          <option value="">Select an application...</option>
        </select>
      </div>
    </div>

    <div id="cicd-dashboard">
      <div class="qa-grid qa-grid-2 qa-gap-6">
        <div class="qa-card">
          <div class="qa-card-header"><h3 class="qa-card-title">Recent Deployments</h3></div>
          <div class="qa-card-body">
            <p class="qa-text-muted qa-text-center qa-p-6">Select an application to view deployments</p>
          </div>
        </div>
        <div class="qa-card">
          <div class="qa-card-header"><h3 class="qa-card-title">Webhook Events</h3></div>
          <div class="qa-card-body" hx-get="{URL_PREFIX}/webhooks/events" hx-trigger="load" hx-swap="innerHTML">
            <p class="qa-text-muted qa-text-center qa-p-6">Loading webhook events...</p>
          </div>
        </div>
      </div>
    </div>

    <script>
    // Load projects for selector
    fetch('{URL_PREFIX}/projects').then(r => r.json()).then(projects => {
      const select = document.getElementById('cicd-project');
      projects.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name;
        select.appendChild(opt);
      });
    });

    function loadCicdDashboard(projectId) {
      if (!projectId) return;
      document.getElementById('cicd-dashboard').innerHTML = '<div class="qa-text-center qa-p-6"><p class="qa-text-muted">Loading CI/CD dashboard...</p></div>';
      htmx.ajax('GET', '/api/projects/' + projectId + '/ci-cd/dashboard', {target: '#cicd-dashboard', swap: 'innerHTML'});
    }
    </script>
    '''


def get_tests_content():
    """Content for the Tests page"""
    return '''
    <div class="qa-section-header">
      <p class="qa-text-secondary">Run and manage component tests</p>
    </div>

    <!-- Project Selector -->
    <div class="qa-card qa-mb-6">
      <div class="qa-card-body">
        <label class="qa-label">Select Application</label>
        <select id="tests-project" class="qa-input qa-select" style="max-width: 400px;" onchange="loadTestsDashboard(this.value)">
          <option value="">Select an application...</option>
        </select>
      </div>
    </div>

    <div id="tests-dashboard">
      <!-- Test Stats -->
      <div class="qa-grid qa-grid-4 qa-gap-4 qa-mb-6">
        <div class="qa-stat-card"><div class="qa-stat-value">-</div><div class="qa-stat-label">Total Tests</div></div>
        <div class="qa-stat-card"><div class="qa-stat-value qa-text-success">-</div><div class="qa-stat-label">Passed</div></div>
        <div class="qa-stat-card"><div class="qa-stat-value qa-text-danger">-</div><div class="qa-stat-label">Failed</div></div>
        <div class="qa-stat-card"><div class="qa-stat-value qa-text-warning">-</div><div class="qa-stat-label">Pending</div></div>
      </div>

      <div class="qa-card">
        <div class="qa-card-header"><h3 class="qa-card-title">Test Results</h3></div>
        <div class="qa-card-body">
          <p class="qa-text-muted qa-text-center qa-p-6">Select an application to view tests, or run tests from the command line with: <code>pytest tests/</code></p>
        </div>
      </div>
    </div>

    <script>
    // Load projects for selector
    fetch('{URL_PREFIX}/projects').then(r => r.json()).then(projects => {
      const select = document.getElementById('tests-project');
      projects.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name;
        select.appendChild(opt);
      });
    });

    function loadTestsDashboard(projectId) {
      if (!projectId) return;
      document.getElementById('tests-dashboard').innerHTML = '<div class="qa-text-center qa-p-6"><p class="qa-text-muted">Loading tests dashboard...</p></div>';
      htmx.ajax('GET', '/api/projects/' + projectId + '/tests/dashboard', {target: '#tests-dashboard', swap: 'innerHTML'});
    }
    </script>
    '''


def get_components_content():
    """Content for the Components page with test management"""
    return '''
    <div class="qa-section-header">
      <p class="qa-text-secondary">Browse and manage Quantum components with test tracking</p>
    </div>

    <!-- Application Selector Card -->
    <div class="qa-card qa-mb-6">
      <div class="qa-card-body qa-flex qa-justify-between qa-items-center">
        <div class="qa-flex qa-items-center qa-gap-4">
          <label class="qa-label qa-mb-0">Select Application</label>
          <select id="components-project" class="qa-input qa-select" style="max-width: 400px;" onchange="loadComponentsDashboard(this.value)">
            <option value="">Select an application...</option>
          </select>
        </div>
        <button id="sync-btn" class="qa-btn qa-btn-secondary" onclick="syncComponents()" disabled>
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
          Sync from Filesystem
        </button>
      </div>
    </div>

    <!-- Stats Cards (loaded dynamically) -->
    <div id="components-stats" class="qa-grid qa-grid-4 qa-gap-4 qa-mb-6" style="display: none;">
      <div class="qa-stat-card">
        <div class="qa-stat-label">Total Components</div>
        <div class="qa-stat-value" id="stat-total">0</div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">With Tests</div>
        <div class="qa-stat-value qa-text-success" id="stat-with-tests">0</div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Without Tests</div>
        <div class="qa-stat-value qa-text-warning" id="stat-without-tests">0</div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Tests Passing</div>
        <div class="qa-stat-value qa-text-success" id="stat-passing">0</div>
      </div>
    </div>

    <!-- Action Buttons (loaded dynamically) -->
    <div id="components-actions" class="qa-flex qa-gap-2 qa-mb-4" style="display: none;">
      <button class="qa-btn qa-btn-success" onclick="runAllTests()">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        Run All Tests
      </button>
      <button class="qa-btn qa-btn-primary" onclick="generateMissingTests()">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
        Generate Missing Tests
      </button>
      <button class="qa-btn qa-btn-secondary" onclick="syncTestsFromFS()">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg>
        Discover Existing Tests
      </button>
    </div>

    <div id="components-dashboard">
      <div class="qa-card">
        <div class="qa-card-header"><h3 class="qa-card-title">Components</h3></div>
        <div class="qa-card-body">
          <p class="qa-text-muted qa-text-center qa-p-6">Select an application to view components</p>
        </div>
      </div>
    </div>

    <!-- Legend -->
    <div id="components-legend" class="qa-card qa-mt-4" style="display: none;">
      <div class="qa-card-body qa-flex qa-gap-6 qa-text-sm">
        <span><strong>Actions:</strong></span>
        <span><button class="qa-btn qa-btn-xs qa-btn-success">&#9654;</button> Run Tests</span>
        <span><button class="qa-btn qa-btn-xs qa-btn-primary">+</button> Create Tests</span>
        <span><button class="qa-btn qa-btn-xs qa-btn-ghost">&#128065;</button> View Details</span>
        <span><button class="qa-btn qa-btn-xs qa-btn-warning">!</button> Has Errors</span>
      </div>
    </div>

    <script>
    let currentProjectId = null;

    // Load projects for selector
    fetch('{URL_PREFIX}/projects').then(r => r.json()).then(projects => {
      const select = document.getElementById('components-project');
      projects.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name;
        select.appendChild(opt);
      });
    });

    function loadComponentsDashboard(projectId) {
      if (!projectId) {
        document.getElementById('components-stats').style.display = 'none';
        document.getElementById('components-actions').style.display = 'none';
        document.getElementById('components-legend').style.display = 'none';
        document.getElementById('sync-btn').disabled = true;
        return;
      }
      currentProjectId = projectId;
      document.getElementById('sync-btn').disabled = false;
      document.getElementById('components-dashboard').innerHTML = '<div class="qa-text-center qa-p-6"><p class="qa-text-muted">Loading components...</p></div>';
      htmx.ajax('GET', '/api/projects/' + projectId + '/components/dashboard', {target: '#components-dashboard', swap: 'innerHTML'});
    }

    function syncComponents() {
      if (!currentProjectId) return;
      showToast('Syncing components from filesystem...', 'info');
      fetch('{URL_PREFIX}/projects/' + currentProjectId + '/components/sync', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
          showToast('Synced: ' + data.created + ' created, ' + data.updated + ' updated, ' + data.deleted + ' deleted', 'success');
          loadComponentsDashboard(currentProjectId);
        })
        .catch(err => showToast('Sync failed: ' + err.message, 'error'));
    }

    function syncTestsFromFS() {
      if (!currentProjectId) return;
      showToast('Discovering existing tests...', 'info');
      fetch('{URL_PREFIX}/api/projects/' + currentProjectId + '/components/sync-tests', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
          showToast('Discovered ' + data.tests_synced + ' tests, updated ' + data.components_updated + ' components', 'success');
          loadComponentsDashboard(currentProjectId);
        })
        .catch(err => showToast('Discovery failed: ' + err.message, 'error'));
    }

    function runAllTests() {
      if (!currentProjectId) return;
      showToast('Starting test run for all components...', 'info');
      fetch('{URL_PREFIX}/api/projects/' + currentProjectId + '/tests/run-all', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
          showToast('Test run started: ' + data.test_run_id, 'success');
          // Poll for results
          pollTestRun(data.test_run_id);
        })
        .catch(err => showToast('Failed to start tests: ' + err.message, 'error'));
    }

    function generateMissingTests() {
      if (!currentProjectId) return;
      showToast('Generating tests for components without tests...', 'info');
      fetch('{URL_PREFIX}/api/projects/' + currentProjectId + '/components/generate-missing-tests', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
          showToast('Generated tests for ' + data.components_processed + ' components', 'success');
          loadComponentsDashboard(currentProjectId);
        })
        .catch(err => showToast('Generation failed: ' + err.message, 'error'));
    }

    function runComponentTests(componentId) {
      showToast('Running tests for component...', 'info');
      fetch('{URL_PREFIX}/api/projects/' + currentProjectId + '/components/' + componentId + '/tests/run', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
          showToast('Test run started: ' + data.test_run_id, 'success');
          pollTestRun(data.test_run_id);
        })
        .catch(err => showToast('Failed to run tests: ' + err.message, 'error'));
    }

    function generateComponentTests(componentId) {
      showToast('Generating tests for component...', 'info');
      fetch('{URL_PREFIX}/projects/' + currentProjectId + '/components/' + componentId + '/tests/generate', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
          showToast('Generated ' + data.generated + ' tests', 'success');
          loadComponentsDashboard(currentProjectId);
        })
        .catch(err => showToast('Generation failed: ' + err.message, 'error'));
    }

    function viewComponentDetails(componentId) {
      // Open modal or navigate to details page
      window.location.href = '{URL_PREFIX}/projects/' + currentProjectId + '/components/' + componentId;
    }

    function toggleAllComponents(checkbox) {
      document.querySelectorAll('.component-checkbox').forEach(cb => {
        cb.checked = checkbox.checked;
      });
    }

    function pollTestRun(testRunId) {
      const interval = setInterval(() => {
        fetch('{URL_PREFIX}/projects/' + currentProjectId + '/test-runs/' + testRunId)
          .then(r => r.json())
          .then(data => {
            if (data.status === 'completed' || data.status === 'failed') {
              clearInterval(interval);
              showToast('Tests completed: ' + data.passed_tests + ' passed, ' + data.failed_tests + ' failed',
                data.failed_tests > 0 ? 'warning' : 'success');
              loadComponentsDashboard(currentProjectId);
            }
          });
      }, 2000);
    }

    function updateStats(stats) {
      document.getElementById('stat-total').textContent = stats.total;
      document.getElementById('stat-with-tests').textContent = stats.with_tests;
      document.getElementById('stat-without-tests').textContent = stats.without_tests;
      document.getElementById('stat-passing').textContent = stats.tests_passing;
      document.getElementById('components-stats').style.display = 'grid';
      document.getElementById('components-actions').style.display = 'flex';
      document.getElementById('components-legend').style.display = 'block';
    }
    </script>
    '''


def get_resources_content():
    """Content for the Resource Manager page"""
    return '''
    <div class="qa-section-header">
      <p class="qa-text-secondary">Manage ports, secrets, services, and auto-discover system resources</p>
    </div>

    <!-- Stats Cards with Auto-Discovery -->
    <div class="qa-mb-6" hx-get="{URL_PREFIX}/resources/overview-html" hx-trigger="load" hx-swap="innerHTML">
      <div class="qa-grid qa-grid-4 qa-gap-4">
        <div class="qa-stat-card qa-pulse"><div class="qa-stat-label">Loading...</div><div class="qa-stat-value">-</div></div>
        <div class="qa-stat-card qa-pulse"><div class="qa-stat-label">Loading...</div><div class="qa-stat-value">-</div></div>
        <div class="qa-stat-card qa-pulse"><div class="qa-stat-label">Loading...</div><div class="qa-stat-value">-</div></div>
        <div class="qa-stat-card qa-pulse"><div class="qa-stat-label">Loading...</div><div class="qa-stat-value">-</div></div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="qa-tabs qa-mb-4">
      <button class="qa-tab qa-tab-active" onclick="showResourceTab('discovery', this)">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
        Discovery
      </button>
      <button class="qa-tab" onclick="showResourceTab('ports', this)">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 14v3m4-3v3m4-3v3M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z"/></svg>
        Ports
      </button>
      <button class="qa-tab" onclick="showResourceTab('secrets', this)">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/></svg>
        Secrets
      </button>
      <button class="qa-tab" onclick="showResourceTab('services', this)">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2"/></svg>
        Services
      </button>
    </div>

    <!-- Discovery Tab (NEW) -->
    <div id="tab-discovery" class="qa-tab-content">
      <div class="qa-grid qa-grid-2 qa-gap-4">
        <!-- Discovered Ports -->
        <div class="qa-card">
          <div class="qa-card-header qa-flex qa-justify-between qa-items-center">
            <h3 class="qa-card-title">Ports in Use</h3>
            <button class="qa-btn qa-btn-ghost qa-btn-sm" hx-get="{URL_PREFIX}/api/resources/discovered-ports-html" hx-target="#discovered-ports-list" hx-swap="innerHTML">
              <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
            </button>
          </div>
          <div class="qa-card-body qa-p-0" id="discovered-ports-list" hx-get="{URL_PREFIX}/api/resources/discovered-ports-html" hx-trigger="load" hx-swap="innerHTML" style="max-height: 400px; overflow-y: auto;">
            <div class="qa-text-center qa-text-muted qa-p-6">Scanning ports...</div>
          </div>
        </div>

        <!-- Docker Containers -->
        <div class="qa-card">
          <div class="qa-card-header qa-flex qa-justify-between qa-items-center">
            <h3 class="qa-card-title">Docker Containers</h3>
            <button class="qa-btn qa-btn-ghost qa-btn-sm" hx-get="{URL_PREFIX}/api/resources/containers-html" hx-target="#discovered-containers-list" hx-swap="innerHTML">
              <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
            </button>
          </div>
          <div class="qa-card-body qa-p-0" id="discovered-containers-list" hx-get="{URL_PREFIX}/api/resources/containers-html" hx-trigger="load" hx-swap="innerHTML" style="max-height: 400px; overflow-y: auto;">
            <div class="qa-text-center qa-text-muted qa-p-6">Scanning containers...</div>
          </div>
        </div>
      </div>

      <!-- Sync Status -->
      <div class="qa-card qa-mt-4">
        <div class="qa-card-header qa-flex qa-justify-between qa-items-center">
          <h3 class="qa-card-title">Resource Sync</h3>
          <button class="qa-btn qa-btn-secondary qa-btn-sm" hx-post="{URL_PREFIX}/resources/sync" hx-target="#sync-results" hx-swap="innerHTML">
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
            Sync Now
          </button>
        </div>
        <div class="qa-card-body" id="sync-results">
          <p class="qa-text-muted">Click "Sync Now" to compare discovered resources with tracked allocations.</p>
        </div>
      </div>
    </div>

    <!-- Port Allocations Tab -->
    <div id="tab-ports" class="qa-tab-content">
      <div class="qa-card">
        <div class="qa-card-header qa-flex qa-justify-between qa-items-center">
          <h3 class="qa-card-title">Port Allocations</h3>
          <button class="qa-btn qa-btn-primary qa-btn-sm" onclick="openAllocatePortModal()">
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
            Allocate Port
          </button>
        </div>
        <div class="qa-card-body qa-p-0" hx-get="{URL_PREFIX}/api/resources/ports-html" hx-trigger="load" hx-swap="innerHTML" id="ports-table">
          <div class="qa-text-center qa-text-muted qa-p-6">Loading ports...</div>
        </div>
      </div>
    </div>

    <!-- Secrets Tab -->
    <div id="tab-secrets" class="qa-tab-content" style="display: none;">
      <div class="qa-card">
        <div class="qa-card-header qa-flex qa-justify-between qa-items-center">
          <h3 class="qa-card-title">Secrets</h3>
          <button class="qa-btn qa-btn-primary qa-btn-sm" onclick="openAddSecretModal()">
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
            Add Secret
          </button>
        </div>
        <div class="qa-card-body qa-p-0" hx-get="{URL_PREFIX}/api/resources/secrets-html" hx-trigger="load" hx-swap="innerHTML" id="secrets-table">
          <div class="qa-text-center qa-text-muted qa-p-6">Loading secrets...</div>
        </div>
      </div>
    </div>

    <!-- Services Tab -->
    <div id="tab-services" class="qa-tab-content" style="display: none;">
      <div class="qa-card">
        <div class="qa-card-header qa-flex qa-justify-between qa-items-center">
          <h3 class="qa-card-title">Service Registry</h3>
          <div class="qa-flex qa-gap-2">
            <button class="qa-btn qa-btn-outline qa-btn-sm" onclick="runHealthChecks()">
              <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/></svg>
              Health Check
            </button>
            <button class="qa-btn qa-btn-primary qa-btn-sm" onclick="openRegisterServiceModal()">
              <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
              Register Service
            </button>
          </div>
        </div>
        <div class="qa-card-body qa-p-0" hx-get="{URL_PREFIX}/api/resources/services-html" hx-trigger="load" hx-swap="innerHTML" id="services-table">
          <div class="qa-text-center qa-text-muted qa-p-6">Loading services...</div>
        </div>
      </div>
    </div>

    <script>
      function showResourceTab(tab, btn) {
        document.querySelectorAll('.qa-tab').forEach(t => t.classList.remove('qa-tab-active'));
        document.querySelectorAll('.qa-tab-content').forEach(c => c.style.display = 'none');
        btn.classList.add('qa-tab-active');
        document.getElementById('tab-' + tab).style.display = 'block';
      }

      function openAllocatePortModal() {
        alert('Port allocation modal - Coming soon!');
      }

      function openAddSecretModal() {
        alert('Secret creation modal - Coming soon!');
      }

      function openRegisterServiceModal() {
        alert('Service registration modal - Coming soon!');
      }

      async function runHealthChecks() {
        try {
          const response = await fetch('{URL_PREFIX}/resources/services/health-check', { method: 'POST' });
          const data = await response.json();
          showToast('Health checks completed', 'success');
          htmx.trigger('#services-table', 'load');
        } catch (error) {
          showToast('Health check failed: ' + error.message, 'error');
        }
      }
    </script>
    '''


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Quantum Admin API",
        "version": "1.0.0"
    }


@app.get("/docker/status", tags=["Docker"])
def docker_status(request: Request = None):
    """Get Docker connection status"""
    global docker_service

    is_htmx = request and request.headers.get("HX-Request")

    if docker_service is None:
        if is_htmx:
            return HTMLResponse(content="""
                <span class="qa-status-badge">
                    <span class="qa-status-dot muted"></span>
                    <span class="qa-status-text">Not connected</span>
                </span>
            """)
        return {
            "connected": False,
            "host": os.environ.get("DOCKER_HOST", "local"),
            "error": "Docker service not initialized"
        }

    try:
        info = docker_service.client.info()
        if is_htmx:
            return HTMLResponse(content=f"""
                <span class="qa-status-badge">
                    <span class="qa-status-dot success"></span>
                    <span class="qa-status-text success">{info.get("Containers", 0)} containers</span>
                </span>
            """)
        return {
            "connected": True,
            "host": docker_service.host,
            "remote": docker_service.remote,
            "server_version": info.get("ServerVersion"),
            "containers": info.get("Containers"),
            "images": info.get("Images"),
            "os": info.get("OperatingSystem"),
            "architecture": info.get("Architecture")
        }
    except Exception as e:
        if is_htmx:
            return HTMLResponse(content="""
                <span class="qa-status-badge">
                    <span class="qa-status-dot error"></span>
                    <span class="qa-status-text error">Error</span>
                </span>
            """)
        return {
            "connected": False,
            "host": docker_service.host if docker_service else "unknown",
            "error": str(e)
        }


@app.post("/docker/connect", tags=["Docker"])
def docker_connect(host: str = None):
    """
    Connect to a Docker host.

    Args:
        host: Docker host URL. Examples:
            - ssh://user@quantum.sargas.cloud (SSH tunnel)
            - tcp://192.168.1.100:2375 (TCP, insecure)
            - None: Use local Docker

    Note: For SSH, ensure you have SSH keys configured.
    """
    global docker_service

    try:
        if host:
            os.environ["DOCKER_HOST"] = host

        docker_service = DockerService(docker_host=host)
        return {
            "success": True,
            "host": docker_service.host,
            "remote": docker_service.remote
        }
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[User]:
    """Dependency to get current user from JWT token"""
    if not credentials:
        return None

    auth_service = get_auth_service()
    user = auth_service.get_current_user(credentials.credentials)
    return user


def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Dependency that requires authentication"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    auth_service = get_auth_service()
    user = auth_service.get_current_user(credentials.credentials)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


def require_admin(user: User = Depends(require_auth)) -> User:
    """Dependency that requires admin role"""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


@app.post("/auth/login", tags=["Auth"])
def login(username: str, password: str):
    """
    Authenticate and get JWT token

    Use default credentials: admin/admin (change ADMIN_PASSWORD env var in production)
    """
    auth_service = get_auth_service()
    result = auth_service.authenticate(username, password)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    return result


@app.get("/auth/me", tags=["Auth"])
def get_me(user: User = Depends(require_auth)):
    """Get current user info"""
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role
    }


@app.get("/auth/users", tags=["Auth"])
def list_users(user: User = Depends(require_admin)):
    """List all users (admin only)"""
    auth_service = get_auth_service()
    return auth_service.list_users()


@app.post("/auth/users", tags=["Auth"])
def create_user(
    username: str,
    password: str,
    role: str = "user",
    admin: User = Depends(require_admin)
):
    """Create a new user (admin only)"""
    auth_service = get_auth_service()
    new_user = auth_service.create_user(username, password, role)

    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )

    return {"id": new_user.id, "username": new_user.username, "role": new_user.role}


@app.post("/auth/change-password", tags=["Auth"])
def change_password(
    new_password: str,
    user: User = Depends(require_auth)
):
    """Change current user's password"""
    auth_service = get_auth_service()
    success = auth_service.change_password(user.username, new_password)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to change password"
        )

    return {"message": "Password changed successfully"}


# ============================================================================
# SETTINGS ENDPOINTS
# ============================================================================

@app.get("/settings", tags=["Settings"])
def get_settings(user: User = Depends(require_auth)):
    """Get all global settings"""
    settings_service = get_settings_service()
    return settings_service.get_global_settings()


@app.put("/settings", tags=["Settings"])
def update_settings(
    updates: Dict[str, Any],
    user: User = Depends(require_admin)
):
    """Update global settings (admin only)"""
    settings_service = get_settings_service()

    try:
        return settings_service.update_global_settings(updates)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# CONNECTOR ENDPOINTS (Infrastructure Connectors)
# ============================================================================

try:
    from .connector_service import get_connector_service, ConnectorService, PROVIDER_CONFIGS
except ImportError:
    from connector_service import get_connector_service, ConnectorService, PROVIDER_CONFIGS


@app.get("/settings/connectors", tags=["Connectors"])
def list_connectors(
    connector_type: Optional[str] = None,
    application_id: Optional[int] = None,
    request: Request = None
):
    """
    List all infrastructure connectors, optionally filtered by type and/or application.

    Types: database, mq, cache, storage, ai
    Scope: public (available to all) or application-specific
    """
    connector_service = get_connector_service()
    connectors = connector_service.list_connectors(connector_type, application_id)

    is_htmx = request and request.headers.get("HX-Request")

    if is_htmx:
        if not connectors:
            return HTMLResponse(content='''
                <div class="qa-empty">
                    <svg class="qa-empty-icon" width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2"/>
                    </svg>
                    <p class="qa-empty-title">No connectors configured</p>
                    <p class="qa-empty-text">Add a connector to start using infrastructure services</p>
                </div>
            ''')

        cards = ""
        for conn in connectors:
            # Use CSS classes for provider icons
            provider_class = f'qa-provider-{conn.provider}'

            # Badges
            default_badge = '<span class="qa-badge qa-badge-primary qa-ml-2">Default</span>' if conn.is_default else ''
            docker_badge = '<span class="qa-badge qa-badge-info qa-ml-2">Docker</span>' if conn.docker_auto else ''
            scope_badge = '<span class="qa-badge qa-badge-success qa-ml-2">Public</span>' if conn.scope == 'public' else f'<span class="qa-badge qa-badge-warning qa-ml-2">App #{conn.application_id}</span>'

            cards += f'''
                <div class="qa-connector-card">
                    <div class="qa-connector-header">
                        <div class="qa-connector-info">
                            <div class="qa-connector-icon {provider_class}">{conn.provider[:2].upper()}</div>
                            <div class="qa-connector-details">
                                <div class="qa-connector-name">
                                    {conn.name}
                                    {scope_badge}{default_badge}{docker_badge}
                                </div>
                                <div class="qa-connector-provider">{conn.provider}</div>
                            </div>
                        </div>
                        <div class="qa-connector-status">
                            <span class="qa-connector-status-dot {conn.status}"></span>
                            <span class="qa-connector-status-text">{conn.status}</span>
                        </div>
                    </div>
                    <div class="qa-connector-meta">
                        <span class="qa-font-mono">{conn.host}:{conn.port}</span>
                        {f'<span class="qa-text-muted qa-ml-2">/ {conn.database}</span>' if conn.database else ''}
                    </div>
                    <div class="qa-connector-actions">
                        <div class="qa-flex qa-gap-1">
                            <button class="qa-btn qa-btn-ghost qa-btn-icon qa-btn-sm" onclick="testConnector('{conn.id}')" title="Test">
                                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                            </button>
                            <button class="qa-btn qa-btn-ghost qa-btn-icon qa-btn-sm" onclick="editConnector('{conn.id}')" title="Edit">
                                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                            </button>
                            <button class="qa-btn qa-btn-ghost qa-btn-icon qa-btn-sm" onclick="setDefaultConnector('{conn.id}')" title="Set default">
                                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/></svg>
                            </button>
                        </div>
                        <button class="qa-btn qa-btn-danger qa-btn-icon qa-btn-sm" onclick="deleteConnector('{conn.id}')" title="Delete">
                            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                        </button>
                    </div>
                </div>
            '''
        return HTMLResponse(content=cards)

    return [c.to_safe_dict() for c in connectors]


@app.get("/settings/connectors/providers", tags=["Connectors"])
def get_connector_providers():
    """Get available connector providers with their configurations"""
    providers = {}
    for name, config in PROVIDER_CONFIGS.items():
        providers[name] = {
            "type": config["type"].value if hasattr(config["type"], 'value') else config["type"],
            "default_port": config["default_port"],
            "docker_image": config.get("docker_image"),
            "has_docker": config.get("docker_image") is not None
        }
    return providers


@app.post("/settings/connectors", tags=["Connectors"])
def create_connector(connector: Dict[str, Any]):
    """Create a new infrastructure connector"""
    connector_service = get_connector_service()

    try:
        new_connector = connector_service.create_connector(connector)
        return {"success": True, "id": new_connector.id, "connector": new_connector.to_safe_dict()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/settings/connectors/id/{connector_id}", tags=["Connectors"])
def get_connector(connector_id: str):
    """Get a specific connector by ID"""
    connector_service = get_connector_service()
    connector = connector_service.get_connector(connector_id)

    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector not found"
        )

    return connector.to_dict()


@app.put("/settings/connectors/{connector_id}", tags=["Connectors"])
def update_connector(connector_id: str, connector: Dict[str, Any]):
    """Update an existing connector"""
    connector_service = get_connector_service()

    updated = connector_service.update_connector(connector_id, connector)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector not found"
        )

    return {"success": True, "connector": updated.to_safe_dict()}


@app.delete("/settings/connectors/{connector_id}", tags=["Connectors"])
def delete_connector(connector_id: str):
    """Delete a connector"""
    connector_service = get_connector_service()

    success = connector_service.delete_connector(connector_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector not found"
        )

    return {"success": True}


@app.post("/settings/connectors/{connector_id}/default", tags=["Connectors"])
def set_connector_default(connector_id: str):
    """Set a connector as the default for its type"""
    connector_service = get_connector_service()

    success = connector_service.set_default(connector_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector not found"
        )

    return {"success": True}


@app.post("/settings/connectors/{connector_id}/test", tags=["Connectors"])
async def test_connector(connector_id: str):
    """Test a connector's connection"""
    connector_service = get_connector_service()

    result = await connector_service.test_connection(connector_id)
    return result


@app.post("/settings/connectors/test", tags=["Connectors"])
async def test_connector_data(connector: Dict[str, Any]):
    """Test connection with provided data (before saving)"""
    connector_service = get_connector_service()

    result = await connector_service.test_connection_data(connector)
    return result


@app.post("/settings/connectors/{connector_id}/docker/start", tags=["Connectors"])
def start_connector_docker(connector_id: str):
    """Start Docker container for a connector"""
    connector_service = get_connector_service()

    result = connector_service.start_docker_container(connector_id)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to start container")
        )

    return result


@app.post("/settings/connectors/{connector_id}/docker/stop", tags=["Connectors"])
def stop_connector_docker(connector_id: str):
    """Stop Docker container for a connector"""
    connector_service = get_connector_service()

    result = connector_service.stop_docker_container(connector_id)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to stop container")
        )

    return result


@app.get("/settings/connectors/type/{connector_type}", tags=["Connectors"])
def list_connectors_by_type(connector_type: str, request: Request = None):
    """List connectors filtered by type"""
    return list_connectors(connector_type=connector_type, request=request)


@app.get("/settings/connectors/type/{connector_type}/default", tags=["Connectors"])
def get_default_connector(connector_type: str):
    """Get the default connector for a specific type"""
    connector_service = get_connector_service()
    connector = connector_service.get_default(connector_type)

    if not connector:
        return None

    return connector.to_safe_dict()


@app.get("/settings/{path:path}", tags=["Settings"])
def get_setting(path: str, user: User = Depends(require_auth)):
    """Get a specific setting by path (e.g., /settings/server/port)"""
    settings_service = get_settings_service()
    # Convert path to dot notation
    dot_path = path.replace("/", ".")
    value = settings_service.get_setting(dot_path)

    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{dot_path}' not found"
        )

    return {"path": dot_path, "value": value}


@app.put("/settings/{path:path}", tags=["Settings"])
def set_setting(
    path: str,
    value: Any,
    user: User = Depends(require_admin)
):
    """Set a specific setting by path (admin only)"""
    settings_service = get_settings_service()
    dot_path = path.replace("/", ".")

    try:
        settings_service.set_setting(dot_path, value)
        return {"path": dot_path, "value": value, "updated": True}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# PROJECT SETTINGS ENDPOINTS
# ============================================================================

@app.get("/projects/{project_id}/settings", tags=["Project Settings"])
def get_project_settings(
    project_id: int,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get settings for a specific project"""
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    settings_service = get_settings_service()
    return settings_service.get_project_settings(project_id)


@app.put("/projects/{project_id}/settings", tags=["Project Settings"])
def update_project_settings(
    project_id: int,
    updates: Dict[str, Any],
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update settings for a specific project (admin only)"""
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    settings_service = get_settings_service()
    try:
        return settings_service.update_project_settings(project_id, updates)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/settings/export", tags=["Settings"])
def export_settings(user: User = Depends(require_admin)):
    """Export all settings (admin only)"""
    settings_service = get_settings_service()
    return settings_service.export_settings()


@app.post("/settings/import", tags=["Settings"])
def import_settings(
    data: Dict[str, Any],
    user: User = Depends(require_admin)
):
    """Import settings from export (admin only)"""
    settings_service = get_settings_service()
    success = settings_service.import_settings(data)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import settings"
        )

    return {"message": "Settings imported successfully"}


# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@app.get("/dashboard/stats", tags=["Dashboard"])
def get_dashboard_stats(
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    global docker_service

    # Get project stats
    projects = crud.get_projects(db)
    active_projects = len([p for p in projects if p.status == 'active'])

    # Get Docker stats
    containers = 0
    running_containers = 0
    if docker_service:
        try:
            info = docker_service.client.info()
            containers = info.get("Containers", 0)
            running_containers = info.get("ContainersRunning", 0)
        except Exception:
            pass

    # Get connector stats
    connectors = db.query(models.Connector).all()
    connected_connectors = len([c for c in connectors if c.status == 'connected'])

    # Get environment stats
    environments = db.query(models.Environment).all()
    active_envs = len([e for e in environments if e.is_active])

    # Get test stats
    test_runs = db.query(models.TestRun).order_by(models.TestRun.started_at.desc()).limit(10).all()
    recent_tests = len(test_runs)
    passed_tests = sum(1 for t in test_runs if t.status == 'completed' and t.failed_tests == 0)

    # Get user stats
    auth_service = get_auth_service()
    users = auth_service.list_users()
    admin_users = len([u for u in users if u.get("role") == "admin"])

    # Get job stats
    job_service = get_job_service()
    scheduled_jobs = len(job_service.list_jobs())

    # Get deployment stats
    deployments = db.query(models.Deployment).all()
    successful_deploys = len([d for d in deployments if d.status == 'completed'])

    stats = {
        "projects": len(projects),
        "activeProjects": active_projects,
        "containers": containers,
        "runningContainers": running_containers,
        "connectors": len(connectors),
        "connectedConnectors": connected_connectors,
        "environments": len(environments),
        "activeEnvironments": active_envs,
        "tests": recent_tests,
        "passedTests": passed_tests,
        "jobs": scheduled_jobs,
        "users": len(users),
        "adminUsers": admin_users,
        "deployments": len(deployments),
        "successfulDeploys": successful_deploys
    }

    # Check if HTMX request
    if request and request.headers.get("HX-Request"):
        return HTMLResponse(content=f"""
            <!-- Projects -->
            <div class="qa-stat-card">
                <div class="qa-flex qa-items-center qa-justify-between">
                    <div>
                        <p class="qa-stat-label">Applications</p>
                        <p class="qa-stat-value">{stats['projects']}</p>
                    </div>
                    <div class="qa-stat-icon qa-provider-ollama">
                        <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                        </svg>
                    </div>
                </div>
                <p class="qa-stat-change positive">
                    <span class="qa-font-medium">{stats['activeProjects']}</span> active
                </p>
            </div>

            <!-- Containers -->
            <div class="qa-stat-card">
                <div class="qa-flex qa-items-center qa-justify-between">
                    <div>
                        <p class="qa-stat-label">Containers</p>
                        <p class="qa-stat-value">{stats['containers']}</p>
                    </div>
                    <div class="qa-stat-icon qa-provider-postgres">
                        <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2"/>
                        </svg>
                    </div>
                </div>
                <p class="qa-stat-change positive">
                    <span class="qa-font-medium">{stats['runningContainers']}</span> running
                </p>
            </div>

            <!-- Deployments -->
            <div class="qa-stat-card">
                <div class="qa-flex qa-items-center qa-justify-between">
                    <div>
                        <p class="qa-stat-label">Deployments</p>
                        <p class="qa-stat-value">{stats['deployments']}</p>
                    </div>
                    <div class="qa-stat-icon qa-provider-openai">
                        <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                        </svg>
                    </div>
                </div>
                <p class="qa-stat-change positive">
                    <span class="qa-font-medium">{stats['successfulDeploys']}</span> successful
                </p>
            </div>

            <!-- Connectors -->
            <div class="qa-stat-card">
                <div class="qa-flex qa-items-center qa-justify-between">
                    <div>
                        <p class="qa-stat-label">Connectors</p>
                        <p class="qa-stat-value">{stats['connectors']}</p>
                    </div>
                    <div class="qa-stat-icon" style="background: var(--q-info-dim); color: var(--q-info);">
                        <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/>
                        </svg>
                    </div>
                </div>
                <p class="qa-stat-change positive">
                    <span class="qa-font-medium">{stats['connectedConnectors']}</span> connected
                </p>
            </div>

            <!-- Environments -->
            <div class="qa-stat-card">
                <div class="qa-flex qa-items-center qa-justify-between">
                    <div>
                        <p class="qa-stat-label">Environments</p>
                        <p class="qa-stat-value">{stats['environments']}</p>
                    </div>
                    <div class="qa-stat-icon" style="background: var(--q-warning-dim); color: var(--q-warning);">
                        <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2"/>
                        </svg>
                    </div>
                </div>
                <p class="qa-stat-change positive">
                    <span class="qa-font-medium">{stats['activeEnvironments']}</span> active
                </p>
            </div>

            <!-- Tests -->
            <div class="qa-stat-card">
                <div class="qa-flex qa-items-center qa-justify-between">
                    <div>
                        <p class="qa-stat-label">Tests</p>
                        <p class="qa-stat-value">{stats['tests']}</p>
                    </div>
                    <div class="qa-stat-icon" style="background: var(--q-success-dim); color: var(--q-success);">
                        <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                    </div>
                </div>
                <p class="qa-stat-change positive">
                    <span class="qa-font-medium">{stats['passedTests']}</span> passed
                </p>
            </div>

            <!-- Jobs -->
            <div class="qa-stat-card">
                <div class="qa-flex qa-items-center qa-justify-between">
                    <div>
                        <p class="qa-stat-label">Jobs</p>
                        <p class="qa-stat-value">{stats['jobs']}</p>
                    </div>
                    <div class="qa-stat-icon" style="background: var(--q-primary-dim); color: var(--q-primary);">
                        <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                    </div>
                </div>
                <p class="qa-stat-change">
                    <span class="qa-font-medium">scheduled</span>
                </p>
            </div>
        """)

    return stats


@app.get("/dashboard/activity-legacy", tags=["Dashboard"])
def get_dashboard_activity_legacy(
    request: Request = None,
    limit: int = 10,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get recent activity for dashboard (uses AuditLog)"""
    audit_service = get_audit_service(db)
    activities = audit_service.get_recent_activity(limit=limit)

    if request and request.headers.get("HX-Request"):
        if not activities:
            return HTMLResponse(content='<p class="qa-text-center qa-text-muted qa-p-6">No recent activity</p>')

        items_html = ""
        for act in activities:
            color = act.get("color", "muted")
            message = act.get("message", "")
            user_id = act.get("user_id", "system")
            timestamp = act.get("timestamp", "")

            # Format timestamp
            if timestamp:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamp = dt.strftime('%H:%M:%S')
                except:
                    timestamp = timestamp[:8]

            items_html += f"""
                <div class="qa-activity-item qa-flex qa-items-start qa-gap-3 qa-p-3" style="border-bottom: 1px solid var(--q-border);">
                    <div class="qa-activity-dot" style="width: 10px; height: 10px; border-radius: 50%; background: var(--q-{color}); margin-top: 4px;"></div>
                    <div class="qa-flex-1">
                        <p class="qa-text-secondary">{message}</p>
                        <p class="qa-text-xs qa-text-muted qa-mt-1">{user_id} - {timestamp}</p>
                    </div>
                </div>
            """

        return HTMLResponse(content=items_html)

    return {"activities": activities}


@app.get("/health/database", tags=["Health"])
def health_database(request: Request = None):
    """Check database connectivity"""
    try:
        # Simple query to test connection
        from sqlalchemy import text
        try:
            from .database import SessionLocal
        except ImportError:
            from database import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()

        # Check if HTMX request
        if request and request.headers.get("HX-Request"):
            return HTMLResponse(content="""
                <span class="qa-status-badge">
                    <span class="qa-status-dot success"></span>
                    <span class="qa-status-text success">Connected</span>
                </span>
            """)

        return {"status": "healthy", "message": "Database connected"}
    except Exception as e:
        if request and request.headers.get("HX-Request"):
            return HTMLResponse(content=f"""
                <span class="qa-status-badge">
                    <span class="qa-status-dot error"></span>
                    <span class="qa-status-text error">Error</span>
                </span>
            """)
        return {"status": "unhealthy", "message": str(e)}


# ============================================================================
# DOCKER MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/docker/info", tags=["Docker"])
def get_docker_info(request: Request = None):
    """Get detailed Docker system info"""
    global docker_service

    is_htmx = request and request.headers.get("HX-Request")

    if docker_service is None:
        if is_htmx:
            return HTMLResponse(content="""
                <div class="qa-empty qa-p-4">
                    <p class="qa-text-muted">Docker not connected</p>
                    <button class="qa-btn qa-btn-primary qa-btn-sm qa-mt-4"
                            hx-post="{URL_PREFIX}/docker/connect?host=ssh://abathur@10.10.1.40"
                            hx-swap="outerHTML">
                        Connect to Forge
                    </button>
                </div>
            """)
        return {"error": "Docker not connected"}

    try:
        info = docker_service.client.info()
        data = {
            "version": info.get("ServerVersion"),
            "os": info.get("OperatingSystem"),
            "architecture": info.get("Architecture"),
            "cpus": info.get("NCPU"),
            "memory": f"{info.get('MemTotal', 0) / (1024**3):.1f} GB",
            "containers": info.get("Containers"),
            "running": info.get("ContainersRunning"),
            "images": info.get("Images"),
            "driver": info.get("Driver")
        }

        if is_htmx:
            return HTMLResponse(content=f"""
                <div class="qa-grid qa-grid-2 qa-gap-4 qa-text-sm">
                    <div>
                        <p class="qa-text-muted">Version</p>
                        <p class="qa-font-medium qa-text-primary">{data['version']}</p>
                    </div>
                    <div>
                        <p class="qa-text-muted">OS</p>
                        <p class="qa-font-medium qa-text-primary">{data['os']}</p>
                    </div>
                    <div>
                        <p class="qa-text-muted">CPUs</p>
                        <p class="qa-font-medium qa-text-primary">{data['cpus']}</p>
                    </div>
                    <div>
                        <p class="qa-text-muted">Memory</p>
                        <p class="qa-font-medium qa-text-primary">{data['memory']}</p>
                    </div>
                    <div>
                        <p class="qa-text-muted">Containers</p>
                        <p class="qa-font-medium qa-text-primary">{data['containers']} ({data['running']} running)</p>
                    </div>
                    <div>
                        <p class="qa-text-muted">Images</p>
                        <p class="qa-font-medium qa-text-primary">{data['images']}</p>
                    </div>
                </div>
            """)
        return data
    except Exception as e:
        if is_htmx:
            return HTMLResponse(content=f"""
                <div class="qa-empty qa-p-4">
                    <p class="qa-text-danger">Error: {str(e)}</p>
                </div>
            """)
        return {"error": str(e)}


@app.get("/docker/images", tags=["Docker"])
def list_docker_images():
    """List all Docker images"""
    global docker_service

    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service not available"
        )

    try:
        images = docker_service.client.images.list()
        return [
            {
                "id": img.short_id,
                "tags": img.tags,
                "size": f"{img.attrs.get('Size', 0) / (1024**2):.1f} MB",
                "created": img.attrs.get("Created", "")[:10]
            }
            for img in images
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/docker/volumes", tags=["Docker"])
def list_docker_volumes():
    """List all Docker volumes"""
    global docker_service

    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service not available"
        )

    try:
        volumes = docker_service.client.volumes.list()
        return [
            {
                "name": vol.name,
                "driver": vol.attrs.get("Driver", "local"),
                "mountpoint": vol.attrs.get("Mountpoint", "")
            }
            for vol in volumes
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/docker/networks", tags=["Docker"])
def list_docker_networks():
    """List all Docker networks"""
    global docker_service

    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service not available"
        )

    try:
        networks = docker_service.client.networks.list()
        return [
            {
                "id": net.short_id,
                "name": net.name,
                "driver": net.attrs.get("Driver", ""),
                "scope": net.attrs.get("Scope", ""),
                "subnet": net.attrs.get("IPAM", {}).get("Config", [{}])[0].get("Subnet", "N/A") if net.attrs.get("IPAM", {}).get("Config") else "N/A"
            }
            for net in networks
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/docker/containers/{container_id}/start", tags=["Docker"])
def start_container(container_id: str):
    """Start a Docker container"""
    global docker_service

    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service not available"
        )

    try:
        container = docker_service.client.containers.get(container_id)
        container.start()
        return {"success": True, "message": f"Container {container_id} started"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/docker/containers/{container_id}/stop", tags=["Docker"])
def stop_container(container_id: str):
    """Stop a Docker container"""
    global docker_service

    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service not available"
        )

    try:
        container = docker_service.client.containers.get(container_id)
        container.stop()
        return {"success": True, "message": f"Container {container_id} stopped"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/docker/containers/{container_id}/restart", tags=["Docker"])
def restart_container(container_id: str):
    """Restart a Docker container"""
    global docker_service

    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service not available"
        )

    try:
        container = docker_service.client.containers.get(container_id)
        container.restart()
        return {"success": True, "message": f"Container {container_id} restarted"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/docker/containers/{container_id}/logs", tags=["Docker"])
def get_container_logs(container_id: str, lines: int = 100):
    """Get logs from a Docker container"""
    global docker_service

    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service not available"
        )

    try:
        container = docker_service.client.containers.get(container_id)
        logs = container.logs(tail=lines, timestamps=True).decode('utf-8', errors='replace')
        return logs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.delete("/docker/containers/{container_id}", tags=["Docker"])
def remove_docker_container(container_id: str, force: bool = False):
    """Remove a Docker container"""
    global docker_service

    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service not available"
        )

    try:
        container = docker_service.client.containers.get(container_id)
        container.remove(force=force)
        return {"success": True, "message": f"Container {container_id} removed"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# DEPLOYMENT ENDPOINTS
# ============================================================================

@app.get("/deployments", tags=["Deploy"])
def list_deployments(
    project_id: int = None,
    limit: int = 20,
    user: User = Depends(require_auth)
):
    """List recent deployments"""
    try:
        from .deploy_service import get_deploy_service
    except ImportError:
        from deploy_service import get_deploy_service

    deploy_service = get_deploy_service()
    deployments = deploy_service.list_deployments(project_id=project_id, limit=limit)
    return [d.to_dict() for d in deployments]


@app.post("/deploy", tags=["Deploy"])
def create_deployment(
    project_id: int,
    environment: str = "local",
    branch: str = "main",
    strategy: str = "rolling",
    run_migrations: bool = False,
    health_check: bool = True,
    notify: bool = False,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Create and start a new deployment

    Args:
        project_id: Project to deploy
        environment: Target environment (local, docker, staging, production)
        branch: Git branch to deploy
        strategy: Deployment strategy (rolling, blue-green, recreate)
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    try:
        from .deploy_service import get_deploy_service
    except ImportError:
        from deploy_service import get_deploy_service

    deploy_service = get_deploy_service()

    # Create deployment
    deployment = deploy_service.create_deployment(
        project_id=project_id,
        project_name=project.name,
        environment=environment,
        branch=branch,
        strategy=strategy,
        triggered_by=user.username
    )

    # Start deployment asynchronously
    deploy_service.start_deployment(deployment.id, run_async=True)

    return {
        "deploy_id": deployment.id,
        "project_id": project_id,
        "project_name": project.name,
        "environment": environment,
        "branch": branch,
        "status": "started",
        "message": "Deployment initiated"
    }


@app.get("/deploy/{deploy_id}/status", tags=["Deploy"])
def get_deployment_status(
    deploy_id: str,
    user: User = Depends(require_auth)
):
    """Get deployment status and logs"""
    try:
        from .deploy_service import get_deploy_service
    except ImportError:
        from deploy_service import get_deploy_service

    deploy_service = get_deploy_service()
    deployment = deploy_service.get_deployment(deploy_id)

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )

    return {
        "deploy_id": deployment.id,
        "project_id": deployment.project_id,
        "environment": deployment.environment,
        "status": deployment.status.value,
        "completed": deployment.status.value in ("completed", "failed", "cancelled", "rolled_back"),
        "failed": deployment.status.value == "failed",
        "steps": [{"name": s.name, "status": s.status, "message": s.message} for s in deployment.steps],
        "logs": deployment.logs,
        "error_message": deployment.error_message,
        "started_at": deployment.started_at.isoformat() if deployment.started_at else None,
        "completed_at": deployment.completed_at.isoformat() if deployment.completed_at else None
    }


@app.post("/deploy/{deploy_id}/cancel", tags=["Deploy"])
def cancel_deployment(
    deploy_id: str,
    user: User = Depends(require_auth)
):
    """Cancel a running deployment"""
    try:
        from .deploy_service import get_deploy_service
    except ImportError:
        from deploy_service import get_deploy_service

    deploy_service = get_deploy_service()

    if not deploy_service.cancel_deployment(deploy_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel deployment (not found or not running)"
        )

    return {
        "success": True,
        "message": f"Deployment {deploy_id} cancelled"
    }


@app.post("/deploy/{deploy_id}/rollback", tags=["Deploy"])
def rollback_deployment(
    deploy_id: str,
    user: User = Depends(require_auth)
):
    """Rollback a deployment to previous version"""
    try:
        from .deploy_service import get_deploy_service
    except ImportError:
        from deploy_service import get_deploy_service

    deploy_service = get_deploy_service()
    rollback = deploy_service.rollback_deployment(deploy_id)

    if not rollback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )

    return {
        "success": True,
        "rollback_deploy_id": rollback.id,
        "message": f"Rollback initiated for deployment {deploy_id}"
    }


@app.get("/projects/{project_id}/environments/{env_id}/versions", tags=["Deploy Versions"])
def list_environment_versions(
    project_id: int,
    env_id: int,
    limit: int = 10,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    List deployment versions for an environment.
    These are potential rollback targets.
    """
    versions = db.query(models.DeploymentVersion).filter(
        models.DeploymentVersion.project_id == project_id,
        models.DeploymentVersion.environment_id == env_id,
        models.DeploymentVersion.is_rollback_target == True
    ).order_by(models.DeploymentVersion.created_at.desc()).limit(limit).all()

    return [v.to_dict() for v in versions]


@app.post("/projects/{project_id}/environments/{env_id}/rollback", tags=["Deploy"])
def rollback_to_version(
    project_id: int,
    env_id: int,
    target_version_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Rollback an environment to a specific deployment version.

    This will:
    1. Stop the current container
    2. Start the container with the old image/tag
    3. Run health check
    4. Update version flags in database
    5. Create audit log entry
    """
    try:
        from .deploy_service import get_deploy_service
    except ImportError:
        from deploy_service import get_deploy_service

    # Get project
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get environment
    environment = db.query(models.Environment).filter(
        models.Environment.id == env_id,
        models.Environment.project_id == project_id
    ).first()
    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")

    # Get target version
    target_version = db.query(models.DeploymentVersion).filter(
        models.DeploymentVersion.id == target_version_id,
        models.DeploymentVersion.project_id == project_id,
        models.DeploymentVersion.environment_id == env_id
    ).first()
    if not target_version:
        raise HTTPException(status_code=404, detail="Target version not found")

    # Get current version for audit
    current_version = db.query(models.DeploymentVersion).filter(
        models.DeploymentVersion.project_id == project_id,
        models.DeploymentVersion.environment_id == env_id,
        models.DeploymentVersion.is_current == True
    ).first()

    # Perform rollback
    deploy_service = get_deploy_service()
    rollback = deploy_service.rollback_to_version(
        project_id=project_id,
        project_name=project.name,
        environment=environment.name,
        target_version_id=target_version_id,
        docker_client=docker_service.client if docker_service else None,
        docker_image=target_version.docker_image,
        docker_tag=target_version.docker_tag
    )

    if rollback and rollback.status.value == "completed":
        # Update version flags
        if current_version:
            current_version.is_current = False
        target_version.is_current = True
        db.commit()

        # Audit log
        audit_log(
            db,
            action=AuditAction.ROLLBACK,
            resource_type="environment",
            resource_id=env_id,
            resource_name=f"{project.name}/{environment.name}",
            user_id=user.username,
            user_ip=request.client.host if request.client else None,
            project_id=project_id,
            details={
                "from_version": current_version.id if current_version else None,
                "to_version": target_version_id,
                "target_commit": target_version.git_commit,
                "target_tag": target_version.docker_tag
            },
            request_method="POST",
            request_path=f"/projects/{project_id}/environments/{env_id}/rollback"
        )

        return {
            "success": True,
            "message": f"Rolled back to version {target_version_id}",
            "deploy_id": rollback.id,
            "target_version": target_version.to_dict()
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Rollback failed: {rollback.error_message if rollback else 'Unknown error'}"
        )


@app.get("/api/projects/{project_id}/environments/{env_id}/rollback-html", response_class=HTMLResponse, tags=["Deploy"])
def get_rollback_html(
    project_id: int,
    env_id: int,
    db: Session = Depends(get_db)
):
    """Get rollback UI as HTML"""
    versions = db.query(models.DeploymentVersion).filter(
        models.DeploymentVersion.project_id == project_id,
        models.DeploymentVersion.environment_id == env_id,
        models.DeploymentVersion.is_rollback_target == True
    ).order_by(models.DeploymentVersion.created_at.desc()).limit(10).all()

    if not versions:
        return HTMLResponse(content='''
            <div class="qa-text-center qa-p-6">
                <p class="qa-text-muted">No previous versions available for rollback</p>
            </div>
        ''')

    html = '<div class="qa-list">'
    for v in versions:
        current_badge = '<span class="qa-badge qa-badge-success qa-ml-2">Current</span>' if v.is_current else ''
        commit_short = v.git_commit[:7] if v.git_commit else 'N/A'
        created = v.created_at.strftime('%Y-%m-%d %H:%M') if v.created_at else ''

        html += f'''
            <div class="qa-list-item qa-flex qa-justify-between qa-items-center qa-p-3" style="border-bottom: 1px solid var(--q-border);">
                <div>
                    <div class="qa-flex qa-items-center qa-gap-2">
                        <span class="qa-font-mono qa-font-bold">{commit_short}</span>
                        {current_badge}
                    </div>
                    <p class="qa-text-sm qa-text-muted qa-mt-1">{v.git_message or 'No message'}</p>
                    <p class="qa-text-xs qa-text-dim qa-mt-1">{created} - {v.docker_tag or 'latest'}</p>
                </div>
                {"" if v.is_current else f'''
                <button class="qa-btn qa-btn-warning qa-btn-sm"
                        onclick="confirmRollback({v.id}, '{commit_short}')"
                        hx-post="{URL_PREFIX}/projects/{project_id}/environments/{env_id}/rollback?target_version_id={v.id}"
                        hx-confirm="Are you sure you want to rollback to {commit_short}?"
                        hx-target="closest .qa-card-body"
                        hx-swap="innerHTML">
                    Rollback
                </button>
                '''}
            </div>
        '''
    html += '</div>'

    return HTMLResponse(content=html)


# ============================================================================
# ENVIRONMENT ENDPOINTS (Multi-environment Deploy)
# ============================================================================

try:
    from .environment_service import get_environment_service
    from .pipeline_service import get_pipeline_service
    from .webhook_service import get_webhook_service
    from .websocket_manager import get_websocket_manager
except ImportError:
    from environment_service import get_environment_service
    from pipeline_service import get_pipeline_service
    from webhook_service import get_webhook_service
    from websocket_manager import get_websocket_manager


@app.get("/projects/{project_id}/environments", tags=["Environments"])
def list_environments(
    project_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all environments for a project"""
    env_service = get_environment_service(db)
    environments = env_service.list_environments(project_id, active_only)
    return [env.to_dict() for env in environments]


@app.post("/projects/{project_id}/environments", tags=["Environments"])
def create_environment(
    project_id: int,
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Create a new environment"""
    env_service = get_environment_service(db)
    try:
        env = env_service.create_environment(project_id, data)
        return {"success": True, "environment": env.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/projects/{project_id}/environments/{env_id}", tags=["Environments"])
def get_environment(
    project_id: int,
    env_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific environment"""
    env_service = get_environment_service(db)
    env = env_service.get_environment(env_id)
    if not env or env.project_id != project_id:
        raise HTTPException(status_code=404, detail="Environment not found")
    return env.to_dict()


@app.put("/projects/{project_id}/environments/{env_id}", tags=["Environments"])
def update_environment(
    project_id: int,
    env_id: int,
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Update an environment"""
    env_service = get_environment_service(db)
    env = env_service.update_environment(env_id, data)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    return {"success": True, "environment": env.to_dict()}


@app.delete("/projects/{project_id}/environments/{env_id}", tags=["Environments"])
def delete_environment(
    project_id: int,
    env_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Delete an environment"""
    env_service = get_environment_service(db)
    if not env_service.delete_environment(env_id):
        raise HTTPException(status_code=404, detail="Environment not found")
    return {"success": True}


@app.post("/projects/{project_id}/environments/{env_id}/test", tags=["Environments"])
async def test_environment_connection(
    project_id: int,
    env_id: int,
    db: Session = Depends(get_db)
):
    """Test Docker connection to an environment"""
    env_service = get_environment_service(db)
    result = await env_service.test_connection(env_id)
    return result


@app.post("/projects/{project_id}/environments/{env_id}/launch", tags=["Environments"])
async def launch_app_in_environment(
    project_id: int,
    env_id: int,
    db: Session = Depends(get_db)
):
    """
    Launch the Quantum application for a specific project/environment.

    This starts the Quantum CLI server in development mode and returns the URL.
    """
    import subprocess
    import socket

    try:
        from .environment_service import get_environment_service
    except ImportError:
        from environment_service import get_environment_service

    # Get project and environment
    project = crud.get_project(db, project_id)
    if not project:
        return {"success": False, "error": "Project not found"}

    env_service = get_environment_service(db)
    environment = env_service.get_environment(env_id)
    if not environment:
        return {"success": False, "error": "Environment not found"}

    # Get source path from project
    source_path = project.source_path
    if not source_path:
        return {"success": False, "error": "Project source_path not configured. Set it in the Source tab."}

    # Check if source path exists
    if not os.path.exists(source_path):
        return {"success": False, "error": f"Source path not found: {source_path}"}

    # Get port from environment or find available port
    env_dict = environment.to_dict()
    port = env_dict.get("port")

    if not port:
        # Find an available port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            port = s.getsockname()[1]

    # Determine the Quantum CLI path
    quantum_cli = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src", "cli", "runner.py")

    if not os.path.exists(quantum_cli):
        return {"success": False, "error": f"Quantum CLI not found at: {quantum_cli}"}

    # Start the Quantum server in background
    try:
        # Build the command
        cmd = [
            "python", quantum_cli,
            "start",
            "--port", str(port),
            "--root", source_path
        ]

        # Set environment variables based on the environment config
        env_vars = os.environ.copy()
        env_vars["QUANTUM_ENV"] = env_dict.get("name", "development")

        # Start the server as a background process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=source_path,
            env=env_vars,
            start_new_session=True
        )

        # Give it a moment to start
        import time
        time.sleep(1)

        # Check if process started successfully
        if process.poll() is not None:
            # Process already terminated
            stderr = process.stderr.read().decode() if process.stderr else ""
            return {"success": False, "error": f"Failed to start server: {stderr}"}

        # Return the URL
        url = f"http://localhost:{port}"

        return {
            "success": True,
            "url": url,
            "port": port,
            "pid": process.pid,
            "environment": env_dict.get("name"),
            "source_path": source_path
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/projects/{project_id}/environments/{env_id}/approve", tags=["Environments"])
def approve_environment(
    project_id: int,
    env_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Approve an environment for deployment (required for production)"""
    env_service = get_environment_service(db)
    if not env_service.approve_environment(env_id, user.username):
        raise HTTPException(status_code=404, detail="Environment not found")
    return {"success": True, "approved_by": user.username}


@app.post("/projects/{project_id}/environments/defaults", tags=["Environments"])
def create_default_environments(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Create default environments (dev, staging, production)"""
    env_service = get_environment_service(db)
    environments = env_service.create_default_environments(project_id)
    return {"success": True, "environments": [e.to_dict() for e in environments]}


# ============================================================================
# PIPELINE ENDPOINTS (Advanced Deploy)
# ============================================================================

@app.post("/deploy/start", tags=["Deploy Pipeline"])
async def start_pipeline(
    project_id: int,
    environment_id: int,
    git_branch: Optional[str] = None,
    git_commit: Optional[str] = None,
    skip_test: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Start a deployment pipeline

    This is the main entry point for the new multi-environment deploy system.
    It uses Git, Docker, health checks, and supports rollback.
    """
    pipeline = get_pipeline_service(db)

    deployment = await pipeline.run_pipeline(
        project_id=project_id,
        environment_id=environment_id,
        triggered_by=user.username,
        git_commit=git_commit,
        git_branch=git_branch,
        skip_test=skip_test
    )

    if not deployment:
        raise HTTPException(status_code=400, detail="Failed to start deployment")

    return {
        "success": True,
        "deployment_id": deployment.id,
        "status": deployment.status,
        "message": "Deployment pipeline started"
    }


@app.get("/deploy/pipeline/{deployment_id}", tags=["Deploy Pipeline"])
def get_pipeline_status(
    deployment_id: int,
    db: Session = Depends(get_db)
):
    """Get status of a deployment pipeline"""
    pipeline = get_pipeline_service(db)
    status = pipeline.get_pipeline_status(deployment_id)

    if not status:
        raise HTTPException(status_code=404, detail="Deployment not found")

    return status


@app.get("/deploy/pipeline/{deployment_id}/logs", tags=["Deploy Pipeline"])
def get_pipeline_logs(
    deployment_id: int,
    limit: int = 100
):
    """Get logs from a deployment pipeline"""
    ws_manager = get_websocket_manager()
    logs = ws_manager.get_logs(str(deployment_id), limit)
    return {"logs": logs}


@app.post("/deploy/pipeline/{deployment_id}/cancel", tags=["Deploy Pipeline"])
async def cancel_pipeline(
    deployment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Cancel a running pipeline"""
    pipeline = get_pipeline_service(db)

    if await pipeline.cancel_pipeline(deployment_id):
        return {"success": True, "message": "Pipeline cancelled"}

    raise HTTPException(status_code=400, detail="Cannot cancel pipeline")


@app.post("/deploy/pipeline/{deployment_id}/rollback", tags=["Deploy Pipeline"])
async def rollback_pipeline(
    deployment_id: int,
    target_version_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Rollback to a previous version"""
    pipeline = get_pipeline_service(db)

    rollback = await pipeline.rollback(
        deployment_id=deployment_id,
        target_version_id=target_version_id,
        triggered_by=user.username
    )

    if not rollback:
        raise HTTPException(status_code=400, detail="Failed to start rollback")

    return {
        "success": True,
        "deployment_id": rollback.id,
        "message": "Rollback initiated"
    }


@app.post("/deploy/pipeline/{deployment_id}/promote", tags=["Deploy Pipeline"])
async def promote_deployment(
    deployment_id: int,
    target_environment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Promote a deployment to the next environment"""
    pipeline = get_pipeline_service(db)

    promotion = await pipeline.promote(
        deployment_id=deployment_id,
        target_env_id=target_environment_id,
        triggered_by=user.username
    )

    if not promotion:
        raise HTTPException(status_code=400, detail="Failed to promote deployment")

    return {
        "success": True,
        "deployment_id": promotion.id,
        "message": "Promotion initiated"
    }


# ============================================================================
# DEPLOYMENT VERSIONS
# ============================================================================

@app.get("/projects/{project_id}/versions", tags=["Deploy Versions"])
def list_deployment_versions(
    project_id: int,
    environment_id: Optional[int] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """List deployment versions for a project"""
    try:
        from .models import DeploymentVersion
    except ImportError:
        from models import DeploymentVersion

    query = db.query(DeploymentVersion).filter(DeploymentVersion.project_id == project_id)

    if environment_id:
        query = query.filter(DeploymentVersion.environment_id == environment_id)

    versions = query.order_by(DeploymentVersion.created_at.desc()).limit(limit).all()
    return [v.to_dict() for v in versions]


@app.get("/projects/{project_id}/versions/{version_id}", tags=["Deploy Versions"])
def get_deployment_version(
    project_id: int,
    version_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific deployment version"""
    try:
        from .models import DeploymentVersion
    except ImportError:
        from models import DeploymentVersion

    version = db.query(DeploymentVersion).filter(
        DeploymentVersion.id == version_id,
        DeploymentVersion.project_id == project_id
    ).first()

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return version.to_dict()


# ============================================================================
# WEBHOOK ENDPOINTS (CI/CD)
# ============================================================================

@app.post("/webhooks/github", tags=["Webhooks"])
async def github_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    GitHub webhook endpoint

    Configure in GitHub: Settings > Webhooks > Add webhook
    - Payload URL: https://your-domain/webhooks/github
    - Content type: application/json
    - Secret: (set GITHUB_WEBHOOK_SECRET env var)
    - Events: Push
    """
    webhook_service = get_webhook_service(db)

    # Get raw body for signature verification
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not webhook_service.verify_github_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Check event type
    event_type = request.headers.get("X-GitHub-Event", "")

    if event_type == "push":
        event, deployment_id = await webhook_service.process_github_push(payload)
        return {
            "success": True,
            "event_id": event.id,
            "deployment_id": deployment_id,
            "message": "Push event processed"
        }
    elif event_type == "ping":
        return {"success": True, "message": "Pong!"}
    else:
        return {"success": True, "message": f"Event {event_type} ignored"}


@app.post("/webhooks/gitlab", tags=["Webhooks"])
async def gitlab_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    GitLab webhook endpoint

    Configure in GitLab: Settings > Webhooks
    - URL: https://your-domain/webhooks/gitlab
    - Secret token: (set GITLAB_WEBHOOK_TOKEN env var)
    - Trigger: Push events
    """
    webhook_service = get_webhook_service(db)

    # Verify token
    token = request.headers.get("X-Gitlab-Token", "")

    if not webhook_service.verify_gitlab_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")

    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Check event type
    event_type = payload.get("object_kind", "")

    if event_type == "push":
        event, deployment_id = await webhook_service.process_gitlab_push(payload)
        return {
            "success": True,
            "event_id": event.id,
            "deployment_id": deployment_id,
            "message": "Push event processed"
        }
    else:
        return {"success": True, "message": f"Event {event_type} ignored"}


@app.get("/webhooks/events", tags=["Webhooks"])
def list_webhook_events(
    project_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """List recent webhook events"""
    webhook_service = get_webhook_service(db)
    events = webhook_service.list_events(project_id=project_id, limit=limit)
    return [e.to_dict() for e in events]


@app.get("/webhooks/events/{event_id}", tags=["Webhooks"])
def get_webhook_event(
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Get details of a specific webhook event"""
    webhook_service = get_webhook_service(db)
    event = webhook_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event.to_dict()


# ============================================================================
# CI/CD PIPELINE STATUS ENDPOINTS
# ============================================================================

@app.get("/projects/{project_id}/pipelines", tags=["CI/CD"])
def list_pipelines(
    project_id: int,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    List recent CI/CD pipelines (webhook events with deployments) for a project

    Returns combined view of deployments triggered by webhooks.
    """
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get webhook events as pipeline records
    webhook_service = get_webhook_service(db)
    events = webhook_service.list_events(project_id=project_id, limit=limit)

    pipelines = []
    for event in events:
        pipelines.append({
            "id": event.id,
            "status": "completed" if event.processed else "pending",
            "provider": event.provider,
            "event_type": event.event_type,
            "triggered_by": f"webhook:{event.provider}",
            "received_at": event.received_at.isoformat() if event.received_at else None,
            "deployment_id": event.deployment_id,
            "git_commit": event.commit,
            "git_branch": event.branch,
            "git_message": event.message,
            "author": event.author,
            "error": event.error_message
        })

    return {"pipelines": pipelines, "total": len(pipelines)}


@app.get("/projects/{project_id}/pipelines/{pipeline_id}/status", tags=["CI/CD"])
def get_pipeline_status(
    project_id: int,
    pipeline_id: int,
    db: Session = Depends(get_db)
):
    """Get current status of a pipeline (webhook event)"""
    webhook_service = get_webhook_service(db)
    event = webhook_service.get_event(pipeline_id)

    if not event or event.project_id != project_id:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    return {
        "id": event.id,
        "status": "completed" if event.processed else "pending",
        "received_at": event.received_at.isoformat() if event.received_at else None,
        "deployment_id": event.deployment_id,
        "git_commit": event.commit,
        "git_branch": event.branch,
        "error_message": event.error_message
    }


@app.get("/projects/{project_id}/badge.svg", tags=["CI/CD"])
def get_build_badge(
    project_id: int,
    branch: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get build status badge (SVG format)

    Returns an SVG badge showing the latest build/pipeline status.
    Can be embedded in README.md files.
    """
    from fastapi.responses import Response

    project = crud.get_project(db, project_id)
    if not project:
        return Response(
            content=_generate_badge("build", "unknown", "#9f9f9f"),
            media_type="image/svg+xml"
        )

    # Get latest webhook event as pipeline status
    webhook_service = get_webhook_service(db)
    events = webhook_service.list_events(project_id=project_id, limit=1)

    if not events:
        return Response(
            content=_generate_badge("build", "no builds", "#9f9f9f"),
            media_type="image/svg+xml"
        )

    event = events[0]

    # Determine badge based on webhook event processing status
    if event.processed and not event.error_message:
        color = "#4c1"  # Green
        label = "passing"
    elif event.error_message:
        color = "#e05d44"  # Red
        label = "failing"
    elif not event.processed:
        color = "#dfb317"  # Yellow
        label = "pending"
    else:
        color = "#9f9f9f"  # Gray
        label = "unknown"

    return Response(
        content=_generate_badge("build", label, color),
        media_type="image/svg+xml"
    )


@app.get("/projects/{project_id}/tests/badge.svg", tags=["CI/CD"])
def get_tests_badge(
    project_id: int,
    db: Session = Depends(get_db)
):
    """
    Get test status badge (SVG format)

    Returns an SVG badge showing the latest test results.
    """
    from fastapi.responses import Response

    # Get latest test run
    test_runs = crud.get_test_runs(db, project_id, limit=1)
    if not test_runs:
        return Response(
            content=_generate_badge("tests", "no tests", "#9f9f9f"),
            media_type="image/svg+xml"
        )

    test_run = test_runs[0]

    # Determine badge content
    if test_run.status == "completed" and test_run.failed_tests == 0:
        color = "#4c1"  # Green
        label = f"{test_run.passed_tests} passing"
    elif test_run.status == "running":
        color = "#dfb317"  # Yellow
        label = "running"
    elif test_run.failed_tests > 0:
        color = "#e05d44"  # Red
        label = f"{test_run.failed_tests} failing"
    else:
        color = "#9f9f9f"  # Gray
        label = test_run.status

    return Response(
        content=_generate_badge("tests", label, color),
        media_type="image/svg+xml"
    )


def _generate_badge(left_text: str, right_text: str, color: str) -> str:
    """Generate an SVG badge"""
    left_width = len(left_text) * 7 + 10
    right_width = len(right_text) * 7 + 10
    total_width = left_width + right_width

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20">
  <linearGradient id="smooth" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <rect rx="3" width="{total_width}" height="20" fill="#555"/>
  <rect rx="3" x="{left_width}" width="{right_width}" height="20" fill="{color}"/>
  <rect rx="3" width="{total_width}" height="20" fill="url(#smooth)"/>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="{left_width/2}" y="15" fill="#010101" fill-opacity=".3">{left_text}</text>
    <text x="{left_width/2}" y="14">{left_text}</text>
    <text x="{left_width + right_width/2}" y="15" fill="#010101" fill-opacity=".3">{right_text}</text>
    <text x="{left_width + right_width/2}" y="14">{right_text}</text>
  </g>
</svg>'''


@app.post("/projects/{project_id}/pipelines/{pipeline_id}/retry", tags=["CI/CD"])
async def retry_pipeline(
    project_id: int,
    pipeline_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Retry a failed pipeline (based on webhook event)"""
    # Get the webhook event as pipeline reference
    webhook_service = get_webhook_service(db)
    event = webhook_service.get_event(pipeline_id)

    if not event or event.project_id != project_id:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    if event.processed and not event.error_message:
        raise HTTPException(status_code=400, detail="Pipeline already succeeded, no retry needed")

    # Get pipeline service and retry
    try:
        from .pipeline_service import get_pipeline_service
    except ImportError:
        from pipeline_service import get_pipeline_service

    try:
        pipeline = get_pipeline_service()
        # Get first active environment for the project
        env = db.query(Environment).filter(
            Environment.project_id == project_id,
            Environment.is_active == True
        ).first()

        if not env:
            raise HTTPException(status_code=400, detail="No active environment found")

        new_deployment = await pipeline.run_pipeline(
            project_id=project_id,
            environment_id=env.id,
            triggered_by=f"retry:{user.username}",
            git_commit=event.commit,
            git_branch=event.branch
        )
        return {
            "success": True,
            "new_pipeline_id": new_deployment.id if new_deployment else None,
            "message": "Pipeline retry started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_id}/ci-cd/dashboard", response_class=HTMLResponse, tags=["CI/CD"])
def get_cicd_dashboard_html(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Get CI/CD dashboard HTML with pipeline overview"""
    project = crud.get_project(db, project_id)
    if not project:
        return HTMLResponse(content='<div class="qa-error">Application not found</div>')

    # Get webhook events as pipeline history
    webhook_service = get_webhook_service(db)
    events = webhook_service.list_events(project_id=project_id, limit=10)

    html = f'''
    <div class="qa-cicd-dashboard">
        <!-- Webhook Setup Info -->
        <div class="qa-card qa-mb-4">
            <div class="qa-card-header">
                <h4>Webhook Configuration</h4>
            </div>
            <div class="qa-card-body">
                <div class="qa-grid qa-grid-2">
                    <div>
                        <h5>GitHub</h5>
                        <code class="qa-code-block">/webhooks/github</code>
                        <p class="qa-text-muted qa-text-sm">Set GITHUB_WEBHOOK_SECRET env var</p>
                    </div>
                    <div>
                        <h5>GitLab</h5>
                        <code class="qa-code-block">/webhooks/gitlab</code>
                        <p class="qa-text-muted qa-text-sm">Set GITLAB_WEBHOOK_TOKEN env var</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Badges -->
        <div class="qa-card qa-mb-4">
            <div class="qa-card-header">
                <h4>Status Badges</h4>
            </div>
            <div class="qa-card-body">
                <p>Add these to your README.md:</p>
                <code class="qa-code-block">
                    ![Build](https://your-domain/projects/{project_id}/badge.svg)
                    ![Tests](https://your-domain/projects/{project_id}/tests/badge.svg)
                </code>
            </div>
        </div>

        <!-- Recent Pipelines -->
        <div class="qa-card qa-mb-4">
            <div class="qa-card-header">
                <h4>Recent Pipelines</h4>
            </div>
            <div class="qa-card-body">
    '''

    # Use events as pipeline history
    if not events:
        html += '<p class="qa-text-muted">No pipelines yet. Configure webhooks to enable CI/CD.</p>'
    else:
        html += '''
                <table class="qa-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Status</th>
                            <th>Branch</th>
                            <th>Commit</th>
                            <th>Author</th>
                            <th>Time</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        '''

        for e in events:
            if e.processed and not e.error_message:
                status = "success"
                status_badge = "qa-badge-success"
            elif e.error_message:
                status = "failed"
                status_badge = "qa-badge-danger"
            else:
                status = "pending"
                status_badge = "qa-badge-gray"

            commit_short = (e.commit[:7] if e.commit else '-')
            time_str = e.received_at.strftime('%Y-%m-%d %H:%M') if e.received_at else '-'

            html += f'''
                        <tr>
                            <td>#{e.id}</td>
                            <td><span class="qa-badge {status_badge}">{status}</span></td>
                            <td>{e.branch or '-'}</td>
                            <td><code>{commit_short}</code></td>
                            <td>{e.author or '-'}</td>
                            <td>{time_str}</td>
                            <td>
                                <button class="qa-btn qa-btn-sm"
                                        hx-post="{URL_PREFIX}/projects/{project_id}/pipelines/{e.id}/retry"
                                        hx-swap="none">
                                    Retry
                                </button>
                            </td>
                        </tr>
            '''

        html += '''
                    </tbody>
                </table>
        '''

    html += '''
            </div>
        </div>

        <!-- Recent Webhook Events -->
        <div class="qa-card">
            <div class="qa-card-header">
                <h4>Recent Webhook Events</h4>
            </div>
            <div class="qa-card-body">
    '''

    if not events:
        html += '<p class="qa-text-muted">No webhook events yet</p>'
    else:
        html += '''
                <table class="qa-table">
                    <thead>
                        <tr>
                            <th>Provider</th>
                            <th>Event</th>
                            <th>Branch</th>
                            <th>Commit</th>
                            <th>Author</th>
                            <th>Received</th>
                        </tr>
                    </thead>
                    <tbody>
        '''

        for e in events:
            received = e.received_at.strftime('%Y-%m-%d %H:%M') if e.received_at else '-'
            commit_short = e.commit[:8] if e.commit else '-'

            html += f'''
                        <tr>
                            <td>{e.provider}</td>
                            <td>{e.event_type}</td>
                            <td>{e.branch or '-'}</td>
                            <td><code>{commit_short}</code></td>
                            <td>{e.author or '-'}</td>
                            <td>{received}</td>
                        </tr>
            '''

        html += '''
                    </tbody>
                </table>
        '''

    html += '''
            </div>
        </div>

        <!-- Logs container -->
        <div id="pipeline-logs" class="qa-mt-4"></div>
    </div>
    '''

    return HTMLResponse(content=html)


# ============================================================================
# JOB MANAGEMENT ENDPOINTS
# ============================================================================

try:
    from .job_service import get_job_service
except ImportError:
    from job_service import get_job_service


@app.get("/jobs", tags=["Jobs"])
def list_all_jobs(
    queue: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    user: User = Depends(require_auth)
):
    """List all queued jobs"""
    job_service = get_job_service()
    return {
        "jobs": job_service.list_jobs(queue=queue, status=status, limit=limit),
        "total": len(job_service.list_jobs(queue=queue, status=status, limit=1000))
    }


@app.get("/jobs/overview", tags=["Jobs"])
def get_jobs_overview(user: User = Depends(require_auth)):
    """Get job system overview with stats"""
    job_service = get_job_service()
    return job_service.get_overview()


@app.get("/jobs/{job_id}", tags=["Jobs"])
def get_job_details(
    job_id: int,
    user: User = Depends(require_auth)
):
    """Get job details by ID"""
    job_service = get_job_service()
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/jobs/{job_id}/cancel", tags=["Jobs"])
def cancel_job(
    job_id: int,
    user: User = Depends(require_auth)
):
    """Cancel a pending job"""
    job_service = get_job_service()
    success = job_service.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Could not cancel job")
    return {"success": True, "message": "Job cancelled"}


@app.post("/jobs/{job_id}/retry", tags=["Jobs"])
def retry_job(
    job_id: int,
    user: User = Depends(require_auth)
):
    """Retry a failed job"""
    job_service = get_job_service()
    success = job_service.retry_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Could not retry job")
    return {"success": True, "message": "Job queued for retry"}


@app.post("/jobs/dispatch", tags=["Jobs"])
def dispatch_job(
    name: str,
    queue: str = 'default',
    params: Optional[Dict] = None,
    delay: Optional[str] = None,
    priority: int = 0,
    user: User = Depends(require_auth)
):
    """Dispatch a new job to the queue"""
    job_service = get_job_service()
    job_id = job_service.dispatch_job(
        name=name,
        queue=queue,
        params=params or {},
        delay=delay,
        priority=priority
    )
    if not job_id:
        raise HTTPException(status_code=500, detail="Could not dispatch job")
    return {"success": True, "job_id": job_id}


# ============================================================================
# SCHEDULE MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/schedules", tags=["Jobs"])
def list_schedules(user: User = Depends(require_auth)):
    """List all scheduled tasks"""
    job_service = get_job_service()
    return {"schedules": job_service.list_schedules()}


@app.get("/schedules/{name}", tags=["Jobs"])
def get_schedule_details(
    name: str,
    user: User = Depends(require_auth)
):
    """Get schedule details by name"""
    job_service = get_job_service()
    schedule = job_service.get_schedule(name)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@app.post("/schedules/{name}/pause", tags=["Jobs"])
def pause_schedule(
    name: str,
    user: User = Depends(require_auth)
):
    """Pause a scheduled task"""
    job_service = get_job_service()
    success = job_service.pause_schedule(name)
    if not success:
        raise HTTPException(status_code=400, detail="Could not pause schedule")
    return {"success": True, "message": "Schedule paused"}


@app.post("/schedules/{name}/resume", tags=["Jobs"])
def resume_schedule(
    name: str,
    user: User = Depends(require_auth)
):
    """Resume a paused schedule"""
    job_service = get_job_service()
    success = job_service.resume_schedule(name)
    if not success:
        raise HTTPException(status_code=400, detail="Could not resume schedule")
    return {"success": True, "message": "Schedule resumed"}


@app.post("/schedules/{name}/run", tags=["Jobs"])
def run_schedule_now(
    name: str,
    user: User = Depends(require_auth)
):
    """Trigger immediate execution of a schedule"""
    job_service = get_job_service()
    success = job_service.run_schedule_now(name)
    if not success:
        raise HTTPException(status_code=400, detail="Could not run schedule")
    return {"success": True, "message": "Schedule triggered"}


@app.delete("/schedules/{name}", tags=["Jobs"])
def remove_schedule(
    name: str,
    user: User = Depends(require_auth)
):
    """Remove a scheduled task"""
    job_service = get_job_service()
    success = job_service.remove_schedule(name)
    if not success:
        raise HTTPException(status_code=400, detail="Could not remove schedule")
    return {"success": True, "message": "Schedule removed"}


# ============================================================================
# THREAD MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/threads", tags=["Jobs"])
def list_threads(
    status: Optional[str] = None,
    user: User = Depends(require_auth)
):
    """List all threads"""
    job_service = get_job_service()
    return {"threads": job_service.list_threads(status=status)}


@app.get("/threads/{name}", tags=["Jobs"])
def get_thread_details(
    name: str,
    user: User = Depends(require_auth)
):
    """Get thread details by name"""
    job_service = get_job_service()
    thread = job_service.get_thread(name)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@app.post("/threads/{name}/terminate", tags=["Jobs"])
def terminate_thread(
    name: str,
    user: User = Depends(require_auth)
):
    """Request thread termination"""
    job_service = get_job_service()
    success = job_service.terminate_thread(name)
    if not success:
        raise HTTPException(status_code=400, detail="Could not terminate thread")
    return {"success": True, "message": "Thread termination requested"}


# ============================================================================
# QUEUE MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/queues", tags=["Jobs"])
def list_queues(user: User = Depends(require_auth)):
    """List all job queues with stats"""
    job_service = get_job_service()
    return {"queues": job_service.list_queues()}


@app.get("/queues/{queue}/stats", tags=["Jobs"])
def get_queue_stats(
    queue: str,
    user: User = Depends(require_auth)
):
    """Get queue statistics"""
    job_service = get_job_service()
    return job_service.get_queue_stats(queue)


@app.post("/queues/{queue}/purge", tags=["Jobs"])
def purge_queue(
    queue: str,
    status: Optional[str] = None,
    user: User = Depends(require_auth)
):
    """Purge jobs from a queue"""
    job_service = get_job_service()
    count = job_service.purge_queue(queue, status=status)
    return {"success": True, "purged": count}


# ============================================================================
# JOBS DASHBOARD HTML
# ============================================================================

@app.get("/api/jobs/dashboard", response_class=HTMLResponse, tags=["Jobs"])
def get_jobs_dashboard_html(db: Session = Depends(get_db)):
    """Get Jobs dashboard HTML"""
    job_service = get_job_service()
    overview = job_service.get_overview()

    html = '''
    <div class="qa-jobs-dashboard">
        <!-- Overview Cards -->
        <div class="qa-grid qa-grid-4 qa-mb-4">
    '''

    if overview.get('available'):
        jobs = overview.get('jobs', {})
        schedules = overview.get('schedules', {})
        threads = overview.get('threads', {})

        html += f'''
            <div class="qa-card qa-text-center">
                <div class="qa-card-body">
                    <h2 class="qa-text-primary">{jobs.get('pending', 0)}</h2>
                    <p class="qa-text-muted">Pending Jobs</p>
                </div>
            </div>
            <div class="qa-card qa-text-center">
                <div class="qa-card-body">
                    <h2 class="qa-text-warning">{jobs.get('running', 0)}</h2>
                    <p class="qa-text-muted">Running</p>
                </div>
            </div>
            <div class="qa-card qa-text-center">
                <div class="qa-card-body">
                    <h2 class="qa-text-success">{schedules.get('active', 0)}</h2>
                    <p class="qa-text-muted">Active Schedules</p>
                </div>
            </div>
            <div class="qa-card qa-text-center">
                <div class="qa-card-body">
                    <h2 class="qa-text-info">{threads.get('running', 0)}</h2>
                    <p class="qa-text-muted">Active Threads</p>
                </div>
            </div>
        '''
    else:
        html += '''
            <div class="qa-card qa-col-span-4">
                <div class="qa-card-body qa-text-center">
                    <p class="qa-text-muted">Job executor not available</p>
                </div>
            </div>
        '''

    html += '''
        </div>

        <!-- Queued Jobs -->
        <div class="qa-card qa-mb-4">
            <div class="qa-card-header qa-flex qa-justify-between qa-items-center">
                <h4>Job Queue</h4>
                <div>
                    <button class="qa-btn qa-btn-sm qa-btn-primary"
                            hx-get="{URL_PREFIX}/api/jobs/dashboard"
                            hx-target=".qa-jobs-dashboard"
                            hx-swap="outerHTML">
                        Refresh
                    </button>
                </div>
            </div>
            <div class="qa-card-body">
    '''

    jobs_list = job_service.list_jobs(limit=20)
    if not jobs_list:
        html += '<p class="qa-text-muted">No jobs in queue</p>'
    else:
        html += '''
                <table class="qa-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Queue</th>
                            <th>Status</th>
                            <th>Attempts</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        '''

        for job in jobs_list:
            status_badge = {
                'pending': 'qa-badge-gray',
                'running': 'qa-badge-warning',
                'completed': 'qa-badge-success',
                'failed': 'qa-badge-danger'
            }.get(job.get('status'), 'qa-badge-gray')

            created = job.get('created_at', '-')[:16] if job.get('created_at') else '-'

            html += f'''
                        <tr>
                            <td>#{job.get('id')}</td>
                            <td>{job.get('name')}</td>
                            <td>{job.get('queue')}</td>
                            <td><span class="qa-badge {status_badge}">{job.get('status')}</span></td>
                            <td>{job.get('attempts')}/{job.get('max_attempts')}</td>
                            <td>{created}</td>
                            <td>
            '''

            if job.get('status') == 'pending':
                html += f'''
                                <button class="qa-btn qa-btn-sm qa-btn-danger"
                                        hx-post="{URL_PREFIX}/jobs/{job.get('id')}/cancel"
                                        hx-swap="none"
                                        hx-confirm="Cancel this job?">
                                    Cancel
                                </button>
                '''
            elif job.get('status') == 'failed':
                html += f'''
                                <button class="qa-btn qa-btn-sm qa-btn-warning"
                                        hx-post="{URL_PREFIX}/jobs/{job.get('id')}/retry"
                                        hx-swap="none">
                                    Retry
                                </button>
                '''

            html += '''
                            </td>
                        </tr>
            '''

        html += '''
                    </tbody>
                </table>
        '''

    html += '''
            </div>
        </div>

        <!-- Scheduled Tasks -->
        <div class="qa-card qa-mb-4">
            <div class="qa-card-header">
                <h4>Scheduled Tasks</h4>
            </div>
            <div class="qa-card-body">
    '''

    schedules_list = job_service.list_schedules()
    if not schedules_list:
        html += '<p class="qa-text-muted">No scheduled tasks</p>'
    else:
        html += '''
                <table class="qa-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Trigger</th>
                            <th>Status</th>
                            <th>Next Run</th>
                            <th>Run Count</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        '''

        for sched in schedules_list:
            status = 'active' if sched.get('enabled') else 'paused'
            status_badge = 'qa-badge-success' if sched.get('enabled') else 'qa-badge-gray'
            next_run = sched.get('next_run', '-')[:16] if sched.get('next_run') else '-'

            html += f'''
                        <tr>
                            <td>{sched.get('name')}</td>
                            <td>{sched.get('trigger_info')}</td>
                            <td><span class="qa-badge {status_badge}">{status}</span></td>
                            <td>{next_run}</td>
                            <td>{sched.get('run_count', 0)}</td>
                            <td>
                                <button class="qa-btn qa-btn-sm qa-btn-primary"
                                        hx-post="{URL_PREFIX}/schedules/{sched.get('name')}/run"
                                        hx-swap="none">
                                    Run Now
                                </button>
            '''

            if sched.get('enabled'):
                html += f'''
                                <button class="qa-btn qa-btn-sm"
                                        hx-post="{URL_PREFIX}/schedules/{sched.get('name')}/pause"
                                        hx-swap="none">
                                    Pause
                                </button>
                '''
            else:
                html += f'''
                                <button class="qa-btn qa-btn-sm"
                                        hx-post="{URL_PREFIX}/schedules/{sched.get('name')}/resume"
                                        hx-swap="none">
                                    Resume
                                </button>
                '''

            html += '''
                            </td>
                        </tr>
            '''

        html += '''
                    </tbody>
                </table>
        '''

    html += '''
            </div>
        </div>

        <!-- Queues Overview -->
        <div class="qa-card">
            <div class="qa-card-header">
                <h4>Queues</h4>
            </div>
            <div class="qa-card-body">
    '''

    queues_list = job_service.list_queues()
    if not queues_list:
        html += '<p class="qa-text-muted">No queues</p>'
    else:
        html += '''
                <table class="qa-table">
                    <thead>
                        <tr>
                            <th>Queue</th>
                            <th>Pending</th>
                            <th>Running</th>
                            <th>Completed</th>
                            <th>Failed</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        '''

        for q in queues_list:
            html += f'''
                        <tr>
                            <td>{q.get('name')}</td>
                            <td>{q.get('pending', 0)}</td>
                            <td>{q.get('running', 0)}</td>
                            <td>{q.get('completed', 0)}</td>
                            <td>{q.get('failed', 0)}</td>
                            <td>
                                <button class="qa-btn qa-btn-sm qa-btn-danger"
                                        hx-post="{URL_PREFIX}/queues/{q.get('name')}/purge?status=completed"
                                        hx-swap="none"
                                        hx-confirm="Purge completed jobs from this queue?">
                                    Purge Completed
                                </button>
                            </td>
                        </tr>
            '''

        html += '''
                    </tbody>
                </table>
        '''

    html += '''
            </div>
        </div>
    </div>
    '''

    return HTMLResponse(content=html)


# ============================================================================
# WEBSOCKET ENDPOINT (Real-time Logs)
# ============================================================================

from fastapi import WebSocket, WebSocketDisconnect


@app.websocket("/ws/deploy/{deployment_id}/logs")
async def websocket_deploy_logs(
    websocket: WebSocket,
    deployment_id: str
):
    """
    WebSocket endpoint for streaming deployment logs

    Connect via: ws://host/ws/deploy/{deployment_id}/logs

    Messages received:
    - {"type": "log", "data": {"timestamp": ..., "level": ..., "message": ..., "step": ...}}
    - {"type": "status", "data": {"status": ..., "step": ..., "progress": ...}}
    - {"type": "step_complete", "data": {"step": ..., "success": ..., "duration": ...}}
    - {"type": "complete", "data": {"success": ..., "message": ..., "version": ...}}
    """
    ws_manager = get_websocket_manager()

    if not await ws_manager.connect(websocket, deployment_id):
        return

    try:
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (ping/pong or disconnect)
                message = await websocket.receive_text()

                # Handle ping
                if message == "ping":
                    await websocket.send_text("pong")

            except WebSocketDisconnect:
                break

    finally:
        await ws_manager.disconnect(websocket, deployment_id)


# ============================================================================
# PROJECT ENDPOINTS
# ============================================================================

@app.get("/projects", tags=["Projects"])
def list_projects(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all projects"""
    projects = crud.get_projects(db, skip=skip, limit=limit)

    # If HTMX request, return HTML cards
    if request.headers.get("HX-Request"):
        if not projects:
            return HTMLResponse(content='''
                <div class="qa-card" style="grid-column: span 3;">
                    <div class="qa-card-body qa-text-center qa-p-8">
                        <svg width="48" height="48" class="qa-mx-auto qa-mb-4 qa-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
                        </svg>
                        <p class="qa-text-muted qa-mb-4">No applications yet</p>
                        <button class="qa-btn qa-btn-primary" onclick="openProjectModal()">Create your first application</button>
                    </div>
                </div>
            ''')

        cards = ""
        for p in projects:
            status_class = "qa-badge-success" if p.status == "active" else "qa-badge-gray"
            status_label = "Active" if p.status == "active" else "Inactive"

            # Count datasources
            ds_count = len(p.datasources) if hasattr(p, 'datasources') and p.datasources else 0

            cards += f'''
            <div class="qa-card qa-card-hover" onclick="window.location='/admin/projects/{p.id}'" style="cursor: pointer;">
                <div class="qa-card-body">
                    <div class="qa-flex qa-justify-between qa-items-start qa-mb-3">
                        <div class="qa-project-icon">
                            <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                            </svg>
                        </div>
                        <span class="qa-badge {status_class}">{status_label}</span>
                    </div>
                    <h3 class="qa-card-title qa-mb-2">{p.name}</h3>
                    <p class="qa-text-sm qa-text-muted qa-mb-4" style="min-height: 40px;">{p.description or "No description"}</p>
                    <div class="qa-flex qa-justify-between qa-items-center qa-text-xs qa-text-muted">
                        <span><strong>{ds_count}</strong> datasource{"s" if ds_count != 1 else ""}</span>
                        <span>ID: {p.id}</span>
                    </div>
                </div>
                <div class="qa-card-footer qa-flex qa-justify-end qa-gap-2">
                    <button class="qa-btn qa-btn-ghost qa-btn-sm" onclick="event.stopPropagation(); editProject({p.id})">
                        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                    </button>
                    <button class="qa-btn qa-btn-ghost qa-btn-sm qa-text-danger" onclick="event.stopPropagation(); deleteProject({p.id}, '{p.name}')">
                        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                    </button>
                </div>
            </div>
            '''

        return HTMLResponse(content=cards)

    # Default: return JSON
    return projects


@app.get("/api/projects-grid", response_class=HTMLResponse, tags=["Projects"])
def get_projects_grid(db: Session = Depends(get_db)):
    """Get projects as HTML grid cards for HTMX"""
    projects = crud.get_projects(db, limit=100)

    if not projects:
        return HTMLResponse(content='''
            <div class="qa-card" style="grid-column: span 3;">
                <div class="qa-card-body qa-text-center qa-p-8">
                    <svg width="48" height="48" class="qa-mx-auto qa-mb-4 qa-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
                    </svg>
                    <p class="qa-text-muted qa-mb-4">No applications yet</p>
                    <button class="qa-btn qa-btn-primary" onclick="openProjectModal()">Create your first application</button>
                </div>
            </div>
        ''')

    cards = ""
    for p in projects:
        status_class = "qa-badge-success" if p.status == "active" else "qa-badge-gray"
        status_label = "Active" if p.status == "active" else "Inactive"
        ds_count = len(p.datasources) if hasattr(p, 'datasources') and p.datasources else 0

        cards += f'''
        <div class="qa-card qa-card-hover" onclick="window.location='{URL_PREFIX}/projects/{p.id}'" style="cursor: pointer;">
            <div class="qa-card-body">
                <div class="qa-flex qa-justify-between qa-items-start qa-mb-3">
                    <div class="qa-project-icon">
                        <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                        </svg>
                    </div>
                    <span class="qa-badge {status_class}">{status_label}</span>
                </div>
                <h3 class="qa-card-title qa-mb-2">{p.name}</h3>
                <p class="qa-text-sm qa-text-muted qa-mb-4" style="min-height: 40px;">{p.description or "No description"}</p>
                <div class="qa-flex qa-justify-between qa-items-center qa-text-xs qa-text-muted">
                    <span><strong>{ds_count}</strong> datasource{"s" if ds_count != 1 else ""}</span>
                    <span>ID: {p.id}</span>
                </div>
            </div>
            <div class="qa-card-footer qa-flex qa-justify-end qa-gap-2">
                <button class="qa-btn qa-btn-ghost qa-btn-sm" onclick="event.stopPropagation(); editProject({p.id})">
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                </button>
                <button class="qa-btn qa-btn-ghost qa-btn-sm qa-text-danger" onclick="event.stopPropagation(); deleteProject({p.id}, '{p.name}')">
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                </button>
            </div>
        </div>
        '''

    return HTMLResponse(content=cards)


@app.post(
    "/projects",
    response_model=schemas.ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects"]
)
def create_project(
    project: schemas.ProjectCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new project"""
    try:
        new_project = crud.create_project(
            db,
            name=project.name,
            description=project.description or ""
        )

        # Audit log
        audit_log(
            db,
            action=AuditAction.CREATE,
            resource_type="project",
            resource_id=new_project.id,
            resource_name=new_project.name,
            user_id="admin",  # TODO: get from auth
            user_ip=request.client.host if request.client else None,
            project_id=new_project.id,
            request_method="POST",
            request_path="/projects"
        )

        return new_project
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/projects/{project_id}", response_model=schemas.ProjectDetailResponse, tags=["Projects"])
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get a single project with all related data"""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    return project


@app.put("/projects/{project_id}", response_model=schemas.ProjectResponse, tags=["Projects"])
def update_project(
    project_id: int,
    project: schemas.ProjectUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update a project"""
    updated_project = crud.update_project(
        db,
        project_id,
        name=project.name,
        description=project.description,
        status=project.status,
        source_path=project.source_path,
        git_url=project.git_url,
        git_branch=project.git_branch
    )
    if not updated_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Audit log
    audit_log(
        db,
        action=AuditAction.UPDATE,
        resource_type="project",
        resource_id=project_id,
        resource_name=updated_project.name,
        user_id="admin",
        user_ip=request.client.host if request.client else None,
        project_id=project_id,
        request_method="PUT",
        request_path=f"/projects/{project_id}"
    )

    return updated_project


@app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Projects"])
def delete_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    """Delete a project"""
    # Get project name before deleting for audit
    project = crud.get_project(db, project_id)
    project_name = project.name if project else f"Project {project_id}"

    success = crud.delete_project(db, project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Audit log
    audit_log(
        db,
        action=AuditAction.DELETE,
        resource_type="project",
        resource_id=project_id,
        resource_name=project_name,
        user_id="admin",
        user_ip=request.client.host if request.client else None,
        request_method="DELETE",
        request_path=f"/projects/{project_id}"
    )

    return None


# ============================================================================
# DATASOURCE ENDPOINTS
# ============================================================================

@app.get("/projects/{project_id}/datasources", response_model=List[schemas.DatasourceResponse], tags=["Datasources"])
def list_datasources(project_id: int, db: Session = Depends(get_db)):
    """Get all datasources for a project"""
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    datasources = crud.get_datasources(db, project_id)
    return datasources




@app.get("/api/datasources/by-name/{name}", tags=["API"])
def get_datasource_by_name(name: str, db: Session = Depends(get_db)):
    """
    Get datasource configuration by name for runtime use
    
    This endpoint is used by Quantum runtime to fetch datasource configuration
    when executing q:query components.
    """
    # Find datasource by name across all projects
    datasource = db.query(models.Datasource).filter(
        models.Datasource.name == name
    ).first()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource '{name}' not found"
        )
    
    # Only return if status is 'running' and setup is 'ready'
    if datasource.status != 'running':
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Datasource '{name}' is not running (status: {datasource.status})"
        )
    
    if datasource.setup_status != 'ready':
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Datasource '{name}' is not ready (setup status: {datasource.setup_status})"
        )
    
    # Decrypt password for runtime use
    try:
        from .secret_manager import decrypt_value
    except ImportError:
        from secret_manager import decrypt_value

    decrypted_password = decrypt_value(datasource.password_encrypted) if datasource.password_encrypted else None

    # Return datasource configuration for runtime use
    return {
        'name': datasource.name,
        'type': datasource.type,
        'host': datasource.host,
        'port': datasource.port,
        'database_name': datasource.database_name,
        'username': datasource.username,
        'password': decrypted_password,  # ✅ Decrypted for runtime use
        'connection_string': f"{datasource.type}://{datasource.username}:{decrypted_password}@{datasource.host}:{datasource.port}/{datasource.database_name}"
    }


# ============================================================================
# PROJECT DETAIL HTML ENDPOINTS (for HTMX)
# ============================================================================

@app.get("/api/projects/{project_id}/header", tags=["Project Detail"])
def get_project_header_html(project_id: int, request: Request, db: Session = Depends(get_db)):
    """Get project header HTML for detail page"""
    project = crud.get_project(db, project_id)
    if not project:
        return HTMLResponse(content='<div class="qa-text-danger">Application not found</div>')

    status_class = "qa-badge-success" if project.status == "active" else "qa-badge-gray"
    ds_count = len(project.datasources) if project.datasources else 0

    return HTMLResponse(content=f'''
        <div class="qa-flex qa-items-center qa-gap-4">
          <div class="qa-project-icon" style="width: 56px; height: 56px;">
            <svg width="28" height="28" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
          </div>
          <div>
            <div class="qa-flex qa-items-center qa-gap-3">
              <h2 class="qa-text-xl qa-font-bold">{project.name}</h2>
              <span class="qa-badge {status_class}">{project.status.title()}</span>
            </div>
            <p class="qa-text-muted">{project.description or "No description"}</p>
            <div class="qa-flex qa-gap-4 qa-mt-2 qa-text-sm qa-text-muted">
              <span><strong>{ds_count}</strong> datasource{"s" if ds_count != 1 else ""}</span>
              <span>ID: {project.id}</span>
            </div>
          </div>
        </div>
        <div class="qa-flex qa-gap-2">
          <button class="qa-btn qa-btn-secondary" onclick="openProjectSettingsModal()">
            <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
            Edit
          </button>
        </div>
    ''')


@app.get("/api/projects/{project_id}/general", tags=["Project Detail"])
def get_project_general_html(project_id: int, request: Request, db: Session = Depends(get_db)):
    """Get project general settings HTML"""
    project = crud.get_project(db, project_id)
    if not project:
        return HTMLResponse(content='<div class="qa-text-danger">Application not found</div>')

    return HTMLResponse(content=f'''
        <form id="general-form" onsubmit="saveGeneralSettings(event)">
          <div class="qa-form-row">
            <div class="qa-form-group">
              <label class="qa-label">Application Name</label>
              <input type="text" id="gen-name" class="qa-input" value="{project.name}" required />
            </div>
            <div class="qa-form-group">
              <label class="qa-label">Status</label>
              <select id="gen-status" class="qa-input qa-select">
                <option value="active" {"selected" if project.status == "active" else ""}>Active</option>
                <option value="inactive" {"selected" if project.status == "inactive" else ""}>Inactive</option>
              </select>
            </div>
          </div>
          <div class="qa-form-group">
            <label class="qa-label">Description</label>
            <textarea id="gen-description" class="qa-input" rows="3">{project.description or ""}</textarea>
          </div>
          <div class="qa-form-row qa-text-muted qa-text-sm">
            <div>Created: {project.created_at.strftime("%Y-%m-%d %H:%M") if project.created_at else "N/A"}</div>
            <div>Updated: {project.updated_at.strftime("%Y-%m-%d %H:%M") if project.updated_at else "N/A"}</div>
          </div>
          <div class="qa-mt-4">
            <button type="submit" class="qa-btn qa-btn-primary">Save Changes</button>
          </div>
        </form>
        <script>
        function saveGeneralSettings(e) {{
          e.preventDefault();
          fetch('{URL_PREFIX}/projects/{project_id}', {{
            method: 'PUT',
            headers: {{
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ' + localStorage.getItem('token')
            }},
            body: JSON.stringify({{
              name: document.getElementById('gen-name').value,
              description: document.getElementById('gen-description').value,
              status: document.getElementById('gen-status').value
            }})
          }})
          .then(r => {{
            if (r.ok) {{
              location.reload();
            }} else {{
              r.json().then(d => alert(d.detail || 'Error saving'));
            }}
          }});
        }}
        </script>
    ''')


@app.get("/api/projects/{project_id}/source-html", response_class=HTMLResponse, tags=["Project Detail"])
def get_project_source_html(project_id: int, db: Session = Depends(get_db)):
    """Get project source code configuration HTML"""
    project = crud.get_project(db, project_id)
    if not project:
        return HTMLResponse(content='<div class="qa-text-danger">Application not found</div>')

    source_path = project.source_path or ""
    git_url = project.git_url or ""
    git_branch = project.git_branch or "main"

    return HTMLResponse(content=f'''
        <form id="source-form" onsubmit="saveSourceSettings(event)">
          <div class="qa-form-group">
            <label class="qa-label">Source Path</label>
            <input type="text" id="src-source-path" class="qa-input" value="{source_path}"
                   placeholder="/path/to/your/quantum/app" />
            <p class="qa-text-sm qa-text-muted qa-mt-1">
              Local path to the application source code. Used for component discovery and test generation.
            </p>
          </div>

          <div class="qa-form-group">
            <label class="qa-label">Git Repository URL</label>
            <div class="qa-flex qa-gap-2">
              <input type="text" id="src-git-url" class="qa-input" value="{git_url}"
                     placeholder="https://github.com/user/repo.git" style="flex: 1;" />
              <button type="button" class="qa-btn qa-btn-secondary" onclick="testGitConnection()">
                Test Connection
              </button>
            </div>
            <p class="qa-text-sm qa-text-muted qa-mt-1">
              Git repository URL for version control and CI/CD integration.
            </p>
          </div>

          <div class="qa-form-row">
            <div class="qa-form-group">
              <label class="qa-label">Default Branch</label>
              <input type="text" id="src-git-branch" class="qa-input" value="{git_branch}"
                     placeholder="main" />
            </div>
          </div>

          <div class="qa-mt-4">
            <button type="submit" class="qa-btn qa-btn-primary">Save Changes</button>
          </div>
        </form>

        <div class="qa-card qa-mt-6">
          <div class="qa-card-header">
            <h4 class="qa-card-title">Quick Actions</h4>
          </div>
          <div class="qa-card-body">
            <div class="qa-flex qa-gap-2 qa-flex-wrap">
              <button class="qa-btn qa-btn-secondary" onclick="cloneRepository()" {"disabled" if not git_url else ""}>
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                Clone Repository
              </button>
              <button class="qa-btn qa-btn-secondary" onclick="pullLatest()" {"disabled" if not source_path else ""}>
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                Pull Latest
              </button>
              <a href="{URL_PREFIX}/components" class="qa-btn qa-btn-secondary" {"style='pointer-events:none;opacity:0.5'" if not source_path else ""}>
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6z"/></svg>
                Discover Components
              </a>
            </div>
          </div>
        </div>

        <script>
        function saveSourceSettings(e) {{
          e.preventDefault();
          fetch('{URL_PREFIX}/projects/{project_id}', {{
            method: 'PUT',
            headers: {{
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ' + localStorage.getItem('token')
            }},
            body: JSON.stringify({{
              source_path: document.getElementById('src-source-path').value || null,
              git_url: document.getElementById('src-git-url').value || null,
              git_branch: document.getElementById('src-git-branch').value || 'main'
            }})
          }})
          .then(r => {{
            if (r.ok) {{
              alert('Source configuration saved!');
              location.reload();
            }} else {{
              r.json().then(d => alert(d.detail || 'Error saving'));
            }}
          }});
        }}

        function testGitConnection() {{
          const gitUrl = document.getElementById('src-git-url').value;
          if (!gitUrl) {{
            alert('Please enter a Git URL first');
            return;
          }}
          alert('Testing connection to: ' + gitUrl + '\\n\\n(Git operations require GitPython to be installed)');
        }}

        function cloneRepository() {{
          const gitUrl = document.getElementById('src-git-url').value;
          const sourcePath = document.getElementById('src-source-path').value;
          if (!gitUrl) {{
            alert('Please enter a Git URL first');
            return;
          }}
          if (!sourcePath) {{
            alert('Please enter a source path first');
            return;
          }}
          if (!confirm('Clone ' + gitUrl + ' to ' + sourcePath + '?')) return;
          alert('Cloning repository... (Git operations require GitPython to be installed)');
        }}

        function pullLatest() {{
          const sourcePath = document.getElementById('src-source-path').value;
          if (!sourcePath) {{
            alert('Please configure source path first');
            return;
          }}
          if (!confirm('Pull latest changes in ' + sourcePath + '?')) return;
          fetch('{URL_PREFIX}/projects/{project_id}/git/pull', {{ method: 'POST' }})
            .then(r => r.json())
            .then(data => {{
              if (data.commit) {{
                alert('Pulled to commit: ' + data.commit);
              }} else {{
                alert(data.message || 'Pull completed');
              }}
            }})
            .catch(err => alert('Error: ' + err.message));
        }}
        </script>
    ''')


@app.get("/api/projects/{project_id}/datasources-html", tags=["Project Detail"])
def get_project_datasources_html(project_id: int, request: Request, db: Session = Depends(get_db)):
    """Get project datasources list HTML"""
    datasources = crud.get_datasources(db, project_id)

    if not datasources:
        return HTMLResponse(content='''
            <div class="qa-text-center qa-p-8">
              <svg width="48" height="48" class="qa-mx-auto qa-mb-4 qa-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"/>
              </svg>
              <p class="qa-text-muted qa-mb-4">No datasources configured</p>
              <button class="qa-btn qa-btn-primary" onclick="openDatasourceModal()">Add your first datasource</button>
            </div>
        ''')

    rows = ""
    for ds in datasources:
        # Status styling
        status_map = {
            "running": ("qa-badge-success", "●"),
            "stopped": ("qa-badge-gray", "○"),
            "restarting": ("qa-badge-warning", "↻"),
            "error": ("qa-badge-danger", "✕"),
        }
        status_class, status_icon = status_map.get(ds.status, ("qa-badge-gray", "?"))
        type_icon = "🐘" if ds.type == "postgres" else "🐬" if ds.type == "mysql" else "📦" if ds.type == "sqlite" else "🍃"

        # Container actions (start/stop/logs)
        container_btns = ""
        if ds.container_id or ds.connection_type == "docker":
            if ds.status == "running":
                container_btns = f'''
                  <button class="qa-btn qa-btn-danger qa-btn-xs" onclick="stopDatasource({ds.id})" title="Stop Container">
                    <svg width="12" height="12" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12"/></svg>
                  </button>
                  <button class="qa-btn qa-btn-secondary qa-btn-xs" onclick="viewDatasourceLogs({ds.id}, '{ds.name}')" title="View Logs">
                    <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                  </button>
                '''
            else:
                container_btns = f'''
                  <button class="qa-btn qa-btn-success qa-btn-xs" onclick="startDatasource({ds.id})" title="Start Container">
                    <svg width="12" height="12" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                  </button>
                '''

        rows += f'''
        <tr>
          <td>
            <div class="qa-flex qa-items-center qa-gap-2">
              <span style="font-size: 1.2rem;">{type_icon}</span>
              <div>
                <span class="qa-font-medium">{ds.name}</span>
                <div class="qa-text-xs qa-text-muted">{ds.database_name or "—"}</div>
              </div>
            </div>
          </td>
          <td><span class="qa-badge qa-badge-outline">{ds.type.upper()}</span></td>
          <td>{ds.connection_type.title()}</td>
          <td class="qa-font-mono qa-text-sm">{ds.host or "localhost"}:{ds.port or "—"}</td>
          <td>
            <span class="qa-badge {status_class}">
              <span class="qa-mr-1">{status_icon}</span> {ds.status}
            </span>
          </td>
          <td>
            <div class="qa-flex qa-gap-1 qa-items-center">
              {container_btns}
              <button class="qa-btn qa-btn-ghost qa-btn-xs" onclick="testDatasourceConnection({ds.id})" title="Test Connection">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
              </button>
              <button class="qa-btn qa-btn-ghost qa-btn-xs" onclick="openDatasourceModal({ds.id})" title="Edit">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
              </button>
              <button class="qa-btn qa-btn-ghost qa-btn-xs qa-text-danger" onclick="deleteDatasource({ds.id}, '{ds.name}')" title="Delete">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              </button>
            </div>
          </td>
        </tr>
        '''

    return HTMLResponse(content=f'''
        <table class="qa-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Connection</th>
              <th>Host:Port</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
    ''')


@app.get("/api/projects/{project_id}/connectors-html", tags=["Project Detail"])
def get_project_connectors_html(project_id: int, request: Request, db: Session = Depends(get_db)):
    """Get project connectors access HTML"""
    settings_service = get_settings_service()
    connectors = settings_service.get_connectors()

    # Get project's allowed connectors
    project_settings = settings_service.get_project_settings(project_id)
    allowed_connectors = project_settings.get("allowed_connectors", [])

    if not connectors:
        return HTMLResponse(content='''
            <div class="qa-text-center qa-p-8">
              <p class="qa-text-muted">No connectors available. Configure connectors in Settings.</p>
            </div>
        ''')

    items = ""
    for conn in connectors:
        conn_id = conn.get("id", conn.get("name", ""))
        is_allowed = conn_id in allowed_connectors or conn.get("scope") == "public"
        is_public = conn.get("scope") == "public"

        checked = "checked" if is_allowed else ""
        disabled = "disabled" if is_public else ""

        scope_badge = '<span class="qa-badge qa-badge-success qa-ml-2">Public</span>' if is_public else ""

        items += f'''
        <div class="qa-flex qa-items-center qa-justify-between qa-p-4 qa-border-b">
          <div class="qa-flex qa-items-center qa-gap-3">
            <div class="qa-connector-icon">
              <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/>
              </svg>
            </div>
            <div>
              <div class="qa-font-medium">{conn.get("name", "Unknown")}{scope_badge}</div>
              <div class="qa-text-sm qa-text-muted">{conn.get("type", "Unknown")} - {conn.get("provider", "Unknown")}</div>
            </div>
          </div>
          <label class="qa-switch">
            <input type="checkbox" {checked} {disabled} onchange="toggleConnector('{conn_id}', this.checked)" />
            <span class="qa-switch-slider"></span>
          </label>
        </div>
        '''

    return HTMLResponse(content=f'''
        <div class="qa-connectors-list">
          {items}
        </div>
        <script>
        function toggleConnector(connId, enabled) {{
          // Save connector access
          fetch('{URL_PREFIX}/projects/{project_id}/settings', {{
            method: 'PUT',
            headers: {{
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ' + localStorage.getItem('token')
            }},
            body: JSON.stringify({{
              toggle_connector: {{ id: connId, enabled: enabled }}
            }})
          }});
        }}
        </script>
    ''')


@app.get("/api/projects/{project_id}/environments-html", tags=["Project Detail"])
def get_project_environments_html(project_id: int, request: Request, db: Session = Depends(get_db)):
    """Get project environments list HTML"""
    try:
        from .environment_service import get_environment_service
    except ImportError:
        from environment_service import get_environment_service

    env_service = get_environment_service(db)
    environments = env_service.list_environments(project_id, active_only=False)

    if not environments:
        return HTMLResponse(content=f'''
            <div class="qa-text-center qa-p-8">
              <svg width="48" height="48" class="qa-mx-auto qa-mb-4 qa-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2"/>
              </svg>
              <p class="qa-text-muted qa-mb-4">No environments configured</p>
              <button class="qa-btn qa-btn-secondary qa-mr-2" onclick="createDefaultEnvs({project_id})">Create Defaults (dev, staging, prod)</button>
            </div>
        ''')

    # Color mapping for environment types
    env_colors = {
        "development": "#22c55e",  # green
        "staging": "#f59e0b",      # amber
        "production": "#ef4444",   # red
    }

    cards = '<div class="qa-grid qa-grid-3 qa-gap-4">'
    for env in environments:
        env_dict = env.to_dict()
        env_name = env_dict.get("name", "").lower()
        env_color = env_colors.get(env_name, "#6366f1")

        # Status indicators
        auto_badge = '<span class="qa-badge qa-badge-info">Auto-deploy</span>' if env_dict.get("auto_deploy") else ""
        approval_badge = '<span class="qa-badge qa-badge-warning">Approval Required</span>' if env_dict.get("requires_approval") else ""
        active_indicator = "qa-border-success" if env_dict.get("is_active") else "qa-border-muted"

        # Docker host display
        docker_host = env_dict.get("docker_host") or "Not configured"
        if docker_host.startswith("ssh://"):
            docker_host = docker_host.replace("ssh://", "")

        cards += f'''
        <div class="qa-card {active_indicator}" style="border-left: 4px solid {env_color};">
          <div class="qa-card-body">
            <div class="qa-flex qa-justify-between qa-items-start qa-mb-3">
              <div>
                <h4 class="qa-font-bold qa-text-lg">{env_dict.get("display_name", env_dict.get("name", "?"))}</h4>
                <div class="qa-text-sm qa-text-muted">Order: {env_dict.get("order", 1)}</div>
              </div>
              <div class="qa-flex qa-gap-1">
                <button class="qa-btn qa-btn-ghost qa-btn-icon qa-btn-sm" onclick="editEnvironment({env_dict.get('id')})" title="Edit">
                  <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                </button>
                <button class="qa-btn qa-btn-ghost qa-btn-icon qa-btn-sm qa-text-danger" onclick="deleteEnvironment({env_dict.get('id')}, '{env_dict.get('display_name', env_dict.get('name'))}')" title="Delete">
                  <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                </button>
              </div>
            </div>

            <div class="qa-space-y-2 qa-text-sm">
              <div class="qa-flex qa-justify-between">
                <span class="qa-text-muted">Branch:</span>
                <code class="qa-bg-dark qa-px-2 qa-py-1 qa-rounded">{env_dict.get("branch", "main")}</code>
              </div>
              <div class="qa-flex qa-justify-between">
                <span class="qa-text-muted">Docker Host:</span>
                <span class="qa-font-mono qa-text-xs">{docker_host[:25]}{"..." if len(docker_host) > 25 else ""}</span>
              </div>
              <div class="qa-flex qa-justify-between">
                <span class="qa-text-muted">Container:</span>
                <span>{env_dict.get("container_name") or "Not set"}</span>
              </div>
              <div class="qa-flex qa-justify-between">
                <span class="qa-text-muted">Port:</span>
                <span>{env_dict.get("port") or "—"}</span>
              </div>
            </div>

            <div class="qa-flex qa-gap-1 qa-mt-3 qa-flex-wrap">
              {auto_badge}
              {approval_badge}
            </div>

            <div class="qa-flex qa-gap-2 qa-mt-4">
              <button class="qa-btn qa-btn-success qa-btn-sm qa-flex-1" onclick="launchApp({project_id}, {env_dict.get('id')}, '{env_dict.get('name')}')">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                Launch
              </button>
              <button class="qa-btn qa-btn-secondary qa-btn-sm qa-flex-1" onclick="testEnvironment({env_dict.get('id')})">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                Test
              </button>
              <button class="qa-btn qa-btn-primary qa-btn-sm qa-flex-1" onclick="deployToEnvironment({env_dict.get('id')})">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>
                Deploy
              </button>
            </div>
          </div>
        </div>
        '''

    cards += '</div>'
    return HTMLResponse(content=cards)


@app.get("/api/projects/{project_id}/paths-html", tags=["Project Detail"])
def get_project_paths_html(project_id: int, request: Request, db: Session = Depends(get_db)):
    """Get project paths configuration HTML"""
    settings_service = get_settings_service()
    project_settings = settings_service.get_project_settings(project_id)

    paths = project_settings.get("paths", {})
    components_path = paths.get("components", "./components")
    static_path = paths.get("static", "./static")
    logs_path = paths.get("logs", "./logs")
    migrations_path = paths.get("migrations", "./migrations")

    return HTMLResponse(content=f'''
        <form id="paths-form" onsubmit="savePathsSettings(event)">
          <div class="qa-form-row">
            <div class="qa-form-group">
              <label class="qa-label">Components Path</label>
              <input type="text" id="path-components" class="qa-input" value="{components_path}" />
              <p class="qa-text-xs qa-text-muted qa-mt-1">Directory containing .q component files</p>
            </div>
            <div class="qa-form-group">
              <label class="qa-label">Static Files Path</label>
              <input type="text" id="path-static" class="qa-input" value="{static_path}" />
              <p class="qa-text-xs qa-text-muted qa-mt-1">Directory for static assets (CSS, JS, images)</p>
            </div>
          </div>
          <div class="qa-form-row">
            <div class="qa-form-group">
              <label class="qa-label">Logs Path</label>
              <input type="text" id="path-logs" class="qa-input" value="{logs_path}" />
              <p class="qa-text-xs qa-text-muted qa-mt-1">Directory for application logs</p>
            </div>
            <div class="qa-form-group">
              <label class="qa-label">Migrations Path</label>
              <input type="text" id="path-migrations" class="qa-input" value="{migrations_path}" />
              <p class="qa-text-xs qa-text-muted qa-mt-1">Directory for database migrations</p>
            </div>
          </div>
          <div class="qa-mt-4">
            <button type="submit" class="qa-btn qa-btn-primary">Save Paths</button>
          </div>
        </form>
        <script>
        function savePathsSettings(e) {{
          e.preventDefault();
          fetch('{URL_PREFIX}/projects/{project_id}/settings', {{
            method: 'PUT',
            headers: {{
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ' + localStorage.getItem('token')
            }},
            body: JSON.stringify({{
              paths: {{
                components: document.getElementById('path-components').value,
                static: document.getElementById('path-static').value,
                logs: document.getElementById('path-logs').value,
                migrations: document.getElementById('path-migrations').value
              }}
            }})
          }})
          .then(r => {{
            if (r.ok) alert('Paths saved!');
            else r.json().then(d => alert(d.detail || 'Error saving'));
          }});
        }}
        </script>
    ''')


@app.post(
    "/projects/{project_id}/datasources",
    response_model=schemas.DatasourceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Datasources"]
)
def create_datasource(
    project_id: int,
    datasource: schemas.DatasourceCreate,
    db: Session = Depends(get_db)
):
    """Create a new datasource and optionally create Docker container"""
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Check if Docker is required but unavailable
    if datasource.connection_type == "docker" and docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service is not available. Please ensure Docker Desktop is running."
        )

    try:
        container_id = None
        resolved_port = datasource.port

        # Create Docker container if connection_type is "docker"
        if datasource.connection_type == "docker":
            # Auto-resolve port conflicts
            if resolved_port:
                resolved_port = docker_service.find_available_port(datasource.port)
                if resolved_port != datasource.port:
                    logger.info(f"Port {datasource.port} was in use, auto-assigned port {resolved_port}")

            # Prepare environment variables for database
            env_vars = {}
            if datasource.type == "postgres":
                env_vars = {
                    "POSTGRES_DB": datasource.database_name,
                    "POSTGRES_USER": datasource.username,
                    "POSTGRES_PASSWORD": datasource.password
                }
            elif datasource.type in ["mysql", "mariadb"]:
                env_vars = {
                    "MYSQL_DATABASE": datasource.database_name,
                    "MYSQL_USER": datasource.username,
                    "MYSQL_PASSWORD": datasource.password,
                    "MYSQL_ROOT_PASSWORD": datasource.password  # For initial setup
                }
            elif datasource.type == "mongodb":
                env_vars = {
                    "MONGO_INITDB_DATABASE": datasource.database_name,
                    "MONGO_INITDB_ROOT_USERNAME": datasource.username,
                    "MONGO_INITDB_ROOT_PASSWORD": datasource.password
                }

            # Create container
            container_name = f"{project.name}_{datasource.name}".replace(" ", "_").lower()
            container_id = docker_service.create_container(
                name=container_name,
                image=datasource.image,
                port=resolved_port,
                env_vars=env_vars,
                auto_start=datasource.auto_start
            )

            if not container_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create Docker container"
                )

        # Encrypt password before storing
        try:
            from .secret_manager import encrypt_value
        except ImportError:
            from secret_manager import encrypt_value

        encrypted_password = encrypt_value(datasource.password) if datasource.password else None

        new_datasource = crud.create_datasource(
            db,
            project_id=project_id,
            name=datasource.name,
            type=datasource.type,
            connection_type=datasource.connection_type,
            container_id=container_id,
            image=datasource.image,
            port=resolved_port,  # Use the auto-resolved port
            host=datasource.host if datasource.connection_type == "direct" else "localhost",
            database_name=datasource.database_name,
            username=datasource.username,
            password_encrypted=encrypted_password,  # ✅ Encrypted!
            auto_start=datasource.auto_start
        )
        return new_datasource
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.delete("/datasources/{datasource_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Datasources"])
def delete_datasource(datasource_id: int, db: Session = Depends(get_db)):
    """Delete a datasource and optionally remove its container"""
    # Get datasource
    datasource = db.query(crud.models.Datasource).filter(
        crud.models.Datasource.id == datasource_id
    ).first()

    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource with id {datasource_id} not found"
        )

    # If it's a Docker container, stop and remove it
    if datasource.connection_type == "docker" and datasource.container_id and docker_service:
        try:
            # Stop container if running
            docker_service.stop_container(datasource.container_id)
            # Remove container
            docker_service.remove_container(datasource.container_id, force=True)
        except Exception as e:
            # Log error but continue with database deletion
            print(f"Warning: Failed to remove container: {e}")

    # Delete from database
    db.delete(datasource)
    db.commit()

    return None


# ============================================================================
# COMPONENT ENDPOINTS
# ============================================================================

@app.get("/projects/{project_id}/components", response_model=List[schemas.ComponentResponse], tags=["Components"])
def list_components(project_id: int, db: Session = Depends(get_db)):
    """Get all components for a project"""
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    components = crud.get_components(db, project_id)
    return components


# Import component discovery
try:
    from .component_discovery import get_discovery_service, ComponentMetadata
except ImportError:
    from component_discovery import get_discovery_service, ComponentMetadata


@app.post("/projects/{project_id}/components/discover", tags=["Components"])
def discover_components(
    project_id: int,
    base_path: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Discover components in project directory

    Scans the project directory for .q files and returns metadata about each component.
    """
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    discovery = get_discovery_service(db)
    try:
        components = discovery.discover_components(project_id, base_path)
        return {
            "count": len(components),
            "components": [
                {
                    "name": c.name,
                    "file_path": c.file_path,
                    "is_valid": c.is_valid,
                    "functions": len(c.functions),
                    "endpoints": len(c.endpoints),
                    "queries": len(c.queries),
                    "dependencies": len(c.dependencies),
                    "variables": len(c.variables),
                    "line_count": c.line_count,
                    "last_modified": c.last_modified.isoformat() if c.last_modified else None,
                    "errors": c.errors,
                    "warnings": c.warnings
                }
                for c in components
            ]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/projects/{project_id}/components/sync", tags=["Components"])
def sync_components(
    project_id: int,
    base_path: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Sync components with database

    Discovers components and updates the database:
    - Creates new component records for discovered files
    - Updates existing component records
    - Removes records for deleted files
    - Syncs endpoints for each component
    """
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    discovery = get_discovery_service(db)
    try:
        created, updated, deleted = discovery.sync_components(project_id, base_path)
        return {
            "success": True,
            "created": created,
            "updated": updated,
            "deleted": deleted,
            "total": created + updated
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/projects/{project_id}/components/{component_id}/details", tags=["Components"])
def get_component_details(
    project_id: int,
    component_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed metadata for a specific component

    Returns full parsing results including functions, endpoints, queries, etc.
    """
    discovery = get_discovery_service(db)
    metadata = discovery.get_component_details(project_id, component_id)

    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Component {component_id} not found"
        )

    return {
        "name": metadata.name,
        "file_path": metadata.file_path,
        "is_valid": metadata.is_valid,
        "line_count": metadata.line_count,
        "last_modified": metadata.last_modified.isoformat() if metadata.last_modified else None,
        "functions": [
            {
                "name": f.name,
                "params": f.params,
                "return_type": f.return_type,
                "line_number": f.line_number
            }
            for f in metadata.functions
        ],
        "endpoints": [
            {
                "method": e.method,
                "path": e.path,
                "function_name": e.function_name,
                "line_number": e.line_number
            }
            for e in metadata.endpoints
        ],
        "queries": [
            {
                "name": q.name,
                "datasource": q.datasource,
                "query_type": q.query_type,
                "line_number": q.line_number
            }
            for q in metadata.queries
        ],
        "dependencies": [
            {
                "component_name": d.component_name,
                "import_path": d.import_path,
                "line_number": d.line_number
            }
            for d in metadata.dependencies
        ],
        "variables": metadata.variables,
        "errors": metadata.errors,
        "warnings": metadata.warnings
    }


@app.get("/projects/{project_id}/components/dependencies", tags=["Components"])
def get_dependency_graph(
    project_id: int,
    base_path: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get component dependency graph

    Returns a mapping of component names to their dependencies.
    Useful for understanding component relationships.

    base_path: Optional path to scan for components (required if project has no path configured)
    """
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    discovery = get_discovery_service(db)
    graph = discovery.get_dependency_graph(project_id, base_path)

    return {
        "components": list(graph.keys()),
        "dependencies": graph,
        "total_components": len(graph),
        "total_dependencies": sum(len(deps) for deps in graph.values())
    }


@app.get("/projects/{project_id}/components/unused", tags=["Components"])
def get_unused_components(
    project_id: int,
    base_path: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Find unused components

    Returns components that are not imported by any other component.
    These may be entry points or potentially dead code.

    base_path: Optional path to scan for components (required if project has no path configured)
    """
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    discovery = get_discovery_service(db)
    unused = discovery.find_unused_components(project_id, base_path)

    return {
        "unused_components": unused,
        "count": len(unused)
    }


@app.post("/components/validate", tags=["Components"])
def validate_component_file(
    file_path: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Validate a component file

    Parses the file and returns validation results.
    """
    discovery = get_discovery_service(db)
    is_valid, errors, warnings = discovery.validate_component(file_path)

    return {
        "file_path": file_path,
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings
    }


# ============================================================================
# DOCKER CONTAINER MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/datasources/{datasource_id}/start", tags=["Docker"])
def start_datasource_container(datasource_id: int, db: Session = Depends(get_db)):
    """Start a datasource's Docker container"""
    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service is not available"
        )

    # Get datasource
    datasource = db.query(crud.models.Datasource).filter(
        crud.models.Datasource.id == datasource_id
    ).first()

    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource with id {datasource_id} not found"
        )

    if datasource.connection_type != "docker":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This datasource is not managed by Docker"
        )

    if not datasource.container_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No container associated with this datasource"
        )

    # Start container
    success = docker_service.start_container(datasource.container_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start container"
        )

    # Update status
    datasource.status = "running"
    db.commit()

    # Auto-run setup if this is the first time starting (setup_status is pending)
    if datasource.setup_status == "pending":
        logger.info(f"Auto-running database setup for datasource {datasource_id}")
        datasource.setup_status = "configuring"
        db.commit()

        # Run setup in background (non-blocking)
        import threading
        from .database import SessionLocal

        def run_setup():
            # Create new database session for this thread
            thread_db = SessionLocal()
            try:
                # Reload datasource in this thread's session
                thread_datasource = thread_db.query(crud.models.Datasource).filter(
                    crud.models.Datasource.id == datasource_id
                ).first()

                if thread_datasource:
                    success, message = DatabaseSetupService.setup_database(thread_datasource)
                    thread_datasource.setup_status = "ready" if success else "error"
                    thread_db.commit()

                    if success:
                        logger.info(f"Database setup completed for datasource {datasource_id}")
                    else:
                        logger.error(f"Database setup failed for datasource {datasource_id}: {message}")
            except Exception as e:
                logger.error(f"Error in setup thread: {e}")
                thread_db.rollback()
            finally:
                thread_db.close()

        setup_thread = threading.Thread(target=run_setup)
        setup_thread.daemon = True
        setup_thread.start()

    return {"message": "Container started successfully", "container_id": datasource.container_id}


@app.post("/datasources/{datasource_id}/stop", tags=["Docker"])
def stop_datasource_container(datasource_id: int, db: Session = Depends(get_db)):
    """Stop a datasource's Docker container"""
    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service is not available"
        )

    # Get datasource
    datasource = db.query(crud.models.Datasource).filter(
        crud.models.Datasource.id == datasource_id
    ).first()

    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource with id {datasource_id} not found"
        )

    if datasource.connection_type != "docker":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This datasource is not managed by Docker"
        )

    if not datasource.container_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No container associated with this datasource"
        )

    # Stop container
    success = docker_service.stop_container(datasource.container_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop container"
        )

    # Update status
    datasource.status = "stopped"
    db.commit()

    return {"message": "Container stopped successfully", "container_id": datasource.container_id}


@app.post("/datasources/{datasource_id}/restart", tags=["Docker"])
def restart_datasource_container(datasource_id: int, db: Session = Depends(get_db)):
    """Restart a datasource's Docker container"""
    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service is not available"
        )

    # Get datasource
    datasource = db.query(crud.models.Datasource).filter(
        crud.models.Datasource.id == datasource_id
    ).first()

    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource with id {datasource_id} not found"
        )

    if datasource.connection_type != "docker":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This datasource is not managed by Docker"
        )

    if not datasource.container_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No container associated with this datasource"
        )

    # Restart container
    success = docker_service.restart_container(datasource.container_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restart container"
        )

    # Update status
    datasource.status = "running"
    db.commit()

    return {"message": "Container restarted successfully", "container_id": datasource.container_id}


@app.get("/datasources/{datasource_id}/logs", tags=["Docker"])
def get_datasource_container_logs(
    datasource_id: int,
    tail: int = 100,
    db: Session = Depends(get_db)
):
    """Get logs from a datasource's Docker container"""
    if docker_service is None:
        return {"error": "Docker service is not available", "logs": ""}

    # Get datasource
    datasource = db.query(crud.models.Datasource).filter(
        crud.models.Datasource.id == datasource_id
    ).first()

    if not datasource:
        return {"error": f"Datasource with id {datasource_id} not found", "logs": ""}

    if not datasource.container_id:
        return {"error": "No container associated with this datasource", "logs": ""}

    try:
        # Get container logs
        container = docker_service.client.containers.get(datasource.container_id)
        logs = container.logs(tail=tail, timestamps=True).decode('utf-8', errors='replace')
        return {"logs": logs, "container_id": datasource.container_id}
    except Exception as e:
        return {"error": str(e), "logs": ""}


@app.post("/datasources/{datasource_id}/test", tags=["Docker"])
def test_datasource_connection(
    datasource_id: int,
    db: Session = Depends(get_db)
):
    """Test connection to a datasource"""
    # Get datasource
    datasource = db.query(crud.models.Datasource).filter(
        crud.models.Datasource.id == datasource_id
    ).first()

    if not datasource:
        return {"success": False, "error": "Datasource not found"}

    # Test connection based on type
    try:
        if datasource.type == "postgres":
            import psycopg2
            conn = psycopg2.connect(
                host=datasource.host or "localhost",
                port=datasource.port or 5432,
                user=datasource.username,
                password=datasource.password_encrypted,  # TODO: decrypt
                database=datasource.database_name or "postgres",
                connect_timeout=5
            )
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            conn.close()
            return {"success": True, "version": version}

        elif datasource.type == "mysql":
            import pymysql
            conn = pymysql.connect(
                host=datasource.host or "localhost",
                port=datasource.port or 3306,
                user=datasource.username,
                password=datasource.password_encrypted,
                database=datasource.database_name or "mysql",
                connect_timeout=5
            )
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            conn.close()
            return {"success": True, "version": f"MySQL {version}"}

        elif datasource.type == "sqlite":
            import sqlite3
            db_path = datasource.database_name or datasource.host
            if db_path:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT sqlite_version();")
                version = cursor.fetchone()[0]
                conn.close()
                return {"success": True, "version": f"SQLite {version}"}
            return {"success": False, "error": "No database path specified"}

        else:
            return {"success": False, "error": f"Unsupported database type: {datasource.type}"}

    except ImportError as e:
        return {"success": False, "error": f"Database driver not installed: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/datasources/{datasource_id}/status", tags=["Docker"])
def get_datasource_container_status(datasource_id: int, db: Session = Depends(get_db)):
    """Get detailed status of a datasource's Docker container"""
    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service is not available"
        )

    # Get datasource
    datasource = db.query(crud.models.Datasource).filter(
        crud.models.Datasource.id == datasource_id
    ).first()

    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource with id {datasource_id} not found"
        )

    if datasource.connection_type != "docker":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This datasource is not managed by Docker"
        )

    if not datasource.container_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No container associated with this datasource"
        )

    # Get container status
    status_info = docker_service.get_container_status(datasource.container_id)
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found in Docker"
        )

    return status_info


@app.get("/datasources/{datasource_id}/logs", tags=["Docker"])
def get_datasource_container_logs(
    datasource_id: int,
    lines: int = 100,
    db: Session = Depends(get_db)
):
    """Get logs from a datasource's Docker container"""
    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service is not available"
        )

    # Get datasource
    datasource = db.query(crud.models.Datasource).filter(
        crud.models.Datasource.id == datasource_id
    ).first()

    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource with id {datasource_id} not found"
        )

    if datasource.connection_type != "docker":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This datasource is not managed by Docker"
        )

    if not datasource.container_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No container associated with this datasource"
        )

    # Get container logs
    logs = docker_service.get_container_logs(datasource.container_id, lines=lines)
    if logs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found in Docker"
        )

    return {"logs": logs, "lines": lines}


@app.get("/docker/containers", tags=["Docker"])
def list_all_containers(request: Request = None, all: bool = True):
    """List all Docker containers (optionally including stopped ones)"""
    if docker_service is None:
        if request and request.headers.get("HX-Request"):
            return HTMLResponse(content="""
                <tr>
                    <td colspan="6" class="px-6 py-8 text-center text-gray-500">
                        Docker not connected
                    </td>
                </tr>
            """)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service is not available"
        )

    try:
        containers = docker_service.client.containers.list(all=all)

        if request and request.headers.get("HX-Request"):
            if not containers:
                return HTMLResponse(content="""
                    <tr>
                        <td colspan="6" class="px-6 py-8 text-center text-gray-500">
                            No containers found
                        </td>
                    </tr>
                """)

            rows = ""
            for c in containers[:50]:  # Limit to 50 for performance
                status_badge = "qa-badge-success" if c.status == "running" else "qa-badge-gray"
                # Handle ports - c.ports is a dict like {'8080/tcp': [{'HostIp': '', 'HostPort': '8080'}]}
                port_strs = []
                if c.ports:
                    for container_port, host_bindings in list(c.ports.items())[:3]:
                        if host_bindings:
                            for binding in host_bindings:
                                port_strs.append(f"{binding.get('HostPort', '?')}:{container_port.split('/')[0]}")
                        else:
                            port_strs.append(container_port.split('/')[0])
                ports = ", ".join(port_strs) if port_strs else "-"
                image = c.image.tags[0] if c.image.tags else c.image.short_id
                container_id = c.id

                # Build action buttons based on status
                if c.status == "running":
                    action_btn = f'<button class="qa-btn qa-btn-danger qa-btn-icon qa-btn-sm" onclick="stopContainer(\'{container_id}\')" title="Stop"><svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="1" stroke-width="2"/></svg></button>'
                else:
                    action_btn = f'<button class="qa-btn qa-btn-success qa-btn-icon qa-btn-sm" onclick="startContainer(\'{container_id}\')" title="Start"><svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/></svg></button>'

                rows += f"""
                    <tr>
                        <td>
                            <div>
                                <p class="qa-font-medium qa-text-primary">{c.name}</p>
                                <p class="qa-text-xs qa-text-muted">{c.short_id}</p>
                            </div>
                        </td>
                        <td><span class="qa-text-sm qa-font-mono qa-text-secondary">{image[:40]}</span></td>
                        <td><span class="qa-badge {status_badge}">{c.status}</span></td>
                        <td><span class="qa-text-sm qa-text-secondary">{ports}</span></td>
                        <td><span class="qa-text-sm qa-text-muted">{c.attrs.get('Created', '')[:10]}</span></td>
                        <td class="qa-text-right">
                            <div class="qa-flex qa-items-center qa-justify-end qa-gap-1">
                                {action_btn}
                                <button class="qa-btn qa-btn-ghost qa-btn-icon qa-btn-sm" onclick="showLogs('{container_id}')" title="Logs">
                                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                                    </svg>
                                </button>
                            </div>
                        </td>
                    </tr>
                """
            return HTMLResponse(content=rows)

        # JSON response
        container_list = []
        for c in containers:
            container_list.append({
                "id": c.id,
                "short_id": c.short_id,
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                "status": c.status,
                "ports": c.ports,
                "created": c.attrs.get("Created", "")
            })
        return {"containers": container_list, "count": len(container_list)}

    except Exception as e:
        if request and request.headers.get("HX-Request"):
            return HTMLResponse(content=f"""
                <tr>
                    <td colspan="6" class="qa-text-center qa-p-6 qa-text-danger">
                        Error: {str(e)}
                    </td>
                </tr>
            """)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/datasources/{datasource_id}/setup", tags=["Docker"])
def setup_datasource(datasource_id: int, db: Session = Depends(get_db)):
    """Initialize database in a running container"""
    # Get datasource
    datasource = db.query(crud.models.Datasource).filter(
        crud.models.Datasource.id == datasource_id
    ).first()

    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource with id {datasource_id} not found"
        )

    if datasource.connection_type != "docker":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup is only available for Docker datasources"
        )

    if datasource.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Container must be running before setup. Please start the container first."
        )

    if datasource.setup_status == "ready":
        return {
            "message": "Database is already configured",
            "setup_status": "ready"
        }

    # Update status to configuring
    datasource.setup_status = "configuring"
    db.commit()

    try:
        # Run database setup
        success, message = DatabaseSetupService.setup_database(datasource)

        if success:
            datasource.setup_status = "ready"
            db.commit()
            return {
                "message": message,
                "setup_status": "ready"
            }
        else:
            datasource.setup_status = "error"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database setup failed: {message}"
            )

    except Exception as e:
        datasource.setup_status = "error"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Setup error: {str(e)}"
        )


# ============================================================================
# ENDPOINT ENDPOINTS
# ============================================================================

@app.get("/projects/{project_id}/endpoints", response_model=List[schemas.EndpointResponse], tags=["Endpoints"])
def list_endpoints(project_id: int, db: Session = Depends(get_db)):
    """Get all API endpoints for a project"""
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    endpoints = crud.get_endpoints(db, project_id)
    return endpoints


# ============================================================================
# TEST EXECUTION ENDPOINTS
# ============================================================================

@app.post(
    "/projects/{project_id}/tests/run",
    response_model=schemas.TestRunResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Tests"]
)
async def run_tests(
    project_id: int,
    test_config: schemas.TestRunCreate,
    db: Session = Depends(get_db)
):
    """
    Execute tests for a project

    This endpoint runs the test_runner.py script and tracks all results in the database.
    The execution is asynchronous, so the endpoint returns immediately with a test_run_id.
    Use the /tests/runs/{id}/status endpoint to check progress.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Import test execution service
    try:
        from .test_execution_service import TestExecutionService
    except ImportError:
        from test_execution_service import TestExecutionService

    # Run tests asynchronously
    try:
        test_run_id = await TestExecutionService.run_tests(
            db=db,
            project_id=project_id,
            suite_filter=test_config.suite_filter,
            verbose=test_config.verbose,
            stop_on_fail=test_config.stop_on_fail,
            triggered_by=test_config.triggered_by
        )

        # Get test run
        test_run = crud.get_test_run(db, test_run_id)
        return test_run

    except Exception as e:
        logger.error(f"Failed to run tests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute tests: {str(e)}"
        )


@app.get("/projects/{project_id}/tests/runs", response_model=List[schemas.TestRunResponse], tags=["Tests"])
def list_test_runs(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all test runs for a project

    Returns a list of test runs ordered by start time (most recent first).
    Use pagination parameters to limit results.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    test_runs = crud.get_test_runs(db, project_id, skip=skip, limit=limit)
    return test_runs


@app.get("/projects/{project_id}/tests/runs/{run_id}", response_model=schemas.TestRunDetailResponse, tags=["Tests"])
def get_test_run(
    project_id: int,
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed test run results

    Returns the test run with all individual test results.
    Useful for displaying detailed test reports.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Get test run
    test_run = crud.get_test_run(db, run_id)
    if not test_run or test_run.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test run with id {run_id} not found"
        )

    return test_run


@app.get("/projects/{project_id}/tests/runs/{run_id}/status", response_model=schemas.TestRunStatusResponse, tags=["Tests"])
def get_test_run_status(
    project_id: int,
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Get real-time status of a test run

    Use this endpoint to poll for updates while tests are running.
    Returns progress percentage, current suite, and estimated time remaining.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Import test execution service
    try:
        from .test_execution_service import TestExecutionService
    except ImportError:
        from test_execution_service import TestExecutionService

    # Get status
    status_info = TestExecutionService.get_test_run_status(db, run_id)
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test run with id {run_id} not found"
        )

    return status_info


@app.post("/projects/{project_id}/tests/runs/{run_id}/cancel", tags=["Tests"])
async def cancel_test_run(
    project_id: int,
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Cancel a running test execution

    Terminates the test runner process and marks the test run as cancelled.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Import test execution service
    try:
        from .test_execution_service import TestExecutionService
    except ImportError:
        from test_execution_service import TestExecutionService

    # Cancel test run
    success = await TestExecutionService.cancel_test_run(db, run_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not cancel test run {run_id} (may not be running)"
        )

    return {"message": f"Test run {run_id} cancelled successfully"}


@app.delete("/projects/{project_id}/tests/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tests"])
def delete_test_run(
    project_id: int,
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a test run and all its results

    Permanently removes a test run from the database.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Delete test run
    success = crud.delete_test_run(db, run_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test run with id {run_id} not found"
        )

    return None


# ============================================================================
# TEST GENERATOR ENDPOINTS
# ============================================================================

# Import test generator
try:
    from .test_generator import get_test_generator, TestSuite
except ImportError:
    from test_generator import get_test_generator, TestSuite


@app.post("/projects/{project_id}/tests/generate", tags=["Test Generator"])
def generate_tests_for_project(
    project_id: int,
    base_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    test_types: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Generate tests for all components in a project

    Args:
        base_path: Path to scan for components
        output_dir: Directory to write test files (optional)
        test_types: List of test types to generate (unit, integration, api)

    Returns:
        Summary of generated tests
    """
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    generator = get_test_generator(db)
    try:
        suites = generator.generate_tests_for_project(
            project_id=project_id,
            base_path=base_path,
            output_dir=output_dir,
            test_types=test_types
        )

        return {
            "success": True,
            "suites": len(suites),
            "total_tests": sum(len(s.tests) for s in suites),
            "summary": [
                {
                    "component": s.component_name,
                    "tests": len(s.tests),
                    "test_names": [t.name for t in s.tests]
                }
                for s in suites
            ],
            "output_dir": output_dir
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/projects/{project_id}/components/{component_id}/tests/generate", tags=["Test Generator"])
def generate_tests_for_component(
    project_id: int,
    component_id: int,
    output_dir: Optional[str] = None,
    test_types: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Generate tests for a specific component

    Args:
        output_dir: Directory to write test files (optional)
        test_types: List of test types to generate (unit, integration, api)

    Returns:
        Generated test suite
    """
    generator = get_test_generator(db)
    try:
        suite = generator.generate_tests_for_component(
            project_id=project_id,
            component_id=component_id,
            output_dir=output_dir,
            test_types=test_types
        )

        return {
            "success": True,
            "component": suite.component_name,
            "tests": len(suite.tests),
            "test_details": [
                {
                    "name": t.name,
                    "type": t.test_type,
                    "description": t.description,
                    "target_function": t.target_function,
                    "target_endpoint": t.target_endpoint,
                    "content": t.content
                }
                for t in suite.tests
            ],
            "output_dir": output_dir
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/projects/{project_id}/components/{component_id}/tests/run", tags=["Test Generator"])
def run_component_tests(
    project_id: int,
    component_id: int,
    test_types: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Run tests for a specific component

    Creates a TestRun and executes tests associated with the component.
    """
    try:
        from .models import Component, ComponentTest, TestRun, TestResult
    except ImportError:
        from models import Component, ComponentTest, TestRun, TestResult

    from datetime import datetime
    import subprocess
    import threading

    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Verify component exists
    component = db.query(Component).filter(
        Component.id == component_id,
        Component.project_id == project_id
    ).first()
    if not component:
        raise HTTPException(status_code=404, detail=f"Component {component_id} not found")

    # Get tests for this component
    tests_query = db.query(ComponentTest).filter(ComponentTest.component_id == component_id)
    if test_types:
        tests_query = tests_query.filter(ComponentTest.test_type.in_(test_types))
    tests = tests_query.all()

    if not tests:
        raise HTTPException(status_code=400, detail="No tests found for this component")

    # Create TestRun
    test_run = TestRun(
        project_id=project_id,
        status="running",
        started_at=datetime.utcnow(),
        total_tests=len(tests),
        triggered_by=user.username if user else "api",
        suite_filter=component.name
    )
    db.add(test_run)
    db.commit()
    db.refresh(test_run)

    # Update component with test run reference
    component.last_test_run_id = test_run.id
    component.last_test_run_at = datetime.utcnow()
    db.commit()

    # Run tests in background
    def run_tests_background(test_run_id, component_id, test_files):
        from database import SessionLocal
        bg_db = SessionLocal()
        try:
            # Get unique test files
            unique_files = list(set(test_files))

            passed = 0
            failed = 0
            results = []

            for test_file in unique_files:
                try:
                    # Run pytest on the test file
                    result = subprocess.run(
                        ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
                        capture_output=True,
                        text=True,
                        timeout=300
                    )

                    if result.returncode == 0:
                        status = "passed"
                        passed += 1
                    else:
                        status = "failed"
                        failed += 1

                    results.append({
                        "file": test_file,
                        "status": status,
                        "output": result.stdout + result.stderr
                    })

                except subprocess.TimeoutExpired:
                    failed += 1
                    results.append({
                        "file": test_file,
                        "status": "error",
                        "output": "Test execution timed out"
                    })
                except Exception as e:
                    failed += 1
                    results.append({
                        "file": test_file,
                        "status": "error",
                        "output": str(e)
                    })

            # Update test run
            run = bg_db.query(TestRun).filter(TestRun.id == test_run_id).first()
            if run:
                run.status = "completed"
                run.completed_at = datetime.utcnow()
                run.passed_tests = passed
                run.failed_tests = failed
                run.duration_seconds = int((datetime.utcnow() - run.started_at).total_seconds())

            # Update component test counts
            comp = bg_db.query(Component).filter(Component.id == component_id).first()
            if comp:
                comp.tests_passing = passed
                comp.tests_failing = failed

            bg_db.commit()

        except Exception as e:
            # Mark test run as failed
            run = bg_db.query(TestRun).filter(TestRun.id == test_run_id).first()
            if run:
                run.status = "failed"
                run.error_message = str(e)
                run.completed_at = datetime.utcnow()
                bg_db.commit()
        finally:
            bg_db.close()

    # Get test files
    test_files = [t.test_file for t in tests]

    # Start background thread
    thread = threading.Thread(
        target=run_tests_background,
        args=(test_run.id, component_id, test_files)
    )
    thread.daemon = True
    thread.start()

    return {
        "test_run_id": test_run.id,
        "component_id": component_id,
        "status": "running",
        "message": f"Running {len(tests)} tests for component {component.name}"
    }


@app.post("/api/projects/{project_id}/components/sync-tests", tags=["Test Generator"])
def sync_component_tests(
    project_id: int,
    tests_dir: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Discover existing tests in filesystem and sync with database

    Scans the tests directory and associates discovered tests with components.
    """
    discovery = get_discovery_service(db)
    try:
        tests_synced, components_updated = discovery.sync_component_tests(project_id, tests_dir)
        return {
            "success": True,
            "tests_synced": tests_synced,
            "components_updated": components_updated
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/projects/{project_id}/components/generate-missing-tests", tags=["Test Generator"])
def generate_missing_tests(
    project_id: int,
    output_dir: Optional[str] = None,
    test_types: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Generate tests for all components that don't have tests

    Finds components with test_count=0 and generates tests for them.
    """
    try:
        from .models import Component
    except ImportError:
        from models import Component

    # Get project
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Get components without tests
    components = db.query(Component).filter(
        Component.project_id == project_id,
        Component.test_count == 0
    ).all()

    if not components:
        return {
            "success": True,
            "message": "All components already have tests",
            "components_processed": 0,
            "tests_generated": 0
        }

    generator = get_test_generator(db)
    total_tests = 0
    components_processed = 0

    # Use project output_dir or default
    if not output_dir:
        output_dir = "tests/generated/" if project.source_path else None

    for component in components:
        try:
            suite = generator.generate_tests_for_component(
                project_id=project_id,
                component_id=component.id,
                output_dir=output_dir,
                test_types=test_types or ["unit", "api"]
            )
            total_tests += len(suite.tests)
            components_processed += 1
        except Exception as e:
            logger.warning(f"Failed to generate tests for component {component.name}: {e}")

    return {
        "success": True,
        "components_processed": components_processed,
        "tests_generated": total_tests,
        "output_dir": output_dir
    }


@app.post("/api/projects/{project_id}/tests/run-all", tags=["Test Generator"])
def run_all_tests(
    project_id: int,
    test_types: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Run all tests for all components in a project

    Creates a TestRun and executes all component tests.
    """
    try:
        from .models import Component, ComponentTest, TestRun
    except ImportError:
        from models import Component, ComponentTest, TestRun

    from datetime import datetime

    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Get all tests
    tests_query = db.query(ComponentTest).join(Component).filter(
        Component.project_id == project_id
    )
    if test_types:
        tests_query = tests_query.filter(ComponentTest.test_type.in_(test_types))
    tests = tests_query.all()

    if not tests:
        raise HTTPException(status_code=400, detail="No tests found for this project")

    # Create TestRun
    test_run = TestRun(
        project_id=project_id,
        status="running",
        started_at=datetime.utcnow(),
        total_tests=len(tests),
        triggered_by=user.username if user else "api"
    )
    db.add(test_run)
    db.commit()
    db.refresh(test_run)

    # Get unique test files
    test_files = list(set(t.test_file for t in tests))

    # Run tests in background (similar to single component run)
    import threading
    import subprocess

    def run_all_tests_background(test_run_id, test_files, project_id):
        from database import SessionLocal
        bg_db = SessionLocal()
        try:
            passed = 0
            failed = 0

            for test_file in test_files:
                try:
                    result = subprocess.run(
                        ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    if result.returncode == 0:
                        passed += 1
                    else:
                        failed += 1
                except:
                    failed += 1

            # Update test run
            run = bg_db.query(TestRun).filter(TestRun.id == test_run_id).first()
            if run:
                run.status = "completed"
                run.completed_at = datetime.utcnow()
                run.passed_tests = passed
                run.failed_tests = failed
                run.duration_seconds = int((datetime.utcnow() - run.started_at).total_seconds())
                bg_db.commit()

        except Exception as e:
            run = bg_db.query(TestRun).filter(TestRun.id == test_run_id).first()
            if run:
                run.status = "failed"
                run.error_message = str(e)
                run.completed_at = datetime.utcnow()
                bg_db.commit()
        finally:
            bg_db.close()

    thread = threading.Thread(
        target=run_all_tests_background,
        args=(test_run.id, test_files, project_id)
    )
    thread.daemon = True
    thread.start()

    return {
        "test_run_id": test_run.id,
        "status": "running",
        "total_tests": len(tests),
        "test_files": len(test_files),
        "message": f"Running {len(tests)} tests across {len(test_files)} files"
    }


@app.get("/api/projects/{project_id}/components/{component_id}/tests", tags=["Test Generator"])
def get_component_tests(
    project_id: int,
    component_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all tests for a specific component
    """
    try:
        from .models import Component, ComponentTest
    except ImportError:
        from models import Component, ComponentTest

    # Verify component exists
    component = db.query(Component).filter(
        Component.id == component_id,
        Component.project_id == project_id
    ).first()
    if not component:
        raise HTTPException(status_code=404, detail=f"Component {component_id} not found")

    tests = db.query(ComponentTest).filter(
        ComponentTest.component_id == component_id
    ).all()

    return {
        "component_id": component_id,
        "component_name": component.name,
        "total_tests": len(tests),
        "tests_passing": component.tests_passing,
        "tests_failing": component.tests_failing,
        "tests": [t.to_dict() for t in tests]
    }


@app.get("/projects/{project_id}/tests/coverage-estimate", tags=["Test Generator"])
def get_test_coverage_estimate(
    project_id: int,
    base_path: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get estimated test coverage based on component analysis

    Analyzes components and estimates how many tests could be generated.
    """
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    generator = get_test_generator(db)
    try:
        estimate = generator.get_test_coverage_estimate(project_id, base_path)
        return estimate
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/projects/{project_id}/tests/conftest", tags=["Test Generator"])
def generate_conftest(
    project_id: int,
    output_dir: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Generate conftest.py with common test fixtures

    Creates a pytest conftest.py file with common fixtures for the project.
    """
    generator = get_test_generator(db)
    try:
        content = generator.generate_conftest(project_id, output_dir)
        return {
            "success": True,
            "content": content,
            "output_dir": output_dir
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# TEST DASHBOARD HTML ENDPOINTS
# ============================================================================

@app.get("/api/projects/{project_id}/tests/dashboard", response_class=HTMLResponse, tags=["Test Dashboard"])
def get_test_dashboard_html(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Get test dashboard HTML with overview stats and recent runs"""
    project = crud.get_project(db, project_id)
    if not project:
        return HTMLResponse(content='<div class="qa-error">Application not found</div>')

    # Get recent test runs
    test_runs = crud.get_test_runs(db, project_id, limit=10)

    # Calculate overall stats
    total_runs = len(test_runs)
    successful_runs = len([r for r in test_runs if r.status == 'completed' and r.failed_tests == 0])
    failed_runs = len([r for r in test_runs if r.status == 'failed' or (r.status == 'completed' and r.failed_tests > 0)])

    # Calculate success rate
    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0

    # Get latest run stats
    latest_run = test_runs[0] if test_runs else None

    html = f'''
    <div class="qa-test-dashboard">
        <!-- Stats Cards -->
        <div class="qa-stats-row qa-mb-4">
            <div class="qa-stat-card">
                <div class="qa-stat-label">Total Runs</div>
                <div class="qa-stat-value qa-text-primary">{total_runs}</div>
            </div>
            <div class="qa-stat-card">
                <div class="qa-stat-label">Success Rate</div>
                <div class="qa-stat-value {'qa-text-success' if success_rate >= 80 else 'qa-text-warning' if success_rate >= 50 else 'qa-text-danger'}">{success_rate:.1f}%</div>
            </div>
            <div class="qa-stat-card">
                <div class="qa-stat-label">Passed Runs</div>
                <div class="qa-stat-value qa-text-success">{successful_runs}</div>
            </div>
            <div class="qa-stat-card">
                <div class="qa-stat-label">Failed Runs</div>
                <div class="qa-stat-value qa-text-danger">{failed_runs}</div>
            </div>
        </div>

        <!-- Actions -->
        <div class="qa-actions qa-mb-4">
            <button class="qa-btn qa-btn-primary"
                    hx-post="{URL_PREFIX}/projects/{project_id}/tests/run"
                    hx-trigger="click"
                    hx-swap="afterbegin"
                    hx-target="#test-runs-list">
                <i class="qa-icon">play</i> Run All Tests
            </button>
            <button class="qa-btn qa-btn-secondary"
                    hx-get="{URL_PREFIX}/api/projects/{project_id}/tests/dashboard"
                    hx-trigger="click"
                    hx-swap="outerHTML">
                <i class="qa-icon">refresh</i> Refresh
            </button>
        </div>
    '''

    # Latest run summary
    if latest_run:
        status_class = 'qa-badge-success' if latest_run.status == 'completed' and latest_run.failed_tests == 0 else 'qa-badge-danger' if latest_run.failed_tests > 0 else 'qa-badge-warning'
        html += f'''
        <div class="qa-card qa-mb-4">
            <div class="qa-card-header">
                <h4>Latest Run</h4>
                <span class="qa-badge {status_class}">{latest_run.status}</span>
            </div>
            <div class="qa-card-body">
                <div class="qa-progress-bar qa-mb-2">
                    <div class="qa-progress-fill qa-bg-success" style="width: {(latest_run.passed_tests / latest_run.total_tests * 100) if latest_run.total_tests > 0 else 0}%"></div>
                </div>
                <div class="qa-row">
                    <span class="qa-text-success">{latest_run.passed_tests} passed</span>
                    <span class="qa-text-danger">{latest_run.failed_tests} failed</span>
                    <span class="qa-text-muted">of {latest_run.total_tests} total</span>
                </div>
            </div>
        </div>
        '''

    # Recent runs list
    html += '''
        <div class="qa-card">
            <div class="qa-card-header">
                <h4>Recent Test Runs</h4>
            </div>
            <div class="qa-card-body">
                <table class="qa-table">
                    <thead>
                        <tr>
                            <th>Run ID</th>
                            <th>Status</th>
                            <th>Passed</th>
                            <th>Failed</th>
                            <th>Duration</th>
                            <th>Started</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="test-runs-list">
    '''

    for run in test_runs:
        status_badge = {
            'running': 'qa-badge-warning',
            'completed': 'qa-badge-success' if run.failed_tests == 0 else 'qa-badge-danger',
            'failed': 'qa-badge-danger',
            'cancelled': 'qa-badge-gray'
        }.get(run.status, 'qa-badge-gray')

        started = run.started_at.strftime('%Y-%m-%d %H:%M') if run.started_at else '-'
        duration = f"{run.duration_seconds}s" if run.duration_seconds else '-'

        html += f'''
                        <tr>
                            <td>#{run.id}</td>
                            <td><span class="qa-badge {status_badge}">{run.status}</span></td>
                            <td class="qa-text-success">{run.passed_tests}</td>
                            <td class="qa-text-danger">{run.failed_tests}</td>
                            <td>{duration}</td>
                            <td>{started}</td>
                            <td>
                                <button class="qa-btn qa-btn-sm"
                                        hx-get="{URL_PREFIX}/api/projects/{project_id}/tests/runs/{run.id}/details"
                                        hx-target="#test-details-modal"
                                        hx-swap="innerHTML">
                                    View
                                </button>
                            </td>
                        </tr>
        '''

    html += '''
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Modal for test details -->
        <div id="test-details-modal" class="qa-modal-content"></div>
    </div>
    '''

    return HTMLResponse(content=html)


@app.get("/api/projects/{project_id}/tests/runs/{run_id}/details", response_class=HTMLResponse, tags=["Test Dashboard"])
def get_test_run_details_html(
    project_id: int,
    run_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed HTML view of a test run with all results"""
    test_run = crud.get_test_run(db, run_id)
    if not test_run:
        return HTMLResponse(content='<div class="qa-error">Test run not found</div>')

    # Group results by suite
    suites = {}
    for result in test_run.test_results:
        if result.suite_name not in suites:
            suites[result.suite_name] = []
        suites[result.suite_name].append(result)

    html = f'''
    <div class="qa-modal-dialog">
        <div class="qa-modal-header">
            <h3>Test Run #{run_id}</h3>
            <button class="qa-btn qa-btn-close" onclick="this.closest('.qa-modal-content').innerHTML=''">x</button>
        </div>
        <div class="qa-modal-body">
            <div class="qa-stats-row qa-mb-4">
                <div class="qa-stat-mini">
                    <span class="qa-text-success">{test_run.passed_tests}</span> passed
                </div>
                <div class="qa-stat-mini">
                    <span class="qa-text-danger">{test_run.failed_tests}</span> failed
                </div>
                <div class="qa-stat-mini">
                    <span class="qa-text-muted">{test_run.duration_seconds or 0}s</span> duration
                </div>
            </div>
    '''

    for suite_name, results in suites.items():
        passed = len([r for r in results if r.status == 'passed'])
        total = len(results)

        html += f'''
            <div class="qa-suite-card qa-mb-2">
                <div class="qa-suite-header">
                    <span class="qa-suite-name">{suite_name}</span>
                    <span class="qa-badge qa-badge-{'success' if passed == total else 'warning'}">{passed}/{total}</span>
                </div>
                <div class="qa-suite-tests">
        '''

        for result in results:
            icon = '✓' if result.status == 'passed' else '✗' if result.status == 'failed' else '○'
            color = 'qa-text-success' if result.status == 'passed' else 'qa-text-danger' if result.status == 'failed' else 'qa-text-muted'

            html += f'''
                    <div class="qa-test-item">
                        <span class="{color}">{icon}</span>
                        <span class="qa-test-file">{result.test_file}</span>
                        {f'<span class="qa-test-error qa-text-danger">{result.error_message}</span>' if result.error_message else ''}
                    </div>
            '''

        html += '''
                </div>
            </div>
        '''

    html += '''
        </div>
        <div class="qa-modal-footer">
            <button class="qa-btn qa-btn-secondary" onclick="this.closest('.qa-modal-content').innerHTML=''">Close</button>
        </div>
    </div>
    '''

    return HTMLResponse(content=html)


@app.get("/api/projects/{project_id}/tests/summary", tags=["Test Dashboard"])
def get_test_summary(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Get test summary statistics for a project"""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all test runs
    test_runs = crud.get_test_runs(db, project_id, limit=100)

    # Calculate stats
    total_runs = len(test_runs)
    successful_runs = len([r for r in test_runs if r.status == 'completed' and r.failed_tests == 0])
    total_tests = sum(r.total_tests for r in test_runs)
    total_passed = sum(r.passed_tests for r in test_runs)
    total_failed = sum(r.failed_tests for r in test_runs)
    avg_duration = sum(r.duration_seconds or 0 for r in test_runs) / total_runs if total_runs > 0 else 0

    # Get latest run
    latest_run = test_runs[0] if test_runs else None

    return {
        "project_id": project_id,
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": total_runs - successful_runs,
        "success_rate": (successful_runs / total_runs * 100) if total_runs > 0 else 0,
        "total_tests_executed": total_tests,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "average_duration_seconds": avg_duration,
        "latest_run": {
            "id": latest_run.id,
            "status": latest_run.status,
            "passed": latest_run.passed_tests,
            "failed": latest_run.failed_tests,
            "total": latest_run.total_tests
        } if latest_run else None
    }


# ============================================================================
# CONFIGURATION MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/projects/{project_id}/environment-variables", response_model=List[schemas.EnvironmentVariableResponse], tags=["Configuration"])
def list_environment_variables(
    project_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all environment variables for a project

    Values are returned masked for security. Use the individual endpoint to get the full value if needed.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Import secret manager
    try:
        from .secret_manager import mask_value
    except ImportError:
        from secret_manager import mask_value

    env_vars = crud.get_environment_variables(db, project_id)

    # Convert to response format with masked values
    return [
        schemas.EnvironmentVariableResponse(
            id=env_var.id,
            project_id=env_var.project_id,
            key=env_var.key,
            value_masked=mask_value(env_var.value_encrypted) if env_var.is_secret else env_var.value_encrypted[:20] + "...",
            description=env_var.description,
            is_secret=env_var.is_secret,
            created_at=env_var.created_at,
            updated_at=env_var.updated_at
        )
        for env_var in env_vars
    ]


@app.post("/projects/{project_id}/environment-variables", response_model=schemas.EnvironmentVariableResponse, status_code=status.HTTP_201_CREATED, tags=["Configuration"])
def create_environment_variable(
    project_id: int,
    env_var: schemas.EnvironmentVariableCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new environment variable

    The value is automatically encrypted before storage.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Import secret manager
    try:
        from .secret_manager import encrypt_value, mask_value
    except ImportError:
        from secret_manager import encrypt_value, mask_value

    # Encrypt the value
    try:
        encrypted_value = encrypt_value(env_var.value)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to encrypt value: {str(e)}"
        )

    # Create environment variable
    try:
        new_env_var = crud.create_environment_variable(
            db=db,
            project_id=project_id,
            key=env_var.key,
            value_encrypted=encrypted_value,
            description=env_var.description,
            is_secret=env_var.is_secret
        )

        # Create configuration history entry
        import json
        changes = {"action": "create", "key": env_var.key, "is_secret": env_var.is_secret}
        crud.create_configuration_history(
            db=db,
            project_id=project_id,
            changes_json=json.dumps(changes),
            snapshot_json="{}",
            changed_by="api"
        )

        return schemas.EnvironmentVariableResponse(
            id=new_env_var.id,
            project_id=new_env_var.project_id,
            key=new_env_var.key,
            value_masked=mask_value(new_env_var.value_encrypted),
            description=new_env_var.description,
            is_secret=new_env_var.is_secret,
            created_at=new_env_var.created_at,
            updated_at=new_env_var.updated_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.put("/projects/{project_id}/environment-variables/{key}", response_model=schemas.EnvironmentVariableResponse, tags=["Configuration"])
def update_environment_variable(
    project_id: int,
    key: str,
    env_var_update: schemas.EnvironmentVariableUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an environment variable

    If value is provided, it will be encrypted before storage.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Import secret manager
    try:
        from .secret_manager import encrypt_value, mask_value
    except ImportError:
        from secret_manager import encrypt_value, mask_value

    # Encrypt new value if provided
    encrypted_value = None
    if env_var_update.value is not None:
        try:
            encrypted_value = encrypt_value(env_var_update.value)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to encrypt value: {str(e)}"
            )

    # Update environment variable
    updated_env_var = crud.update_environment_variable(
        db=db,
        project_id=project_id,
        key=key,
        value_encrypted=encrypted_value,
        description=env_var_update.description,
        is_secret=env_var_update.is_secret
    )

    if not updated_env_var:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment variable '{key}' not found"
        )

    # Create configuration history entry
    import json
    changes = {"action": "update", "key": key}
    if env_var_update.value is not None:
        changes["value_changed"] = True
    if env_var_update.description is not None:
        changes["description"] = env_var_update.description
    crud.create_configuration_history(
        db=db,
        project_id=project_id,
        changes_json=json.dumps(changes),
        snapshot_json="{}",
        changed_by="api"
    )

    return schemas.EnvironmentVariableResponse(
        id=updated_env_var.id,
        project_id=updated_env_var.project_id,
        key=updated_env_var.key,
        value_masked=mask_value(updated_env_var.value_encrypted),
        description=updated_env_var.description,
        is_secret=updated_env_var.is_secret,
        created_at=updated_env_var.created_at,
        updated_at=updated_env_var.updated_at
    )


@app.delete("/projects/{project_id}/environment-variables/{key}", status_code=status.HTTP_204_NO_CONTENT, tags=["Configuration"])
def delete_environment_variable(
    project_id: int,
    key: str,
    db: Session = Depends(get_db)
):
    """
    Delete an environment variable
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Delete environment variable
    success = crud.delete_environment_variable(db, project_id, key)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment variable '{key}' not found"
        )

    # Create configuration history entry
    import json
    changes = {"action": "delete", "key": key}
    crud.create_configuration_history(
        db=db,
        project_id=project_id,
        changes_json=json.dumps(changes),
        snapshot_json="{}",
        changed_by="api"
    )

    return None


@app.get("/projects/{project_id}/configuration/history", response_model=List[schemas.ConfigurationHistoryResponse], tags=["Configuration"])
def get_configuration_history(
    project_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get configuration change history for a project

    Returns the most recent configuration changes.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    history = crud.get_configuration_history(db, project_id, limit=limit)
    return history


# ============================================================================
# AUDIT LOG ENDPOINTS
# ============================================================================

@app.get("/api/projects/{project_id}/audit-log", tags=["Audit Log"])
def get_project_audit_log(
    project_id: int,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get audit log entries for a project

    Filter by action type (create, update, delete, deploy, etc.) or resource type.
    """
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    audit_service = get_audit_service(db)
    logs = audit_service.get_logs(
        project_id=project_id,
        action=action,
        resource_type=resource_type,
        limit=limit,
        offset=offset
    )
    return [log.to_dict() for log in logs]


@app.get("/api/projects/{project_id}/audit-log-html", response_class=HTMLResponse, tags=["Audit Log"])
def get_project_audit_log_html(
    project_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get audit log as HTML for HTMX"""
    project = crud.get_project(db, project_id)
    if not project:
        return HTMLResponse(content='<p class="qa-text-muted">Project not found</p>')

    audit_service = get_audit_service(db)
    logs = audit_service.get_logs(project_id=project_id, limit=limit)

    if not logs:
        return HTMLResponse(content='''
            <div class="qa-text-center qa-p-6">
                <p class="qa-text-muted">No activity recorded yet</p>
            </div>
        ''')

    # Generate HTML
    html = '<div class="qa-audit-log">'
    for log in logs:
        timestamp = log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log.timestamp else ''

        # Color based on action
        if log.action in ['create', 'deploy', 'start']:
            color = 'success'
            icon = 'plus-circle'
        elif log.action in ['update', 'config_change']:
            color = 'info'
            icon = 'edit'
        elif log.action in ['delete', 'stop']:
            color = 'danger'
            icon = 'trash-2'
        elif log.action in ['rollback']:
            color = 'warning'
            icon = 'rotate-ccw'
        else:
            color = 'muted'
            icon = 'activity'

        html += f'''
            <div class="qa-audit-item qa-flex qa-items-start qa-gap-3 qa-p-3" style="border-bottom: 1px solid var(--q-border);">
                <div class="qa-audit-icon" style="color: var(--q-{color}); margin-top: 2px;">
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <circle cx="12" cy="12" r="10" stroke-width="2"/>
                    </svg>
                </div>
                <div class="qa-audit-content qa-flex-1">
                    <div class="qa-flex qa-justify-between qa-items-start">
                        <span class="qa-font-medium">{log.action.replace('_', ' ').title()}</span>
                        <span class="qa-text-xs qa-text-muted">{timestamp}</span>
                    </div>
                    <p class="qa-text-sm qa-text-secondary qa-mt-1">
                        {log.resource_type or ''}{': ' + log.resource_name if log.resource_name else ''}
                    </p>
                    <p class="qa-text-xs qa-text-muted qa-mt-1">by {log.user_id or 'system'}</p>
                </div>
            </div>
        '''
    html += '</div>'

    return HTMLResponse(content=html)


@app.get("/audit-log", tags=["Audit Log"])
def get_global_audit_log(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Get global audit log (all projects)"""
    audit_service = get_audit_service(db)
    logs = audit_service.get_logs(
        action=action,
        resource_type=resource_type,
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    return [log.to_dict() for log in logs]


@app.get("/audit-log/stats", tags=["Audit Log"])
def get_audit_stats(
    project_id: Optional[int] = None,
    days: int = 7,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Get audit log statistics"""
    audit_service = get_audit_service(db)
    return audit_service.get_stats(project_id=project_id, days=days)


# ============================================================================
# APPLICATION LOGS ENDPOINTS
# ============================================================================

@app.get("/api/projects/{project_id}/logs", tags=["Logs"])
def get_project_logs(
    project_id: int,
    source: Optional[str] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get application logs for a project.

    Filters:
    - source: app, db, access, deploy, system, or all
    - level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    - search: Text to search in message
    - since: ISO datetime or duration like "1h", "24h", "7d"
    """
    from datetime import datetime, timedelta

    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Parse since parameter
    since_dt = None
    if since:
        if since.endswith('h'):
            hours = int(since[:-1])
            since_dt = datetime.utcnow() - timedelta(hours=hours)
        elif since.endswith('d'):
            days = int(since[:-1])
            since_dt = datetime.utcnow() - timedelta(days=days)
        elif since.endswith('m'):
            minutes = int(since[:-1])
            since_dt = datetime.utcnow() - timedelta(minutes=minutes)
        else:
            try:
                since_dt = datetime.fromisoformat(since)
            except:
                pass

    log_service = get_log_service(db)
    logs = log_service.get_logs(
        project_id=project_id,
        source=source,
        level=level,
        search=search,
        since=since_dt,
        limit=limit,
        offset=offset
    )

    return [log.to_dict() for log in logs]


@app.get("/api/projects/{project_id}/logs-html", response_class=HTMLResponse, tags=["Logs"])
def get_project_logs_html(
    project_id: int,
    source: Optional[str] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get project logs as HTML for HTMX"""
    from datetime import datetime, timedelta

    project = crud.get_project(db, project_id)
    if not project:
        return HTMLResponse(content='<p class="qa-text-muted">Project not found</p>')

    log_service = get_log_service(db)
    logs = log_service.get_logs(
        project_id=project_id,
        source=source,
        level=level,
        search=search,
        limit=limit
    )

    if not logs:
        return HTMLResponse(content='''
            <div class="qa-text-center qa-p-6">
                <p class="qa-text-muted">No logs found</p>
                <p class="qa-text-xs qa-text-dim qa-mt-2">Logs will appear here as your application runs</p>
            </div>
        ''')

    html = '<div class="qa-log-list" style="font-family: monospace; font-size: 13px;">'
    for log in logs:
        timestamp = log.timestamp.strftime('%H:%M:%S') if log.timestamp else ''
        level_class = {
            'DEBUG': 'qa-text-muted',
            'INFO': 'qa-text-info',
            'WARNING': 'qa-text-warning',
            'ERROR': 'qa-text-danger',
            'CRITICAL': 'qa-text-danger qa-font-bold'
        }.get(log.level, 'qa-text-secondary')

        source_badge = {
            'app': ('APP', 'primary'),
            'db': ('DB', 'info'),
            'access': ('HTTP', 'success'),
            'deploy': ('DEPLOY', 'warning'),
            'system': ('SYS', 'muted')
        }.get(log.source, ('LOG', 'muted'))

        message = log.message[:150] if log.message else ''
        if len(log.message or '') > 150:
            message += '...'

        html += f'''
            <div class="qa-log-item qa-flex qa-gap-2 qa-p-2" style="border-bottom: 1px solid var(--q-border); white-space: nowrap; overflow: hidden;">
                <span class="qa-text-muted" style="width: 70px; flex-shrink: 0;">{timestamp}</span>
                <span class="qa-badge qa-badge-{source_badge[1]}" style="width: 50px; flex-shrink: 0; text-align: center;">{source_badge[0]}</span>
                <span class="{level_class}" style="width: 60px; flex-shrink: 0;">{log.level}</span>
                <span class="qa-text-secondary" style="overflow: hidden; text-overflow: ellipsis;">{message}</span>
            </div>
        '''
    html += '</div>'

    return HTMLResponse(content=html)


@app.get("/api/projects/{project_id}/logs/stats", tags=["Logs"])
def get_project_log_stats(
    project_id: int,
    hours: int = 24,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Get log statistics for a project"""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    log_service = get_log_service(db)
    return log_service.get_stats(project_id=project_id, hours=hours)


# ============================================================================
# HEALTH CHECK & MONITORING ENDPOINTS
# ============================================================================

@app.get("/health/system", tags=["Health"])
def get_system_health(
    db: Session = Depends(get_db)
):
    """Get overall system health summary"""
    health_service = get_health_service(db)
    return health_service.get_summary()


@app.get("/health/system-html", response_class=HTMLResponse, tags=["Health"])
def get_system_health_html(
    db: Session = Depends(get_db)
):
    """Get system health status as HTML for dashboard"""
    health_service = get_health_service(db)
    summary = health_service.get_summary()

    status = summary.get("overall_status", "unknown")
    status_class = {
        "healthy": ("success", "All systems operational"),
        "unhealthy": ("danger", "Some systems are down"),
        "degraded": ("warning", "Some systems are degraded"),
        "unknown": ("muted", "Status unknown")
    }.get(status, ("muted", "Unknown"))

    html = f'''
        <div class="qa-flex qa-items-center qa-gap-2">
            <span class="qa-connector-status-dot {status_class[0]}"></span>
            <span class="qa-text-{status_class[0]}">{status_class[1]}</span>
        </div>
    '''
    return HTMLResponse(content=html)


@app.get("/api/projects/{project_id}/health", tags=["Health"])
def get_project_health(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Get health check status for a project"""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    health_service = get_health_service(db)
    checks = health_service.get_checks(project_id=project_id)
    incidents = health_service.get_incidents(project_id=project_id, status="active")

    return {
        "project_id": project_id,
        "checks": [c.to_dict() for c in checks],
        "active_incidents": [i.to_dict() for i in incidents],
        "status": "healthy" if not incidents else "unhealthy"
    }


@app.get("/api/projects/{project_id}/health-html", response_class=HTMLResponse, tags=["Health"])
def get_project_health_html(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Get project health status as HTML"""
    health_service = get_health_service(db)
    checks = health_service.get_checks(project_id=project_id)
    incidents = health_service.get_incidents(project_id=project_id, status="active")

    if not checks:
        return HTMLResponse(content='''
            <div class="qa-text-center qa-p-4">
                <p class="qa-text-muted">No health checks configured</p>
                <button class="qa-btn qa-btn-primary qa-btn-sm qa-mt-2" onclick="openAddHealthCheckModal()">
                    Add Health Check
                </button>
            </div>
        ''')

    html = '<div class="qa-list">'
    for check in checks:
        status_class = {
            "healthy": "success",
            "unhealthy": "danger",
            "unknown": "muted",
            "degraded": "warning"
        }.get(check.last_status, "muted")

        last_check = check.last_check.strftime('%H:%M:%S') if check.last_check else 'Never'

        html += f'''
            <div class="qa-list-item qa-flex qa-justify-between qa-items-center qa-p-3" style="border-bottom: 1px solid var(--q-border);">
                <div>
                    <span class="qa-font-medium">{check.name}</span>
                    <p class="qa-text-xs qa-text-muted qa-mt-1">{check.endpoint}</p>
                </div>
                <div class="qa-flex qa-items-center qa-gap-3">
                    <span class="qa-text-xs qa-text-muted">{last_check}</span>
                    <span class="qa-badge qa-badge-{status_class}">{check.last_status}</span>
                </div>
            </div>
        '''
    html += '</div>'

    if incidents:
        html += f'<div class="qa-alert qa-alert-danger qa-mt-3"><strong>{len(incidents)}</strong> active incident(s)</div>'

    return HTMLResponse(content=html)


@app.post("/api/projects/{project_id}/health-checks", tags=["Health"])
def create_health_check_endpoint(
    project_id: int,
    name: str,
    endpoint: str,
    environment_id: Optional[int] = None,
    method: str = "GET",
    expected_status: int = 200,
    timeout_seconds: int = 30,
    interval_seconds: int = 60,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Create a new health check for a project"""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    health_service = get_health_service(db)
    check = health_service.create_check(
        name=name,
        endpoint=endpoint,
        project_id=project_id,
        environment_id=environment_id,
        method=method,
        expected_status=expected_status,
        timeout_seconds=timeout_seconds,
        interval_seconds=interval_seconds
    )

    return {"success": True, "check": check.to_dict()}


@app.post("/api/projects/{project_id}/health-checks/run", tags=["Health"])
async def run_project_health_checks(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Run all health checks for a project"""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    health_service = get_health_service(db)
    results = await health_service.run_all_checks(project_id=project_id)

    return {"success": True, "results": results}


@app.get("/api/projects/{project_id}/incidents", tags=["Health"])
def get_project_incidents(
    project_id: int,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Get incidents for a project"""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    health_service = get_health_service(db)
    incidents = health_service.get_incidents(project_id=project_id, status=status, limit=limit)

    return [i.to_dict() for i in incidents]


@app.post("/incidents/{incident_id}/resolve", tags=["Health"])
def resolve_incident_endpoint(
    incident_id: int,
    resolution_notes: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Resolve an incident"""
    health_service = get_health_service(db)
    incident = health_service.resolve_incident(
        incident_id=incident_id,
        resolved_by=user.username,
        resolution_notes=resolution_notes
    )

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return {"success": True, "incident": incident.to_dict()}


@app.post("/incidents/{incident_id}/acknowledge", tags=["Health"])
def acknowledge_incident_endpoint(
    incident_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Acknowledge an incident"""
    health_service = get_health_service(db)
    incident = health_service.acknowledge_incident(
        incident_id=incident_id,
        acknowledged_by=user.username
    )

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return {"success": True, "incident": incident.to_dict()}


@app.get("/dashboard/activity", response_class=HTMLResponse, tags=["Dashboard"])
def get_dashboard_activity_html(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get recent activity for dashboard as HTML"""
    audit_service = get_audit_service(db)
    activities = audit_service.get_recent_activity(limit=limit)

    if not activities:
        return HTMLResponse(content='''
            <div class="qa-text-center qa-p-6">
                <p class="qa-text-muted">No recent activity</p>
            </div>
        ''')

    html = '<div class="qa-activity-list">'
    for activity in activities:
        timestamp = activity.get('timestamp', '')
        if timestamp:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp = dt.strftime('%H:%M')
            except:
                timestamp = timestamp[:5]

        color = activity.get('color', 'muted')
        message = activity.get('message', '')
        user_id = activity.get('user_id', 'system')

        html += f'''
            <div class="qa-activity-item qa-flex qa-items-center qa-gap-3 qa-p-3" style="border-bottom: 1px solid var(--q-border);">
                <div class="qa-activity-dot" style="width: 8px; height: 8px; border-radius: 50%; background: var(--q-{color});"></div>
                <div class="qa-flex-1">
                    <p class="qa-text-sm">{message}</p>
                    <p class="qa-text-xs qa-text-muted">{user_id}</p>
                </div>
                <span class="qa-text-xs qa-text-muted">{timestamp}</span>
            </div>
        '''
    html += '</div>'

    return HTMLResponse(content=html)


# ============================================================================
# RESOURCE MANAGER ENDPOINTS (Ports, Secrets, Services)
# ============================================================================


@app.get("/resources/overview", tags=["Resources"])
def get_resources_overview(
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Get complete resource overview including ports, processes, and containers.
    This performs an auto-discovery scan of system resources.
    """
    resource_manager = get_resource_manager(db)
    overview = resource_manager.scan_resources(docker_service.client if docker_service else None)

    # Add database stats
    overview["allocations"] = {
        "ports": len(resource_manager.ports.list_allocations()),
        "services": len(resource_manager.services.list_all()),
        "secrets": len(resource_manager.secrets.list_secrets())
    }

    return overview


@app.get("/resources/overview-html", response_class=HTMLResponse, tags=["Resources"])
def get_resources_overview_html(
    db: Session = Depends(get_db)
):
    """Get resource overview as HTML for dashboard"""
    resource_manager = get_resource_manager(db)
    overview = resource_manager.scan_resources(docker_service.client if docker_service else None)

    ports_count = len(overview.get("ports_in_use", []))
    procs_count = len(overview.get("quantum_processes", []))
    containers_count = len(overview.get("docker_containers", []))
    system = overview.get("system", {})

    cpu_percent = system.get("cpu_percent", 0) if system.get("available") else 0
    mem_percent = system.get("memory", {}).get("percent", 0) if system.get("available") else 0

    html = f'''
    <div class="qa-grid qa-grid-4 qa-gap-4">
        <div class="qa-stat-card">
            <div class="qa-stat-icon" style="background: var(--q-primary-dim); color: var(--q-primary);">
                <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/>
                </svg>
            </div>
            <div class="qa-stat-content">
                <div class="qa-stat-value">{ports_count}</div>
                <div class="qa-stat-label">Ports in Use</div>
            </div>
        </div>
        <div class="qa-stat-card">
            <div class="qa-stat-icon" style="background: var(--q-success-dim); color: var(--q-success);">
                <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2"/>
                </svg>
            </div>
            <div class="qa-stat-content">
                <div class="qa-stat-value">{containers_count}</div>
                <div class="qa-stat-label">Containers</div>
            </div>
        </div>
        <div class="qa-stat-card">
            <div class="qa-stat-icon" style="background: var(--q-warning-dim); color: var(--q-warning);">
                <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                </svg>
            </div>
            <div class="qa-stat-content">
                <div class="qa-stat-value">{cpu_percent:.0f}%</div>
                <div class="qa-stat-label">CPU Usage</div>
            </div>
        </div>
        <div class="qa-stat-card">
            <div class="qa-stat-icon" style="background: var(--q-info-dim); color: var(--q-info);">
                <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
            </div>
            <div class="qa-stat-content">
                <div class="qa-stat-value">{mem_percent:.0f}%</div>
                <div class="qa-stat-label">Memory</div>
            </div>
        </div>
    </div>
    '''

    return HTMLResponse(content=html)


@app.get("/resources/scan", tags=["Resources"])
def scan_resources(
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Force a resource scan and return discovered resources"""
    resource_manager = get_resource_manager(db)
    return resource_manager.scan_resources(docker_service.client if docker_service else None)


@app.get("/resources/ports/discovered", tags=["Resources"])
def get_discovered_ports(
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Get ports currently in use on the system (via psutil)"""
    resource_manager = get_resource_manager(db)
    return resource_manager.scan_ports()


@app.get("/resources/processes", tags=["Resources"])
def get_quantum_processes(
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Get running Quantum framework processes"""
    resource_manager = get_resource_manager(db)
    return resource_manager.scan_processes()


@app.get("/resources/containers", tags=["Resources"])
def get_docker_containers_resource(
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Get Docker containers via Resource Manager"""
    resource_manager = get_resource_manager(db)
    return resource_manager.scan_containers(docker_service.client if docker_service else None)


@app.get("/resources/system", tags=["Resources"])
def get_system_resources(
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Get system resource usage (CPU, memory, disk)"""
    resource_manager = get_resource_manager(db)
    return resource_manager.get_system_resources()


@app.post("/resources/sync", tags=["Resources"])
def sync_discovered_resources(
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Sync discovered ports with database allocations.
    Returns orphaned allocations and untracked ports.
    """
    resource_manager = get_resource_manager(db)
    return resource_manager.sync_discovered_ports(docker_service.client if docker_service else None)


@app.get("/resources/ports", tags=["Resources"])
def list_port_allocations(
    project_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    host: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """List all port allocations with optional filters"""
    resource_manager = get_resource_manager(db)
    ports = resource_manager.ports.list_allocations(
        project_id=project_id,
        environment_id=environment_id,
        host=host,
        status=status_filter
    )
    return [p.to_dict() for p in ports]


@app.post("/resources/ports/allocate", tags=["Resources"])
def allocate_port(
    project_id: int,
    service_name: str,
    port_type: str = "app",
    environment_id: Optional[int] = None,
    preferred_port: Optional[int] = None,
    host: str = "localhost",
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Allocate a port for a service

    Port types: app, database, cache, web, queue
    """
    resource_manager = get_resource_manager(db)
    allocation = resource_manager.ports.allocate(
        project_id=project_id,
        service_name=service_name,
        port_type=port_type,
        environment_id=environment_id,
        preferred_port=preferred_port,
        host=host
    )

    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not allocate port - no ports available in range"
        )

    return {"success": True, "allocation": allocation.to_dict()}


@app.post("/resources/ports/release", tags=["Resources"])
def release_port(
    port: int,
    host: str = "localhost",
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Release an allocated port"""
    resource_manager = get_resource_manager(db)

    if resource_manager.ports.release(port, host):
        return {"success": True, "message": f"Port {port} released"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Port {port} not found or already released"
    )


@app.get("/resources/ports/check/{port}", tags=["Resources"])
def check_port_availability(
    port: int,
    host: str = "localhost",
    db: Session = Depends(get_db)
):
    """Check if a port is available"""
    resource_manager = get_resource_manager(db)
    available = resource_manager.ports.is_available(port, host)
    return {"port": port, "host": host, "available": available}


@app.get("/resources/ports/ranges", tags=["Resources"])
def list_port_ranges(
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """List configured port ranges"""
    resource_manager = get_resource_manager(db)
    ranges = resource_manager.ports.get_ranges()
    return [r.to_dict() for r in ranges]


@app.post("/resources/ports/ranges", tags=["Resources"])
def create_port_range(
    name: str,
    start_port: int,
    end_port: int,
    host: str = "localhost",
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Create a new port range"""
    resource_manager = get_resource_manager(db)

    port_range = resource_manager.ports.create_range(
        name=name,
        start_port=start_port,
        end_port=end_port,
        host=host,
        description=description
    )

    return {"success": True, "range": port_range.to_dict()}


@app.post("/resources/ports/reserve", tags=["Resources"])
def reserve_port(
    port: int,
    reason: str,
    host: str = "localhost",
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Reserve a port (prevents automatic allocation)"""
    resource_manager = get_resource_manager(db)

    if resource_manager.ports.reserve(port, reason, host):
        return {"success": True, "message": f"Port {port} reserved: {reason}"}

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Port {port} is already in use"
    )


# ============================================================================
# SECRETS ENDPOINTS
# ============================================================================

@app.get("/resources/secrets", tags=["Resources"])
def list_secrets(
    project_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    scope: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    List secrets (values are masked)

    Scopes: global, project, environment
    """
    resource_manager = get_resource_manager(db)
    secrets = resource_manager.secrets.list_secrets(
        project_id=project_id,
        environment_id=environment_id,
        scope=scope
    )

    # Mask values
    return [
        {
            "id": s.id,
            "key": s.key,
            "scope": s.scope,
            "project_id": s.project_id,
            "environment_id": s.environment_id,
            "description": s.description,
            "is_sensitive": s.is_sensitive,
            "value_masked": "****" if s.is_sensitive else resource_manager.secrets.get(s.key, s.project_id, s.environment_id)[:4] + "****" if resource_manager.secrets.get(s.key, s.project_id, s.environment_id) else None
        }
        for s in secrets
    ]


@app.post("/resources/secrets", tags=["Resources"])
def create_or_update_secret(
    key: str,
    value: str,
    scope: str = "project",
    project_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    description: Optional[str] = None,
    is_sensitive: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Create or update a secret"""
    resource_manager = get_resource_manager(db)

    secret = resource_manager.secrets.set(
        key=key,
        value=value,
        scope=scope,
        project_id=project_id,
        environment_id=environment_id,
        description=description,
        is_sensitive=is_sensitive
    )

    return {
        "success": True,
        "secret": {
            "id": secret.id,
            "key": secret.key,
            "scope": secret.scope,
            "description": secret.description
        }
    }


@app.delete("/resources/secrets/{secret_id}", tags=["Resources"])
def delete_secret(
    secret_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Delete a secret"""
    resource_manager = get_resource_manager(db)

    if resource_manager.secrets.delete(secret_id):
        return {"success": True, "message": "Secret deleted"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Secret not found"
    )


@app.post("/resources/secrets/{secret_id}/rotate", tags=["Resources"])
def rotate_secret(
    secret_id: int,
    new_value: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Rotate a secret value"""
    resource_manager = get_resource_manager(db)

    if resource_manager.secrets.rotate(secret_id, new_value):
        return {"success": True, "message": "Secret rotated"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Secret not found"
    )


# ============================================================================
# SERVICE REGISTRY ENDPOINTS
# ============================================================================

@app.get("/resources/services", tags=["Resources"])
def list_services(
    project_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    service_type: Optional[str] = None,
    healthy_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    List registered services

    Types: app, api, database, cache, queue, web
    """
    resource_manager = get_resource_manager(db)
    services = resource_manager.services.list_services(
        project_id=project_id,
        environment_id=environment_id,
        service_type=service_type,
        healthy_only=healthy_only
    )
    return [s.to_dict() for s in services]


@app.post("/resources/services", tags=["Resources"])
def register_service(
    name: str,
    service_type: str,
    host: str,
    port: int,
    protocol: str = "http",
    project_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    health_endpoint: Optional[str] = None,
    health_interval: int = 30,
    metadata: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Register a new service"""
    resource_manager = get_resource_manager(db)

    service = resource_manager.services.register(
        name=name,
        service_type=service_type,
        host=host,
        port=port,
        protocol=protocol,
        project_id=project_id,
        environment_id=environment_id,
        health_endpoint=health_endpoint,
        health_interval=health_interval,
        metadata=metadata
    )

    return {"success": True, "service": service.to_dict()}


@app.delete("/resources/services/{service_id}", tags=["Resources"])
def unregister_service(
    service_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Unregister a service"""
    resource_manager = get_resource_manager(db)

    if resource_manager.services.unregister(service_id):
        return {"success": True, "message": "Service unregistered"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Service not found"
    )


@app.get("/resources/services/{service_id}/health", tags=["Resources"])
async def check_service_health(
    service_id: int,
    db: Session = Depends(get_db)
):
    """Check health of a specific service"""
    resource_manager = get_resource_manager(db)
    result = await resource_manager.services.check_health(service_id)
    return result


@app.post("/resources/services/health-check", tags=["Resources"])
async def run_health_checks(
    project_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Run health checks on all services"""
    resource_manager = get_resource_manager(db)
    results = await resource_manager.services.run_health_checks(
        project_id=project_id,
        environment_id=environment_id
    )
    return {"results": results}


@app.get("/resources/services/discover/{service_type}", tags=["Resources"])
def discover_services(
    service_type: str,
    project_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Discover healthy services of a given type"""
    resource_manager = get_resource_manager(db)
    services = resource_manager.services.discover(
        service_type=service_type,
        project_id=project_id,
        environment_id=environment_id
    )
    return [s.to_dict() for s in services]


# ============================================================================
# CONFIG GENERATION ENDPOINTS
# ============================================================================

try:
    from .config_generator import get_config_generator
except ImportError:
    from config_generator import get_config_generator


@app.get("/projects/{project_id}/config/env", tags=["Config Generation"])
def generate_env_file(
    project_id: int,
    environment_id: Optional[int] = None,
    include_secrets: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Generate .env file content for a project

    Set include_secrets=true to include decrypted secret values (requires admin)
    """
    generator = get_config_generator(db)

    try:
        content = generator.generate_env_file(
            project_id=project_id,
            environment_id=environment_id,
            include_secrets=include_secrets
        )
        return {"content": content, "filename": f".env.{environment_id or 'default'}"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/projects/{project_id}/config/docker-compose", tags=["Config Generation"])
def generate_docker_compose(
    project_id: int,
    environment_id: Optional[int] = None,
    include_databases: bool = True,
    include_cache: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Generate docker-compose.yml content for a project"""
    generator = get_config_generator(db)

    try:
        content = generator.generate_docker_compose(
            project_id=project_id,
            environment_id=environment_id,
            include_databases=include_databases,
            include_cache=include_cache
        )
        return {"content": content, "filename": "docker-compose.yml"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/projects/{project_id}/config/nginx", tags=["Config Generation"])
def generate_nginx_config(
    project_id: int,
    environment_id: Optional[int] = None,
    domain: Optional[str] = None,
    ssl: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Generate nginx configuration for a project"""
    generator = get_config_generator(db)

    try:
        content = generator.generate_nginx_conf(
            project_id=project_id,
            environment_id=environment_id,
            domain=domain,
            ssl=ssl
        )
        return {"content": content, "filename": f"nginx-{domain or 'app'}.conf"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/projects/{project_id}/config/systemd", tags=["Config Generation"])
def generate_systemd_service(
    project_id: int,
    environment_id: Optional[int] = None,
    working_dir: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Generate systemd service file for a project"""
    generator = get_config_generator(db)

    try:
        content = generator.generate_systemd_service(
            project_id=project_id,
            environment_id=environment_id,
            working_dir=working_dir
        )
        # Get project name for filename
        project = crud.get_project(db, project_id)
        filename = f"{project.name.lower().replace(' ', '-')}.service" if project else "app.service"
        return {"content": content, "filename": filename}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/projects/{project_id}/config/download/{config_type}", tags=["Config Generation"])
def download_config(
    project_id: int,
    config_type: str,
    environment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Download a generated config file

    config_type: env, docker-compose, nginx, systemd
    """
    from fastapi.responses import Response

    generator = get_config_generator(db)
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        if config_type == "env":
            content = generator.generate_env_file(project_id, environment_id, include_secrets=False)
            filename = f".env.{environment_id or 'default'}"
            media_type = "text/plain"
        elif config_type == "docker-compose":
            content = generator.generate_docker_compose(project_id, environment_id)
            filename = "docker-compose.yml"
            media_type = "application/x-yaml"
        elif config_type == "nginx":
            content = generator.generate_nginx_conf(project_id, environment_id)
            filename = f"nginx-{project.name.lower()}.conf"
            media_type = "text/plain"
        elif config_type == "systemd":
            content = generator.generate_systemd_service(project_id, environment_id)
            filename = f"{project.name.lower().replace(' ', '-')}.service"
            media_type = "text/plain"
        else:
            raise HTTPException(status_code=400, detail=f"Unknown config type: {config_type}")

        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# RESOURCE MANAGER UI (HTML)
# ============================================================================

@app.get("/api/resources/stats", response_class=HTMLResponse, tags=["Resources UI"])
def get_resources_stats_html(db: Session = Depends(get_db)):
    """Get resource stats as HTML cards"""
    resource_manager = get_resource_manager(db)

    # Get stats
    ports = resource_manager.ports.list_allocations()
    active_ports = len([p for p in ports if p.status == 'allocated'])
    total_ports = len(ports)

    secrets = resource_manager.secrets.list_secrets()
    total_secrets = len(secrets)

    services = resource_manager.services.list_services()
    healthy_services = len([s for s in services if s.health_status == 'healthy'])
    total_services = len(services)

    return HTMLResponse(content=f'''
        <div class="qa-stat-card">
            <div class="qa-stat-label">Port Allocations</div>
            <div class="qa-stat-value qa-text-primary">{active_ports}/{total_ports}</div>
            <div class="qa-stat-sub qa-text-success">active</div>
        </div>
        <div class="qa-stat-card">
            <div class="qa-stat-label">Secrets</div>
            <div class="qa-stat-value qa-text-warning">{total_secrets}</div>
            <div class="qa-stat-sub qa-text-muted">encrypted</div>
        </div>
        <div class="qa-stat-card">
            <div class="qa-stat-label">Services</div>
            <div class="qa-stat-value qa-text-success">{healthy_services}/{total_services}</div>
            <div class="qa-stat-sub qa-text-success">healthy</div>
        </div>
    ''')


@app.get("/api/resources/ports-html", response_class=HTMLResponse, tags=["Resources UI"])
def get_ports_html(
    db: Session = Depends(get_db)
):
    """Get port allocations as HTML table"""
    resource_manager = get_resource_manager(db)
    ports = resource_manager.ports.list_allocations()

    if not ports:
        return HTMLResponse(content='''
            <div class="qa-empty qa-p-8 qa-text-center">
                <p class="qa-text-muted">No ports allocated yet</p>
            </div>
        ''')

    rows = ""
    for p in ports:
        status_class = "qa-badge-success" if p.status == "active" else "qa-badge-gray"
        health_class = "qa-text-success" if p.health_status == "healthy" else "qa-text-warning" if p.health_status == "unknown" else "qa-text-danger"

        rows += f'''
            <tr>
                <td class="qa-font-mono qa-font-bold">{p.port}</td>
                <td>{p.service_name}</td>
                <td>{p.host}</td>
                <td><span class="qa-badge {status_class}">{p.status}</span></td>
                <td class="{health_class}">{p.health_status or 'unknown'}</td>
                <td class="qa-text-muted">{p.port_type}</td>
                <td>
                    <button class="qa-btn qa-btn-ghost qa-btn-sm qa-text-danger"
                            onclick="releasePort({p.port}, '{p.host}')">
                        Release
                    </button>
                </td>
            </tr>
        '''

    return HTMLResponse(content=f'''
        <table class="qa-table">
            <thead>
                <tr>
                    <th>Port</th>
                    <th>Service</th>
                    <th>Host</th>
                    <th>Status</th>
                    <th>Health</th>
                    <th>Type</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        <script>
            async function releasePort(port, host) {{
                if (!confirm('Release port ' + port + '?')) return;

                const params = new URLSearchParams({{ port: port, host: host }});
                const response = await fetch('{URL_PREFIX}/resources/ports/release?' + params, {{ method: 'POST' }});

                if (response.ok) {{
                    htmx.trigger('#ports-table', 'load');
                }} else {{
                    alert('Failed to release port');
                }}
            }}
        </script>
    ''')


@app.get("/api/resources/secrets-html", response_class=HTMLResponse, tags=["Resources UI"])
def get_secrets_html(
    db: Session = Depends(get_db)
):
    """Get secrets as HTML table"""
    resource_manager = get_resource_manager(db)
    secrets = resource_manager.secrets.list_secrets()

    if not secrets:
        return HTMLResponse(content='''
            <div class="qa-empty qa-p-8 qa-text-center">
                <p class="qa-text-muted">No secrets configured yet</p>
            </div>
        ''')

    rows = ""
    for s in secrets:
        scope_class = "qa-badge-primary" if s.scope == "global" else "qa-badge-info" if s.scope == "project" else "qa-badge-warning"
        sensitive_icon = '<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>' if s.is_sensitive else ''

        rows += f'''
            <tr>
                <td class="qa-font-mono">{s.key} {sensitive_icon}</td>
                <td><span class="qa-badge {scope_class}">{s.scope}</span></td>
                <td class="qa-text-muted">{s.description or '-'}</td>
                <td class="qa-font-mono qa-text-muted">{'****' if s.is_sensitive else '(visible)'}</td>
                <td>
                    <button class="qa-btn qa-btn-ghost qa-btn-sm" onclick="rotateSecret({s.id})">Rotate</button>
                    <button class="qa-btn qa-btn-ghost qa-btn-sm qa-text-danger" onclick="deleteSecret({s.id})">Delete</button>
                </td>
            </tr>
        '''

    return HTMLResponse(content=f'''
        <table class="qa-table">
            <thead>
                <tr>
                    <th>Key</th>
                    <th>Scope</th>
                    <th>Description</th>
                    <th>Value</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        <script>
            async function rotateSecret(id) {{
                const newValue = prompt('Enter new secret value:');
                if (!newValue) return;

                const params = new URLSearchParams({{ new_value: newValue }});
                const response = await fetch('{URL_PREFIX}/resources/secrets/' + id + '/rotate?' + params, {{ method: 'POST' }});

                if (response.ok) {{
                    htmx.trigger('#secrets-table', 'load');
                    alert('Secret rotated');
                }} else {{
                    alert('Failed to rotate secret');
                }}
            }}

            async function deleteSecret(id) {{
                if (!confirm('Delete this secret?')) return;

                const response = await fetch('{URL_PREFIX}/resources/secrets/' + id, {{ method: 'DELETE' }});

                if (response.ok) {{
                    htmx.trigger('#secrets-table', 'load');
                }} else {{
                    alert('Failed to delete secret');
                }}
            }}
        </script>
    ''')


@app.get("/api/resources/services-html", response_class=HTMLResponse, tags=["Resources UI"])
def get_services_html(
    db: Session = Depends(get_db)
):
    """Get services as HTML table"""
    resource_manager = get_resource_manager(db)
    services = resource_manager.services.list_services()

    if not services:
        return HTMLResponse(content='''
            <div class="qa-empty qa-p-8 qa-text-center">
                <p class="qa-text-muted">No services registered yet</p>
            </div>
        ''')

    rows = ""
    for s in services:
        health_class = "qa-badge-success" if s.health_status == "healthy" else "qa-badge-danger" if s.health_status == "unhealthy" else "qa-badge-warning"
        health_text = s.health_status or "unknown"

        rows += f'''
            <tr>
                <td class="qa-font-bold">{s.name}</td>
                <td><span class="qa-badge qa-badge-info">{s.service_type}</span></td>
                <td class="qa-font-mono">{s.protocol}://{s.host}:{s.port}</td>
                <td><span class="qa-badge {health_class}">{health_text}</span></td>
                <td class="qa-text-muted">{s.health_endpoint or '-'}</td>
                <td>
                    <button class="qa-btn qa-btn-ghost qa-btn-sm" onclick="checkServiceHealth({s.id})">Check</button>
                    <button class="qa-btn qa-btn-ghost qa-btn-sm qa-text-danger" onclick="unregisterService({s.id})">Remove</button>
                </td>
            </tr>
        '''

    return HTMLResponse(content=f'''
        <table class="qa-table">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Endpoint</th>
                    <th>Health</th>
                    <th>Health URL</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        <script>
            async function checkServiceHealth(id) {{
                const response = await fetch('{URL_PREFIX}/resources/services/' + id + '/health');
                const data = await response.json();
                alert('Health: ' + data.status + (data.response_time ? ' (' + data.response_time + 'ms)' : ''));
                htmx.trigger('#services-table', 'load');
            }}

            async function unregisterService(id) {{
                if (!confirm('Unregister this service?')) return;

                const response = await fetch('{URL_PREFIX}/resources/services/' + id, {{ method: 'DELETE' }});

                if (response.ok) {{
                    htmx.trigger('#services-table', 'load');
                }} else {{
                    alert('Failed to unregister service');
                }}
            }}
        </script>
    ''')


@app.get("/api/resources/discovered-ports-html", response_class=HTMLResponse, tags=["Resources UI"])
def get_discovered_ports_html(db: Session = Depends(get_db)):
    """Get discovered ports (via psutil) as HTML list"""
    resource_manager = get_resource_manager(db)
    ports = resource_manager.scan_ports()

    if not ports:
        return HTMLResponse(content='''
            <div class="qa-empty qa-p-6 qa-text-center">
                <p class="qa-text-muted">No ports discovered (psutil may not be installed)</p>
            </div>
        ''')

    # Limit to most relevant ports
    relevant_ports = [p for p in ports if p.get("port", 0) > 1024][:50]

    html = '<div class="qa-list">'
    for p in relevant_ports:
        port = p.get("port", "?")
        process = p.get("process_name", "unknown")
        pid = p.get("pid", "")

        html += f'''
            <div class="qa-list-item qa-flex qa-justify-between qa-items-center qa-p-3" style="border-bottom: 1px solid var(--q-border);">
                <div class="qa-flex qa-items-center qa-gap-3">
                    <span class="qa-badge qa-badge-primary qa-font-mono">{port}</span>
                    <span class="qa-text-sm">{process}</span>
                </div>
                <span class="qa-text-xs qa-text-muted">PID: {pid}</span>
            </div>
        '''
    html += '</div>'

    return HTMLResponse(content=html)


@app.get("/api/resources/containers-html", response_class=HTMLResponse, tags=["Resources UI"])
def get_discovered_containers_html(db: Session = Depends(get_db)):
    """Get Docker containers as HTML list"""
    resource_manager = get_resource_manager(db)
    containers = resource_manager.scan_containers(docker_service.client if docker_service else None)

    if not containers:
        return HTMLResponse(content='''
            <div class="qa-empty qa-p-6 qa-text-center">
                <p class="qa-text-muted">No containers found (Docker may not be connected)</p>
            </div>
        ''')

    html = '<div class="qa-list">'
    for c in containers:
        name = c.get("name", "unknown")
        image = c.get("image", "unknown")
        status = c.get("status", "unknown")
        ports = c.get("ports", {})

        status_class = "qa-badge-success" if status == "running" else "qa-badge-warning" if status == "paused" else "qa-badge-gray"

        ports_str = ", ".join([f"{k}->{v}" for k, v in ports.items()]) if ports else "-"

        html += f'''
            <div class="qa-list-item qa-p-3" style="border-bottom: 1px solid var(--q-border);">
                <div class="qa-flex qa-justify-between qa-items-center">
                    <div>
                        <span class="qa-font-bold">{name}</span>
                        <span class="qa-badge {status_class} qa-ml-2">{status}</span>
                    </div>
                </div>
                <div class="qa-text-xs qa-text-muted qa-mt-1">{image}</div>
                <div class="qa-text-xs qa-text-secondary qa-mt-1">Ports: {ports_str}</div>
            </div>
        '''
    html += '</div>'

    return HTMLResponse(content=html)


# ============================================================================
# UNIFIED DASHBOARD ENDPOINTS (for HTMX frontend)
# ============================================================================

@app.get("/api/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
def get_main_dashboard_html(db: Session = Depends(get_db)):
    """Main dashboard with overview stats"""
    # Get project count
    projects = crud.get_projects(db, limit=100)
    project_count = len(projects)

    # Get docker status
    global docker_service
    docker_connected = docker_service is not None
    try:
        containers = docker_service.list_containers() if docker_connected else []
    except Exception:
        containers = []
        docker_connected = False
    running_containers = len([c for c in containers if c.get('status') == 'running'])

    # Get job stats
    job_service = get_job_service()
    job_overview = job_service.get_overview()

    # Get recent webhook events
    webhook_service = get_webhook_service(db)
    recent_events = webhook_service.list_events(limit=5)

    html = f'''
    <div class="qa-dashboard">
        <!-- Stats Cards -->
        <div class="qa-grid qa-grid-4 qa-mb-6">
            <div class="qa-card">
                <div class="qa-card-body qa-text-center">
                    <h2 class="qa-text-3xl qa-text-primary">{project_count}</h2>
                    <p class="qa-text-muted">Applications</p>
                </div>
            </div>
            <div class="qa-card">
                <div class="qa-card-body qa-text-center">
                    <h2 class="qa-text-3xl qa-text-success">{running_containers}</h2>
                    <p class="qa-text-muted">Containers Running</p>
                </div>
            </div>
            <div class="qa-card">
                <div class="qa-card-body qa-text-center">
                    <h2 class="qa-text-3xl qa-text-warning">{job_overview.get('jobs', {}).get('pending', 0)}</h2>
                    <p class="qa-text-muted">Pending Jobs</p>
                </div>
            </div>
            <div class="qa-card">
                <div class="qa-card-body qa-text-center">
                    <h2 class="qa-text-3xl qa-text-info">{job_overview.get('schedules', {}).get('active', 0)}</h2>
                    <p class="qa-text-muted">Active Schedules</p>
                </div>
            </div>
        </div>

        <div class="qa-grid qa-grid-2 qa-gap-6">
            <!-- Recent Applications -->
            <div class="qa-card">
                <div class="qa-card-header">
                    <h4>Recent Applications</h4>
                </div>
                <div class="qa-card-body">
    '''

    if not projects:
        html += '<p class="qa-text-muted">No applications yet</p>'
    else:
        html += '<div class="qa-list">'
        for p in projects[:5]:
            status_badge = 'qa-badge-success' if p.status == 'active' else 'qa-badge-gray'
            html += f'''
                <div class="qa-list-item qa-flex qa-justify-between qa-items-center">
                    <div>
                        <strong>{p.name}</strong>
                        <span class="qa-text-muted qa-text-sm"> - {p.description or 'No description'}</span>
                    </div>
                    <span class="qa-badge {status_badge}">{p.status}</span>
                </div>
            '''
        html += '</div>'

    html += '''
                </div>
            </div>

            <!-- Docker Status -->
            <div class="qa-card">
                <div class="qa-card-header">
                    <h4>Docker Status</h4>
                </div>
                <div class="qa-card-body">
    '''

    if docker_connected:
        html += f'''
                    <p class="qa-text-success qa-mb-4"><span class="qa-status-dot online"></span> Connected</p>
                    <div class="qa-list">
        '''
        for c in containers[:5]:
            status = c.get('status', 'unknown')
            status_badge = 'qa-badge-success' if status == 'running' else 'qa-badge-gray'
            html += f'''
                        <div class="qa-list-item qa-flex qa-justify-between">
                            <span>{c.get('name', 'unknown')}</span>
                            <span class="qa-badge {status_badge}">{status}</span>
                        </div>
            '''
        html += '</div>'
    else:
        html += '<p class="qa-text-danger"><span class="qa-status-dot offline"></span> Not connected</p>'

    html += '''
                </div>
            </div>
        </div>

        <!-- Recent Activity -->
        <div class="qa-card qa-mt-6">
            <div class="qa-card-header">
                <h4>Recent Webhook Events</h4>
            </div>
            <div class="qa-card-body">
    '''

    if not recent_events:
        html += '<p class="qa-text-muted">No recent events</p>'
    else:
        html += '''
                <table class="qa-table">
                    <thead>
                        <tr>
                            <th>Provider</th>
                            <th>Event</th>
                            <th>Branch</th>
                            <th>Author</th>
                            <th>Time</th>
                        </tr>
                    </thead>
                    <tbody>
        '''
        for e in recent_events:
            time_str = e.received_at.strftime('%Y-%m-%d %H:%M') if e.received_at else '-'
            html += f'''
                        <tr>
                            <td>{e.provider or '-'}</td>
                            <td>{e.event_type or '-'}</td>
                            <td>{e.branch or '-'}</td>
                            <td>{e.author or '-'}</td>
                            <td>{time_str}</td>
                        </tr>
            '''
        html += '''
                    </tbody>
                </table>
        '''

    html += '''
            </div>
        </div>
    </div>
    '''

    return HTMLResponse(content=html)


@app.get("/api/projects/list-html", response_class=HTMLResponse, tags=["Dashboard"])
def get_projects_list_html(db: Session = Depends(get_db)):
    """Projects list as HTML"""
    projects = crud.get_projects(db, limit=100)

    html = '''
    <div class="qa-projects">
        <div class="qa-flex qa-justify-between qa-items-center qa-mb-6">
            <h3>All Applications</h3>
            <button class="qa-btn qa-btn-primary" onclick="showCreateProject()">
                + New Application
            </button>
        </div>

        <div class="qa-grid qa-grid-3 qa-gap-4">
    '''

    for p in projects:
        status_badge = 'qa-badge-success' if p.status == 'active' else 'qa-badge-gray'
        html += f'''
            <div class="qa-card">
                <div class="qa-card-body">
                    <div class="qa-flex qa-justify-between qa-items-start qa-mb-4">
                        <h4>{p.name}</h4>
                        <span class="qa-badge {status_badge}">{p.status}</span>
                    </div>
                    <p class="qa-text-muted qa-text-sm qa-mb-4">{p.description or 'No description'}</p>
                    <div class="qa-flex qa-gap-2">
                        <button class="qa-btn qa-btn-sm" onclick="loadProjectDetail({p.id})">View</button>
                        <button class="qa-btn qa-btn-sm qa-btn-ghost" onclick="editProject({p.id})">Edit</button>
                    </div>
                </div>
            </div>
        '''

    if not projects:
        html += '''
            <div class="qa-col-span-3 qa-text-center qa-py-8">
                <p class="qa-text-muted">No applications yet. Create your first application to get started.</p>
            </div>
        '''

    html += '''
        </div>
    </div>
    <script>
        function showCreateProject() {
            // Show create project modal
            alert('Create project form - TODO');
        }
        function loadProjectDetail(id) {
            loadPage('project_' + id, 'Application Details');
        }
        function editProject(id) {
            alert('Edit project ' + id + ' - TODO');
        }
    </script>
    '''

    return HTMLResponse(content=html)


@app.get("/api/docker/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
def get_docker_dashboard_html():
    """Docker management dashboard"""
    global docker_service
    connected = docker_service is not None

    html = '''
    <div class="qa-docker-dashboard">
        <div class="qa-flex qa-justify-between qa-items-center qa-mb-6">
            <h3>Docker Management</h3>
            <button class="qa-btn qa-btn-primary"
                    hx-get="{URL_PREFIX}/api/docker/dashboard"
                    hx-target=".qa-docker-dashboard"
                    hx-swap="outerHTML">
                Refresh
            </button>
        </div>
    '''

    if not connected:
        html += '''
            <div class="qa-card">
                <div class="qa-card-body qa-text-center qa-py-8">
                    <p class="qa-text-danger qa-mb-4">Docker is not connected</p>
                    <p class="qa-text-muted">Configure Docker host in Settings</p>
                </div>
            </div>
        </div>
        '''
        return HTMLResponse(content=html)

    # Get containers
    try:
        containers = docker_service.list_containers()
        images = docker_service.list_images()
    except Exception:
        containers = []
        images = []

    html += f'''
        <!-- Status Cards -->
        <div class="qa-grid qa-grid-3 qa-mb-6">
            <div class="qa-card qa-text-center">
                <div class="qa-card-body">
                    <h2 class="qa-text-2xl qa-text-success">{len([c for c in containers if c.get('status') == 'running'])}</h2>
                    <p class="qa-text-muted">Running</p>
                </div>
            </div>
            <div class="qa-card qa-text-center">
                <div class="qa-card-body">
                    <h2 class="qa-text-2xl qa-text-warning">{len([c for c in containers if c.get('status') != 'running'])}</h2>
                    <p class="qa-text-muted">Stopped</p>
                </div>
            </div>
            <div class="qa-card qa-text-center">
                <div class="qa-card-body">
                    <h2 class="qa-text-2xl qa-text-info">{len(images)}</h2>
                    <p class="qa-text-muted">Images</p>
                </div>
            </div>
        </div>

        <!-- Containers Table -->
        <div class="qa-card qa-mb-6">
            <div class="qa-card-header">
                <h4>Containers</h4>
            </div>
            <div class="qa-card-body">
                <table class="qa-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Image</th>
                            <th>Status</th>
                            <th>Ports</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
    '''

    for c in containers:
        status = c.get('status', 'unknown')
        status_badge = 'qa-badge-success' if status == 'running' else 'qa-badge-gray'
        ports = ', '.join(c.get('ports', [])) or '-'

        html += f'''
                        <tr>
                            <td>{c.get('name', '-')}</td>
                            <td><code>{c.get('image', '-')}</code></td>
                            <td><span class="qa-badge {status_badge}">{status}</span></td>
                            <td>{ports}</td>
                            <td>
        '''

        if status == 'running':
            html += f'''
                                <button class="qa-btn qa-btn-sm qa-btn-danger"
                                        hx-post="{URL_PREFIX}/docker/containers/{c.get('id')}/stop"
                                        hx-swap="none">Stop</button>
            '''
        else:
            html += f'''
                                <button class="qa-btn qa-btn-sm qa-btn-success"
                                        hx-post="{URL_PREFIX}/docker/containers/{c.get('id')}/start"
                                        hx-swap="none">Start</button>
            '''

        html += '''
                            </td>
                        </tr>
        '''

    html += '''
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Images Table -->
        <div class="qa-card">
            <div class="qa-card-header">
                <h4>Images</h4>
            </div>
            <div class="qa-card-body">
                <table class="qa-table">
                    <thead>
                        <tr>
                            <th>Repository</th>
                            <th>Tag</th>
                            <th>Size</th>
                            <th>Created</th>
                        </tr>
                    </thead>
                    <tbody>
    '''

    for img in images[:20]:
        tags = img.get('tags', [])
        repo = tags[0].split(':')[0] if tags else '-'
        tag = tags[0].split(':')[1] if tags and ':' in tags[0] else 'latest'
        size = f"{img.get('size', 0) / 1024 / 1024:.1f} MB"

        html += f'''
                        <tr>
                            <td>{repo}</td>
                            <td><code>{tag}</code></td>
                            <td>{size}</td>
                            <td>{img.get('created', '-')[:10]}</td>
                        </tr>
        '''

    html += '''
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    '''

    return HTMLResponse(content=html)


@app.get("/api/users/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
def get_users_dashboard_html(
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Users management dashboard"""
    # Check admin permission
    if user.role != 'admin':
        return HTMLResponse(content='<div class="qa-error">Admin access required</div>')

    users = db.query(User).all()

    html = '''
    <div class="qa-users-dashboard">
        <div class="qa-flex qa-justify-between qa-items-center qa-mb-6">
            <h3>User Management</h3>
            <button class="qa-btn qa-btn-primary" onclick="showCreateUser()">
                + Add User
            </button>
        </div>

        <div class="qa-card">
            <div class="qa-card-body">
                <table class="qa-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Username</th>
                            <th>Role</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
    '''

    for u in users:
        role_badge = 'qa-badge-primary' if u.role == 'admin' else 'qa-badge-gray'
        created = u.created_at.strftime('%Y-%m-%d') if u.created_at else '-'

        html += f'''
                        <tr>
                            <td>#{u.id}</td>
                            <td>{u.username}</td>
                            <td><span class="qa-badge {role_badge}">{u.role}</span></td>
                            <td>{created}</td>
                            <td>
                                <button class="qa-btn qa-btn-sm" onclick="editUser({u.id})">Edit</button>
                                <button class="qa-btn qa-btn-sm qa-btn-danger" onclick="deleteUser({u.id})">Delete</button>
                            </td>
                        </tr>
        '''

    html += '''
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <script>
        function showCreateUser() { alert('Create user - TODO'); }
        function editUser(id) { alert('Edit user ' + id + ' - TODO'); }
        function deleteUser(id) {
            if (confirm('Delete this user?')) {
                alert('Delete user ' + id + ' - TODO');
            }
        }
    </script>
    '''

    return HTMLResponse(content=html)


@app.get("/api/settings/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
def get_settings_dashboard_html(user: User = Depends(require_auth)):
    """Settings dashboard"""
    # Check admin permission
    if user.role != 'admin':
        return HTMLResponse(content='<div class="qa-error">Admin access required</div>')

    try:
        from .settings_service import get_settings_service
    except ImportError:
        from settings_service import get_settings_service

    settings_service = get_settings_service()
    all_settings = settings_service.get_all()

    html = '''
    <div class="qa-settings-dashboard">
        <h3 class="qa-mb-6">Settings</h3>

        <div class="qa-grid qa-grid-2 qa-gap-6">
            <!-- Docker Settings -->
            <div class="qa-card">
                <div class="qa-card-header">
                    <h4>Docker</h4>
                </div>
                <div class="qa-card-body">
                    <form hx-post="{URL_PREFIX}/api/settings/docker" hx-swap="none">
                        <div class="qa-form-group">
                            <label class="qa-label">Docker Host</label>
                            <input type="text" name="docker_host" class="qa-input"
                                   value="''' + (all_settings.get('docker_host') or 'unix:///var/run/docker.sock') + '''"
                                   placeholder="unix:///var/run/docker.sock">
                        </div>
                        <div class="qa-form-group">
                            <label class="qa-label">Registry URL</label>
                            <input type="text" name="registry_url" class="qa-input"
                                   value="''' + (all_settings.get('registry_url') or '') + '''"
                                   placeholder="registry.example.com">
                        </div>
                        <button type="submit" class="qa-btn qa-btn-primary">Save Docker Settings</button>
                    </form>
                </div>
            </div>

            <!-- Auth Settings -->
            <div class="qa-card">
                <div class="qa-card-header">
                    <h4>Authentication</h4>
                </div>
                <div class="qa-card-body">
                    <form hx-post="{URL_PREFIX}/api/settings/auth" hx-swap="none">
                        <div class="qa-form-group">
                            <label class="qa-label">JWT Secret</label>
                            <input type="password" name="jwt_secret" class="qa-input"
                                   placeholder="Leave empty to keep current">
                        </div>
                        <div class="qa-form-group">
                            <label class="qa-label">Token Expiry (hours)</label>
                            <input type="number" name="token_expiry" class="qa-input"
                                   value="''' + str(all_settings.get('token_expiry_hours', 24)) + '''">
                        </div>
                        <button type="submit" class="qa-btn qa-btn-primary">Save Auth Settings</button>
                    </form>
                </div>
            </div>

            <!-- Webhook Settings -->
            <div class="qa-card">
                <div class="qa-card-header">
                    <h4>Webhooks</h4>
                </div>
                <div class="qa-card-body">
                    <form hx-post="{URL_PREFIX}/api/settings/webhooks" hx-swap="none">
                        <div class="qa-form-group">
                            <label class="qa-label">GitHub Webhook Secret</label>
                            <input type="password" name="github_secret" class="qa-input"
                                   placeholder="Leave empty to keep current">
                        </div>
                        <div class="qa-form-group">
                            <label class="qa-label">GitLab Webhook Token</label>
                            <input type="password" name="gitlab_token" class="qa-input"
                                   placeholder="Leave empty to keep current">
                        </div>
                        <button type="submit" class="qa-btn qa-btn-primary">Save Webhook Settings</button>
                    </form>
                </div>
            </div>

            <!-- System Info -->
            <div class="qa-card">
                <div class="qa-card-header">
                    <h4>System Info</h4>
                </div>
                <div class="qa-card-body">
                    <div class="qa-list">
                        <div class="qa-list-item qa-flex qa-justify-between">
                            <span>Version</span>
                            <code>2.0.0</code>
                        </div>
                        <div class="qa-list-item qa-flex qa-justify-between">
                            <span>Python</span>
                            <code>''' + str(__import__('sys').version.split()[0]) + '''</code>
                        </div>
                        <div class="qa-list-item qa-flex qa-justify-between">
                            <span>Database</span>
                            <code>SQLite</code>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    '''

    return HTMLResponse(content=html)


@app.get("/api/projects/{project_id}/components/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
def get_components_dashboard_html(
    project_id: int,
    base_path: str = None,
    db: Session = Depends(get_db)
):
    """Components dashboard with test management"""
    try:
        from .models import Component, ComponentTest
    except ImportError:
        from models import Component, ComponentTest

    project = crud.get_project(db, project_id)

    if not project:
        return HTMLResponse(content='<div class="qa-error">Application not found</div>')

    # Check if source_path is configured
    if not project.source_path:
        return HTMLResponse(content=f'''
        <div class="qa-components-dashboard">
            <div class="qa-card">
                <div class="qa-card-body qa-text-center qa-p-8">
                    <svg width="48" height="48" class="qa-mx-auto qa-mb-4 qa-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                    </svg>
                    <h4 class="qa-mb-2">Source Path Not Configured</h4>
                    <p class="qa-text-muted qa-mb-4">Configure the source code path in Application Settings to discover components.</p>
                    <a href="{URL_PREFIX}/projects/{project_id}" class="qa-btn qa-btn-primary">Configure Application</a>
                </div>
            </div>
        </div>
        ''')

    # Get components from database (registered components)
    components = db.query(Component).filter(
        Component.project_id == project_id
    ).order_by(Component.name).all()

    # Calculate stats
    total_components = len(components)
    with_tests = sum(1 for c in components if c.test_count > 0)
    without_tests = total_components - with_tests
    total_passing = sum(c.tests_passing for c in components)
    total_failing = sum(c.tests_failing for c in components)
    total_tests = sum(c.test_count for c in components)

    scan_path = project.source_path

    # Helper function to format time ago
    def time_ago(dt):
        if not dt:
            return "-"
        from datetime import datetime, timezone
        now = datetime.now()
        if dt.tzinfo:
            now = datetime.now(timezone.utc)
        diff = now - dt
        if diff.days > 0:
            return f"{diff.days}d ago"
        hours = diff.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        minutes = diff.seconds // 60
        return f"{minutes}m ago" if minutes > 0 else "just now"

    html = f'''
    <div class="qa-components-dashboard">
        <!-- Header -->
        <div class="qa-flex qa-justify-between qa-items-center qa-mb-4">
            <div>
                <h3 class="qa-mb-1">Components - {project.name}</h3>
                <p class="qa-text-muted qa-text-sm">Source: <code>{scan_path}</code></p>
            </div>
            <button class="qa-btn qa-btn-ghost"
                    hx-get="{URL_PREFIX}/api/projects/{project_id}/components/dashboard"
                    hx-target=".qa-components-dashboard"
                    hx-swap="outerHTML">
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                Refresh
            </button>
        </div>

        <!-- Stats Cards -->
        <div class="qa-grid qa-grid-4 qa-gap-4 qa-mb-6">
            <div class="qa-stat-card">
                <div class="qa-stat-value qa-text-primary">{total_components}</div>
                <div class="qa-stat-label">Components</div>
            </div>
            <div class="qa-stat-card">
                <div class="qa-stat-value qa-text-success">{with_tests}</div>
                <div class="qa-stat-label">With Tests</div>
            </div>
            <div class="qa-stat-card">
                <div class="qa-stat-value qa-text-warning">{without_tests}</div>
                <div class="qa-stat-label">Without Tests</div>
            </div>
            <div class="qa-stat-card">
                <div class="qa-stat-value" style="color: {'var(--success)' if total_failing == 0 else 'var(--danger)'}">
                    {total_passing}/{total_tests}
                </div>
                <div class="qa-stat-label">Tests Passing</div>
            </div>
        </div>

        <!-- Components Table -->
        <div class="qa-card">
            <div class="qa-card-body qa-p-0">
    '''

    if not components:
        html += f'''
                <div class="qa-text-center qa-p-8">
                    <svg width="48" height="48" class="qa-mx-auto qa-mb-4 qa-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                    </svg>
                    <h4 class="qa-mb-2">No Components Registered</h4>
                    <p class="qa-text-muted qa-mb-4">Click "Sync from Filesystem" to discover components in <code>{scan_path}</code></p>
                </div>
        '''
    else:
        html += '''
                <table class="qa-table">
                    <thead>
                        <tr>
                            <th style="width: 40px;"><input type="checkbox" onclick="toggleAllComponents(this)"></th>
                            <th>Component</th>
                            <th>Status</th>
                            <th>Tests</th>
                            <th>Last Run</th>
                            <th style="width: 120px;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        '''

        for c in components:
            # Determine status badge
            status_class = "qa-badge-success" if c.status == "active" else "qa-badge-warning" if c.status == "unknown" else "qa-badge-danger"
            status_icon = "&#9679;" if c.status == "active" else "&#9675;"

            # Determine test status display
            if c.test_count == 0:
                test_display = '<span class="qa-text-muted">No tests</span>'
                test_icon = "&#9675;"  # empty circle
            elif c.tests_failing > 0:
                test_display = f'<span class="qa-text-warning">{c.tests_passing}/{c.test_count}</span>'
                test_icon = "&#9684;"  # half circle
            else:
                test_display = f'<span class="qa-text-success">{c.tests_passing}/{c.test_count}</span>'
                test_icon = "&#10003;"  # checkmark

            # Format file path
            file_path = c.file_path or ''
            short_path = file_path.split('/')[-1] if '/' in file_path else file_path.split('\\')[-1] if '\\' in file_path else file_path

            # Last run time
            last_run = time_ago(c.last_test_run_at) if c.last_test_run_at else "-"

            # Action buttons
            if c.test_count > 0:
                run_btn = f'''<button class="qa-btn qa-btn-xs qa-btn-success" onclick="runComponentTests({c.id})" title="Run Tests">&#9654;</button>'''
            else:
                run_btn = f'''<button class="qa-btn qa-btn-xs qa-btn-primary" onclick="generateComponentTests({c.id})" title="Create Tests">+</button>'''

            if c.status == "error":
                error_btn = f'''<button class="qa-btn qa-btn-xs qa-btn-warning" title="{c.error_message or 'Error'}">!</button>'''
            else:
                error_btn = ""

            html += f'''
                        <tr data-component-id="{c.id}">
                            <td><input type="checkbox" class="component-checkbox" value="{c.id}"></td>
                            <td>
                                <div>
                                    <strong>{c.name}</strong>
                                    <div class="qa-text-xs qa-text-muted" title="{file_path}">{short_path}</div>
                                </div>
                            </td>
                            <td>
                                <span class="qa-badge {status_class}">{status_icon} {c.status}</span>
                            </td>
                            <td>
                                {test_icon} {test_display}
                            </td>
                            <td>
                                <span class="qa-text-sm">{last_run}</span>
                            </td>
                            <td>
                                <div class="qa-flex qa-gap-1">
                                    {run_btn}
                                    {error_btn}
                                    <button class="qa-btn qa-btn-xs qa-btn-ghost" onclick="viewComponentDetails({c.id})" title="View Details">&#128065;</button>
                                </div>
                            </td>
                        </tr>
            '''

        html += '''
                    </tbody>
                </table>
        '''

    html += f'''
            </div>
        </div>
    </div>

    <script>
    // Update parent stats
    if (typeof updateStats === 'function') {{
        updateStats({{
            total: {total_components},
            with_tests: {with_tests},
            without_tests: {without_tests},
            tests_passing: {total_passing}
        }});
    }}
    </script>
    '''

    return HTMLResponse(content=html)


# ============================================================================
# CLOUD INTEGRATIONS ENDPOINTS
# ============================================================================

@app.get("/settings/cloud", tags=["Cloud Integrations"], response_class=HTMLResponse)
def get_cloud_integrations_html(db: Session = Depends(get_db)):
    """Get cloud integrations as HTML cards"""
    integrations = db.query(models.CloudIntegration).filter(
        models.CloudIntegration.is_active == True
    ).order_by(models.CloudIntegration.name).all()

    if not integrations:
        return HTMLResponse(content='''
            <div class="qa-text-center qa-text-muted qa-p-6" style="grid-column: span 2;">
                <p class="qa-mb-2">No cloud integrations configured yet</p>
                <p class="qa-text-xs">Click on a provider above or use "Add Integration" to get started</p>
            </div>
        ''')

    html = ""
    for integ in integrations:
        # Provider icon and color
        provider_info = {
            'aws': ('AWS', '#FF9900', '&#9729;'),
            'kubernetes': ('Kubernetes', '#326CE5', '&#9096;'),
            'azure': ('Azure', '#0078D4', '&#9729;'),
            'gcp': ('GCP', '#4285F4', '&#9729;')
        }
        pname, pcolor, picon = provider_info.get(integ.provider, ('Cloud', '#666', '&#9729;'))

        # Status
        status_class = 'qa-badge-success' if integ.test_status == 'success' else 'qa-badge-warning' if integ.test_status == 'unknown' else 'qa-badge-danger'
        status_text = integ.test_status or 'unknown'

        # Default badge
        default_badge = '<span class="qa-badge qa-badge-primary qa-ml-2">Default</span>' if integ.is_default else ''

        # Last tested
        last_tested = integ.last_tested.strftime('%Y-%m-%d %H:%M') if integ.last_tested else 'Never'

        html += f'''
            <div class="qa-card">
                <div class="qa-card-header qa-flex qa-justify-between qa-items-center">
                    <div class="qa-flex qa-items-center qa-gap-2">
                        <span style="font-size: 1.5rem; color: {pcolor};">{picon}</span>
                        <div>
                            <h4 class="qa-font-medium">{integ.name}</h4>
                            <p class="qa-text-xs qa-text-muted">{pname} - {integ.region or 'No region'}</p>
                        </div>
                        {default_badge}
                    </div>
                    <span class="qa-badge {status_class}">{status_text}</span>
                </div>
                <div class="qa-card-body">
                    <div class="qa-text-sm qa-text-muted">
                        <p>Last tested: {last_tested}</p>
                    </div>
                </div>
                <div class="qa-card-footer qa-flex qa-justify-end qa-gap-2">
                    <button class="qa-btn qa-btn-ghost qa-btn-sm" onclick="testExistingCloudIntegration({integ.id})">Test</button>
                    <button class="qa-btn qa-btn-ghost qa-btn-sm" onclick="openCloudModal(null, {integ.id})">Edit</button>
                    <button class="qa-btn qa-btn-ghost qa-btn-sm qa-text-danger" onclick="deleteCloudIntegration({integ.id})">Delete</button>
                </div>
            </div>
        '''

    return HTMLResponse(content=html)


@app.get("/settings/cloud/{integration_id}", tags=["Cloud Integrations"])
def get_cloud_integration(integration_id: int, db: Session = Depends(get_db)):
    """Get a single cloud integration (without credentials)"""
    integ = db.query(models.CloudIntegration).filter(models.CloudIntegration.id == integration_id).first()
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integ.to_dict(include_credentials=False)


@app.post("/settings/cloud", tags=["Cloud Integrations"])
def create_cloud_integration(data: Dict[str, Any], db: Session = Depends(get_db), request: Request = None):
    """Create a new cloud integration"""
    import json

    # Encrypt credentials (in production, use proper encryption)
    credentials_json = json.dumps(data.get('credentials', {}))

    integ = models.CloudIntegration(
        name=data.get('name'),
        provider=data.get('provider'),
        credentials_encrypted=credentials_json,  # TODO: encrypt properly
        region=data.get('region'),
        is_active=True,
        is_default=data.get('is_default', False),
        test_status='unknown'
    )

    # If this is default, unset others
    if integ.is_default:
        db.query(models.CloudIntegration).filter(
            models.CloudIntegration.provider == integ.provider
        ).update({"is_default": False})

    db.add(integ)
    db.commit()
    db.refresh(integ)

    # Audit log
    try:
        audit_log(
            db,
            user="admin",
            action=AuditAction.CREATE,
            resource_type="cloud_integration",
            resource_id=integ.id,
            resource_name=integ.name,
            request=request
        )
    except Exception:
        pass

    return {"id": integ.id, "message": "Integration created"}


@app.put("/settings/cloud/{integration_id}", tags=["Cloud Integrations"])
def update_cloud_integration(integration_id: int, data: Dict[str, Any], db: Session = Depends(get_db), request: Request = None):
    """Update a cloud integration"""
    import json

    integ = db.query(models.CloudIntegration).filter(models.CloudIntegration.id == integration_id).first()
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")

    if 'name' in data:
        integ.name = data['name']
    if 'region' in data:
        integ.region = data['region']
    if 'credentials' in data and data['credentials']:
        integ.credentials_encrypted = json.dumps(data['credentials'])

    if 'is_default' in data:
        if data['is_default']:
            # Unset others of same provider
            db.query(models.CloudIntegration).filter(
                models.CloudIntegration.provider == integ.provider,
                models.CloudIntegration.id != integration_id
            ).update({"is_default": False})
        integ.is_default = data['is_default']

    db.commit()

    # Audit log
    try:
        audit_log(
            db,
            user="admin",
            action=AuditAction.UPDATE,
            resource_type="cloud_integration",
            resource_id=integ.id,
            resource_name=integ.name,
            request=request
        )
    except Exception:
        pass

    return {"message": "Integration updated"}


@app.delete("/settings/cloud/{integration_id}", tags=["Cloud Integrations"])
def delete_cloud_integration(integration_id: int, db: Session = Depends(get_db), request: Request = None):
    """Delete a cloud integration"""
    integ = db.query(models.CloudIntegration).filter(models.CloudIntegration.id == integration_id).first()
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")

    name = integ.name
    db.delete(integ)
    db.commit()

    # Audit log
    try:
        audit_log(
            db,
            user="admin",
            action=AuditAction.DELETE,
            resource_type="cloud_integration",
            resource_id=integration_id,
            resource_name=name,
            request=request
        )
    except Exception:
        pass

    return {"message": "Integration deleted"}


@app.post("/settings/cloud/test", tags=["Cloud Integrations"])
def test_cloud_connection(data: Dict[str, Any]):
    """Test cloud connection with provided credentials"""
    try:
        from integrations import get_connector
    except ImportError:
        try:
            from .integrations import get_connector
        except ImportError:
            return {"success": False, "error": "Integrations module not available"}

    provider = data.get('provider')
    credentials = data.get('credentials', {})

    if not provider:
        return {"success": False, "error": "Provider is required"}

    try:
        connector = get_connector(provider, credentials)
        result = connector.test_connection()
        return result
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Connection test failed: {str(e)}"}


@app.post("/settings/cloud/{integration_id}/test", tags=["Cloud Integrations"])
def test_existing_cloud_integration(integration_id: int, db: Session = Depends(get_db)):
    """Test an existing cloud integration"""
    import json

    integ = db.query(models.CloudIntegration).filter(models.CloudIntegration.id == integration_id).first()
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        from integrations import get_connector
    except ImportError:
        try:
            from .integrations import get_connector
        except ImportError:
            return {"success": False, "error": "Integrations module not available"}

    try:
        credentials = json.loads(integ.credentials_encrypted) if integ.credentials_encrypted else {}
        connector = get_connector(integ.provider, credentials)
        result = connector.test_connection()

        # Update status
        from datetime import datetime
        integ.last_tested = datetime.utcnow()
        integ.test_status = 'success' if result.get('success') else 'failed'
        db.commit()

        return result
    except Exception as e:
        integ.test_status = 'failed'
        db.commit()
        return {"success": False, "error": str(e)}


@app.get("/integrations", tags=["Cloud Integrations"])
def list_cloud_integrations(db: Session = Depends(get_db)):
    """List all cloud integrations as JSON"""
    integrations = db.query(models.CloudIntegration).filter(
        models.CloudIntegration.is_active == True
    ).order_by(models.CloudIntegration.name).all()

    return [integ.to_dict(include_credentials=False) for integ in integrations]


@app.get("/integrations/{provider}/regions", tags=["Cloud Integrations"])
def get_provider_regions(provider: str):
    """Get available regions for a provider"""
    try:
        from integrations import get_connector
    except ImportError:
        try:
            from .integrations import get_connector
        except ImportError:
            return []

    try:
        connector = get_connector(provider, {})
        return connector.get_regions()
    except Exception:
        return []


@app.get("/integrations/{provider}/config-schema", tags=["Cloud Integrations"])
def get_provider_config_schema(provider: str):
    """Get deployment configuration schema for a provider"""
    try:
        from integrations import get_connector
    except ImportError:
        try:
            from .integrations import get_connector
        except ImportError:
            return {}

    try:
        connector = get_connector(provider, {})
        return connector.get_config_schema()
    except Exception:
        return {}


# ============================================================================
# PROJECT TEMPLATES ENDPOINTS
# ============================================================================

@app.get("/templates", tags=["Templates"])
def list_templates():
    """List all available project templates"""
    template_service = get_template_service()
    templates = template_service.list_templates()
    return [t.to_dict() for t in templates]


@app.get("/templates/{template_id}", tags=["Templates"])
def get_template(template_id: str):
    """Get a specific template by ID"""
    template_service = get_template_service()
    template = template_service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template.to_dict()


@app.get("/templates-html", tags=["Templates"], response_class=HTMLResponse)
def get_templates_html():
    """Get templates as HTML cards for the UI"""
    template_service = get_template_service()
    templates = template_service.list_templates()

    html = ""
    for t in templates:
        features_html = "".join([f'<span class="qa-badge qa-badge-ghost">{f}</span>' for f in t.features[:3]])

        html += f'''
            <div class="qa-card qa-card-interactive template-card" onclick="selectTemplate('{t.id}')" data-template="{t.id}" style="cursor:pointer;">
                <div class="qa-card-body qa-text-center">
                    <div class="qa-text-3xl qa-mb-2">{t.icon}</div>
                    <h4 class="qa-font-medium">{t.name}</h4>
                    <p class="qa-text-xs qa-text-muted qa-mb-2">{t.description}</p>
                    <div class="qa-flex qa-flex-wrap qa-justify-center qa-gap-1">
                        {features_html}
                    </div>
                </div>
            </div>
        '''

    return HTMLResponse(content=html)


@app.post("/projects/from-template", tags=["Templates"])
def create_project_from_template(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    request: Request = None
):
    """Create a new project from a template"""
    from pathlib import Path
    import os

    template_id = data.get("template", "blank")
    project_name = data.get("name")
    options = data.get("options", {})

    if not project_name:
        raise HTTPException(status_code=400, detail="Project name is required")

    # Validate name
    project_name = project_name.strip().replace(" ", "_").lower()
    if not project_name.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid project name")

    # Check if project already exists
    existing = crud.get_project_by_name(db, project_name)
    if existing:
        raise HTTPException(status_code=400, detail="Project with this name already exists")

    template_service = get_template_service()

    # Determine target directory
    # Default: current working directory / projects / {name}
    projects_base = Path(os.getcwd()) / "projects"
    projects_base.mkdir(parents=True, exist_ok=True)

    try:
        result = template_service.scaffold_project(
            template_id=template_id,
            project_name=project_name,
            target_dir=projects_base,
            options=options
        )

        # Create project in database
        project = crud.create_project(db, schemas.ProjectCreate(
            name=project_name,
            description=data.get("description", f"Project created from {template_id} template"),
            source_path=result["project_dir"]
        ))

        # Audit log
        try:
            audit_log(
                db,
                user="admin",
                action=AuditAction.CREATE,
                resource_type="project",
                resource_id=project.id,
                resource_name=project.name,
                details={"template": template_id, "files_created": len(result["files_created"])},
                request=request
            )
        except Exception:
            pass

        return {
            "id": project.id,
            "name": project.name,
            "template": template_id,
            "project_dir": result["project_dir"],
            "files_created": result["files_created"],
            "message": f"Project '{project_name}' created successfully from {template_id} template"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create project from template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@app.get("/create-project-wizard", tags=["Templates"], response_class=HTMLResponse)
def get_create_project_wizard():
    """Get the project creation wizard with template selection"""
    return HTMLResponse(content='''
        <div class="qa-wizard">
            <!-- Step 1: Choose Template -->
            <div id="wizard-step-1" class="wizard-step active">
                <h3 class="qa-mb-4">Choose a Template</h3>
                <p class="qa-text-muted qa-mb-4">Select a template to get started quickly, or start with a blank project.</p>

                <div id="template-grid" class="qa-grid qa-grid-3 qa-gap-4" hx-get="{URL_PREFIX}/templates-html" hx-trigger="load" hx-swap="innerHTML">
                    <div class="qa-text-center qa-text-muted qa-p-6" style="grid-column: span 3;">Loading templates...</div>
                </div>

                <div class="qa-flex qa-justify-end qa-mt-6">
                    <button class="qa-btn qa-btn-primary" onclick="nextWizardStep()" id="btn-next-1" disabled>
                        Next: Configure Project
                        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                    </button>
                </div>
            </div>

            <!-- Step 2: Project Details -->
            <div id="wizard-step-2" class="wizard-step">
                <h3 class="qa-mb-4">Project Details</h3>
                <p class="qa-text-muted qa-mb-4">Configure your new project.</p>

                <form id="template-project-form">
                    <input type="hidden" name="template" id="selected-template" />

                    <div class="qa-form-group">
                        <label class="qa-label">Project Name</label>
                        <input type="text" name="name" id="template-project-name" class="qa-input"
                               placeholder="my-awesome-project" required
                               pattern="[a-z0-9_-]+" title="Lowercase letters, numbers, dashes and underscores only" />
                        <p class="qa-text-xs qa-text-muted">Lowercase letters, numbers, dashes and underscores only</p>
                    </div>

                    <div class="qa-form-group">
                        <label class="qa-label">Description</label>
                        <textarea name="description" id="template-project-desc" class="qa-input" rows="2"
                                  placeholder="A brief description of your project..."></textarea>
                    </div>

                    <!-- Template Options (populated dynamically) -->
                    <div id="template-options" class="qa-mt-4"></div>
                </form>

                <div class="qa-flex qa-justify-between qa-mt-6">
                    <button class="qa-btn qa-btn-secondary" onclick="prevWizardStep()">
                        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
                        Back
                    </button>
                    <button class="qa-btn qa-btn-primary" onclick="createProjectFromTemplate()">
                        Create Project
                    </button>
                </div>
            </div>
        </div>

        <style>
            .wizard-step { display: none; }
            .wizard-step.active { display: block; }
            .template-card.selected {
                border-color: var(--q-primary);
                box-shadow: 0 0 0 2px var(--q-primary);
            }
        </style>

        <script>
            let selectedTemplate = null;
            let currentStep = 1;

            function selectTemplate(templateId) {
                selectedTemplate = templateId;
                document.getElementById('selected-template').value = templateId;

                // Update UI
                document.querySelectorAll('.template-card').forEach(c => c.classList.remove('selected'));
                document.querySelector(`.template-card[data-template="${templateId}"]`).classList.add('selected');
                document.getElementById('btn-next-1').disabled = false;

                // Load template options
                loadTemplateOptions(templateId);
            }

            function loadTemplateOptions(templateId) {
                fetch('{URL_PREFIX}/templates/' + templateId)
                    .then(r => r.json())
                    .then(template => {
                        const container = document.getElementById('template-options');
                        if (!template.options || template.options.length === 0) {
                            container.innerHTML = '';
                            return;
                        }

                        let html = '<h4 class="qa-font-medium qa-mb-3">Template Options</h4>';
                        template.options.forEach(opt => {
                            if (opt.type === 'boolean') {
                                html += `
                                    <label class="qa-checkbox-group qa-mb-2">
                                        <input type="checkbox" name="opt_${opt.name}" class="qa-checkbox" ${opt.default ? 'checked' : ''} />
                                        <span>${opt.label}</span>
                                    </label>
                                `;
                            } else if (opt.type === 'select') {
                                html += `
                                    <div class="qa-form-group">
                                        <label class="qa-label">${opt.label}</label>
                                        <select name="opt_${opt.name}" class="qa-input qa-select">
                                            ${opt.choices.map(c => `<option value="${c}" ${c === opt.default ? 'selected' : ''}>${c}</option>`).join('')}
                                        </select>
                                    </div>
                                `;
                            }
                        });
                        container.innerHTML = html;
                    });
            }

            function nextWizardStep() {
                if (currentStep < 2) {
                    document.getElementById('wizard-step-' + currentStep).classList.remove('active');
                    currentStep++;
                    document.getElementById('wizard-step-' + currentStep).classList.add('active');
                }
            }

            function prevWizardStep() {
                if (currentStep > 1) {
                    document.getElementById('wizard-step-' + currentStep).classList.remove('active');
                    currentStep--;
                    document.getElementById('wizard-step-' + currentStep).classList.add('active');
                }
            }

            function createProjectFromTemplate() {
                const name = document.getElementById('template-project-name').value;
                if (!name) {
                    showToast('Please enter a project name', 'warning');
                    return;
                }

                const form = document.getElementById('template-project-form');
                const formData = new FormData(form);

                const data = {
                    template: selectedTemplate,
                    name: name,
                    description: formData.get('description') || '',
                    options: {}
                };

                // Collect options
                for (const [key, value] of formData.entries()) {
                    if (key.startsWith('opt_')) {
                        const optName = key.substring(4);
                        data.options[optName] = value === 'on' ? true : value;
                    }
                }

                // Handle unchecked checkboxes
                form.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                    if (cb.name.startsWith('opt_') && !cb.checked) {
                        const optName = cb.name.substring(4);
                        data.options[optName] = false;
                    }
                });

                showToast('Creating project...', 'info');

                fetch('{URL_PREFIX}/projects/from-template', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                })
                .then(r => r.json())
                .then(result => {
                    if (result.id) {
                        showToast('Project created successfully!', 'success');
                        // Close modal and navigate to project
                        closeCreateWizard();
                        window.location.href = '{URL_PREFIX}/projects/' + result.id;
                    } else {
                        showToast('Error: ' + (result.detail || 'Unknown error'), 'error');
                    }
                })
                .catch(err => {
                    showToast('Error creating project', 'error');
                });
            }
        </script>
    ''')


# ============================================================================
# RUN SERVER (for development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
# Trigger reload
