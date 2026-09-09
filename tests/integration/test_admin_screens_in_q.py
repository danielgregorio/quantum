"""
The admin's core screens, written in Quantum instead of FastAPI + Jinja + JS.

SATELLITES_AUDIT.md Fase E. These are not decoration: writing a real screen
in the language is the best pressure test the framework has — the eleven
frictions in DOGFOOD_NOTES.md all came out of writing the first one — and a
screen nobody executes rots. So each is rendered here against a real database
and checked for the thing the screen exists to show.

The point of the checks is the ROWS. An empty screen renders fine and proves
nothing, so every test here puts data in first.
"""

import pathlib
import sqlite3

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime
from quantum.runtime.renderer import HTMLRenderer

REPO = pathlib.Path(__file__).resolve().parents[2]
SCREENS = REPO / "components" / "admin"


def render(screen: str, db_path: pathlib.Path):
    """Execute and render a screen against a specific database file."""
    node = QuantumParser().parse_file(str(SCREENS / screen))
    runtime = ComponentRuntime(config={
        'datasources': {
            'admin': {'driver': 'sqlite', 'database': str(db_path)},
        }
    })
    runtime.execute_component(node, {})
    html = HTMLRenderer(runtime.execution_context).render(node)
    return html, runtime.execution_context.get_all_variables()


@pytest.fixture
def admin_db(tmp_path):
    """A real admin database, with the columns the screens select."""
    path = tmp_path / "admin.db"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY, name TEXT, description TEXT,
            status TEXT, git_branch TEXT, updated_at TEXT
        );
        CREATE TABLE datasources (
            id INTEGER PRIMARY KEY, project_id INTEGER, name TEXT, type TEXT,
            connection_type TEXT, container_id TEXT, image TEXT, port INTEGER,
            host TEXT, database_name TEXT, username TEXT,
            password_encrypted TEXT, status TEXT, health_status TEXT,
            setup_status TEXT, auto_start INTEGER, visibility TEXT,
            shared_with TEXT, created_at TEXT, updated_at TEXT
        );
    """)
    conn.commit()
    conn.close()
    return path


def add_project(db, **row):
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO projects (id, name, description, status, git_branch, "
        "updated_at) VALUES (?,?,?,?,?,?)",
        (row['id'], row['name'], row.get('description', ''),
         row.get('status', 'active'), row.get('git_branch', 'main'),
         row.get('updated_at', '2026-01-01')))
    conn.commit()
    conn.close()


def add_datasource(db, **row):
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO datasources (id, project_id, name, type, host, port, "
        "database_name, status, health_status) VALUES (?,?,?,?,?,?,?,?,?)",
        (row['id'], row.get('project_id'), row['name'],
         row.get('type', 'postgres'), row.get('host', 'localhost'),
         row.get('port', 5432), row.get('database_name', 'app'),
         row.get('status', 'running'), row.get('health_status', 'healthy')))
    conn.commit()
    conn.close()


class TestTheProjectsScreen:
    def test_every_project_reaches_the_page(self, admin_db):
        add_project(admin_db, id=1, name="Loja", description="uma loja")
        add_project(admin_db, id=2, name="Blog", description="um blog")

        html, variables = render("projects.q", admin_db)

        assert len(variables['projects']) == 2
        assert html.count('class="card"') == 2
        assert "Loja" in html and "Blog" in html

    def test_the_count_is_the_number_of_rows(self, admin_db):
        for i in range(3):
            add_project(admin_db, id=i + 1, name=f"P{i}")
        _, variables = render("projects.q", admin_db)
        assert variables['total'] == '3'

    def test_an_empty_database_shows_the_empty_state(self, admin_db):
        html, _ = render("projects.q", admin_db)
        assert 'class="card"' not in html
        assert "No projects" in html

    def test_nothing_unresolved_leaks_onto_the_page(self, admin_db):
        import re
        add_project(admin_db, id=1, name="Loja")
        html, _ = render("projects.q", admin_db)
        body = html.split('</style>', 1)[-1]     # CSS braces are not bindings
        assert re.findall(r'\{[a-zA-Z_][\w.]*\}', body) == []


class TestTheDatasourcesScreen:
    def test_every_datasource_reaches_the_page(self, admin_db):
        add_project(admin_db, id=1, name="Loja")
        add_datasource(admin_db, id=1, project_id=1, name="main-db",
                       type="postgres")
        add_datasource(admin_db, id=2, project_id=1, name="cache",
                       type="redis", health_status="unhealthy")

        html, variables = render("datasources.q", admin_db)

        assert len(variables['sources']) == 2
        assert html.count('class="card"') == 2
        assert "main-db" in html and "cache" in html

    def test_the_connection_details_are_shown(self, admin_db):
        add_datasource(admin_db, id=1, name="main-db", host="10.0.0.5",
                       port=5433, database_name="loja")
        html, _ = render("datasources.q", admin_db)
        assert "10.0.0.5:5433/loja" in html

    def test_health_is_visible_as_state_not_just_text(self, admin_db):
        add_datasource(admin_db, id=1, name="cache", health_status="unhealthy")
        html, _ = render("datasources.q", admin_db)
        assert 'class="badge unhealthy"' in html

    def test_the_project_name_comes_from_the_join(self, admin_db):
        add_project(admin_db, id=7, name="Loja")
        add_datasource(admin_db, id=1, project_id=7, name="main-db")
        html, _ = render("datasources.q", admin_db)
        assert "Loja" in html

    def test_a_datasource_without_a_project_still_renders(self, admin_db):
        # LEFT JOIN: project is NULL. The row must not vanish, and the page
        # must not show the word "None".
        add_datasource(admin_db, id=1, project_id=None, name="orfa")
        html, variables = render("datasources.q", admin_db)
        assert len(variables['sources']) == 1
        assert "orfa" in html
        assert "None" not in html, "a SQL NULL leaked to the page as Python"

    def test_an_empty_database_shows_the_empty_state(self, admin_db):
        html, _ = render("datasources.q", admin_db)
        assert 'class="card"' not in html
        assert "No datasources" in html

    def test_nothing_unresolved_leaks_onto_the_page(self, admin_db):
        import re
        add_datasource(admin_db, id=1, name="main-db")
        html, _ = render("datasources.q", admin_db)
        body = html.split('</style>', 1)[-1]
        assert re.findall(r'\{[a-zA-Z_][\w.]*\}', body) == []
