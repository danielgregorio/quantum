"""projects/kanban: boards of columns of cards, served end to end (PLAN_PLATFORMS.md, Phase 1).

The application the platforms are proven with: a database, REST services it calls and the AI tags. The
services are real HTTP servers in the test: a forge that lists a repository's issues and takes the
webhook (FakeForge, below), and a stand-in model server (tests/fake_ollama.py).
"""

import json
import logging
import re
import shutil
import sqlite3
import threading
from pathlib import Path

import pytest
from werkzeug.serving import make_server
from werkzeug.wrappers import Request, Response

from tests.apps.test_blog import page_text
from tests.fake_ollama import FakeOllama

KANBAN = Path(__file__).resolve().parents[2] / "projects" / "kanban"
needs_rag = pytest.mark.skipif(__import__("importlib").util.find_spec("chromadb") is None,
                               reason="the [rag] extra is not installed")

ISSUES = [{"number": 7, "title": "Dark mode", "body": "The site in dark colours.",
           "html_url": "https://forge.test/acme/site/issues/7"},
          {"number": 9, "title": "Search box", "body": "Search the pages by title.",
           "html_url": "https://forge.test/acme/site/issues/9"}]


class FakeForge:
    """A forge's issues API (GitHub's shape) and a webhook, over real HTTP; keeps what it received."""

    def __init__(self):
        self.issues = list(ISSUES)
        self.received = []                   # (method, path, query, headers, json body)
        self.server = make_server("127.0.0.1", 0, self.app, threaded=True)
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()

    def hooks(self):
        return [body for method, path, _, _, body in self.received if path == "/hook"]

    @Request.application
    def app(self, request):
        body = json.loads(request.data) if request.data else None
        self.received.append((request.method, request.path, dict(request.args), dict(request.headers), body))
        if request.path == "/repos/acme/site/issues":
            return Response(json.dumps(self.issues), content_type="application/json")
        if request.path == "/hook":
            return Response("{}", content_type="application/json")
        return Response('{"message": "Not Found"}', status=404, content_type="application/json")


@pytest.fixture
def forge():
    with FakeForge() as server:
        yield server


@pytest.fixture
def model():
    with FakeOllama() as server:
        yield server


@pytest.fixture
def app(tmp_path, monkeypatch, model):
    project = tmp_path / "kanban"
    shutil.copytree(KANBAN, project, ignore=shutil.ignore_patterns("data", ".quantum", "__pycache__"))
    monkeypatch.chdir(project)
    monkeypatch.setenv("QUANTUM_LLM_BASE_URL", model.url)
    from quantum.cli.migrations import MigrationRunner
    assert [r["status"] for r in MigrationRunner(project).up()] == ["applied"]
    from quantum.runtime.web_server import QuantumWebServer
    logging.disable(logging.WARNING)
    flask_app = QuantumWebServer(str(project / "quantum.config.yaml")).app
    flask_app.config["TESTING"] = True
    yield flask_app, project
    logging.disable(logging.NOTSET)


def signed_in(app, who):
    client = app[0].test_client()
    response = client.post("/login", data={"action": "signIn", "email": f"{who}@example.com",
                                           "password": "kanban-demo"})
    assert response.status_code == 302 and response.headers["Location"] == "/"
    return client


def rows(project, sql, *args):
    return sqlite3.connect(project / "data" / "kanban.db").execute(sql, args).fetchall()


def card(project, title):
    (row,) = rows(project, "SELECT id, column_id, started_on, done_on, archived FROM cards WHERE title = ?", title)
    return dict(zip(("id", "column", "started", "done", "archived"), row))


def column(project, name, board=1):
    return rows(project, "SELECT id FROM columns WHERE board_id = ? AND name = ?", board, name)[0][0]


def test_signing_in_and_the_boards_one_belongs_to(app):
    client = app[0].test_client()
    response = client.get("/")
    assert response.status_code == 302 and response.headers["Location"].startswith("/login")
    wrong = client.post("/login", data={"action": "signIn", "email": "bruno@example.com", "password": "nope"})
    assert wrong.headers["Location"] == "/login"
    assert "Wrong e-mail or password." in page_text(client.get("/login"))
    page = page_text(signed_in(app, "bruno").get("/"))
    assert "Bruno (member)" in page and "Website launch" in page and "6 cards" in page and "late" in page
    assert "New board" not in page                                 # only an admin makes boards


