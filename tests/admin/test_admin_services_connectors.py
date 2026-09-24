"""The admin.connectors.* services over quantum_admin/core/connector_service.py.

Everything with the isolated_admin fixture: connectors.yaml in a temporary
folder. The connection tests hit real local servers (http.server), not mocks.
"""

import http.server
import json
import sqlite3
import threading

import pytest
import yaml

from quantum_admin.core import connector_service
from quantum_admin.services import connectors as svc


@pytest.fixture(autouse=True)
def isolated(isolated_admin):
    return isolated_admin


def _file(isolated):
    return isolated / "quantum_admin" / "settings" / "connectors.yaml"


@pytest.fixture
def http_server():
    """A local server; keeps the headers it received. Answers by route."""
    received = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            received.append((self.path, dict(self.headers)))
            if self.path == "/api/tags":
                body = {"models": [{"name": "phi3"}, {"name": "qwen2:7b"}]}
            elif self.path == "/v1/models" and self.headers.get("x-api-key") == "right-key":
                body = {"data": [{"id": "claude-x"}]}
            else:
                self.send_response(401)
                self.end_headers()
                return
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_address[1], received
    server.shutdown()
    server.server_close()


class TestCrud:
    def test_required_fields(self):
        with pytest.raises(svc.ConnectorError, match="required"):
            svc.create_connector(name="", type="database", provider="postgres")

    def test_an_unknown_provider(self):
        with pytest.raises(svc.ConnectorError, match="unknown provider"):
            svc.create_connector(name="x", type="database", provider="oracle")

    def test_the_password_is_encrypted_in_the_file_and_never_returned(self, isolated):
        # the .q screen wrote the password in plain text to the YAML
        c = svc.create_connector(name="pg", type="database", provider="postgres", password="secret-123")
        assert "secret-123" not in _file(isolated).read_text(encoding="utf-8")
        assert c["has_password"] is True and "password" not in c and "password_masked" not in c
        assert all("secret" not in json.dumps(x) for x in svc.list_connectors())

    def test_the_provider_s_default_port(self):
        assert svc.create_connector(name="pg", type="database", provider="postgres")["port"] == 5432

    def test_default_unmarks_the_others_of_the_same_type(self):
        a = svc.create_connector(name="a", type="cache", provider="redis", is_default=True)
        b = svc.create_connector(name="b", type="cache", provider="redis", is_default=True)
        state = {c["name"]: c["is_default"] for c in svc.list_connectors()}
        assert state == {"a": False, "b": True}
        svc.update_connector(a["id"], is_default=True)
        assert {c["name"]: c["is_default"] for c in svc.list_connectors()} == {"a": True, "b": False}
        assert b["id"] != a["id"]

    def test_editing_with_a_blank_password_keeps_the_current_one(self, isolated):
        c = svc.create_connector(name="pg", type="database", provider="postgres", password="old")
        before = yaml.safe_load(_file(isolated).read_text(encoding="utf-8"))[0]["password"]
        svc.update_connector(c["id"], name="pg2", password="")
        after = yaml.safe_load(_file(isolated).read_text(encoding="utf-8"))[0]
        assert after["password"] == before and after["name"] == "pg2"

    def test_the_application_filter_includes_public_ones(self):
        svc.create_connector(name="public", type="cache", provider="redis")
        svc.create_connector(name="the-app", type="database", provider="postgres", application_id=7)
        svc.create_connector(name="another-app", type="database", provider="postgres", application_id=8)
        assert sorted(c["name"] for c in svc.list_connectors(application_id=7)) == ["public", "the-app"]
        assert [c["name"] for c in svc.list_connectors(type="cache")] == ["public"]

    def test_remove_and_missing(self):
        c = svc.create_connector(name="pg", type="database", provider="postgres")
        assert svc.delete_connector(c["id"]) == {"deleted": c["id"]}
        with pytest.raises(svc.ConnectorError, match="no connector"):
            svc.delete_connector(c["id"])


class TestProtectedFile:
    def test_an_invalid_entry_is_not_erased_on_the_next_write(self, isolated):
        # before: the entry that did not load vanished from the file on the next save
        _file(isolated).write_text(yaml.safe_dump([
            {"id": "ok", "name": "good", "type": "cache", "provider": "redis"},
            {"id": "x", "name": "strange", "type": "cache", "provider": "redis", "new_field": 1},
        ]), encoding="utf-8")
        original = _file(isolated).read_text(encoding="utf-8")
        with pytest.raises(connector_service.ConnectorFileError, match="strange"):
            svc.create_connector(name="new", type="cache", provider="redis")
        assert _file(isolated).read_text(encoding="utf-8") == original

    def test_an_unreadable_file_is_not_emptied(self, isolated):
        _file(isolated).write_text("- id: [open\n  name: bad", encoding="utf-8")
        original = _file(isolated).read_text(encoding="utf-8")
        with pytest.raises(connector_service.ConnectorFileError, match="could not be read"):
            svc.create_connector(name="new", type="cache", provider="redis")
        assert _file(isolated).read_text(encoding="utf-8") == original


class TestConnection:
    def test_a_real_sqlite_records_the_status(self, isolated):
        db = isolated / "data.db"
        sqlite3.connect(db).close()
        c = svc.create_connector(name="lite", type="database", provider="sqlite", database=str(db))
        r = svc.test_connector(c["id"])
        assert r["success"] is True and "SQLite" in r["details"]["version"]
        saved = svc.get_connector(c["id"])
        assert saved["status"] == "connected" and saved["last_tested"]

    def test_ollama_lists_models(self, http_server):
        port, _ = http_server
        c = svc.create_connector(name="ollama", type="ai", provider="ollama", host="127.0.0.1", port=port)
        r = svc.test_connector(c["id"])
        assert r["success"] is True and r["details"]["models"] == ["phi3", "qwen2:7b"]

    def test_anthropic_without_a_key_is_not_green(self):
        # before: CONNECTED and made-up models, with no request at all
        c = svc.create_connector(name="claude", type="ai", provider="anthropic")
        r = svc.test_connector(c["id"])
        assert r["success"] is False and "No API key" in r["error"]
        assert svc.get_connector(c["id"])["status"] == "error"

    def test_anthropic_queries_the_api_with_the_key(self, http_server):
        port, received = http_server
        base = f"http://127.0.0.1:{port}/v1"
        right = svc.create_connector(name="right", type="ai", provider="anthropic", password="right-key")
        wrong = svc.create_connector(name="wrong", type="ai", provider="anthropic", password="wrong-key")
        service = connector_service.get_connector_service()
        for connector_id in (right["id"], wrong["id"]):
            current = service.get_connector(connector_id)
            current.options = {"endpoint": base}
            service.update_connector(connector_id, {"options": current.options})
        assert svc.test_connector(right["id"]) == {"success": True, "error": None, "details": {"models": ["claude-x"]}}
        failure = svc.test_connector(wrong["id"])
        assert failure["success"] is False and "401" in failure["error"]
        assert received[0][1].get("x-api-key") == "right-key"

    def test_missing(self):
        with pytest.raises(svc.ConnectorError, match="no connector"):
            svc.test_connector("does-not-exist")
