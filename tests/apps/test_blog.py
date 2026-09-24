"""projects/blog, end to end: migrations, the real server, a person browsing.

The blog was broken for months without anyone seeing — every page was a 500 —
because its only test checked that the file existed and parsed.

What a visitor and the author do — posts, comments, search, pagination, the
first admin account, signing in and out, writing and deleting posts — is
tested in the blog's own language, in projects/blog/tests/*.test.q and
components/admin/index.test.q, run by `quantum test`
(tests/apps/test_app_suites.py). What stays here is what those tests cannot
see: the HTML of forms and links, and a post long enough to take minutes to
read.
"""

import logging
import re
import shutil
import sqlite3
from html import unescape
from pathlib import Path

import pytest

BLOG = Path(__file__).resolve().parents[2] / "projects" / "blog"
PASSWORD = "a-long-test-password"


def page_text(response):
    html = re.sub(r"<(style|script)\b.*?</\1>", "", response.get_data(as_text=True), flags=re.S)
    page = unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)))
    # An expression that does not resolve stays as text (EXPR-4): on a page, that is a defect.
    raw = re.findall(r"\{[^{}]*\}", page) + re.findall(r'="[^"]*(\{[^"{}]*\})[^"]*"', html)
    assert not raw, f"unresolved expressions: {raw[:5]}"
    return page


@pytest.fixture
def blog(tmp_path, monkeypatch):
    project = tmp_path / "blog"
    shutil.copytree(BLOG, project, ignore=shutil.ignore_patterns("data", "logs", "__pycache__"))
    monkeypatch.chdir(project)   # the datasource is ./data/blog.db, relative to the server's folder

    from quantum.cli.migrations import MigrationRunner
    results = MigrationRunner(project).up()
    assert [r["status"] for r in results] == ["applied", "applied"], results

    from quantum.runtime.web_server import QuantumWebServer
    logging.disable(logging.WARNING)
    app = QuantumWebServer(str(project / "quantum.config.yaml")).app
    app.config["TESTING"] = True
    yield app.test_client(), project / "data" / "blog.db"
    logging.disable(logging.NOTSET)


def sign_in(client):
    client.post("/login", data={"action": "setup", "username": "ana", "display_name": "Ana",
                                "password": PASSWORD, "password2": PASSWORD})
    r = client.post("/login", data={"action": "signIn", "username": "ana", "password": PASSWORD})
    assert r.status_code == 302 and r.headers["Location"].endswith("/admin"), r.get_data(as_text=True)[:500]


class TestAuthor:
    def test_the_reading_time_comes_from_the_words(self, blog):
        client, db_path = blog
        sign_in(client)
        client.post("/admin/new", data={"action": "create", "title": "A long one",
                                        "excerpt": "A summary long enough", "tag_id": "2",
                                        "content": "word " * 450, "publish": "on"})
        db = sqlite3.connect(db_path)
        assert db.execute("select reading_time from posts where title = 'A long one'").fetchone() == (3,)
        stored_hash = db.execute("select password_hash from users").fetchone()[0]
        assert PASSWORD not in stored_hash

    def test_the_edit_form_comes_filled_in(self, blog):
        client, _ = blog
        sign_in(client)
        html = client.get("/admin/edit/3").get_data(as_text=True)
        page_text(client.get("/admin/edit/3"))
        assert 'value="Pages are files"' in html
        assert re.search(r'<option value="3" selected="selected">\s*Tutorial', html)
        assert "Post not found" in page_text(client.get("/admin/edit/99"))


class TestPagination:
    def test_the_pager_links_keep_the_filter(self, blog):
        client, db_path = blog
        db = sqlite3.connect(db_path)
        for n in range(10):   # 13 published; 11 of them tutorials
            db.execute("insert into posts (title, slug, excerpt, content, tag_id, is_published, published_at) "
                       "values (?, ?, 'summary', 'text', 3, 1, ?)", (f"Extra {n}", f"extra-{n}", f"2026-08-{n + 1:02d}"))
        db.commit()
        # UI-11: the <ui:pager> (pagination used to be done by hand, with LIMIT/OFFSET and a count)
        first = client.get("/").get_data(as_text=True)
        assert 'aria-current="page"' in first and 'href="/?page=2"' in first
        assert 'href="/?page=0"' not in first
        assert 'href="/?page=1"' in client.get("/?page=2").get_data(as_text=True)
        assert 'href="/?tag=tutorial&amp;page=2"' in client.get("/?tag=tutorial").get_data(as_text=True)
