"""
Every page the framework serves got a CDN <script> injected into it.

An app that is offline, behind a firewall, or on an air-gapped host then
loaded a page whose htmx never arrived — and before 5d348f3 that also meant
"htmx is not defined" from the framework's own inline configuration, on 233
of the 268 files that get the wrapper.

_htmx_url() was already written to prefer a vendored copy. The copy itself was
missing, so it always fell through to the CDN. This checks that it is there,
that it is really htmx, and that the server serves it.
"""

import hashlib
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
VENDOR = REPO / "static" / "vendor"
HTMX = VENDOR / "htmx.min.js"


class TestTheFileIsThere:
    def test_it_exists(self):
        assert HTMX.is_file(), f"{HTMX} is missing; the CDN is the fallback"

    def test_it_is_actually_htmx(self):
        source = HTMX.read_text(encoding="utf-8", errors="replace")
        assert "htmx" in source.lower()
        assert len(source) > 20_000, "too small to be the real library"

    def test_the_licence_travels_with_it(self):
        licence = VENDOR / "LICENSE-htmx.txt"
        assert licence.is_file(), "vendored code ships with its licence"
        assert "BSD 2-Clause" in licence.read_text(encoding="utf-8")

    def test_the_readme_records_where_it_came_from(self):
        readme = (VENDOR / "README.md").read_text(encoding="utf-8")
        assert "1.9.10" in readme
        assert "sha256" in readme

    def test_the_recorded_digest_matches_the_file(self):
        readme = (VENDOR / "README.md").read_text(encoding="utf-8")
        recorded = re.search(r"sha256[:\s]+([0-9a-f]{64})", readme)
        assert recorded, "the README must record the digest"
        actual = hashlib.sha256(HTMX.read_bytes()).hexdigest()
        assert actual == recorded.group(1), (
            "the vendored file does not match the digest recorded beside it")


class TestTheServerUsesIt:
    @pytest.fixture
    def server(self):
        pytest.importorskip("flask")
        from quantum.runtime.web_server import QuantumWebServer
        return QuantumWebServer()

    def test_the_local_copy_is_preferred_over_the_cdn(self, server):
        url = server._htmx_url()
        assert url == "/static/vendor/htmx.min.js"
        assert "http" not in url

    def test_it_is_actually_served(self, server):
        response = server.app.test_client().get("/static/vendor/htmx.min.js")
        assert response.status_code == 200
        assert len(response.data) > 20_000

    def test_the_injected_page_points_at_the_local_copy(self, server):
        # The page has to actually use htmx: the script is only injected for
        # pages that do (5d348f3), which is why this one carries hx-get.
        page = '<html><body><div hx-get="/x">oi</div></body></html>'
        wrapped = server._wrap_with_htmx(page, "x.q")

        assert "/static/vendor/htmx.min.js" in wrapped
        assert "unpkg.com" not in wrapped

    def test_a_page_without_htmx_still_gets_no_script(self, server):
        wrapped = server._wrap_with_htmx("<html><body>oi</body></html>", "x.q")
        assert "htmx.min.js" not in wrapped
