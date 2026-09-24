"""The admin.projects.* services (quantum_admin/services/projects.py).

The behaviors came from components/admin/applications.q, which did them in
q:python over settings/projects.yaml. Each test runs with a new database and a
temporary root — never the admin's real database or folder.
"""

import logging
import os

import pytest
import yaml
from quantum_admin.services import _base
from quantum_admin.services import projects as svc


@pytest.fixture(autouse=True)
def isolated(isolated_admin):
    return isolated_admin


class TestCreate:
    def test_registers_and_creates_the_folder_with_a_default_config(self, isolated):
        p = svc.create_project("shop", "my shop")
        folder = isolated / "projects" / "shop"
        assert (folder / "components").is_dir() and (folder / "static").is_dir()
        config = yaml.safe_load((folder / "quantum.config.yaml").read_text(encoding="utf-8"))
        assert config["server"] == {"port": 8080, "host": "127.0.0.1", "debug": False}
        assert p["source_path"] == "projects/shop" and p["has_config"] and p["status"] == "active"

    def test_it_does_not_overwrite_an_existing_config(self, isolated):
        folder = isolated / "apps" / "old"
        folder.mkdir(parents=True)
        (folder / "quantum.config.yaml").write_text("server:\n  port: 9999\n", encoding="utf-8")
        p = svc.create_project("old", source_path="apps/old")
        assert p["port"] == 9999

    @pytest.mark.parametrize("name", ["", "a", "  "])
    def test_a_short_name_is_an_error(self, name):
        # the old screen ignored it and redirected with "Application created"
        with pytest.raises(svc.ProjectError, match="at least 2"):
            svc.create_project(name)

    def test_a_repeated_name_ignoring_case_is_an_error(self):
        svc.create_project("Shop")
        with pytest.raises(svc.ProjectError, match="already exists"):
            svc.create_project("shop")

    def test_a_path_outside_the_root_is_an_error(self, isolated):
        with pytest.raises(svc.ProjectError, match="inside"):
            svc.create_project("escape", source_path="../outside")
        assert not (isolated.parent / "outside").exists()


class TestList:
    def test_the_screen_fields(self, isolated):
        svc.create_project("shop", "sells things")
        components = isolated / "projects" / "shop" / "components"
        (components / "index.q").write_text("<q:component/>", encoding="utf-8")
        (components / "sub").mkdir()
        (components / "sub" / "b.q").write_text("", encoding="utf-8")
        (isolated / "projects" / "shop" / "outside.q").write_text("", encoding="utf-8")
        [p] = svc.list_projects()
        assert (p["name"], p["initial"], p["component_count"], p["port"], p["running"]) == \
            ("shop", "S", 2, 8080, False)

    def test_search_by_name_or_description(self):
        svc.create_project("shop", "sells things")
        svc.create_project("blog", "texts")
        assert [p["name"] for p in svc.list_projects("SELLS")] == ["shop"]
        assert [p["name"] for p in svc.list_projects("blo")] == ["blog"]

    def test_a_live_process_and_a_stale_pid(self, isolated):
        svc.create_project("running")
        svc.create_project("stopped")
        pids = isolated / "quantum_admin" / "settings" / "pids"
        pids.mkdir(parents=True)
        (pids / "running.pid").write_text(str(os.getpid()), encoding="utf-8")
        (pids / "stopped.pid").write_text("999999", encoding="utf-8")
        state = {p["name"]: p["running"] for p in svc.list_projects()}
        assert state == {"running": True, "stopped": False}
        assert not (pids / "stopped.pid").exists()      # a dead process's pid is cleaned up

    def test_counts_the_project_connectors(self, isolated):
        # connectors live in settings/connectors.yaml, through connector_service
        p = svc.create_project("shop")
        service = _base.connectors()
        service.create_connector({"name": "shop pg", "type": "database", "provider": "postgres",
                                  "scope": "application", "application_id": p["id"]})
        service.create_connector({"name": "shared cache", "type": "cache", "provider": "redis"})
        assert svc.list_projects()[0]["connector_count"] == 1
        assert svc.summary()["connectors"] == 2
        assert (isolated / "quantum_admin" / "settings" / "connectors.yaml").is_file()


class TestRemoveAndSync:
    def test_remove_deletes_the_record_and_leaves_the_files(self, isolated):
        p = svc.create_project("shop")
        assert svc.delete_project(p["id"]) == {"deleted": p["id"]}
        assert svc.list_projects() == []
        assert (isolated / "projects" / "shop" / "quantum.config.yaml").is_file()

    def test_removing_a_missing_one_is_an_error(self):
        with pytest.raises(svc.ProjectError, match="no project"):
            svc.delete_project(42)

    def test_sync_registers_new_folders_and_ignores_hidden_ones(self, isolated):
        for name in ("alpha", "beta", ".git", "_draft"):
            (isolated / "projects" / name).mkdir(parents=True)
        (isolated / "projects" / "file.txt").write_text("x", encoding="utf-8")
        svc.create_project("alpha")
        assert svc.sync_projects() == {"created": ["beta"], "total": 2}
        assert svc.sync_projects()["created"] == []          # idempotent

    def test_summary(self):
        svc.create_project("alpha")
        svc.create_project("beta")
        assert svc.summary() == {"total": 2, "active": 2, "running": 0, "with_config": 2, "connectors": 0}


@pytest.fixture
def admin_server(isolated):
    from quantum.runtime.web_server import QuantumWebServer
    folder = isolated / "components"
    folder.mkdir(exist_ok=True)
    config = isolated / "quantum.config.yaml"
    config.write_text(f"server:\n  debug: true\npaths:\n  components: {folder.as_posix()}\n"
                      "logging:\n  level: ERROR\n  console: false\n  file: false\n"
                      "services:\n  - quantum_admin.services.projects\n", encoding="utf-8")

    def render(body):
        (folder / "p.q").write_text(
            f'<q:component name="p" xmlns:q="https://quantum.lang/ns">{body}</q:component>', encoding="utf-8")
        logging.disable(logging.CRITICAL)
        try:
            r = QuantumWebServer(str(config)).app.test_client().get("/p")
        finally:
            logging.disable(logging.NOTSET)
        assert r.status_code == 200, r.get_data(as_text=True)[-600:]
        return r.get_data(as_text=True)
    return render


def test_a_screen_calls_the_service(admin_server):
    """End to end: a .q page -> q:invoke service= -> the admin's database."""
    svc.create_project("shop", "sells things")
    html = admin_server('<q:invoke name="ps" service="admin.projects.list"/>'
                        '<ul><q:loop items="{ps}" var="p"><li>{p.name}: {p.component_count}</li></q:loop></ul>')
    assert "shop: 0" in html
