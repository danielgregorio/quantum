"""The admin's .q screens (quantum_admin/components/admin), served by the real server.

The screens come from the repository; database, settings and root are
temporary (isolated_admin), and the services run in the same process. Each
test comes in through the login screen, as a person does.
"""

import html as html_lib
import logging
import pathlib
import re

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
PASSWORD = "a-test-password-that-is-long-enough"
MODULES = ["quantum_admin.services.projects", "quantum_admin.services.yaml_import",
           "quantum_admin.services.connectors", "quantum_admin.services.settings",
           "quantum_admin.services.components", "quantum_admin.services.apps",
           "quantum_admin.services.repository", "quantum_admin.services.auth"]


def text(response):
    html = response.get_data(as_text=True)
    # <pre> shows file content (code, pytest output), which may have braces.
    html = re.sub(r"<(style|script|pre)\b.*?</\1>", "", html, flags=re.S)
    page = html_lib.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)))
    # An expression that fails in HTML content stays as text (EXPR-4): on an
    # admin screen that is always a defect of the screen. It applies to text and attributes.
    raw = re.findall(r"\{[^{}]*\}", page) + re.findall(r'="[^"]*(\{[^"{}]*\})[^"]*"', html)
    assert not raw, f"unresolved expressions on the screen: {raw[:5]}"
    return page


@pytest.fixture
def admin(isolated_admin, monkeypatch):
    from quantum import services
    from quantum.runtime.web_server import QuantumWebServer
    from quantum_admin.core import auth_service
    from quantum_admin.services import auth

    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setenv("JWT_SECRET_KEY", "k" * 64)
    monkeypatch.setattr(auth_service, "_auth_service", None)
    auth._reset()
    services._reset()
    config = isolated_admin / "quantum.config.yaml"
    config.write_text(yaml.safe_dump({
        "server": {"debug": False},
        "paths": {"components": (REPO / "quantum_admin" / "components").as_posix()},
        "logging": {"level": "ERROR", "console": False, "file": False},
        "services": MODULES,
    }), encoding="utf-8")
    logging.disable(logging.CRITICAL)
    app = QuantumWebServer(str(config)).app
    app.config["TESTING"] = True
    yield app.test_client()
    logging.disable(logging.NOTSET)
    services._reset()


def sign_in(client, password=PASSWORD):
    return client.post("/admin/login", data={"action": "signIn", "username": "admin", "password": password})


class TestLogin:
    def test_a_protected_screen_sends_to_the_admin_login(self, admin):
        r = admin.get("/admin/applications")
        assert r.status_code == 302 and r.headers["Location"].endswith("/admin/login")

    def test_a_wrong_password_comes_back_with_a_message(self, admin):
        r = sign_in(admin, "wrong")
        assert r.status_code == 302 and r.headers["Location"].endswith("/admin/login")
        assert "invalid username or password" in text(admin.get("/admin/login"))
        assert admin.get("/admin/applications").status_code == 302

    def test_sign_in_and_out(self, admin):
        r = sign_in(admin)
        assert r.status_code == 302 and r.headers["Location"].endswith("/admin/applications")
        assert admin.get("/admin/applications").status_code == 200
        admin.post("/admin/logout", data={"action": "signOut"})
        assert admin.get("/admin/applications").status_code == 302