def test_an_admin_makes_a_board_with_its_columns(app):
    client, project = signed_in(app, "ana"), app[1]
    response = client.post("/", data={"action": "createBoard", "name": "Mobile app", "description": "v1"})
    assert response.status_code == 302 and response.headers["Location"] == "/board/2"
    assert rows(project, "SELECT name, wip_limit, is_done FROM columns WHERE board_id = 2 ORDER BY position") == [
        ("To do", None, 0), ("Doing", 3, 0), ("Done", None, 1)]
    assert rows(project, "SELECT user_id FROM members WHERE board_id = 2") == [(1,)]
    assert "Board created: Mobile app" in page_text(client.get("/board/2"))
    member = signed_in(app, "bruno")
    assert member.post("/", data={"action": "createBoard", "name": "Mine"}).status_code == 403
    assert "There is no board #2 that you belong to." in page_text(member.get("/board/2"))


def test_a_card_is_added_moved_and_done_and_the_webhook_is_told(app, forge):
    project = app[1]
    sqlite3.connect(project / "data" / "kanban.db").execute(
        "UPDATE boards SET webhook_url = ? WHERE id = 1", (forge.url + "/hook",)).connection.commit()
    client = signed_in(app, "bruno")
    added = client.post("/board/1", data={"action": "addCard", "title": "Write the FAQ"})
    assert added.headers["Location"] == "/board/1"
    assert "Card added: Write the FAQ" in page_text(client.get("/board/1"))
    faq = card(project, "Write the FAQ")
    assert faq["column"] == column(project, "To do") and faq["started"] is None

    client.post("/board/1", data={"action": "move", "card": faq["id"], "to": column(project, "Review")})
    faq = card(project, "Write the FAQ")
    assert faq["column"] == column(project, "Review") and faq["started"] and faq["done"] is None
    assert forge.hooks() == []
    client.post("/board/1", data={"action": "move", "card": faq["id"], "to": column(project, "Done")})
    done = card(project, "Write the FAQ")
    assert done["done"] and done["started"] == faq["started"]
    assert forge.hooks() == [{"event": "card.done", "board": "Website launch", "card": faq["id"],
                              "title": "Write the FAQ", "by": "Bruno"}]
    page = page_text(client.get("/board/1?tab=Flow"))
    assert "Done: 2, in" in page and "Write the FAQ Bruno" not in page    # nobody has it
    assert re.search(r"Write the FAQ\s+\d{4}-\d\d-\d\d \d{4}-\d\d-\d\d 0\.0", page)

    back = client.post("/board/1", data={"action": "move", "card": faq["id"], "to": column(project, "To do")})
    assert back.status_code == 302
    again = card(project, "Write the FAQ")
    assert again["started"] is None and again["done"] is None     # back to the start: not started, not done


def test_a_webhook_that_fails_does_not_stop_the_move(app):
    project = app[1]
    sqlite3.connect(project / "data" / "kanban.db").execute(
        "UPDATE boards SET webhook_url = 'http://127.0.0.1:9/hook' WHERE id = 1").connection.commit()
    client = signed_in(app, "bruno")
    contact = card(project, "Contact form")
    response = client.post("/board/1", data={"action": "move", "card": contact["id"], "to": column(project, "Done")})
    assert response.status_code == 302 and card(project, "Contact form")["done"]


def test_a_column_says_when_it_is_over_its_limit(app):
    project = app[1]
    client = signed_in(app, "bruno")
    doing = column(project, "Doing")
    first = client.post("/board/1", data={"action": "move", "card": card(project, "Choose the fonts")["id"], "to": doing})
    assert "over its limit" not in page_text(client.get(first.headers["Location"]))       # 3 of 3
    client.post("/board/1", data={"action": "move", "card": card(project, "Write the about page")["id"], "to": doing})
    page = page_text(client.get("/board/1"))
    assert "Doing holds 4 cards, over its limit of 3." in page and "Doing 4/3" in page and "over the limit" in page


def test_moving_to_a_column_of_another_board_is_refused(app):
    project = app[1]
    signed_in(app, "ana").post("/", data={"action": "createBoard", "name": "Mobile app"})
    client = signed_in(app, "bruno")
    fonts = card(project, "Choose the fonts")
    client.post("/board/1", data={"action": "move", "card": fonts["id"], "to": column(project, "Doing", board=2)})
    assert card(project, "Choose the fonts")["column"] == fonts["column"]
    assert "That column is not on this board." in page_text(client.get("/board/1"))


