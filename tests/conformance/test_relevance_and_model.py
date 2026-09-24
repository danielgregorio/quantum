"""Conformance: answers only from relevant chunks (SPEC IA-9), the removed
q:query mode="rag" (IA-3) and where the model comes from (IA-1).

A model server that speaks HTTP (tests/fake_ollama.py) stands in for Ollama:
its embeddings are a bag of words, so a question shares words with the chunk
that answers it and none with the others. Measured with DOCS below: the chunk
about pagination scores 0.75 for "pagination rows", a chunk that shares no word
with the question 0.5.
"""

import importlib.util
import uuid

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime
from tests.fake_ollama import FakeOllama

NS = 'xmlns:q="https://quantum.lang/ns"'

DOCS = ['Pagination: q:query paginate="true" pageSize="10" splits the rows into pages.',
        'Sessions keep values between requests of the same visitor.',
        'A knowledge base answers questions from documents.']

needs_chromadb = pytest.mark.skipif(importlib.util.find_spec('chromadb') is None,
                                    reason='the [rag] extra is not installed')


@pytest.fixture
def ollama(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('QUANTUM_LLM_DEFAULT_MODEL', raising=False)
    with FakeOllama() as server:
        monkeypatch.setenv('QUANTUM_LLM_BASE_URL', server.url)
        yield server


def run(body, config=None):
    return ComponentRuntime(config=config if config is not None else {}).execute_component(
        QuantumParser().parse(f'<q:component name="c" {NS}>{body}</q:component>'), {})


def ask(question, attrs=''):
    kb = f'kb{uuid.uuid4().hex[:8]}'
    return (f'<q:knowledge name="{kb}" persist="false">'
            + ''.join(f'<q:source type="text">{d}</q:source>' for d in DOCS) +
            f'</q:knowledge><q:llm name="answer" model="phi3" knowledge="{kb}" top="3" {attrs}>'
            f'<q:message role="user">{question}</q:message></q:llm>'
            '<q:return value="{answer_result}"/>')


def chats(ollama):
    return [body for path, body in ollama.received if path == '/api/chat']


# ------------------------------------------------------------------ IA-9

@needs_chromadb
def test_chunks_below_min_relevance_are_not_retrieved(ollama):
    # IA-9: without the floor, top="3" sent all three chunks, related or not
    ollama.reply = 'Use paginate [1].'
    result = run(ask('pagination rows', 'minRelevance="0.6"'))
    assert [s['n'] for s in result['sources']] == [1]
    assert 'Pagination' in result['sources'][0]['text'] and result['sources'][0]['relevance'] >= 0.6
    grounding = chats(ollama)[-1]['messages'][0]['content']
    assert 'Pagination' in grounding and 'Sessions' not in grounding


@needs_chromadb
def test_when_no_chunk_is_relevant_enough_the_model_is_not_asked(ollama):
    # IA-9: found was false only on an EMPTY base; this question used to get three unrelated chunks
    result = run(ask('weather in paris', 'minRelevance="0.6"'))
    assert result['found'] is False and result['sources'] == [] and result['response'] == ''
    assert result['grounded'] is False
    assert chats(ollama) == []


@needs_chromadb
def test_without_min_relevance_the_top_chunks_are_retrieved(ollama):
    # IA-9: minRelevance is 0 when not declared — IA-6 as before
    result = run(ask('weather in paris'))
    assert len(result['sources']) == 3 and result['found'] is True


@needs_chromadb
def test_an_answer_that_cites_no_source_is_not_grounded(ollama):
    # IA-9
    ollama.reply = 'Use paginate [1].'
    assert run(ask('pagination rows'))['grounded'] is True
    ollama.reply = 'I believe you use paginate.'
    result = run(ask('pagination rows'))
    assert result['cited'] == [] and result['grounded'] is False


@pytest.mark.parametrize('value', ['1.5', '-0.1', 'high'])
def test_min_relevance_is_between_0_and_1(value):
    # IA-9
    with pytest.raises(Exception, match=rf'minRelevance="{value}".*between 0 and 1'):
        QuantumParser().parse(f'<q:component name="c" {NS}><q:llm name="a" knowledge="docs" '
                              f'minRelevance="{value}"><q:prompt>x</q:prompt></q:llm></q:component>')


# ------------------------------------------------------------------ IA-3

def test_query_mode_rag_is_a_parse_error_that_points_to_q_llm():
    # IA-3
    with pytest.raises(Exception, match=r'mode="rag" was removed .*<q:llm name="answer" knowledge="docs">'):
        QuantumParser().parse(
            f'<q:component name="c" {NS}><q:query name="answer" datasource="knowledge:docs" mode="rag">'
            'SELECT answer FROM knowledge WHERE question = :q<q:param name="q" value="x"/>'
            '</q:query></q:component>')


# ------------------------------------------------------------------ IA-1: the model

LLM = '<q:llm name="a"><q:prompt>hi</q:prompt></q:llm><q:return value="{a}"/>'
AGENT = ('<q:agent name="helper" maxIterations="1" onerror="continue">'
         '<q:instruction>Answer.</q:instruction>'
         '<q:tool name="one" description="Returns one"><q:function name="f"><q:return value="1"/></q:function></q:tool>'
         '<q:execute task="hi"/></q:agent>')


def test_an_llm_without_model_uses_llm_model_from_the_config(ollama):
    # IA-1: it was `node.model or 'phi3'` — the configuration never reached the tag
    run(LLM, {'llm': {'model': 'qwen2.5'}})
    assert ollama.received[-1][1]['model'] == 'qwen2.5'


def test_the_environment_wins_over_the_config(ollama, monkeypatch):
    # IA-1
    monkeypatch.setenv('QUANTUM_LLM_DEFAULT_MODEL', 'mistral')
    run(LLM, {'llm': {'model': 'qwen2.5'}})
    assert ollama.received[-1][1]['model'] == 'mistral'


def test_the_declared_model_wins_over_both(ollama, monkeypatch):
    # IA-1
    monkeypatch.setenv('QUANTUM_LLM_DEFAULT_MODEL', 'mistral')
    run(LLM.replace('name="a"', 'name="a" model="llama3"'), {'llm': {'model': 'qwen2.5'}})
    assert ollama.received[-1][1]['model'] == 'llama3'


def test_an_agent_without_model_uses_the_configured_one(ollama):
    # IA-1: the agent parser defaulted to 'phi3'
    run(AGENT, {'llm': {'model': 'qwen2.5'}})
    assert {body.get('model') for path, body in ollama.received if path == '/api/chat'} == {'qwen2.5'}


def test_without_any_model_the_error_says_what_to_configure(ollama):
    # IA-1, IA-5
    with pytest.raises(Exception, match=r'<q:llm name="a"> names no model .*llm\.model.*'
                                        r'QUANTUM_LLM_DEFAULT_MODEL.*onerror="continue"'):
        run(LLM)
    assert ollama.received == []
    result = run(AGENT + '<q:return value="{helper_result.error.message}"/>')
    assert 'names no model' in result and ollama.received == []