class TestApplications:
    def test_list_create_and_remove(self, admin, isolated_admin):
        sign_in(admin)
        page = text(admin.get("/admin/applications"))
        assert "Applications" in page and "No Applications Found" in page

        r = admin.post("/admin/applications", data={"action": "createProject", "name": "shop", "description": "sells"})
        assert r.status_code == 302
        page = text(admin.get("/admin/applications"))
        assert "Application shop created" in page and "shop" in page and "sells" in page
        assert (isolated_admin / "projects" / "shop" / "quantum.config.yaml").is_file()

        from quantum_admin.services import projects
        [p] = projects.list_projects()
        admin.post("/admin/applications", data={"action": "deleteProject", "project_id": str(p["id"])})
        assert "Application record removed" in text(admin.get("/admin/applications"))
        assert projects.list_projects() == []

    def test_a_repeated_name_shows_the_service_error(self, admin):
        sign_in(admin)
        admin.post("/admin/applications", data={"action": "createProject", "name": "shop"})
        admin.get("/admin/applications")
        admin.post("/admin/applications", data={"action": "createProject", "name": "SHOP"})
        assert "already exists" in text(admin.get("/admin/applications"))

    def test_search(self, admin):
        sign_in(admin)
        for name in ("shop", "blog"):
            admin.post("/admin/applications", data={"action": "createProject", "name": name})
        page = text(admin.get("/admin/applications?search=blo"))
        assert "blog" in page and "shop" not in page

    def test_import_from_the_old_yaml(self, admin, isolated_admin):
        (isolated_admin / "quantum_admin" / "settings" / "projects.yaml").write_text(
            yaml.safe_dump([{"id": "u1", "name": "legacy", "source_path": "projects/legacy"}]), encoding="utf-8")
        sign_in(admin)
        assert "exist only in the old settings/projects.yaml" in text(admin.get("/admin/applications"))
        admin.post("/admin/applications", data={"action": "importYaml"})
        page = text(admin.get("/admin/applications"))
        assert "1 application(s) imported" in page and "legacy" in page
        assert "exist only in the old" not in page


SCREENS = ["/admin", "/admin/dashboard", "/admin/features", "/admin/agents", "/admin/database",
           "/admin/jobs", "/admin/source?file=README.md", "/admin/components", "/admin/tests",
           "/admin/component/components/shop.q", "/admin/settings", "/admin/connectors", "/admin/app/shop"]


@pytest.mark.parametrize("url", SCREENS)
def test_every_screen_asks_for_login(admin, url):
    r = admin.get(url)
    assert r.status_code == 302 and r.headers["Location"].endswith("/admin/login")


def test_the_layout_is_not_a_page(admin):
    sign_in(admin)
    assert admin.get("/admin/_layout/AdminShell").status_code == 404
    assert admin.get("/admin/AdminShell").status_code == 404


