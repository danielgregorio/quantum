"""Services of the application screen: project, config, environments, server and the project's connectors."""

import socket
import time
import urllib.request

import pytest
import yaml

from quantum_admin.services import apps, connectors
from quantum_admin.services import projects as proj


@pytest.fixture(autouse=True)
def isolated(isolated_admin):
    return isolated_admin


@pytest.fixture
def shop():
    return proj.create_project("shop", "sells things")


class TestProject:
    def test_update_name_description_status(self, shop):
        r = apps.update_project(shop["id"], name="shop-new", description="other", status="archived")
        assert (r["name"], r["description"], r["status"]) == ("shop-new", "other", "archived")

    def test_another_project_s_name_is_an_error(self, shop):
        proj.create_project("blog")
        with pytest.raises(proj.ProjectError, match="already exists"):
            apps.update_project(shop["id"], name="BLOG")

    def test_an_invalid_status(self, shop):
        with pytest.raises(proj.ProjectError, match="status must be"):
            apps.update_project(shop["id"], status="deleted")


class TestConfig:
    def test_read_and_save_the_text(self, shop, isolated):
        text = "# my config\nserver:\n  port: 9100\n"
        r = apps.save_project_config(shop["id"], text)
        assert r["server"] == {"port": 9100} and r["text"] == text
        assert (isolated / "projects" / "shop" / "quantum.config.yaml").read_text(encoding="utf-8") == text

    @pytest.mark.parametrize("text,reason", [("server: [open", "invalid YAML"), ("- a list\n- alone\n", "mapping")])
    def test_invalid_yaml_is_not_saved(self, shop, isolated, text, reason):
        before = (isolated / "projects" / "shop" / "quantum.config.yaml").read_text(encoding="utf-8")
        with pytest.raises(proj.ProjectError, match=reason):
            apps.save_project_config(shop["id"], text)
        assert (isolated / "projects" / "shop" / "quantum.config.yaml").read_text(encoding="utf-8") == before


class TestEnvironments:
    def test_create_with_variables_list_update_remove(self, shop):
        env = apps.create_environment(shop["id"], "Staging", port=8200, variables="DB_HOST=db\n# a comment\nMODE = test\n")
        assert (env["name"], env["display_name"], env["port"], env["variables"]) == \
            ("staging", "Staging", 8200, {"DB_HOST": "db", "MODE": "test"})
        env = apps.update_environment(env["id"], port=8300, variables={"X": "1"})
        assert env["port"] == 8300 and env["variables"] == {"X": "1"}
        assert [e["name"] for e in apps.list_environments(shop["id"])] == ["staging"]
        apps.delete_environment(env["id"])
        assert apps.list_environments(shop["id"]) == []

    def test_a_repeated_name_and_an_invalid_line(self, shop):
        apps.create_environment(shop["id"], "dev")
        with pytest.raises(proj.ProjectError, match="already exists"):
            apps.create_environment(shop["id"], "DEV")
        with pytest.raises(proj.ProjectError, match="NAME=value"):
            apps.create_environment(shop["id"], "prod", variables="NO_EQUALS")

    def test_defaults(self, shop):
        assert [e["name"] for e in apps.create_default_environments(shop["id"])] == \
            ["development", "staging", "production"]


def test_a_project_connector_and_detaching_it(shop):
    c = connectors.create_connector(name="pg", type="database", provider="postgres", application_id=shop["id"])
    assert proj.get_project(shop["id"])["connector_count"] == 1
    detached = connectors.detach_connector(c["id"])
    assert detached["scope"] == "public" and detached["application_id"] is None
    assert proj.get_project(shop["id"])["connector_count"] == 0


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _answers(url):
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            return r.status, r.read().decode()
    except OSError:
        return None, ""


class TestServer:
    def test_without_a_config_it_is_an_error(self):
        p = proj.create_project("empty")
        (proj.root() / "projects" / "empty" / "quantum.config.yaml").unlink()
        with pytest.raises(proj.ProjectError, match="not found"):
            apps.start_server(p["id"])

    def test_it_starts_serves_and_really_stops_with_the_reloader(self, isolated):
        # "start" ran src/cli/runner.py (missing); on Windows "stop" did not bring down the reloader's child
        p = proj.create_project("site")
        folder = isolated / "projects" / "site"
        port = _free_port()
        (folder / "components" / "index.q").write_text(
            '<q:component name="index" xmlns:q="https://quantum.lang/ns"><p>SITE IS UP</p></q:component>',
            encoding="utf-8")
        (folder / "quantum.config.yaml").write_text(yaml.safe_dump({
            "server": {"port": port, "host": "127.0.0.1", "reload": True, "debug": False},
            "paths": {"components": "./components"},
            "logging": {"level": "ERROR", "console": False, "file": False}}), encoding="utf-8")
        try:
            apps.start_server(p["id"], wait=30)
            url = f"http://127.0.0.1:{port}/"
            deadline = time.time() + 30
            while time.time() < deadline and _answers(url)[0] != 200:
                time.sleep(0.3)
            status, body = _answers(url)
            assert status == 200 and "SITE IS UP" in body, apps.server_log(p["id"], 40)["text"]
            assert apps.server_status(p["id"])["running"] is True
            with pytest.raises(proj.ProjectError, match="already running"):
                apps.start_server(p["id"])
        finally:
            apps.stop_server(p["id"])
        deadline = time.time() + 15
        while time.time() < deadline and _answers(url)[0] is not None:
            time.sleep(0.3)
        assert _answers(url)[0] is None, "the port still answers after stopping"
        assert apps.server_status(p["id"])["running"] is False

    def test_a_broken_config_fails_with_the_log(self, isolated):
        p = proj.create_project("broken")
        (isolated / "projects" / "broken" / "quantum.config.yaml").write_text("server: [open", encoding="utf-8")
        with pytest.raises(proj.ProjectError, match="exited with code"):
            apps.start_server(p["id"], wait=30)


def test_a_project_by_name(shop):
    assert apps.project_by_name("SHOP")["id"] == shop["id"]
    with pytest.raises(proj.ProjectError, match="no project named 'ghost'"):
        apps.project_by_name("ghost")


def test_the_project_files_and_routes(shop, isolated):
    folder = isolated / "projects" / "shop" / "components"
    (folder / "products").mkdir(parents=True)
    (folder / "index.q").write_text('<q:component name="Home"><q:set name="x" value="1"/></q:component>', encoding="utf-8")
    (folder / "products" / "[id].q").write_text('<q:component name="Product"/>', encoding="utf-8")
    (isolated / "projects" / "shop" / "static" / "app.css").write_text("body{}", encoding="utf-8")
    r = apps.project_files(shop["id"])
    assert [(c["name"], c["route"], c["dynamic"]) for c in r["components"]] == \
        [("Home", "/", False), ("Product", "/products/[id]", True)]
    assert r["components"][0]["tags"] == ["set"] and r["components"][0]["source"] == "projects/shop/components/index.q"
    assert r["static_files"] == 1


def test_a_connector_with_an_application_belongs_to_it(shop):
    c = connectors.create_connector(name="pg", type="database", provider="postgres", application_id=shop["id"])
    assert c["scope"] == "application"