def test_a_viewer_looks_and_changes_nothing(app):
    project = app[1]
    client = signed_in(app, "carla")
    page = page_text(client.get("/board/1"))
    assert "Carla (viewer)" in page and "Home page copy" in page
    assert "Add a card" not in page and "◀" not in page and "▶" not in page
    fonts = card(project, "Choose the fonts")
    for data in ({"action": "addCard", "title": "Sneaky"},
                 {"action": "move", "card": fonts["id"], "to": column(project, "Done")}):
        assert client.post("/board/1", data=data).status_code == 403
    assert card(project, "Choose the fonts") == fonts and not rows(project, "SELECT 1 FROM cards WHERE title = 'Sneaky'")
    assert client.post(f"/card/{fonts['id']}", data={"action": "archive"}).status_code == 403


def test_the_filters_by_who_by_label_and_by_due_date(app):
    project = app[1]
    db = sqlite3.connect(project / "data" / "kanban.db")
    db.execute("UPDATE cards SET due_on = date('now', '+3 days') WHERE title = 'Choose the fonts'")
    db.commit()
    client = signed_in(app, "bruno")
    ana = page_text(client.get("/board/1?who=Ana"))
    assert "Set up the domain" in ana and "Contact form" not in ana and "filtered: Ana" in ana
    design = page_text(client.get("/board/1?label=design"))
    assert "Choose the fonts" in design and "Logo" in design and "Contact form" not in design
    late = page_text(client.get("/board/1?due=late")).split(" Summary ")[0]      # the Board tab
    assert "Set up the domain" in late and "Choose the fonts" not in late and "Logo" not in late   # Logo is done
    week = page_text(client.get("/board/1?due=week")).split(" Summary ")[0]
    assert "Choose the fonts" in week and "Set up the domain" not in week


def test_a_card_is_edited_and_its_history_kept(app):
    project = app[1]
    client = signed_in(app, "bruno")
    about = card(project, "Write the about page")
    url = f"/card/{about['id']}"
    saved = client.post(url, data={"action": "save", "title": "Write the about page", "description": "Two paragraphs.",
                                   "assignee": "1", "due_on": "2026-12-01", "labels": "content, copy"})
    assert saved.headers["Location"] == url
    page = page_text(client.get(url))
    assert "Saved." in page
    assert rows(project, "SELECT assignee_id, due_on, labels FROM cards WHERE id = ?", about["id"]) == [
        (1, "2026-12-01", "content, copy")]
    assert re.search(r"Bruno save .*assignee_id: 2 → 1", page) and "due_on: 2026-11-02 → 2026-12-01" in page

    refused = client.post(url, data={"action": "save", "title": "No", "labels": "Bad!"})
    assert refused.status_code in (302, 422)
    assert rows(project, "SELECT title FROM cards WHERE id = ?", about["id"]) == [("Write the about page",)]

    client.post(url, data={"action": "archive"})
    assert card(project, "Write the about page")["archived"] == 1
    assert "Write the about page" not in page_text(client.get("/board/1"))
    assert client.post(url, data={"action": "remove"}).status_code == 403          # only an admin deletes
    signed_in(app, "ana").post(url, data={"action": "remove"})
    assert not rows(project, "SELECT 1 FROM cards WHERE id = ?", about["id"])


def test_issues_are_imported_once(app, forge):
    project = app[1]
    admin = signed_in(app, "ana")
    admin.post("/board/1", data={"action": "saveSettings", "webhook_url": "", "issues_api": forge.url})
    assert rows(project, "SELECT issues_api FROM boards WHERE id = 1") == [(forge.url,)]
    client = signed_in(app, "bruno")
    client.post("/board/1", data={"action": "importIssues", "repository": "acme/site"})
    assert "2 issues of acme/site imported." in page_text(client.get("/board/1"))
    (method, _, query, headers, _), = [r for r in forge.received if r[1].endswith("/issues")]
    assert method == "GET" and query == {"state": "open", "per_page": "20"}
    assert headers["Accept"] == "application/vnd.github+json"
    assert rows(project, "SELECT title, labels, source FROM cards WHERE source IS NOT NULL ORDER BY id") == [
        ("Dark mode", "issue", "https://forge.test/acme/site/issues/7"),
        ("Search box", "issue", "https://forge.test/acme/site/issues/9")]
    client.post("/board/1", data={"action": "importIssues", "repository": "acme/site"})
    assert "0 issues of acme/site imported." in page_text(client.get("/board/1"))
    client.post("/board/1", data={"action": "importIssues", "repository": "acme/gone"})
    assert "Could not read acme/gone" in page_text(client.get("/board/1?tab=Settings"))