class TestReadingScreens:
    def test_admin_leads_to_the_applications(self, admin):
        sign_in(admin)
        assert 'url=/admin/applications' in admin.get("/admin").get_data(as_text=True)

    def test_dashboard(self, admin, isolated_admin):
        (isolated_admin / "components").mkdir()
        (isolated_admin / "components" / "shop.q").write_text('<q:component name="Shop"/>', encoding="utf-8")
        sign_in(admin)
        page = text(admin.get("/admin/dashboard"))
        assert "shop.q" in page and "Tags with a parser" in page

    def test_features(self, admin):
        sign_in(admin)
        page = text(admin.get("/admin/features"))
        assert "conditionals" in page and "loops" in page

    def test_agents_and_llm_without_the_key(self, admin, isolated_admin):
        (isolated_admin / "components").mkdir()
        (isolated_admin / "components" / "a.q").write_text(
            '<q:component name="A"><q:agent name="helper" model="phi3" provider="ollama"/></q:component>',
            encoding="utf-8")
        config = isolated_admin / "quantum.config.yaml"
        data = yaml.safe_load(config.read_text(encoding="utf-8"))
        data["llm"] = {"base_url": "http://localhost:11434", "default_model": "phi3", "api_key": "sk-DO-NOT-SHOW"}
        config.write_text(yaml.safe_dump(data), encoding="utf-8")
        sign_in(admin)
        html = admin.get("/admin/agents").get_data(as_text=True)
        page = text(admin.get("/admin/agents"))
        assert "helper" in page and "http://localhost:11434" in page and "components/a.q" in page
        assert "sk-DO-NOT-SHOW" not in html

    def test_databases_and_datasources_without_credentials(self, admin, isolated_admin):
        import sqlite3
        connection = sqlite3.connect(isolated_admin / "shop.db")
        connection.executescript("create table orders (id integer); insert into orders values (1), (2), (3);")
        connection.close()
        config = isolated_admin / "quantum.config.yaml"
        data = yaml.safe_load(config.read_text(encoding="utf-8"))
        data["datasources"] = {"sales": {"driver": "postgres", "database": "sales", "password": "password-DO-NOT-SHOW"}}
        config.write_text(yaml.safe_dump(data), encoding="utf-8")
        sign_in(admin)
        html = admin.get("/admin/database").get_data(as_text=True)
        page = text(admin.get("/admin/database"))
        assert "shop.db" in page and "orders" in page and "sales" in page and "postgres" in page
        assert "password-DO-NOT-SHOW" not in html

    def test_jobs(self, admin, isolated_admin):
        sign_in(admin)
        assert "No Job Queue Yet" in text(admin.get("/admin/jobs"))
        import sqlite3
        connection = sqlite3.connect(isolated_admin / "quantum_jobs.db")
        connection.executescript(
            "create table quantum_jobs (id integer primary key autoincrement, name text, queue text, status text,"
            " attempts integer, max_attempts integer, created_at text, error text);"
            "insert into quantum_jobs (name, queue, status, attempts, max_attempts, error) values"
            " ('send-email','mail','failed',3,3,'SMTP refused'), ('report',null,'pending',0,3,null);")
        connection.close()
        page = text(admin.get("/admin/jobs"))
        assert "send-email" in page and "SMTP refused" in page and "3/3" in page and "report" in page

    def test_the_code_reader(self, admin, isolated_admin):
        (isolated_admin / "README.txt").write_text("first line\nsecond line\n", encoding="utf-8")
        (isolated_admin / ".env").write_text("PASSWORD=secret-DO-NOT-SHOW\n", encoding="utf-8")
        sign_in(admin)
        page = text(admin.get("/admin/source?file=README.txt"))
        assert "3 lines" in page
        assert "second line" in admin.get("/admin/source?file=README.txt").get_data(as_text=True)
        html = admin.get("/admin/source?file=.env").get_data(as_text=True)
        assert "may contain credentials" in text(admin.get("/admin/source?file=.env"))
        assert "secret-DO-NOT-SHOW" not in html
        assert "outside the project root" in text(admin.get("/admin/source?file=../x.txt"))
        assert "a file path is required" in text(admin.get("/admin/source"))


COMPONENT = ('<q:component name="Shop" xmlns:q="https://quantum.lang/ns">'
             '<q:action name="buy" method="POST"><q:param name="item" required="true"/>'
             '<q:redirect url="/shop"/></q:action><p>storefront</p></q:component>\n')


