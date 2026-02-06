"""
Quantum CLI - New Command

Create new Quantum projects with templates.
"""

import os
import shutil
from pathlib import Path
from typing import Optional

import click

from cli.utils import get_console, validate_project_name


# Project templates
TEMPLATES = {
    'default': 'Basic Quantum web application',
    'api': 'REST API with microservices',
    'game': '2D game with canvas',
    'terminal': 'Terminal TUI application',
    'component-lib': 'Reusable component library',
}


@click.command('new')
@click.argument('project_name')
@click.option('--template', '-t', type=click.Choice(list(TEMPLATES.keys())), default='default',
              help='Project template to use')
@click.option('--directory', '-d', type=click.Path(), default=None,
              help='Directory to create project in (default: project name)')
@click.option('--no-git', is_flag=True, help='Skip git initialization')
@click.option('--quiet', '-q', is_flag=True, help='Quiet mode - minimal output')
def new(project_name: str, template: str, directory: Optional[str], no_git: bool, quiet: bool):
    """Create a new Quantum project.

    PROJECT_NAME is the name of your new project.

    Examples:

        quantum new my-app

        quantum new my-api --template api

        quantum new my-game -t game -d ./projects
    """
    console = get_console(quiet=quiet)

    # Validate project name
    is_valid, error = validate_project_name(project_name)
    if not is_valid:
        console.error(error)
        raise click.Abort()

    # Determine project directory
    if directory:
        project_dir = Path(directory) / project_name
    else:
        project_dir = Path.cwd() / project_name

    # Check if directory exists
    if project_dir.exists():
        console.error(f"Directory already exists: {project_dir}")
        raise click.Abort()

    console.header(
        "Creating Quantum Project",
        f"Template: {template} | Location: {project_dir}"
    )

    try:
        with console.spinner("Creating project structure..."):
            _create_project_structure(project_dir, project_name, template)

        if not no_git:
            with console.spinner("Initializing git repository..."):
                _init_git(project_dir)

        console.success(f"Project '{project_name}' created successfully!")
        console.print()
        console.panel(
            f"[bold]Next steps:[/bold]\n\n"
            f"  cd {project_name}\n"
            f"  quantum dev\n\n"
            f"[dim]Open http://localhost:8080 in your browser[/dim]",
            title="Get Started"
        )

    except Exception as e:
        console.error(f"Failed to create project: {e}")
        # Cleanup on failure
        if project_dir.exists():
            shutil.rmtree(project_dir)
        raise click.Abort()


def _create_project_structure(project_dir: Path, project_name: str, template: str) -> None:
    """Create the project directory structure."""
    # Create directories
    dirs = [
        'components',
        'pages',
        'layouts',
        'assets/css',
        'assets/js',
        'assets/images',
        'data',
    ]

    for d in dirs:
        (project_dir / d).mkdir(parents=True, exist_ok=True)

    # Create quantum.config.yaml
    config_content = f"""# Quantum Configuration
# Generated for: {project_name}

app:
  name: {project_name}
  version: 1.0.0
  type: {_get_app_type(template)}

server:
  port: 8080
  host: 0.0.0.0
  debug: true
  reload: true

database:
  default:
    driver: sqlite
    path: ./data/{project_name}.db

templates:
  components_dir: ./components
  layouts_dir: ./layouts
  pages_dir: ./pages

build:
  output_dir: ./dist
  minify: true
  sourcemaps: true

# Environment-specific overrides
environments:
  development:
    server:
      debug: true
      reload: true
  production:
    server:
      debug: false
      reload: false
"""
    (project_dir / 'quantum.config.yaml').write_text(config_content)

    # Create template-specific files
    if template == 'default':
        _create_default_template(project_dir, project_name)
    elif template == 'api':
        _create_api_template(project_dir, project_name)
    elif template == 'game':
        _create_game_template(project_dir, project_name)
    elif template == 'terminal':
        _create_terminal_template(project_dir, project_name)
    elif template == 'component-lib':
        _create_component_lib_template(project_dir, project_name)

    # Create .gitignore
    gitignore = """# Quantum
dist/
.quantum/
*.pyc
__pycache__/

# Environment
.env
.env.local
.env.*.local

# Databases
*.db
*.sqlite

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
*.swp
*.swo

# Dependencies
node_modules/
.venv/
venv/
"""
    (project_dir / '.gitignore').write_text(gitignore)


def _get_app_type(template: str) -> str:
    """Get app type from template."""
    type_map = {
        'default': 'html',
        'api': 'api',
        'game': 'game',
        'terminal': 'terminal',
        'component-lib': 'library',
    }
    return type_map.get(template, 'html')