def test_the_ai_splits_a_card_into_subtasks(app, model):
    project = app[1]
    model.reply = '{"subtasks": ["Pick the photo", "Write who we are", "Ask Ana to review"]}'
    client = signed_in(app, "bruno")
    about = card(project, "Write the about page")
    client.post(f"/card/{about['id']}", data={"action": "split"})
    assert "3 subtasks of Write the about page added." in page_text(client.get("/board/1"))
    assert rows(project, "SELECT title FROM cards WHERE labels = 'subtask' ORDER BY id") == [
        ("Pick the photo",), ("Write who we are",), ("Ask Ana to review",)]
    sent = [body for path, body in model.received if path == "/api/chat"][-1]
    assert "Write the about page" in str(sent["messages"]) and sent.get("format") == "json"


def test_without_a_model_the_card_page_says_so(app, model):
    model.fail["/api/chat"] = (500, "model not loaded")
    project = app[1]
    client = signed_in(app, "bruno")
    about = card(project, "Write the about page")
    client.post(f"/card/{about['id']}", data={"action": "split"})
    assert "The AI did not answer:" in page_text(client.get(f"/card/{about['id']}"))
    assert not rows(project, "SELECT 1 FROM cards WHERE labels = 'subtask'")


def test_the_summary_is_written_as_it_is_read(app, model):
    model.reply = "One card is done; three are in progress; the domain is late."
    client = signed_in(app, "bruno")
    html = client.get("/board/1?tab=Ask&summary=1").get_data(as_text=True)
    link = re.search(r'<noscript>\s*<a href="([^"]+)"', html).group(1)
    assert "the domain is late" in client.get(link).get_data(as_text=True)
    sent = [body for path, body in model.received if path == "/api/chat"][-1]
    assert sent["stream"] is True and "Set up the domain" in str(sent["messages"])


@needs_rag
def test_the_board_answers_from_its_own_cards(app, model):
    signed_in(app, "ana").post("/", data={"action": "createBoard", "name": "Mobile app"})
    project = app[1]
    db = sqlite3.connect(project / "data" / "kanban.db")
    db.execute("INSERT INTO cards (board_id, column_id, title, description) VALUES (2, ?, 'Domain for the app', "
               "'Buy the domain of the mobile app.')", (column(project, "To do", board=2),))
    db.commit()
    model.reply = "Ana has the domain, and it is late [1]."
    client = signed_in(app, "bruno")
    asked = client.post("/board/1", data={"action": "ask", "question": "Who has the domain?"})
    assert asked.headers["Location"] == "/board/1?tab=Ask&q=Who+has+the+domain%3F"
    page = page_text(client.get(asked.headers["Location"]))
    assert "Ana has the domain, and it is late [1]." in page
    assert re.search(r"\[\d\] #3 Set up the domain \(Doing, Ana, due 2026-10-20\)", page)   # where it comes from
    assert "Domain for the app" not in page                       # board 2's cards are board 2's


def test_the_agent_says_what_is_late_and_who_has_it(app, model):
    answers = iter(['{"action": "late_cards", "args": {}}',
                    '{"action": "finish", "result": "Set up the domain is late; Ana has it."}'])
    model.reply = lambda messages: next(answers)
    page = page_text(signed_in(app, "bruno").get("/board/1?tab=Ask&late=1"))
    assert "Set up the domain is late; Ana has it." in page and "late_cards()" in page
    chats = [body for path, body in model.received if path == "/api/chat"]
    assert "Set up the domain" in str(chats[-1]["messages"]) and "Ana" in str(chats[-1]["messages"])


def test_an_admin_edits_the_columns_in_their_table(app):
    project = app[1]
    from quantum.runtime.ui_table_edit import signature_on_page
    admin = signed_in(app, "ana")
    page = admin.get("/board/1?tab=Settings").get_data(as_text=True)
    doing = column(project, "Doing")
    signature = signature_on_page(page, "columns", "wip_limit", str(doing))
    assert signature
    admin.post("/board/1", data={"action": "__edit", "__table": "columns", "__column": "wip_limit",
                                 "__key": str(doing), "value": "5", "__sig": signature},
               headers={"Referer": "/board/1?tab=Settings"})
    assert rows(project, "SELECT wip_limit FROM columns WHERE id = ?", doing) == [(5,)]
    assert "Doing 2/5" in page_text(admin.get("/board/1"))


def test_a_member_cannot_edit_the_columns_the_page_shows_only_to_an_admin(app):
    project = app[1]
    member = signed_in(app, "bruno")
    assert 'name="__table"' not in member.get("/board/1?tab=Settings").get_data(as_text=True)
    doing = column(project, "Doing")
    response = member.post("/board/1", data={"action": "__edit", "__table": "columns", "__column": "wip_limit",
                                             "__key": str(doing), "value": "99"})
    assert response.status_code == 403
    assert rows(project, "SELECT wip_limit FROM columns WHERE id = ?", doing) == [(3,)]