class TestComponentsAndTests:
    @pytest.fixture
    def project(self, isolated_admin):
        (isolated_admin / "components" / "sub").mkdir(parents=True)
        (isolated_admin / "components" / "shop.q").write_text(COMPONENT, encoding="utf-8")
        (isolated_admin / "components" / "sub" / "b.q").write_text('<q:component name="B"/>', encoding="utf-8")
        (isolated_admin / "tests").mkdir()
        (isolated_admin / "tests" / "test_ok.py").write_text("def test_one():\n    assert True\n", encoding="utf-8")
        return isolated_admin

    def test_lists(self, admin, project):
        sign_in(admin)
        page = text(admin.get("/admin/components"))
        assert "shop.q" in page and "sub/b.q" in page and "action, redirect" in page
        assert 'href="/admin/component/components/shop.q"' in admin.get("/admin/components").get_data(as_text=True)
        page = text(admin.get("/admin/tests"))
        assert "test_ok.py" in page

    def test_detail(self, admin, project):
        sign_in(admin)
        page = text(admin.get("/admin/component/components/shop.q"))
        assert "Shop" in page and "buy" in page and "no test file yet" in page

    def test_outside_the_root_and_missing(self, admin, project):
        sign_in(admin)
        # The server already blocks ".." in the URL (404); the service blocks whatever gets past.
        assert admin.get("/admin/component/components/../../outside.q").status_code == 404
        assert "file not found" in text(admin.get("/admin/component/components/missing.q"))

    def test_generate_does_not_overwrite_and_run(self, admin, project):
        sign_in(admin)
        url = "/admin/component/components/shop.q"
        r = admin.post(url, data={"action": "generateTests"})
        assert r.status_code == 302 and r.headers["Location"].endswith("?tab=tests")
        generated = project / "tests" / "test_components_shop.py"
        page = text(admin.get(url + "?tab=tests"))
        assert "tests/test_components_shop.py created" in page and generated.is_file()

        generated.write_text("def test_hand_written():\n    assert True\n\ndef test_broken():\n    assert False\n",
                             encoding="utf-8")
        admin.post(url, data={"action": "generateTests"})  # without overwrite: refuses
        assert "already exists" in text(admin.get(url))
        assert "test_hand_written" in generated.read_text(encoding="utf-8")

        admin.post(url, data={"action": "runTests"})
        page = text(admin.get(url + "?tab=tests"))
        assert "1 failed, 0 errors, 1 passed" in page
        assert "PASSED test_hand_written" in page and "FAILED test_broken" in page

        admin.post(url, data={"action": "generateTests", "overwrite": "true"})
        assert "regenerated" in text(admin.get(url))
        assert "test_hand_written" not in generated.read_text(encoding="utf-8")

    def test_run_without_a_test_file(self, admin, project):
        sign_in(admin)
        admin.post("/admin/component/components/sub/b.q", data={"action": "runTests"})
        assert "there is no test file to run" in text(admin.get("/admin/component/components/sub/b.q"))


class TestSettings:
    @pytest.fixture
    def config(self, admin, isolated_admin):
        path = isolated_admin / "quantum.config.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["server"].update(port=8123, host="127.0.0.1", reload=True)
        path.write_text("# WARNING: do not expose the server\n" + yaml.safe_dump(data), encoding="utf-8")
        return path

    def test_the_form_comes_with_what_is_in_the_file(self, admin, config):
        sign_in(admin)
        html = admin.get("/admin/settings").get_data(as_text=True)
        text(admin.get("/admin/settings"))
        assert 'value="8123"' in html
        assert re.search(r'<input[^>]*name="reload"[^>]*checked', html)
        assert not re.search(r'<input[^>]*name="debug"[^>]*checked', html)
        assert re.search(r'<option value="ERROR" selected', html)  # the fixture's logging.level

    def test_saving_changes_only_the_values(self, admin, config):
        sign_in(admin)
        r = admin.post("/admin/settings", data={"action": "saveSettings", "port": "9090", "host": "127.0.0.1",
                                                "debug": "true", "log_level": "ERROR", "cache_ttl": "0"})
        assert r.status_code == 302
        assert "Saved" in text(admin.get("/admin/settings"))
        content = config.read_text(encoding="utf-8")
        saved = yaml.safe_load(content)
        assert content.startswith("# WARNING: do not expose the server")
        assert saved["server"]["port"] == 9090 and saved["server"]["debug"] is True
        assert saved["server"]["reload"] is False  # unchecked box

    def test_debug_with_a_public_host_is_refused(self, admin, config):
        sign_in(admin)
        before = config.read_text(encoding="utf-8")
        admin.post("/admin/settings", data={"action": "saveSettings", "port": "9090", "host": "0.0.0.0",
                                            "debug": "true", "log_level": "INFO"})
        assert "debug cannot be on with host 0.0.0.0" in text(admin.get("/admin/settings"))
        assert config.read_text(encoding="utf-8") == before