def _create_default_template(project_dir: Path, project_name: str) -> None:
    """Create default web application template."""
    # Main layout
    layout = f"""<!-- Main Layout -->
<q:component name="MainLayout" xmlns:q="https://quantum.lang/ns">
    <q:param name="title" type="string" default="{project_name}" />

    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>{{title}}</title>
        <link rel="stylesheet" href="/assets/css/style.css" />
    </head>
    <body>
        <header>
            <nav>
                <a href="/" class="logo">{project_name}</a>
                <ul>
                    <li><a href="/">Home</a></li>
                    <li><a href="/about">About</a></li>
                </ul>
            </nav>
        </header>

        <main>
            <q:children />
        </main>

        <footer>
            <p>Built with Quantum Framework</p>
        </footer>
    </body>
    </html>
</q:component>
"""
    (project_dir / 'layouts' / 'main.q').write_text(layout)

    # Home page
    home = f"""<!-- Home Page -->
<q:component name="HomePage" xmlns:q="https://quantum.lang/ns">
    <q:layout name="MainLayout" title="Welcome to {project_name}" />

    <section class="hero">
        <h1>Welcome to {project_name}</h1>
        <p>Your Quantum application is ready!</p>

        <q:set name="counter" value="0" />

        <div class="counter">
            <p>Counter: {{counter}}</p>
            <q:action on="click" set="counter" value="{{counter + 1}}">
                <button>Increment</button>
            </q:action>
        </div>
    </section>
</q:component>
"""
    (project_dir / 'pages' / 'home.q').write_text(home)

    # CSS
    css = """/* Quantum Default Styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

:root {
    --primary: #6366f1;
    --primary-hover: #4f46e5;
    --bg: #f8fafc;
    --text: #1e293b;
    --text-muted: #64748b;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
}

header {
    background: white;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    padding: 1rem 2rem;
}

nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    max-width: 1200px;
    margin: 0 auto;
}

.logo {
    font-size: 1.5rem;
    font-weight: bold;
    color: var(--primary);
    text-decoration: none;
}

nav ul {
    display: flex;
    list-style: none;
    gap: 2rem;
}

nav a {
    color: var(--text);
    text-decoration: none;
    transition: color 0.2s;
}

nav a:hover {
    color: var(--primary);
}

main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}

.hero {
    text-align: center;
    padding: 4rem 0;
}

.hero h1 {
    font-size: 3rem;
    margin-bottom: 1rem;
}

.hero p {
    color: var(--text-muted);
    font-size: 1.25rem;
}

.counter {
    margin-top: 2rem;
    padding: 2rem;
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    display: inline-block;
}

button {
    background: var(--primary);
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 6px;
    font-size: 1rem;
    cursor: pointer;
    transition: background 0.2s;
}

button:hover {
    background: var(--primary-hover);
}

footer {
    text-align: center;
    padding: 2rem;
    color: var(--text-muted);
    margin-top: 4rem;
}
"""
    (project_dir / 'assets' / 'css' / 'style.css').write_text(css)

    # Application entry point
    app = f"""<!-- Application Entry Point -->
<q:application id="{project_name}" type="html" xmlns:q="https://quantum.lang/ns">
    <q:route path="/" page="pages/home.q" />
    <q:route path="/about" page="pages/about.q" />
</q:application>
"""
    (project_dir / 'app.q').write_text(app)


def _create_api_template(project_dir: Path, project_name: str) -> None:
    """Create API template."""
    api = f"""<!-- API Application -->
<q:application id="{project_name}-api" type="api" xmlns:q="https://quantum.lang/ns">

    <!-- Health check endpoint -->
    <q:function name="healthCheck" rest="GET /api/health">
        <q:return value='{{"status": "ok", "service": "{project_name}"}}' />
    </q:function>

    <!-- Users CRUD -->
    <q:component name="UsersAPI">
        <q:function name="listUsers" rest="GET /api/users">
            <q:query name="users" datasource="default">
                SELECT id, name, email, created_at FROM users ORDER BY id
            </q:query>
            <q:return value="{{users}}" />
        </q:function>

        <q:function name="getUser" rest="GET /api/users/:id">
            <q:param name="id" type="number" required="true" />
            <q:query name="user" datasource="default">
                SELECT * FROM users WHERE id = :id
            </q:query>
            <q:return value="{{user}}" />
        </q:function>

        <q:function name="createUser" rest="POST /api/users">
            <q:param name="name" type="string" required="true" />
            <q:param name="email" type="string" required="true" />
            <q:query datasource="default">
                INSERT INTO users (name, email) VALUES (:name, :email)
            </q:query>
            <q:return value='{{"success": true}}' />
        </q:function>
    </q:component>

</q:application>
"""
    (project_dir / 'api.q').write_text(api)

    # Update config for API
    config_path = project_dir / 'quantum.config.yaml'
    config = config_path.read_text()
    config = config.replace('type: api', 'type: microservices')
    config_path.write_text(config)


