"""The admin inventory (scripts/admin-inventory.py) measures what it says it measures.

The findings it backs — shadowed routes, UI calls that reach no route — were
checked with real requests. These tests keep the two parts that produced false
positives while it was being written.
"""

import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("admin_inventory", REPO / "scripts" / "admin-inventory.py")
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


def test_concatenation_keeps_the_pieces_after_the_variable():
    # '/docker/containers/' + id + '/start' became /docker/containers/1 and
    # showed as a broken call.
    assert inventory._normalize("'{URL_PREFIX}/docker/containers/' + id + '/start'") == \
        "/docker/containers/1/start"


def test_template_string_and_fstring():
    assert inventory._normalize("`/admin/projects/${{PROJECT_ID}}/environments/${{envId}}`") == \
        "/admin/projects/1/environments/1"
    assert inventory._normalize("`{URL_PREFIX}/api/projects/{project_id}/logs/stats?hours=${{hours}}`") == \
        "/api/projects/1/logs/stats"


def test_a_variable_is_not_resolved():
    assert inventory._normalize("url") is None


def test_every_route_of_main_is_read():
    routes = inventory.routes_from_ast()
    # A floor, to catch the AST reader missing routes: 268 before the deploy
    # feature went (0.23), 234 after.
    assert len(routes) >= 230
    assert any(r["path"] == "/settings/export" and r["handler"] == "export_settings" for r in routes)