class TestConnectors:
    def _create(self, admin, **fields):
        data = {"action": "createConnector", "name": "lite", "conn_type": "database", "provider": "sqlite"}
        data.update(fields)
        return admin.post("/admin/connectors", data=data)

    def test_create_with_an_encrypted_password_never_shown(self, admin, isolated_admin):
        sign_in(admin)
        page = text(admin.get("/admin/connectors"))
        assert "0 registered" in page and "New Connector" in page
        assert self._create(admin, name="main", provider="postgres", conn_type="database",
                            username="app", password="password-DO-NOT-SHOW").status_code == 302
        assert "Connector main created" in text(admin.get("/admin/connectors"))
        html = admin.get("/admin/connectors").get_data(as_text=True)
        page = text(admin.get("/admin/connectors"))
        assert "main" in page and "PostgreSQL" in page and "localhost:5432" in page
        stored = (isolated_admin / "quantum_admin" / "settings" / "connectors.yaml").read_text(encoding="utf-8")
        assert "password-DO-NOT-SHOW" not in stored and "password-DO-NOT-SHOW" not in html

    def test_required_fields_and_an_unknown_provider(self, admin):
        sign_in(admin)
        self._create(admin, provider="magic-db")
        assert "unknown provider" in text(admin.get("/admin/connectors"))

    def test_editing_keeps_the_password_and_testing(self, admin, isolated_admin):
        import sqlite3
        from quantum_admin.services import connectors as svc
        db = isolated_admin / "data.db"
        sqlite3.connect(db).close()
        sign_in(admin)
        self._create(admin, database=str(db), password="kept")
        [c] = svc.list_connectors()

        html = admin.get(f"/admin/connectors?edit={c['id']}").get_data(as_text=True)
        page = text(admin.get(f"/admin/connectors?edit={c['id']}"))
        assert "Edit lite" in page and "saved — leave blank to keep" in html
        assert re.search(r'<option value="sqlite" selected', html)

        admin.post("/admin/connectors", data={"action": "updateConnector", "connector_id": c["id"], "name": "lite2",
                                              "conn_type": "database", "provider": "sqlite", "password": ""})
        assert "Connector lite2 updated" in text(admin.get("/admin/connectors"))
        assert svc.get_connector(c["id"])["has_password"] is True

        admin.post("/admin/connectors", data={"action": "testConnector", "connector_id": c["id"]})
        assert "Connection OK" in text(admin.get("/admin/connectors"))
        assert svc.get_connector(c["id"])["status"] == "connected"

    def test_a_failing_test_shows_the_reason(self, admin):
        from quantum_admin.services import connectors as svc
        sign_in(admin)
        self._create(admin, name="claude", conn_type="ai", provider="anthropic")
        [c] = svc.list_connectors()
        admin.post("/admin/connectors", data={"action": "testConnector", "connector_id": c["id"]})
        assert "Connection failed: No API key" in text(admin.get("/admin/connectors"))

    def test_edit_a_missing_one_and_remove(self, admin):
        from quantum_admin.services import connectors as svc
        sign_in(admin)
        assert "no connector with id 'ghost'" in text(admin.get("/admin/connectors?edit=ghost"))
        self._create(admin)
        [c] = svc.list_connectors()
        admin.post("/admin/connectors", data={"action": "deleteConnector", "connector_id": c["id"]})
        assert "Connector deleted" in text(admin.get("/admin/connectors"))
        assert svc.list_connectors() == []