def _create_game_template(project_dir: Path, project_name: str) -> None:
    """Create game template."""
    game = f"""<!-- Game Application -->
<q:application id="{project_name}" type="game" xmlns:q="https://quantum.lang/ns">

    <!-- Game Configuration -->
    <q:config width="800" height="600" background="#1a1a2e" />

    <!-- Assets -->
    <q:assets>
        <q:sprite id="player" src="/assets/images/player.png" />
    </q:assets>

    <!-- Main Scene -->
    <q:scene id="main" default="true">
        <!-- Player Entity -->
        <q:entity id="player" x="400" y="300">
            <q:sprite ref="player" width="32" height="32" />
            <q:behavior type="keyboard-move" speed="200" />
        </q:entity>

        <!-- Score Display -->
        <q:entity id="score-display" x="10" y="10">
            <q:text content="Score: 0" font="24px Arial" color="white" />
        </q:entity>
    </q:scene>

    <!-- Game Over Scene -->
    <q:scene id="gameover">
        <q:entity id="gameover-text" x="400" y="300" anchor="center">
            <q:text content="Game Over!" font="48px Arial" color="red" />
        </q:entity>
    </q:scene>

</q:application>
"""
    (project_dir / 'game.q').write_text(game)

    # Create placeholder sprite
    (project_dir / 'assets' / 'images' / '.gitkeep').write_text('')


def _create_terminal_template(project_dir: Path, project_name: str) -> None:
    """Create terminal TUI template."""
    terminal = f"""<!-- Terminal TUI Application -->
<q:application id="{project_name}" type="terminal" xmlns:q="https://quantum.lang/ns">

    <!-- Main Screen -->
    <q:screen id="main" default="true">
        <q:header title="{project_name}" />

        <q:container layout="vertical">
            <q:text>Welcome to {project_name}!</q:text>
            <q:text>Press 'q' to quit, 'h' for help.</q:text>

            <q:set name="items" value="['Item 1', 'Item 2', 'Item 3']" />

            <q:list bind="items" selectable="true" on-select="handleSelect">
                <q:template>
                    <q:text>{{item}}</q:text>
                </q:template>
            </q:list>
        </q:container>

        <q:footer>
            <q:text>[q]uit [h]elp [Enter]select</q:text>
        </q:footer>
    </q:screen>

    <!-- Keybindings -->
    <q:keybind key="q" action="quit" />
    <q:keybind key="h" action="show-help" />

</q:application>
"""
    (project_dir / 'app.q').write_text(terminal)


def _create_component_lib_template(project_dir: Path, project_name: str) -> None:
    """Create component library template."""
    # Button component
    button = """<!-- Button Component -->
<q:component name="Button" xmlns:q="https://quantum.lang/ns">
    <q:param name="variant" type="string" default="primary" />
    <q:param name="size" type="string" default="medium" />
    <q:param name="disabled" type="boolean" default="false" />

    <button class="btn btn-{variant} btn-{size}" disabled="{disabled}">
        <q:children />
    </button>
</q:component>
"""
    (project_dir / 'components' / 'Button.q').write_text(button)

    # Card component
    card = """<!-- Card Component -->
<q:component name="Card" xmlns:q="https://quantum.lang/ns">
    <q:param name="title" type="string" />
    <q:param name="elevation" type="number" default="1" />

    <div class="card elevation-{elevation}">
        <q:if condition="{title}">
            <div class="card-header">
                <h3>{title}</h3>
            </div>
        </q:if>
        <div class="card-body">
            <q:children />
        </div>
    </div>
</q:component>
"""
    (project_dir / 'components' / 'Card.q').write_text(card)

    # Input component
    input_comp = """<!-- Input Component -->
<q:component name="Input" xmlns:q="https://quantum.lang/ns">
    <q:param name="name" type="string" required="true" />
    <q:param name="type" type="string" default="text" />
    <q:param name="label" type="string" />
    <q:param name="placeholder" type="string" />
    <q:param name="required" type="boolean" default="false" />
    <q:param name="error" type="string" />

    <div class="form-group">
        <q:if condition="{label}">
            <label for="{name}">{label}</label>
        </q:if>
        <input
            type="{type}"
            id="{name}"
            name="{name}"
            placeholder="{placeholder}"
            required="{required}"
            class="{error ? 'has-error' : ''}"
        />
        <q:if condition="{error}">
            <span class="error-message">{error}</span>
        </q:if>
    </div>
</q:component>
"""
    (project_dir / 'components' / 'Input.q').write_text(input_comp)

    # Index file
    index = f"""<!-- {project_name} Component Library -->
<q:component name="{project_name}Index" xmlns:q="https://quantum.lang/ns">
    <!-- Export all components -->
    <q:import component="Button" />
    <q:import component="Card" />
    <q:import component="Input" />
</q:component>
"""
    (project_dir / 'index.q').write_text(index)


def _init_git(project_dir: Path) -> None:
    """Initialize git repository."""
    import subprocess

    try:
        subprocess.run(['git', 'init'], cwd=project_dir, capture_output=True, check=True)
        subprocess.run(['git', 'add', '.'], cwd=project_dir, capture_output=True, check=True)
        subprocess.run(
            ['git', 'commit', '-m', 'Initial commit - Quantum project'],
            cwd=project_dir,
            capture_output=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Git not available or failed - not critical
        pass
