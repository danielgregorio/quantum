"""projects/docs-assistant without a model server: the page says what is wrong (IA-5).

The answers themselves are tested against a real model in tests/live_ai (D6).
"""

import html
import re
import shutil
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "projects" / "docs-assistant"


@pytest.fixture
def client(tmp_path, monkeypatch):
    # docs/guide is read relative to the app, as in the repository
    root = tmp_path / "repo"
    shutil.copytree(APP, root / "projects" / "docs-assistant", ignore=shutil.ignore_patterns(".quantum"))
    shutil.copytree(APP.parents[1] / "docs" / "guide", root / "docs" / "guide")
    monkeypatch.chdir(root / "projects" / "docs-assistant")
    monkeypatch.setenv("QUANTUM_LLM_BASE_URL", "http://127.0.0.1:9")
    from quantum.runtime.web_server import QuantumWebServer
    return QuantumWebServer("quantum.config.yaml").app.test_client()


def text(response):
    body = response.get_data(as_text=True).split("<body", 1)[1]
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body)))


def test_without_a_model_server_the_page_says_so(client):
    # IA-5
    response = client.get("/?q=How+do+I+paginate")
    assert response.status_code == 200
    assert "The guide could not be indexed:" in text(response)


def test_asking_goes_to_the_url(client):
    # IA-5 + EXPR-12: the question travels in the URL, encoded
    response = client.post("/", data={"action": "ask", "question": "What is a guard & why?"})
    assert response.status_code == 302 and response.headers["Location"] == "/?q=What+is+a+guard+%26+why%3F"
    client.post("/", data={"action": "ask", "question": "x"}, headers={"Referer": "http://localhost/"})
    assert "Must be at least 3 characters" in text(client.get("/"))