class TestApplication:
    @pytest.fixture
    def shop(self, admin):
        from quantum_admin.services import projects
        sign_in(admin)
        return projects.create_project("shop", "sells things")

    def test_missing(self, admin):
        sign_in(admin)
        assert "no project named 'ghost'" in text(admin.get("/admin/app/ghost"))

    def test_general_and_edit(self, admin, shop):
        page = text(admin.get("/admin/app/shop"))
        assert "projects/shop" in page
        assert 'value="sells things"' in admin.get("/admin/app/shop").get_data(as_text=True)
        r = admin.post("/admin/app/shop", data={"action": "updateProject", "new_name": "shop-new",
                                                "description": "other", "status": "archived"})
        assert r.headers["Location"].endswith("/admin/app/shop-new")
        assert "Application updated" in text(admin.get("/admin/app/shop-new"))
        html = admin.get("/admin/app/shop-new").get_data(as_text=True)
        assert 'value="other"' in html and re.search(r'<option value="archived" selected', html)

    def test_the_action_uses_the_project_from_the_url_not_a_hidden_field(self, admin, shop):
        from quantum_admin.services import projects
        blog = projects.create_project("blog")
        admin.post("/admin/app/shop", data={"action": "updateProject", "project_id": str(blog["id"]),
                                            "new_name": "shop", "description": "changed", "status": "active"})
        assert projects.get_project(shop["id"])["description"] == "changed"
        assert projects.get_project(blog["id"])["description"] == ""

    def test_the_application_connectors(self, admin, shop):
        from quantum_admin.services import connectors
        r = admin.post("/admin/app/shop", data={"action": "createProjectConnector", "conn_name": "cache",
                                                "conn_type": "cache", "provider": "redis",
                                                "password": "password-DO-NOT-SHOW"})
        assert r.headers["Location"].endswith("?tab=connectors")
        html = admin.get("/admin/app/shop?tab=connectors").get_data(as_text=True)
        assert re.search(r'id="tab-connectors"[^>]*checked', html) and "password-DO-NOT-SHOW" not in html
        [c] = connectors.list_connectors()
        assert c["application_id"] == shop["id"] and c["scope"] == "application"
        assert "this application" in text(admin.get("/admin/app/shop"))
        admin.post("/admin/app/shop", data={"action": "detachConnector", "connector_id": c["id"]})
        assert "Connector cache is now public" in text(admin.get("/admin/app/shop"))
        assert connectors.get_connector(c["id"])["application_id"] is None

    def test_config(self, admin, shop, isolated_admin):
        path = isolated_admin / "projects" / "shop" / "quantum.config.yaml"
        new = "# a comment that stays\nserver:\n  port: 9111\n"
        admin.post("/admin/app/shop", data={"action": "saveProjectConfig", "config_yaml": new})
        assert "Configuration saved" in text(admin.get("/admin/app/shop"))
        assert path.read_text(encoding="utf-8") == new
        admin.post("/admin/app/shop", data={"action": "saveProjectConfig", "config_yaml": "server: [open"})
        assert "invalid YAML" in text(admin.get("/admin/app/shop"))
        assert path.read_text(encoding="utf-8") == new

    def test_environments(self, admin, shop):
        from quantum_admin.services import apps
        admin.post("/admin/app/shop", data={"action": "createDefaultEnvironments"})
        assert "3 environment(s) created" in text(admin.get("/admin/app/shop"))
        admin.post("/admin/app/shop", data={"action": "createEnvironment", "env_name": "Demo"})
        page = text(admin.get("/admin/app/shop?tab=environments"))
        assert "Environment demo created" in page
        demo = next(e for e in apps.list_environments(shop["id"]) if e["name"] == "demo")
        admin.post("/admin/app/shop", data={"action": "updateEnvironment", "environment_id": str(demo["id"]),
                                            "variables": "DB=shop\nMODE=test", "port": "8201", "branch": "main"})
        assert "Environment demo saved" in text(admin.get("/admin/app/shop"))
        demo = next(e for e in apps.list_environments(shop["id"]) if e["name"] == "demo")
        assert demo["variables"] == {"DB": "shop", "MODE": "test"} and demo["port"] == 8201
        admin.post("/admin/app/shop", data={"action": "updateEnvironment", "environment_id": str(demo["id"]),
                                            "variables": "a line without an equals sign"})
        assert "NAME=value" in text(admin.get("/admin/app/shop"))
        admin.post("/admin/app/shop", data={"action": "deleteEnvironment", "environment_id": str(demo["id"])})
        assert "Environment deleted" in text(admin.get("/admin/app/shop"))
        assert len(apps.list_environments(shop["id"])) == 3

    def test_components_and_runtime(self, admin, shop, isolated_admin):
        folder = isolated_admin / "projects" / "shop" / "components"
        (folder / "products").mkdir(parents=True, exist_ok=True)
        (folder / "products" / "[id].q").write_text('<q:component name="Product"/>', encoding="utf-8")
        page = text(admin.get("/admin/app/shop"))
        assert "/products/[id]" in page and "Product" in page and "dynamic" in page
        assert "Start Server" in page and "Nothing logged yet" in page
