"""projects/shop-agent: a q:agent over SQLite, served end to end.

The model is a scripted stand-in for Ollama, so CI checks the whole chain —
the model asks for a tool, the tool's query runs on the app's database, its
rows go back to the model, the page shows the answer and the calls. What a
real model makes of it is tested in tests/live_ai (D6).
"""

import json
import logging
import shutil
import threading
from pathlib import Path

import pytest
from werkzeug.serving import make_server
from werkzeug.wrappers import Request, Response

from tests.apps.test_blog import page_text

SHOP = Path(__file__).resolve().parents[2] / "projects" / "shop-agent"


class ScriptedModel:
    """Answers /api/chat with the next reply of a script; keeps what it was sent."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.received = []
        self.server = make_server("127.0.0.1", 0, self.app, threaded=True)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    @Request.application
    def app(self, request):
        self.received.append(json.loads(request.data)["messages"])
        content = self.replies.pop(0) if self.replies else '{"action": "finish", "result": "done"}'
        return Response(json.dumps({"model": "phi3", "message": {"role": "assistant", "content": content},
                                    "done": True}), content_type="application/json")


@pytest.fixture
def shop(tmp_path, monkeypatch):
    project = tmp_path / "shop"
    shutil.copytree(SHOP, project, ignore=shutil.ignore_patterns("data", "__pycache__"))
    monkeypatch.chdir(project)
    from quantum.cli.migrations import MigrationRunner
    assert [r["status"] for r in MigrationRunner(project).up()] == ["applied"]
    logging.disable(logging.WARNING)
    yield project
    logging.disable(logging.NOTSET)


def client_for(project, monkeypatch, base_url):
    monkeypatch.setenv("QUANTUM_LLM_BASE_URL", base_url)
    from quantum.runtime.web_server import QuantumWebServer
    return QuantumWebServer(str(project / "quantum.config.yaml")).app.test_client()


def test_the_agent_answers_from_the_database(shop, monkeypatch):
    # IA-4: the tool's query runs on the app's database and its rows reach the model
    model = ScriptedModel(['{"action": "low_stock", "args": {"below": "5"}}',
                           '{"action": "finish", "result": "Three products are almost out."}'])
    try:
        page = page_text(client_for(shop, monkeypatch, model.url).get("/?q=Which+products+are+almost+out%3F"))
    finally:
        model.server.shutdown()
    assert "Three products are almost out." in page
    assert "low_stock(below=5): 3 rows" in page
    tool_result = model.received[1][-1]["content"]
    assert "Paper filters (100)" in tool_result and "Pour-over kettle" in tool_result
    assert "Decaf beans 500g" in tool_result and "Hand grinder" not in tool_result


def test_without_a_model_server_the_page_says_so(shop, monkeypatch):
    # IA-5
    response = client_for(shop, monkeypatch, "http://127.0.0.1:9").get("/?q=How+many+open+orders%3F")
    assert response.status_code == 200
    assert "The agent could not answer:" in page_text(response) and "Cannot connect" in page_text(response)


def test_asking_goes_to_the_url(shop, monkeypatch):
    # EXPR-12
    response = client_for(shop, monkeypatch, "http://127.0.0.1:9").post(
        "/", data={"action": "ask", "question": "Orders of Ana & Bruno?"})
    assert response.status_code == 302 and response.headers["Location"] == "/?q=Orders+of+Ana+%26+Bruno%3F"
