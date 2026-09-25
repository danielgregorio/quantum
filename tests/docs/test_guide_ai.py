"""docs/guide/ai.md: every AI example runs, against a stand-in model server.

The examples are run as the page shows them, with FakeOllama answering (a
real HTTP server; tests/fake_ollama.py): what they send to the model and what
they hand to the page are checked — the prompt's databinding, the JSON answer
as an object, the chat messages, retrieval, the cited sources, the agent's
tool call. The AI tags themselves are checked against a real model by
tests/live_ai. The page's **Error:** blocks are run by
test_guide_examples_run.py.
"""

import importlib.util
import re
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime
from tests.conformance.conftest import serve_pages  # noqa: F401 — the fixture
from tests.fake_ollama import FakeOllama

PAGE = Path(__file__).resolve().parents[2] / 'docs' / 'guide' / 'ai.md'
TEXT = PAGE.read_text(encoding='utf-8')
F = '`' * 3
NS = 'xmlns:q="https://quantum.lang/ns"'
needs_rag = pytest.mark.skipif(importlib.util.find_spec('chromadb') is None,
                               reason='the [rag] extra is not installed')


def block_after(marker, nth=0):
    start = TEXT.index(marker)
    return re.findall(F + r'xml\n(.*?)' + F, TEXT[start:], re.S)[nth]


@pytest.fixture
def ollama(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)                      # ./.quantum/knowledge goes here
    with FakeOllama() as server:
        monkeypatch.setenv('QUANTUM_LLM_BASE_URL', server.url)
        yield server


def run(body):
    """Runs the body as a component; returns its variables."""
    runtime = ComponentRuntime(config={})
    runtime.execute_component(QuantumParser(use_cache=False).parse(
        f'<q:component name="Doc" {NS}>{body}</q:component>'), {})
    return runtime.execution_context.get_variable


def chats(ollama):
    return [body for path, body in ollama.received if path == '/api/chat']


def test_one_model_call_with_databinding_in_the_prompt(ollama):
    ollama.reply = 'Pages, not plumbing.'
    var = run(block_after('## `q:llm` — one model call'))
    assert var('slogan') == 'Pages, not plumbing.'
    assert 'slogan for Quantum, a web framework' in str(chats(ollama)[-1]['messages'])


def test_structured_output_is_an_object(ollama):
    ollama.reply = '{"name": "Maria Souza", "age": 34}'
    var = run(block_after('### Structured output'))
    assert var('person') == {'name': 'Maria Souza', 'age': 34}


def test_chat_messages_are_the_conversation(ollama):
    ollama.reply = 'A declarative web framework.'
    var = run(block_after('### Chat messages'))
    assert var('reply') == 'A declarative web framework.'
    roles = [m['role'] for m in chats(ollama)[-1]['messages']]
    assert roles == ['system', 'user']


@needs_rag
def test_a_knowledge_base_answers_the_query_closest_first(ollama):
    knowledge = block_after('A knowledge base indexes text once')
    query = block_after('Search the chunks — the closest ones first')
    var = run(knowledge + query)
    rows = var('chunks')
    assert rows and 'port 8080' in rows[0]['content']


@needs_rag
def test_answers_cite_their_sources(ollama):
    ollama.reply = 'Pages are served on port 8080 [1].'
    docs = ('<q:knowledge name="docs" embedModel="nomic-embed-text">'
            '<q:source type="text">Quantum pages are served on port 8080 by default.</q:source>'
            '</q:knowledge><q:set name="question" value="Which port serves the pages by default?" />')
    example = block_after('### Answers that cite their sources').replace(' minRelevance="0.79"', '')
    var = run(docs + example)
    result = var('answer_result')
    assert var('answer') == 'Pages are served on port 8080 [1].'
    assert result['sources'] and {'n', 'source', 'name', 'text', 'relevance'} <= set(result['sources'][0])
    assert result['cited'] == [1] and result['grounded'] is True


@needs_rag
def test_nothing_above_min_relevance_means_the_model_is_not_asked(ollama):
    docs = ('<q:knowledge name="docs" embedModel="nomic-embed-text">'
            '<q:source type="text">Quantum pages are served on port 8080 by default.</q:source>'
            '</q:knowledge><q:set name="question" value="Best rice recipe with beans" />')
    before = len(chats(ollama))
    var = run(docs + block_after('### Answers that cite their sources'))
    assert var('answer_result')['found'] is False and not var('answer')
    assert len(chats(ollama)) == before


def test_an_agent_calls_its_tool_and_the_page_lists_the_calls(ollama):
    answers = iter(['{"action": "add", "args": {"a": 17, "b": 25}}',
                    '{"action": "finish", "result": "42"}'])
    ollama.reply = lambda messages: next(answers)
    agent = block_after('## `q:agent` — a model that uses tools')
    listing = block_after('`calc_result` says how it got there')
    var = run(agent + '<ul>' + listing + '</ul>')
    assert var('calc') == '42'
    action = var('calc_result')['actions'][0]
    assert action['call'] == 'add(a=17, b=25)' and action['result'] == 42
    assert var('calc_result')['success'] is True


@needs_rag
def test_a_streamed_answer_renders_at_once_and_a_link_opens_it(ollama, serve_pages):
    ollama.reply = 'Pages are served on port 8080 [1].'
    page = (f'<q:component name="ask" {NS}><q:knowledge name="docs" embedModel="nomic-embed-text" '
            'persist="false"><q:source type="text">Quantum pages are served on port 8080 by default.'
            '</q:source></q:knowledge><q:set name="question" value="Which port?" />'
            + block_after('### Answers that arrive as they are written') + '</q:component>')
    client = serve_pages(ask=page)
    body = client.get('/ask').get_data(as_text=True)
    link = re.search(r'<noscript>\s*<a href="([^"]+)"', body).group(1)     # "Without JavaScript, a link opens it."
    assert 'port 8080' in client.get(link).get_data(as_text=True)
