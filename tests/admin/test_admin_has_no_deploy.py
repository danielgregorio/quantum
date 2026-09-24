"""The admin no longer deploys; what it had stays readable.

The legacy FastAPI backend had a deploy feature (DeployService, a deploy
pipeline with versions and rollback, cloud integrations for AWS, Kubernetes,
Azure and GCP, auto-deploy on a webhook push). None of it deployed anything
real, and it was removed for 1.0. The generic Docker features for datasources
stay, and so does the data an existing install already has: settings files
with a `deployment:` block and environments stored with deploy columns.
"""

import pathlib

import pytest
import yaml

from tests.admin.test_admin_smoke import app, auth, client, token  # noqa: F401 -- fixtures


REMOVED = [
    ("GET", "/deploy"),
    ("GET", "/admin/deploy"),
    ("GET", "/deployments"),
    ("POST", "/deploy"),
    ("GET", "/deploy/1/status"),
    ("POST", "/deploy/start"),
    ("GET", "/deploy/pipeline/1"),
    ("POST", "/projects/1/environments/1/rollback"),
    ("POST", "/projects/1/environments/1/approve"),
    ("GET", "/projects/1/versions"),
    ("GET", "/projects/1/pipelines"),
    ("POST", "/projects/1/pipelines/1/retry"),
    ("GET", "/settings/cloud"),
    ("POST", "/settings/cloud"),
    ("GET", "/integrations"),
    ("GET", "/integrations/aws/regions"),
]


@pytest.mark.parametrize("method,path", REMOVED)
def test_the_deploy_routes_are_gone(client, auth, method, path):
    response = client.request(method, path, headers=auth)
    assert response.status_code in (404, 405), (method, path, response.status_code)


def test_the_screens_no_longer_offer_to_deploy(client, auth):
    for page in ("/admin", "/admin/settings", "/admin/cicd"):
        html = client.get(page, headers=auth).text
        assert "/deploy" not in html, page
        assert "deployToEnvironment" not in html and "openCloudModal" not in html, page


def test_the_docker_features_for_datasources_stay(app):
    # Asked of the router: a 404 from these routes is a real answer ("no such
    # datasource"), not a sign that the route is gone.
    paths = {route.path for route in app.app.routes}
    for path in ("/docker/info", "/docker/containers", "/datasources/{datasource_id}/logs",
                 "/datasources/{datasource_id}/start", "/datasources/{datasource_id}/stop"):
        assert path in paths, path


def test_an_environment_stored_with_deploy_columns_still_loads(app, client, auth):
    models = app.models
    db = next(app.get_db())
    try:
        project = models.Project(name="legacy-deploys", description="")
        db.add(project)
        db.commit()
        db.add(models.Environment(
            project_id=project.id, name="production", display_name="Production",
            docker_registry="registry.example.com/org", deploy_path="/var/www/app",
            auto_deploy=True, requires_approval=True))
        db.commit()
        project_id = project.id
    finally:
        db.close()

    listed = client.get(f"/projects/{project_id}/environments", headers=auth)
    assert listed.status_code == 200
    assert [e["name"] for e in listed.json()] == ["production"]
    page = client.get(f"/api/projects/{project_id}/environments-html", headers=auth)
    assert page.status_code == 200 and "Production" in page.text
    assert "Auto-deploy" not in page.text and "Deploy" not in page.text


def test_a_settings_file_with_a_deployment_block_still_loads(isolated_admin):
    from quantum_admin.core import settings_service

    settings_file = pathlib.Path(settings_service.GLOBAL_SETTINGS_FILE)
    settings_file.write_text(yaml.safe_dump({
        "server": {"port": 9000},
        "deployment": {"default_port": 8080, "environments": [{"name": "prod", "host": "h"}]},
    }), encoding="utf-8")

    service = settings_service.get_settings_service()
    assert service.get_global_settings()["server"]["port"] == 9000
    service.update_global_settings({"server": {"port": 9001}})
    assert service.get_global_settings()["server"]["port"] == 9001


def test_new_settings_do_not_offer_a_deployment_section():
    from dataclasses import asdict
    from quantum_admin.core.settings_service import GlobalSettings, ProjectSettings

    assert "deployment" not in asdict(GlobalSettings())
    assert "deployment" not in asdict(ProjectSettings())
