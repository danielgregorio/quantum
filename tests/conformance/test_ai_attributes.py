"""Conformance: the attributes of the AI tags (SPEC IA-1, IA-2, IA-4), on a model server that speaks HTTP."""

import importlib.util

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime
from tests.fake_ollama import FakeOllama

NS = 'xmlns:q="https://quantum.lang/ns"'


def run(body):
    return ComponentRuntime(config={}).execute_component(
        QuantumParser().parse(f'<q:component name="c" {NS}>{body}</q:component>'), {})


@pytest.fixture
def ollama(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    with FakeOllama() as server:
        monkeypatch.setenv('QUANTUM_LLM_BASE_URL', server.url)
        yield server


def chats(server):
    return [body for path, body in server.received if path == '/api/chat']


def test_temperature_max_tokens_and_json(ollama):
    # IA-1
    ollama.reply = '{"k": 1}'
    assert run('<q:llm name="a" model="phi3" temperature="0.2" maxTokens="7" responseFormat="json">'
               '<q:prompt>hi</q:prompt></q:llm><q:return value="{a}"/>') == {'k': 1}
    sent = chats(ollama)[-1]
    assert sent['options'] == {'temperature': 0.2, 'num_predict': 7} and sent['format'] == 'json'


def test_endpoint_sends_one_tag_to_another_server(ollama):
    # IA-1
    with FakeOllama() as other:
        other.reply = 'from the other server'
        assert run(f'<q:llm name="a" model="phi3" endpoint="{other.url}"><q:prompt>hi</q:prompt></q:llm>'
                   '<q:return value="{a}"/>') == 'from the other server'
    assert chats(ollama) == []


def test_the_task_and_the_context_of_an_agent(ollama):
    # IA-4
    ollama.reply = '{"action": "finish", "result": "done"}'
    assert run('<q:agent name="g" model="phi3" maxIterations="2"><q:instruction>x</q:instruction>'
               '<q:tool name="t" description="d"><q:function name="f"><q:return value="1"/></q:function></q:tool>'
               '<q:execute task="the task" context="the extra context"/></q:agent><q:return value="{g}"/>') == 'done'
    sent = str(chats(ollama)[0]['messages'])
    assert 'the task' in sent and 'the extra context' in sent


@pytest.mark.skipif(importlib.util.find_spec('chromadb') is None, reason='the [rag] extra is not installed')
def test_chunk_size_and_persistence(ollama, tmp_path):
    # IA-2: 300 characters in chunks of 40 are several embeddings; persist="false" writes nothing
    run(f'<q:knowledge name="kb" persist="false" chunkSize="40" chunkOverlap="5">'
        f'<q:source type="text">{"word " * 60}</q:source></q:knowledge>')
    (path, body), = [(p, b) for p, b in ollama.received if p == '/api/embed']
    assert len(body['input']) > 5
    assert not (tmp_path / '.quantum').exists()
    run('<q:knowledge name="kb2"><q:source type="text">Quantum pages are .q files.</q:source></q:knowledge>')
    assert (tmp_path / '.quantum' / 'knowledge').is_dir()


def test_model_on_a_knowledge_base_is_a_parse_error():
    # IA-2 (it was read only by the removed q:query mode="rag"; since then it did nothing)
    with pytest.raises(Exception, match=r'<q:knowledge name="docs"> model= is not supported.*q:llm'):
        QuantumParser().parse(f'<q:component name="c" {NS}><q:knowledge name="docs" model="phi3">'
                              '<q:source type="text">x</q:source></q:knowledge></q:component>')


def test_model_is_an_expression(ollama):
    # IA-1 (before: model="{m}" was sent to the server as the text "{m}")
    run('<q:set name="m" value="qwen2.5"/><q:llm name="a" model="{m}"><q:prompt>hi</q:prompt></q:llm>')
    ollama.reply = '{"action": "finish", "result": "done"}'
    run('<q:set name="m" value="mistral"/><q:agent name="g" model="{m}" maxIterations="2">'
        '<q:instruction>x</q:instruction><q:tool name="t" description="d"><q:function name="f">'
        '<q:return value="1"/></q:function></q:tool><q:execute task="hi"/></q:agent>')
    assert [body['model'] for body in chats(ollama)] == ['qwen2.5', 'mistral']


def test_a_tool_argument_the_model_leaves_out_takes_its_default(ollama):
    # IA-4 (before: default= was parsed and never applied — the body failed on the missing name)
    answers = iter(['{"action": "add", "args": {"a": "2"}}', '{"action": "finish", "result": "ok"}'])
    ollama.reply = lambda messages: next(answers)
    result = run('<q:agent name="g" model="phi3" maxIterations="3"><q:instruction>x</q:instruction>'
                 '<q:tool name="add" description="Add"><q:param name="a" type="number"/>'
                 '<q:param name="b" type="number" default="5"/><q:function name="f">'
                 '<q:return value="{a + b}"/></q:function></q:tool><q:execute task="hi"/></q:agent>'
                 '<q:return value="{g_result.actions}"/>')
    assert result[0]['result'] == 7


@pytest.mark.skipif(importlib.util.find_spec('chromadb') is None, reason='the [rag] extra is not installed')
def test_the_default_store_is_the_one_in_the_working_directory(ollama, tmp_path, monkeypatch):
    # IA-2: the same base, indexed from two directories in one process, lands
    # in each directory. ChromaDB kept one store per path string, so the
    # relative default named the first directory's store for the whole process
    # (and "Failed to get segments" once that directory was gone).
    kb = '<q:knowledge name="kb2"><q:source type="text">Quantum pages are .q files.</q:source></q:knowledge>'
    for name in ('first', 'second'):
        (tmp_path / name).mkdir()
        monkeypatch.chdir(tmp_path / name)
        run(kb)
        assert (tmp_path / name / '.quantum' / 'knowledge' / 'chroma.sqlite3').is_file(), name


@pytest.mark.skipif(importlib.util.find_spec('chromadb') is None, reason='the [rag] extra is not installed')
def test_each_base_follows_its_own_persist(ollama, tmp_path):
    # IA-2: a persist="false" base first did not make the next one in-memory.
    run('<q:knowledge name="mem" persist="false"><q:source type="text">in memory</q:source></q:knowledge>'
        '<q:knowledge name="disk"><q:source type="text">on disk</q:source></q:knowledge>')
    assert (tmp_path / '.quantum' / 'knowledge' / 'chroma.sqlite3').is_file()
