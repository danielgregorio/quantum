"""
Path traversal in the component router was unauthenticated RCE.

Two independent audit dimensions reproduced it: a raw socket sending
`GET /../../pwned` (Flask only normalises `..` for clients that send a
normalised path — curl --path-as-is and raw sockets do not) reached a .q two
directories above the web root and executed it. Since a .q can carry
<q:python>, and the default config listens on 0.0.0.0 with python_scripting on,
that is remote code execution from an unauthenticated GET.

The router built `Path(components_dir) / f'{component_path}.q'` and called
.exists() with no containment check. Reproduced via raw socket before fixing.
"""

import pathlib

import pytest

from quantum.runtime.web_server import QuantumWebServer


@pytest.fixture
def server(tmp_path):
    root = tmp_path / "app" / "components"
    root.mkdir(parents=True)
    (root / "index.q").write_text(
        '<q:component name="Index"><h1>home</h1></q:component>', encoding="utf-8"
    )
    (root / "admin").mkdir()
    (root / "admin" / "projects.q").write_text(
        '<q:component name="P"><h1>legit</h1></q:component>', encoding="utf-8"
    )
    # The payload, one and two levels ABOVE the web root.
    for up in (tmp_path / "app", tmp_path):
        (up / "pwned.q").write_text(
            '<q:component name="Pwned"><q:python>q.marker = "TRAVERSAL-RAN-PYTHON"'
            '</q:python><h1>{marker}</h1></q:component>',
            encoding="utf-8",
        )

    s = QuantumWebServer()
    s.config["paths"]["components"] = str(root)
    s.config.setdefault("security", {})["python_scripting"] = True
    return s


class TestContainment:
    """_is_within_components is the guard; test it directly with the DECODED
    values the handler actually receives (Flask decodes %2e/%2f before routing)."""

    @pytest.mark.parametrize("cp", [
        "../pwned", "../../pwned", "..\\pwned", "a/../../pwned",
        "../../../../Windows/win", "../secret",
    ])
    def test_traversal_paths_are_rejected(self, server, cp):
        assert server._is_within_components(cp) is False

    @pytest.mark.parametrize("cp", [
        "index", "admin/projects", "a/b/c", "deeply/nested/page",
    ])
    def test_legitimate_paths_are_allowed(self, server, cp):
        assert server._is_within_components(cp) is True


class TestEndToEnd:
    """Through the real routing handler, with the encodings a raw client sends.
    Flask decodes these to `..` before the handler sees them."""

    @pytest.mark.parametrize("url", [
        "/..%2f..%2fpwned",
        "/..%2fpwned",
        "/%2e%2e%2f%2e%2e%2fpwned",
        "/%2e%2e/pwned",
    ])
    def test_encoded_traversal_does_not_execute(self, server, url):
        resp = server.app.test_client().get(url)
        body = resp.get_data(as_text=True)
        assert "TRAVERSAL-RAN-PYTHON" not in body, (
            f"{url} executed a q:python block outside the web root"
        )
        assert resp.status_code == 404

    def test_legitimate_route_still_serves(self, server):
        resp = server.app.test_client().get("/admin/projects")
        assert resp.status_code == 200
        assert "legit" in resp.get_data(as_text=True)

    def test_index_still_serves(self, server):
        assert server.app.test_client().get("/index").status_code == 200
